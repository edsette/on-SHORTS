"""Legendas ASS (libass) sincronizadas por palavra + gancho, CTA, flash e barra de progresso.

Tudo é texto/desenho ASS renderizado pelo filtro `ass` do FFmpeg — sem fontes por caminho (evita o
problema dos caminhos C: no Windows) e sem dependências extra.
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_video import LEX_RE  # noqa: E402  (léxico partilhado com a análise)

from .select import STOP, Clip  # noqa: E402

EMPH = set("""caramba nossa eita incrivel insano insane epic epico explosao explosion brutal loucura crazy
wow uau omg hilario hilarious funny engracado segredo secret escondido hidden easter detalhe detail
primeira first nunca never melhor best pior worst rapido fast enorme huge gigante giant""".split())


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _clean_word(w: str) -> str:
    return re.sub(r"[{}\\]", "", w.strip())


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def keyword_categories(units: list[dict], moments: list[dict]) -> dict[tuple, str]:
    """Marca palavras importantes: léxico de momentos, números, nomes próprios, palavras de ênfase."""
    cat_by_unit = {m["segment_id"]: m["category"] for m in moments}
    marks: dict[tuple, str] = {}
    for u in units:
        words = u.get("words") or []
        if not words:
            continue
        normed = [_norm(_clean_word(w["word"])) for w in words]
        joined, offs, pos = "", [], 0
        for nw in normed:
            offs.append((pos, pos + len(nw)))
            joined += nw + " "
            pos += len(nw) + 1
        for cat, regs in LEX_RE.items():
            for r in regs:
                for m in r.finditer(joined):
                    for k, (a, b) in enumerate(offs):
                        if a < m.end() and m.start() < b:
                            marks[(words[k]["start"], words[k]["end"])] = cat
        ucat = cat_by_unit.get(u["id"], "default")
        for k, w in enumerate(words):
            raw = _clean_word(w["word"])
            core = re.sub(r"[^\wÀ-ÿ]", "", raw)
            key = (w["start"], w["end"])
            if key in marks or not core:
                continue
            nw = _norm(core)
            if (any(ch.isdigit() for ch in core) or nw in EMPH
                    or (k > 0 and core[:1].isupper() and nw not in STOP and len(core) > 1)
                    or (len(nw) >= 9 and nw not in STOP)):
                marks[key] = ucat
    return marks


def _words_out(clip: Clip, all_units: list[dict]) -> list[list[dict]]:
    """Palavras de cada peça, convertidas para o tempo de saída."""
    pieces_words, off = [], 0.0
    all_words = [w for u in all_units for w in (u.get("words") or [])]
    for p in clip.pieces:
        ws = []
        for w in all_words:
            if w["start"] >= p.src_start - 0.05 and w["end"] <= p.src_end + 0.05:
                ws.append({**w, "o_start": off + max(0.0, w["start"] - p.src_start),
                           "o_end": off + min(p.dur, w["end"] - p.src_start)})
        pieces_words.append(ws)
        off += p.dur
    return pieces_words


def _chunks(words: list[dict], wpc: int, max_chars: int) -> list[list[dict]]:
    out, cur = [], []
    for w in words:
        txt = " ".join(_clean_word(x["word"]) for x in cur + [w])
        if cur and (len(cur) >= wpc or w["o_start"] - cur[-1]["o_end"] > 0.45 or len(txt) > max_chars
                    or re.search(r"[.!?…]$", _clean_word(cur[-1]["word"]))):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def build_ass(clip: Clip, all_units: list[dict], moments: list[dict], style: dict, W: int, H: int,
              texts: dict, out_path: Path, flash_times: list[float]) -> dict:
    base = 1.3333 * math.sqrt(W * H)
    fs = round(style["font_size"] * base)
    ow = round(style["outline_w"] * base, 1)
    sh = round(style["shadow"] * base, 1)
    hook_fs = round(fs * (0.72 if style["hook"] != "fade" else 0.85))
    D = clip.out_duration
    marks = keyword_categories(all_units, moments)
    hl = style["highlight"]

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{style['font']},{fs},{style['primary']},{style['primary']},{style['outline']},&H80000000,0,0,0,0,100,100,1,0,1,{ow},{sh},5,{int(W * 0.08)},{int(W * 0.08)},0,1
Style: Hook,{style['font']},{hook_fs},{style['hook_text']},{style['hook_text']},{style['hook_back']},{style['hook_back']},0,0,0,0,100,100,1,0,3,{round(fs * 0.22)},0,8,{int(W * 0.07)},{int(W * 0.07)},0,1
Style: CTA,{style['font']},{round(fs * 0.8)},&H00FFFFFF,&H00FFFFFF,&H002020FF,&H002020FF,0,0,0,0,100,100,1,0,3,{round(fs * 0.2)},0,5,0,0,0,1
Style: FX,Arial,10,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev: list[str] = []

    def add(layer, a, b, st, text):
        if b - a >= 0.04:
            ev.append(f"Dialogue: {layer},{ass_time(a)},{ass_time(b)},{st},,0,0,0,,{text}")

    cx, cy = W // 2, int(H * style["caption_y"])

    def render_word(w, active: bool) -> str:
        t = _clean_word(w["word"])
        if style["uppercase"]:
            t = t.upper()
            t = re.sub(r"[.,;:]+$", "", t)
        key = (w["start"], w["end"])
        if active and style["karaoke"]:
            s = style["active_scale"]
            return f"{{\\c{style['active']}&\\fscx{s}\\fscy{s}}}{t}{{\\r}}"
        if key in marks:
            col = hl.get(marks[key], hl["default"])
            return f"{{\\c{col}&}}{t}{{\\r}}"
        return t

    n_caps = 0
    for pw in _words_out(clip, all_units):
        chunks = _chunks(pw, style["words_per_caption"], style["max_chars"])
        for ci, ch in enumerate(chunks):
            c_start = ch[0]["o_start"]
            nxt = chunks[ci + 1][0]["o_start"] if ci + 1 < len(chunks) else D
            c_end = min(nxt, ch[-1]["o_end"] + 0.25)
            pos = f"\\an5\\pos({cx},{cy})"
            pop = "\\fscx80\\fscy80\\t(0,90,\\fscx100\\fscy100)" if style["pop"] else ""
            n_caps += 1
            if not style["karaoke"]:
                add(2, c_start, c_end, "Cap", f"{{{pos}{pop}}}" + " ".join(render_word(w, False) for w in ch))
                continue
            for i, w in enumerate(ch):
                a = c_start if i == 0 else w["o_start"]
                b = ch[i + 1]["o_start"] if i + 1 < len(ch) else c_end
                pre = f"{{{pos}{pop if i == 0 else ''}}}"
                add(2, a, b, "Cap", pre + " ".join(render_word(x, x is w) for x in ch))

    # gancho (título nos primeiros segundos)
    hook = clip.hook_text if not style["uppercase"] else clip.hook_text.upper()
    hpos = f"\\an8\\pos({W // 2},{int(H * 0.11)})"
    anim = {
        "box": "\\fad(120,200)\\fscx70\\fscy70\\t(0,150,\\fscx108\\fscy108)\\t(150,230,\\fscx100\\fscy100)",
        "pop": "\\fad(80,200)\\fscx40\\fscy40\\frz-4\\t(0,180,\\fscx112\\fscy112\\frz2)\\t(180,280,\\fscx100\\fscy100\\frz0)",
        "fade": "\\fad(300,400)",
    }[style["hook"]]
    add(5, 0.0, min(style["hook_secs"], D), "Hook", f"{{{hpos}{anim}}}{hook}")

    # CTA final
    if style["cta"] and D > 8:
        a = D - 2.0
        add(5, a, D, "CTA", f"{{\\an5\\fad(150,0)\\move({W // 2},{int(H * 0.47)},{W // 2},{int(H * 0.42)},0,250)}}{texts['cta']}")

    # flash branco nas transições (teaser -> início)
    for t in flash_times:
        add(9, max(0, t - 0.02), t + 0.18, "FX",
            f"{{\\an7\\pos(0,0)\\p1\\1c&HFFFFFF&\\1a&H50&\\bord0\\shad0\\fad(0,160)}}m 0 0 l {W} 0 {W} {H} 0 {H}{{\\p0}}")

    # barra de progresso animada
    if style["progress"]:
        bh = max(8, int(H * 0.008))
        ms = int(D * 1000)
        add(6, 0.0, D, "FX",
            f"{{\\an7\\pos(0,{H - bh})\\p1\\1c{style['active']}&\\bord0\\shad0\\clip(0,0,0,{H})"
            f"\\t(0,{ms},\\clip(0,0,{W},{H}))}}m 0 0 l {W} 0 {W} {bh} 0 {bh}{{\\p0}}")

    out_path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8-sig")
    return {"captions": n_caps, "events": len(ev), "highlighted_words": len(marks), "font_px": fs}
