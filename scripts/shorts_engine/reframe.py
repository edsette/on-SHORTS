"""Enquadramento para o formato de saída.

smart: crop vertical que segue o centro do movimento (diferença entre frames a 4 fps, 192 px de largura),
       suavizado por média móvel e com saltos apenas em cortes de cena (sem "tremidos").
blur:  vídeo completo centrado sobre uma cópia ampliada e desfocada (sem perder informação).
"""

from __future__ import annotations

import subprocess

import numpy as np

AW, AH = 192, 108  # resolução de análise


def _decode_gray(src: str, start: float, dur: float, fps: int = 4) -> np.ndarray:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
           "-i", src, "-vf", f"fps={fps},scale={AW}:{AH},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (AW * AH)
    return np.frombuffer(raw[: n * AW * AH], dtype=np.uint8).reshape(n, AH, AW).astype(np.float32)


def motion_centers(src: str, start: float, dur: float, scene_times: list[float], fps: int = 4,
                   max_offset: float = 0.12, smooth_s: float = 4.0) -> list[tuple[float, float]]:
    """Devolve keyframes (t relativo, centro x normalizado 0-1).

    Modo gameplay: em jogos na 3.ª pessoa a personagem está perto do centro e quase tudo o resto
    (câmara, folhagem, trânsito) também se move. Por isso o centro de movimento só desloca o crop até
    `max_offset` (fração da largura) a partir do centro, com suavização longa. max_offset=0.5 = livre."""
    frames = _decode_gray(src, start, dur, fps)
    if len(frames) < 3:
        return [(0.0, 0.5)]
    diffs = np.abs(np.diff(frames, axis=0))
    diffs[:, : int(AH * 0.08), :] = 0      # ignora faixas de HUD/legenda no topo
    diffs[:, -int(AH * 0.12):, :] = 0      # e no fundo
    col = diffs.sum(axis=1)                # (n-1, AW)
    xs = np.arange(AW) + 0.5
    centers = []
    for c in col:
        tot = c.sum()
        if tot < 2000:                      # quase sem movimento: centro
            centers.append(np.nan)
        else:
            w = np.maximum(c - np.percentile(c, 60), 0)  # só as colunas com movimento acima do fundo
            centers.append(float((w * xs).sum() / w.sum() / AW) if w.sum() > 0 else np.nan)
    centers = np.array(centers)
    times = (np.arange(len(centers)) + 1) / fps

    # segmentar por cortes de cena e suavizar dentro de cada cena
    cuts = [0.0] + [t - start for t in scene_times if start < t < start + dur] + [dur + 1]
    out: list[tuple[float, float]] = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        m = (times >= a) & (times < b)
        seg = centers[m]
        if not len(seg):
            continue
        fill = np.nanmedian(seg) if np.isfinite(seg).any() else 0.5
        seg = np.where(np.isfinite(seg), seg, fill)
        seg = 0.5 + np.clip(seg - 0.5, -max_offset, max_offset)
        k = min(len(seg), int(smooth_s * fps) | 1)  # janela de suavização (ímpar)
        sm = np.convolve(np.pad(seg, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        ts = times[m]
        if out:
            out.append((max(a, out[-1][0] + 0.001), float(sm[0])))  # salto seco no corte
        for t, x in zip(ts[:: fps], sm[:: fps]):                    # 1 keyframe por segundo
            out.append((float(t), float(x)))
    return out or [(0.0, 0.5)]


def x_expr(keys: list[tuple[float, float]], src_w: int, crop_w: int) -> str:
    """Expressão FFmpeg (função de t) com interpolação linear entre keyframes, já em píxeis."""
    def px(cx: float) -> float:
        return float(np.clip(cx * src_w - crop_w / 2, 0, src_w - crop_w))

    keys = sorted(keys)
    # reduzir keyframes quase iguais
    red = [keys[0]]
    for t, x in keys[1:]:
        if abs(px(x) - px(red[-1][1])) > 6 or t - red[-1][0] < 0.01:
            red.append((t, x))
    if len(red) == 1:
        return f"{px(red[0][1]):.1f}"
    expr = f"{px(red[-1][1]):.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(red[:-1], red[1:]))):
        a, b = px(x0), px(x1)
        seg = f"{a:.1f}+({b - a:.1f})*(t-{t0:.3f})/{max(t1 - t0, 0.001):.3f}"
        expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"
    return f"if(lt(t,{red[0][0]:.3f}),{px(red[0][1]):.1f},{expr})"


def video_chain(mode: str, src_w: int, src_h: int, out_w: int, out_h: int, keys=None) -> tuple[str, dict]:
    """Cadeia de filtros para um input. Devolve (cadeia, info). Usa rótulos {IN} e {OUT}."""
    src_ar, out_ar = src_w / src_h, out_w / out_h
    if mode == "smart" and src_ar > out_ar + 0.01:
        crop_w = int(round(src_h * out_ar / 2) * 2)
        x = x_expr(keys or [(0.0, 0.5)], src_w, crop_w)
        chain = (f"{{IN}}crop=w={crop_w}:h={src_h}:x='{x}':y=0,scale={out_w}:{out_h}:flags=lanczos,"
                 f"setsar=1{{OUT}}")
        return chain, {"mode": "smart", "crop_w": crop_w, "keyframes": len(keys or [])}
    if mode == "smart" or abs(src_ar - out_ar) <= 0.01:
        chain = (f"{{IN}}scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
                 f"crop={out_w}:{out_h},setsar=1{{OUT}}")
        return chain, {"mode": "cover"}
    # blur: fundo desfocado + vídeo inteiro
    chain = (f"{{IN}}split=2[bg_{{K}}][fg_{{K}}];"
             f"[bg_{{K}}]scale={out_w // 4}:{out_h // 4}:force_original_aspect_ratio=increase,"
             f"crop={out_w // 4}:{out_h // 4},gblur=sigma=12,eq=brightness=-0.10:saturation=1.2,"
             f"scale={out_w}:{out_h}[bgs_{{K}}];"
             f"[fg_{{K}}]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags=lanczos[fgs_{{K}}];"
             f"[bgs_{{K}}][fgs_{{K}}]overlay=(W-w)/2:(H-h)/2,setsar=1{{OUT}}")
    fg_h = int(min(out_h, out_w / src_ar))
    return chain, {"mode": "blur", "fg_h": fg_h}
