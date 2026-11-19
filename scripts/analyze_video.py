"""Transcrição local + análise de momentos para seleção de Shorts.

Uso (a partir da raiz do repo):
    .venv\\Scripts\\python.exe scripts\\analyze_video.py VIDEO --out projects\\<nome>\\analysis
        [--model large-v3-turbo] [--device auto|cuda|cpu] [--lang auto|pt|en]
        [--variant auto|pt-BR|pt-PT|en] [--no-scenes]

Saídas em --out:
    media.json        ffprobe resumido
    audio16k.wav      áudio 16 kHz mono (entrada do Whisper)
    transcript.json   formato canónico do Cut-as-Code (segments[] -> words[] com start/end/word/prob)
    transcript.srt    legendas por segmento
    analysis.json     falas (turnos), picos de volume, cortes de cena, ritmo de fala
    moments.json      momentos engraçados / surpreendentes / interessantes + janelas candidatas a Short
    summary.md        resumo legível

Tudo corre localmente (faster-whisper + FFmpeg + numpy). Sem APIs externas.
Os momentos são heurísticos: servem de shortlist para o /video-to-shorts, não substituem a decisão editorial.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO / "models" / "faster-whisper"

# --------------------------------------------------------------------------- GPU setup


def _add_cuda_dlls() -> None:
    """Expõe as DLLs CUDA instaladas via pip (nvidia-*-cu12) ao CTranslate2. Não requer CUDA Toolkit."""
    site = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for d in glob.glob(str(site / "*" / "bin")):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(d)


# --------------------------------------------------------------------------- helpers


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)


def fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _np_default(o):
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=_np_default), encoding="utf-8")


# --------------------------------------------------------------------------- media


def probe(video: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    if r.returncode:
        raise SystemExit(f"ffprobe falhou: {r.stderr.strip()}")
    info = json.loads(r.stdout)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    return {
        "path": str(video.resolve()),
        "duration_s": float(info["format"].get("duration", 0)),
        "video": None if not v else {
            "codec": v.get("codec_name"), "width": v.get("width"), "height": v.get("height"),
            "fps": v.get("avg_frame_rate") or v.get("r_frame_rate"),
        },
        "audio": None if not a else {
            "codec": a.get("codec_name"), "sample_rate": a.get("sample_rate"), "channels": a.get("channels"),
        },
    }


def extract_audio(video: Path, wav: Path) -> None:
    r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
    if r.returncode:
        raise SystemExit(f"ffmpeg (extração de áudio) falhou: {r.stderr.strip()}")


def read_wav(wav: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return data, sr


def scene_changes(video: Path, threshold: float) -> list[float]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an",
             "-vf", f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    return [round(float(m), 3) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


# --------------------------------------------------------------------------- transcription

VARIANT_PROMPT = {
    "pt-BR": "Transcrição em português do Brasil, com pontuação.",
    "pt-PT": "Transcrição em português de Portugal, com pontuação.",
    "en": "Transcript in English, with punctuation.",
}


def load_model(name: str, device: str):
    from faster_whisper import WhisperModel

    if device in ("auto", "cuda"):
        _add_cuda_dlls()
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return WhisperModel(name, device="cuda", compute_type="float16",
                                    download_root=str(MODELS_DIR)), "cuda", "float16"
        except Exception as exc:  # noqa: BLE001
            if device == "cuda":
                raise
            print(f"[aviso] GPU indisponível ({exc}); a usar CPU.", file=sys.stderr)
    return WhisperModel(name, device="cpu", compute_type="int8",
                        download_root=str(MODELS_DIR)), "cpu", "int8"


def transcribe(model, wav: Path, lang: str, variant: str) -> tuple[dict, float]:
    language = None if lang == "auto" else lang
    prompt = VARIANT_PROMPT.get(variant)
    t0 = time.time()
    segments, info = model.transcribe(
        str(wav), language=language, word_timestamps=True, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500}, beam_size=5,
        condition_on_previous_text=False, initial_prompt=prompt,
    )
    out = []
    for seg in segments:  # gerador: a transcrição acontece aqui
        out.append({
            "id": seg.id, "start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text,
            "avg_logprob": round(seg.avg_logprob, 3), "no_speech_prob": round(seg.no_speech_prob, 3),
            "words": [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word,
                       "prob": round(w.probability, 3)} for w in (seg.words or [])],
        })
    elapsed = time.time() - t0
    return {
        "audio": str(wav), "model": None, "duration": round(info.duration, 3),
        "language": info.language, "language_probability": round(info.language_probability, 3),
        "segments": out,
    }, elapsed


# --------------------------------------------------------------------------- audio features


def loudness_curve(samples: np.ndarray, sr: int, hop_s: float = 0.25) -> tuple[np.ndarray, np.ndarray]:
    hop = int(sr * hop_s)
    n = len(samples) // hop
    if n == 0:
        return np.array([]), np.array([])
    frames = samples[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    times = (np.arange(n) + 0.5) * hop_s
    return times, db


def refine_boundaries(segments: list[dict], samples: np.ndarray, sr: int, min_gap: float = 0.25,
                      back: float = 0.5, fwd: float = 0.6, below_voice_db: float = 25.0,
                      floor_max_db: float = -50.0) -> int:
    """Ajusta início/fim de palavras junto a pausas ao onset/offset real da energia (frames de 10 ms).

    O Whisper tende a marcar inícios ~0,2-0,5 s cedo após pausas. Só se corrige quando a janela
    contém silêncio verdadeiro (mínimo < -50 dB) e a voz ultrapassa (mediana da voz - 25 dB) durante
    >= 30 ms. Em áudio sem silêncio (música, ruído de jogo) nada é alterado.
    Guarda os valores originais em start_raw/end_raw. Devolve o nº de fronteiras ajustadas."""
    hop = int(sr * 0.01)
    n = len(samples) // hop
    if n == 0:
        return 0
    db = 20 * np.log10(np.sqrt(np.mean(samples[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12) + 1e-12)
    voiced = db[db > -60]
    if len(voiced) < 10:
        return 0
    thr = float(np.median(voiced)) - below_voice_db
    total = len(samples) / sr
    words = [w for s in segments for w in s["words"]]
    changed = 0
    for k, w in enumerate(words):
        prev_end = words[k - 1]["end"] if k else 0.0
        next_start = words[k + 1]["start"] if k + 1 < len(words) else total
        if k == 0 or w["start"] - prev_end >= min_gap:
            a = int(max(prev_end, w["start"] - back) * 100)
            b = int(min(w["end"], w["start"] + fwd) * 100)
            seg = db[a:b]
            if len(seg) > 5 and seg.min() < floor_max_db:
                # transição silêncio -> voz: 3 frames abaixo do limiar seguidos de 3 acima
                hits = [i for i in range(3, len(seg) - 2)
                        if np.all(seg[i - 3:i] <= thr) and np.all(seg[i:i + 3] > thr)]
                if hits:
                    t = round((a + hits[0]) / 100 - 0.02, 3)  # 20 ms de margem antes do onset
                    if abs(t - w["start"]) > 0.03 and t < w["end"]:
                        w["start_raw"], w["start"] = w["start"], max(prev_end, t)
                        changed += 1
        if k + 1 == len(words) or next_start - w["end"] >= min_gap:
            a = int(max(w["start"], w["end"] - fwd) * 100)
            b = int(min(next_start, w["end"] + back) * 100)
            seg = db[a:b]
            if len(seg) > 5 and seg.min() < floor_max_db:
                # transição voz -> silêncio: 3 frames acima do limiar seguidos de 3 abaixo
                hits = [i for i in range(2, len(seg) - 3)
                        if np.all(seg[i - 2:i + 1] > thr) and np.all(seg[i + 1:i + 4] <= thr)]
                if hits:
                    t = round((a + hits[-1] + 1) / 100 + 0.03, 3)  # 30 ms de margem após o offset
                    if abs(t - w["end"]) > 0.03 and t > w["start"]:
                        w["end_raw"], w["end"] = w["end"], min(next_start, t)
                        changed += 1
    for s in segments:
        if s["words"]:
            s["start"], s["end"] = min(s["start"], s["words"][0]["start"]), max(s["end"], s["words"][-1]["end"])
    return changed


def loudness_peaks(times: np.ndarray, db: np.ndarray, min_gap_s: float = 2.0) -> list[dict]:
    voiced = db[db > -60]
    if len(voiced) < 8:
        return []
    med = float(np.median(voiced))
    mad = float(np.median(np.abs(voiced - med))) or 1.0
    z = (db - med) / (1.4826 * mad)
    idx = [i for i in np.argsort(-z) if z[i] >= 2.5]
    peaks: list[dict] = []
    for i in idx:
        t = float(times[i])
        if all(abs(t - p["t"]) >= min_gap_s for p in peaks):
            peaks.append({"t": round(t, 2), "db": round(float(db[i]), 1), "z": round(float(z[i]), 2)})
    return sorted(peaks, key=lambda p: p["t"])


def speech_turns(segments: list[dict], max_gap: float = 0.8) -> list[dict]:
    """Agrupa palavras em 'falas' contínuas, separadas por pausas > max_gap (não é diarização de oradores)."""
    words = [w for s in segments for w in s["words"]]
    turns, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > max_gap:
            turns.append(cur)
            cur = []
        cur.append(w)
    if cur:
        turns.append(cur)
    out = []
    for i, t in enumerate(turns, 1):
        dur = t[-1]["end"] - t[0]["start"]
        out.append({"id": f"turn-{i:03d}", "start": t[0]["start"], "end": t[-1]["end"],
                    "words": len(t), "wps": round(len(t) / dur, 2) if dur > 0 else 0.0,
                    "text": "".join(w["word"] for w in t).strip()})
    return out


def sentence_units(segments: list[dict], max_gap: float = 0.8) -> list[dict]:
    """Divide em frases: corta após palavras terminadas em . ! ? … ou em pausas > max_gap.
    Os segmentos do Whisper juntam várias frases; a frase é a unidade certa para pontuar momentos."""
    units, cur = [], []

    def flush():
        if cur:
            units.append({"id": f"s-{len(units) + 1:03d}", "start": cur[0]["start"], "end": cur[-1]["end"],
                          "text": "".join(w["word"] for w in cur).strip(), "words": list(cur)})
            cur.clear()

    for seg in segments:
        for w in seg["words"]:
            if cur and w["start"] - cur[-1]["end"] > max_gap:
                flush()
            cur.append(w)
            if re.search(r"[.!?…]+[\"')\]]*$", w["word"].strip()):
                flush()
        flush()  # fronteira de segmento do Whisper também fecha a frase
    return units


# --------------------------------------------------------------------------- moment scoring

LEX = {
    "engracado": [
        r"\bha(?:[\s,!.-]*ha)+h?\b", r"\bhe(?:[\s,!.-]*he)+\b", r"\bhue(?:hue)+\b", r"\bk{3,}\b", r"\b(rs){2,}\b", r"\blol\b", r"\blmao\b",
        r"\brisos?\b", r"\blaugh(ter|ing|s)?\b", r"\bhilari(o|ous|ante)\b", r"\bengracad[oa]\b",
        r"\bmorri\b", r"\bto morrendo\b", r"\bpiada\b", r"\bzoeira\b", r"\bfunny\b", r"\bjoke\b",
        r"\bque comedia\b", r"\bridicul[oa]\b",
    ],
    "surpreendente": [
        r"\bcaramba\b", r"\bnossa\b", r"\bmeu deus\b", r"\bminha nossa\b", r"\beita\b", r"\boxe\b",
        r"\bnao acredito\b", r"\bque isso\b", r"\bcomo assim\b", r"\buau+\b", r"\bwow+\b", r"\bwhoa+\b",
        r"\boh my god\b", r"\bomg\b", r"\bno way\b", r"\bwhat the\b", r"\bholy\b", r"\binsane\b",
        r"\bincrivel\b", r"\binacreditavel\b", r"\bfogo\b", r"\bbolas\b", r"\bepa\b", r"\bbrutal\b",
        r"\bque loucura\b", r"\bsurreal\b", r"\bunbelievable\b", r"\bcrazy\b", r"\bsurpres[ao]\b",
        r"\bshock(ed|ing)?\b", r"\bchocante\b", r"\bimpressionante\b",
    ],
    "interessante": [
        r"\bolha\b", r"\brepar[ae]m?\b", r"\bvejam\b", r"\bdetalhes?\b", r"\bsegredos?\b",
        r"\bcuriosidades?\b", r"\bsabia[ms]?\b", r"\bvoce sabia\b", r"\beaster eggs?\b",
        r"\bpela primeira vez\b", r"\bescondid[oa]s?\b", r"\bimportante\b", r"\blook at\b",
        r"\bcheck (this|it) out\b", r"\bnotice\b", r"\bsecrets?\b", r"\bdetails?\b", r"\bdid you know\b",
        r"\bfirst time\b", r"\bhidden\b", r"\bnew\b", r"\bnov[oa]s?\b", r"\bmelhor(es)?\b", r"\bbest\b",
    ],
}
LEX_RE = {k: [re.compile(p) for p in v] for k, v in LEX.items()}


def lex_hits(text: str) -> dict[str, list[str]]:
    t = norm(text)
    return {k: [m.group(0) for r in rs for m in r.finditer(t)] for k, rs in LEX_RE.items()}


def score_segments(segments: list[dict], peaks: list[dict], scenes: list[float]) -> list[dict]:
    rates = []
    for s in segments:
        d = s["end"] - s["start"]
        rates.append(len(s["words"]) / d if d > 0 else 0.0)
    r_mean = float(np.mean(rates)) if rates else 0.0
    r_std = float(np.std(rates)) or 1.0

    moments = []
    for s, rate in zip(segments, rates):
        hits = lex_hits(s["text"])
        # a reação vem depois do evento (explosão, queda, grito): aceitar picos até 1,5 s antes da frase
        near_peaks = [p for p in peaks if s["start"] - 1.5 <= p["t"] <= s["end"] + 1.0]
        peak_z = max((p["z"] for p in near_peaks), default=0.0)
        near_scenes = [c for c in scenes if s["start"] - 1.0 <= c <= s["end"] + 1.0]
        exclaim = s["text"].count("!")
        question = "?" in s["text"]
        rate_z = (rate - r_mean) / r_std
        reasons: list[str] = []

        funny = 40 * min(len(hits["engracado"]), 2) + (10 if peak_z >= 2.5 else 0) + 5 * min(exclaim, 2)
        surprise = (30 * min(len(hits["surpreendente"]), 2) + min(35, 8 * peak_z) + 10 * min(exclaim, 2)
                    + (10 if rate_z > 1 else 0) + (10 if near_scenes else 0))
        interest = (20 * min(len(hits["interessante"]), 2) + (10 if question else 0)
                    + (10 if near_scenes else 0) + (5 if rate_z > 1 else 0))
        scores = {"engracado": min(100, round(funny)), "surpreendente": min(100, round(surprise)),
                  "interessante": min(100, round(interest))}

        for k, v in hits.items():
            if v:
                reasons.append(f"léxico {k}: {', '.join(sorted(set(v)))}")
        if peak_z:
            reasons.append(f"pico de volume z={peak_z:.1f}")
        if exclaim:
            reasons.append(f"{exclaim} exclamação(ões)")
        if question:
            reasons.append("pergunta")
        if rate_z > 1:
            reasons.append(f"fala acelerada ({rate:.1f} pal/s)")
        if near_scenes:
            reasons.append(f"{len(near_scenes)} corte(s) de cena")

        best = max(scores, key=scores.get)
        if scores[best] >= 30:
            moments.append({
                "segment_id": s["id"], "start": s["start"], "end": s["end"], "text": s["text"].strip(),
                "category": best, "score": scores[best], "scores": scores, "reasons": reasons,
            })
    return sorted(moments, key=lambda m: -m["score"])


def short_windows(segments: list[dict], moments: list[dict], duration: float,
                  min_len: float = 20.0, max_len: float = 60.0, limit: int = 10) -> list[dict]:
    """Expande cada momento para uma janela de Short, alinhada a fronteiras de segmento."""
    by_id = {s["id"]: i for i, s in enumerate(segments)}
    wins: list[dict] = []
    for m in moments:
        i = j = by_id[m["segment_id"]]
        if i > 0 and segments[i]["start"] - segments[i - 1]["start"] <= 8:  # contexto anterior curto
            i -= 1
        while (segments[j]["end"] - segments[i]["start"] < min_len and j + 1 < len(segments)
               and segments[j + 1]["end"] - segments[i]["start"] <= max_len):
            j += 1
        start = max(0.0, segments[i]["start"] - 0.2)
        end = min(duration, segments[j]["end"] + 0.3)
        cand = {"start": round(start, 3), "end": round(end, 3), "duration_s": round(end - start, 2),
                "anchor": m, "category": m["category"], "score": m["score"],
                "excerpt": " ".join(s["text"].strip() for s in segments[i: j + 1])}
        overlap = next((w for w in wins if min(w["end"], end) - max(w["start"], start)
                        > 0.5 * min(w["end"] - w["start"], end - start)), None)
        if overlap is None:
            wins.append(cand)
        elif cand["score"] > overlap["score"]:
            wins[wins.index(overlap)] = cand
    wins = sorted(wins, key=lambda w: -w["score"])[:limit]
    for n, w in enumerate(wins, 1):
        w["id"] = f"win-{n:03d}"
        w["fits_short_20_90s"] = bool(20 <= w["duration_s"] <= 90)
    return wins


# --------------------------------------------------------------------------- main


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--lang", default="auto", help="auto | pt | en | ...")
    ap.add_argument("--variant", default="auto", choices=["auto", "pt-BR", "pt-PT", "en"])
    ap.add_argument("--scene-threshold", type=float, default=0.35)
    ap.add_argument("--no-scenes", action="store_true")
    ap.add_argument("--no-refine", action="store_true", help="não ajustar fronteiras de palavras à energia do áudio")
    args = ap.parse_args()

    if args.variant in ("pt-BR", "pt-PT") and args.lang == "auto":
        args.lang = "pt"
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    t = time.time()
    media = probe(args.video)
    write_json(out / "media.json", media)
    wav = out / "audio16k.wav"
    extract_audio(args.video, wav)
    timings["probe_extract_s"] = round(time.time() - t, 2)

    t = time.time()
    model, device, ctype = load_model(args.model, args.device)
    timings["model_load_s"] = round(time.time() - t, 2)

    transcript, tr_s = transcribe(model, wav, args.lang, args.variant)
    timings["transcribe_s"] = round(tr_s, 2)
    transcript["model"] = args.model
    transcript["device"] = device
    transcript["compute_type"] = ctype
    transcript["variant"] = args.variant
    samples, sr = read_wav(wav)
    transcript["boundary_refined"] = 0 if args.no_refine else refine_boundaries(transcript["segments"], samples, sr)
    write_json(out / "transcript.json", transcript)
    srt = [f"{i}\n{fmt_srt(s['start'])} --> {fmt_srt(s['end'])}\n{s['text'].strip()}\n"
           for i, s in enumerate(transcript["segments"], 1)]
    (out / "transcript.srt").write_text("\n".join(srt), encoding="utf-8")

    t = time.time()
    times, db = loudness_curve(samples, sr)
    peaks = loudness_peaks(times, db)
    scenes = [] if (args.no_scenes or not media["video"]) else scene_changes(args.video, args.scene_threshold)
    turns = speech_turns(transcript["segments"])
    timings["analysis_s"] = round(time.time() - t, 2)

    segs = transcript["segments"]
    units = sentence_units(segs)
    moments = score_segments(units, peaks, scenes)
    windows = short_windows(units, moments, media["duration_s"])
    n_words = sum(len(s["words"]) for s in segs)
    speech_s = sum(tn["end"] - tn["start"] for tn in turns)
    rtf = tr_s / media["duration_s"] if media["duration_s"] else None

    analysis = {
        "source": media["path"], "duration_s": media["duration_s"], "language": transcript["language"],
        "language_probability": transcript["language_probability"], "variant": args.variant,
        "words": n_words, "segments": len(segs), "speech_s": round(speech_s, 2),
        "speaking_ratio": round(speech_s / media["duration_s"], 3) if media["duration_s"] else None,
        "mean_word_prob": round(float(np.mean([w["prob"] for s in segs for w in s["words"]])), 3) if n_words else None,
        "sentences": len(units),
        "turns": turns, "loudness_peaks": peaks, "scene_changes": scenes,
        "loudness_db_0_5s": [round(float(x), 1) for x in db[::2]],
        "device": device, "compute_type": ctype, "model": args.model,
        "timings": timings, "realtime_factor": round(rtf, 3) if rtf else None,
    }
    write_json(out / "analysis.json", analysis)
    write_json(out / "moments.json", {"moments": moments, "short_windows": windows,
                                      "note": "Heurístico: shortlist para revisão no /video-to-shorts."})

    lines = [
        f"# Análise — {args.video.name}", "",
        f"- Duração: {media['duration_s']:.1f} s | Língua: {transcript['language']} "
        f"(p={transcript['language_probability']}) | Variante pedida: {args.variant}",
        f"- Modelo: {args.model} em {device}/{ctype} | Transcrição: {tr_s:.1f} s (RTF {analysis['realtime_factor']})",
        f"- Palavras: {n_words} | Segmentos: {len(segs)} | Falas: {len(turns)} | "
        f"Prob. média por palavra: {analysis['mean_word_prob']}",
        f"- Picos de volume: {len(peaks)} | Cortes de cena: {len(scenes)}", "",
        "## Momentos", "", "| Início | Fim | Categoria | Score | Texto | Sinais |", "|---|---|---|---:|---|---|",
    ]
    for m in moments:
        lines.append(f"| {m['start']:.2f} | {m['end']:.2f} | {m['category']} | {m['score']} | "
                     f"{m['text'][:70]} | {'; '.join(m['reasons'])} |")
    lines += ["", "## Janelas candidatas a Short", "", "| ID | Início | Fim | Duração | Categoria | Score |",
              "|---|---|---|---:|---|---:|"]
    for w in windows:
        lines.append(f"| {w['id']} | {w['start']:.2f} | {w['end']:.2f} | {w['duration_s']} | "
                     f"{w['category']} | {w['score']} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: analysis[k] for k in ("language", "language_probability", "words", "segments",
                                                "device", "compute_type", "realtime_factor", "timings")},
                     ensure_ascii=False))
    print(f"momentos={len(moments)} janelas={len(windows)} -> {out}")


if __name__ == "__main__":
    main()
