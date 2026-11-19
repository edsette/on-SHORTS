"""Render de cada Short: peças -> reframe -> concat -> zoom/efeitos -> legendas ASS -> MP4.

- Cada peça é um input separado (-ss/-t antes de -i): memória constante mesmo com vídeos longos.
- O filtergraph é escrito num ficheiro e o FFmpeg corre com cwd na pasta de trabalho, para que o
  filtro `ass` receba só o nome do ficheiro (caminhos com "C:" partem filtros no Windows).
- Vídeo: h264_nvenc (RTX 4060); recai em libx264 se o NVENC falhar. Áudio: AAC 192k, loudnorm -14 LUFS.
"""

from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from . import reframe
from .select import Clip


STD_FPS = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
           Fraction(50), Fraction(60000, 1001), Fraction(60)]


def _fps(media: dict) -> Fraction:
    """Taxa de saída: r_frame_rate (nominal) arredondada a uma taxa padrão; máximo 60."""
    f = Fraction(30)
    for key in ("r_fps", "fps"):
        try:
            cand = Fraction(media["video"].get(key) or "0")
            if cand > 0:
                f = cand
                break
        except Exception:  # noqa: BLE001
            continue
    best = min(STD_FPS, key=lambda s: abs(float(s) - float(f)))
    if abs(float(best) - float(f)) / float(best) < 0.02:
        f = best
    return min(f, Fraction(60))


def emphasis_times(clip: Clip, peaks: list[dict], moments: list[dict], style: dict) -> list[tuple[float, float]]:
    """(t_saída, força) para zoom-punch: picos de volume e inícios de momentos surpreendentes/engraçados."""
    if not style["max_punches"]:
        return []
    cand = []
    off = 0.0
    for p in clip.pieces:
        for pk in peaks:
            if p.src_start + 0.2 <= pk["t"] <= p.src_end - 0.2:
                cand.append((off + pk["t"] - p.src_start, min(1.0, pk["z"] / 5)))
        for m in moments:
            if m["category"] in ("surpreendente", "engracado") and p.src_start <= m["start"] <= p.src_end - 0.3:
                cand.append((off + m["start"] - p.src_start + 0.05, min(1.0, m["score"] / 100)))
        off += p.dur
    cand.sort(key=lambda x: -x[1])
    picked: list[tuple[float, float]] = []
    for t, s in cand:
        if t < 0.4 or any(abs(t - q) < 2.5 for q, _ in picked):
            continue
        picked.append((round(t, 3), round(s, 2)))
        if len(picked) >= style["max_punches"]:
            break
    return sorted(picked)


def zoom_chain(style: dict, W: int, H: int, fps: Fraction, D: float, punches: list[tuple[float, float]]) -> str:
    if not (style["zoom_punch"] or style["push_in"]):
        return ""
    z = "1"
    if style["push_in"]:
        z += f"+{style['push_in']}*it/{D:.3f}"
    for t, s in punches:
        z += f"+{style['zoom_punch'] * s:.3f}*exp(-pow((it-{t:.3f})/0.22,2))"
    shake = "0"
    if style["shake_px"]:
        for t, s in punches:
            if s >= 0.6:
                shake += f"+{style['shake_px'] * s:.1f}*sin(it*55)*exp(-pow((it-{t:.3f})/0.18,2))"
    # zoompan trabalha sobre uma versão 1,5x maior para reduzir o "tremido" de arredondamento
    UW, UH = int(W * 1.5) // 2 * 2, int(H * 1.5) // 2 * 2
    sx = UW / W
    return (f",scale={UW}:{UH}:flags=bicubic,zoompan=z='{z}':d=1:s={W}x{H}:fps={fps}"
            f":x='iw/2-(iw/zoom/2)+({shake})*{sx:.3f}':y='ih/2-(ih/zoom/2)'")


def render_clip(clip: Clip, src: str, media: dict, style: dict, W: int, H: int, ass_name: str,
                work: Path, out_mp4: Path, scenes: list[float], punches: list[tuple[float, float]],
                encoder: str = "auto") -> dict:
    fps = _fps(media)
    sw, sh = media["video"]["width"], media["video"]["height"]
    D = clip.out_duration
    lines, labels, infos = [], [], []
    for k, p in enumerate(clip.pieces):
        keys = None
        if style["reframe"] == "smart":
            keys = reframe.motion_centers(src, p.src_start, p.dur, scenes)
        chain, info = reframe.video_chain(style["reframe"], sw, sh, W, H, keys)
        infos.append(info)
        chain = chain.replace("{IN}", f"[{k}:v]").replace("{OUT}", f",fps={fps},format=yuv420p[v{k}]").replace("{K}", str(k))
        lines.append(chain + ";")
        lines.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{k}];")
        labels.append(f"[v{k}][a{k}]")
    n = len(clip.pieces)
    lines.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[vc][ac];")
    lines.append(f"[vc]setpts=PTS-STARTPTS{zoom_chain(style, W, H, fps, D, punches)},ass={ass_name},format=yuv420p[vout];")
    lines.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    graph = work / f"{out_mp4.stem}.filtergraph.txt"
    graph.write_text("\n".join(lines), encoding="utf-8")

    def cmd_for(enc: str) -> list[str]:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for p in clip.pieces:
            cmd += ["-ss", f"{p.src_start:.3f}", "-t", f"{p.dur:.3f}", "-i", src]
        cmd += ["-/filter_complex", graph.name, "-map", "[vout]", "-map", "[aout]", "-r", str(fps)]
        if enc == "nvenc":
            cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "20",
                    "-b:v", "0", "-maxrate", "16M", "-bufsize", "32M", "-profile:v", "high"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high"]
        cmd += ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                "-t", f"{D:.3f}", str(out_mp4.resolve())]
        return cmd

    used = None
    errors = []
    for enc in (["nvenc", "x264"] if encoder == "auto" else [encoder]):
        r = subprocess.run(cmd_for(enc), cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            used = enc
            break
        errors.append(f"{enc}: {r.stderr.strip()[-800:]}")
    if used is None:
        raise RuntimeError("render falhou:\n" + "\n".join(errors))
    return {"encoder": used, "reframe": infos, "fps": str(fps), "punches": punches, "filtergraph": graph.name}


def verify(mp4: Path, W: int, H: int, expected: float) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(mp4)], capture_output=True, text=True)
    info = json.loads(r.stdout or "{}")
    v = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), {})
    dur = float(info.get("format", {}).get("duration", 0))
    ok = (v.get("width") == W and v.get("height") == H and bool(a) and abs(dur - expected) < 0.25)
    return {"ok": ok, "width": v.get("width"), "height": v.get("height"), "video": v.get("codec_name"),
            "audio": a.get("codec_name"), "fps": v.get("r_frame_rate"), "duration_s": round(dur, 3),
            "expected_s": round(expected, 3), "size_mb": round(mp4.stat().st_size / 1e6, 2)}


def contact_sheet(mp4: Path, out_jpg: Path, D: float, n: int = 6) -> None:
    """Folha de contacto com n frames distribuídos, para revisão rápida."""
    times = [D * (k + 0.5) / n for k in range(n)]
    sel = "+".join(f"between(t,{t - 0.02:.2f},{t + 0.02:.2f})" for t in times)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp4),
                    "-vf", f"select='{sel}',scale=270:-2,tile={n}x1:padding=6:color=white",
                    "-frames:v", "1", "-update", "1", str(out_jpg)], capture_output=True)
