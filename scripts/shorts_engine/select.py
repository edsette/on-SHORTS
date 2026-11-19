"""Seleção dos melhores segmentos: janelas alinhadas a frases, pontuação, deduplicação e gancho."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from . import profanity

STOP = set("""
a o os as um uma uns umas de do da dos das em no na nos nas por para pra com sem que e é ou se mas
eu tu ele ela nós vós eles elas você vocês voce voces me te lhe nos vos isso isto aquilo esse essa este
esta aquele aquela muito mais menos já ja não nao sim tá ta aqui ali lá la então entao foi ser ter tem
vai vou era está esta estou estão estao né ne aí ai the a an of to in on at for and or but is are was
were be been it this that these those i you he she we they me him her us them my your our their so
just very really like what with from as by not no yes do does did have has had will would can could
""".split())


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", norm(text)) if t not in STOP and len(t) > 2]


@dataclass
class Piece:
    src_start: float
    src_end: float
    kind: str  # "teaser" | "main"

    @property
    def dur(self) -> float:
        return self.src_end - self.src_start


@dataclass
class Clip:
    id: str
    start: float
    end: float
    score: float
    category: str
    units: list[dict]
    peak: dict | None
    pieces: list[Piece] = field(default_factory=list)
    hook_text: str = ""
    reasons: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(u["text"] for u in self.units).strip()

    @property
    def out_duration(self) -> float:
        return sum(p.dur for p in self.pieces)


def _pseudo_units(duration: float, peaks: list[dict], scenes: list[float], step: float = 2.0) -> list[dict]:
    """Para vídeos sem fala: blocos de 2 s pontuados por picos de volume e cortes de cena."""
    units = []
    t, k = 0.0, 0
    while t < duration - 0.5:
        e = min(duration, t + step)
        k += 1
        units.append({"id": f"b-{k:04d}", "start": t, "end": e, "text": "", "words": []})
        t = e
    return units


def _unit_scores(units, moments, peaks, scenes) -> dict[str, tuple[float, str]]:
    by = {m["segment_id"]: (float(m["score"]), m["category"]) for m in moments}
    out = {}
    for u in units:
        if u["id"] in by:
            out[u["id"]] = by[u["id"]]
            continue
        # sem momento lexical: energia (picos) e cortes contam pouco, mas contam (gameplay sem fala)
        pz = max((p["z"] for p in peaks if u["start"] - 0.5 <= p["t"] <= u["end"] + 0.5), default=0.0)
        sc = sum(1 for c in scenes if u["start"] <= c <= u["end"])
        out[u["id"]] = (min(45.0, 6 * pz + 4 * sc), "surpreendente" if pz else "default")
    return out


def select_clips(units: list[dict], moments: list[dict], peaks: list[dict], scenes: list[float],
                 duration: float, count: int, target: float, min_len: float, max_len: float,
                 teaser: bool, lang_texts: dict, truncated_end: bool = False) -> list[Clip]:
    """truncated_end: a fonte é um trecho cortado (ex.: 30 min de uma live); evitar cortes que acabam
    colados ao fim, porque a frase pode continuar para lá do trecho."""
    speech = bool(units)
    if not speech:
        units = _pseudo_units(duration, peaks, scenes)
    scores = _unit_scores(units, moments, peaks, scenes)

    cands: list[Clip] = []
    n = len(units)
    for i in range(n):
        for j in range(i, n):
            start, end = units[i]["start"], units[j]["end"]
            dur = end - start
            if dur > max_len:
                break
            if dur < min_len:
                continue
            win = units[i:j + 1]
            ss = [scores[u["id"]][0] for u in win]
            peak_k = max(range(len(win)), key=lambda k: ss[k])
            peak_score = ss[peak_k]
            spoken = sum(u["end"] - u["start"] for u in win)
            gaps = [win[k + 1]["start"] - win[k]["end"] for k in range(len(win) - 1)]
            early = max((ss[k] for k, u in enumerate(win) if u["start"] - start <= 3.0), default=0.0)
            n_peaks = sum(1 for p in peaks if start <= p["t"] <= end)
            n_scenes = sum(1 for c in scenes if start <= c <= end)
            # penalizações de qualidade (Fase 8)
            n_words = sum(len(u.get("words") or []) for u in win)
            wps = n_words / dur
            pen_density = 25 * max(0.0, 1.2 - wps) / 1.2 if speech else 0.0       # pouca fala
            last, first = win[-1], win[0]
            frag_end = (speech and len(win) > 1 and len(last.get("words") or []) < 3
                        and last["start"] - win[-2]["end"] > 1.0)                  # fim em fragmento solto
            frag_start = (speech and len(win) > 1 and len(first.get("words") or []) < 3
                          and win[1]["start"] - first["end"] > 1.0)                # início em fragmento solto
            at_cut_end = truncated_end and duration - end < 3.0
            if at_cut_end:
                reasons_extra = ["penalizado: acaba no fim do trecho descarregado"]
            score = (-40 if at_cut_end else 0) + (1.0 * peak_score + 0.35 * sum(ss) + (20 * spoken / dur if speech else 0)
                     + 0.5 * early + 3 * min(n_peaks, 4) + 1 * min(n_scenes, 6)
                     - 30 * abs(dur - target) / target - (10 if gaps and max(gaps) > 2.5 else 0)
                     - pen_density - (15 if frag_end else 0) - (10 if frag_start else 0))
            reasons = [f"pico {peak_score:.0f} ({scores[win[peak_k]['id']][1]})",
                       f"soma {sum(ss):.0f}", f"gancho inicial {early:.0f}",
                       f"{n_peaks} picos de volume", f"{n_scenes} cortes de cena", f"{dur:.1f}s",
                       f"{wps:.1f} palavras/s"]
            if frag_end:
                reasons.append("penalizado: termina em fragmento")
            if frag_start:
                reasons.append("penalizado: começa em fragmento")
            if at_cut_end:
                reasons.extend(reasons_extra)
            cands.append(Clip(id="", start=start, end=end, score=round(score, 1),
                              category=scores[win[peak_k]["id"]][1], units=win, peak=win[peak_k],
                              reasons=reasons))

    cands.sort(key=lambda c: -c.score)
    picked: list[Clip] = []
    for c in cands:
        if len(picked) >= count:
            break
        if any(min(c.end, p.end) - max(c.start, p.start) > 0 for p in picked):
            continue  # sem sobreposição temporal
        ct = set(tokens(c.text))
        if ct and any(_jaccard(ct, set(tokens(p.text))) > 0.45 for p in picked):
            continue  # conteúdo repetido (mesma fala dita duas vezes)
        picked.append(c)

    picked.sort(key=lambda c: c.start)
    for k, c in enumerate(picked, 1):
        c.id = f"short-{k:02d}"
        _make_pieces(c, units, teaser, max_len)
        c.hook_text = _hook_text(c, lang_texts, scores)
    return picked


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a and b) else 0.0


def _make_pieces(c: Clip, all_units: list[dict], teaser: bool, max_total: float | None = None) -> None:
    """Cortes naturais: começar ligeiramente antes da 1.ª palavra e acabar ~0,35 s depois da última,
    sem invadir a frase anterior/seguinte. Opcionalmente, um teaser (cold open) com o momento-pico."""
    idx = {u["id"]: k for k, u in enumerate(all_units)}
    i, j = idx[c.units[0]["id"]], idx[c.units[-1]["id"]]
    prev_end = all_units[i - 1]["end"] if i > 0 else 0.0
    next_start = all_units[j + 1]["start"] if j + 1 < len(all_units) else c.end + 1.0
    start = max(prev_end + 0.03, c.start - 0.15, 0.0)
    end = min(next_start - 0.03, c.end + 0.35)
    c.pieces = []
    pk = c.peak
    if teaser and pk is not None and pk.get("words") and pk["start"] - c.start > 3.0:
        tz = _teaser_range(c, pk)
        if tz:
            c.pieces.append(Piece(max(0.0, tz[0] - 0.08), tz[1] + 0.15, "teaser"))
        else:
            c.reasons.append("sem teaser (momento-pico curto demais ou sem conteúdo)")
    c.pieces.append(Piece(start, end, "main"))
    if max_total and len(c.pieces) > 1 and c.out_duration > max_total:
        c.pieces = c.pieces[1:]  # o teaser não pode fazer o Short ultrapassar a duração máxima
        c.reasons.append("teaser removido (excederia a duração máxima)")


TEASER_MIN, TEASER_MAX = 1.5, 3.5


def _teaser_range(c: Clip, pk: dict) -> tuple[float, float] | None:
    """Teaser = momento-pico + frases seguintes do corte, entre 1,5 e 3,5 s, a acabar no fim de uma
    palavra (de preferência no fim de uma frase), com >= 3 palavras e >= 2 palavras que não sejam palavrões."""
    k0 = next((k for k, u in enumerate(c.units) if u["id"] == pk["id"]), None)
    if k0 is None:
        return None
    words = [w for u in c.units[k0:] for w in (u.get("words") or [])]
    t0 = pk["start"]
    within = [w for w in words if w["end"] - t0 <= TEASER_MAX]
    if not within or within[-1]["end"] - t0 < TEASER_MIN:
        return None
    ends = [k for k, w in enumerate(within)
            if re.search(r"[.!?…]$", w["word"].strip()) and w["end"] - t0 >= TEASER_MIN]
    last = ends[-1] if ends else len(within) - 1
    chosen = within[:last + 1]
    text = "".join(w["word"] for w in chosen)
    if len(chosen) < 3 or profanity.clean_word_count(text) < 2:
        return None
    return t0, chosen[-1]["end"]


# palavras que não podem terminar um gancho (indicam frase cortada: "que eu tava com")
FUNCTION_END = set("""a o as os um uma de do da dos das em no na nos nas por para pra com sem que e ou mas se
meu minha teu tua seu sua the a an of to in on at for and or but with my your is are was""".split())


def _hook_ok(text: str) -> str | None:
    words = text.strip().rstrip(".!?…,;:").split()
    if not (2 <= len(words) <= 7) or len(" ".join(words)) > 40:
        return None
    joined = " ".join(words)
    if profanity.has_profanity(joined) or len(tokens(joined)) < 1:
        return None  # sem palavrões e com pelo menos uma palavra com conteúdo
    if norm(re.sub(r"[^\wÀ-ÿ]", "", words[-1])) in FUNCTION_END:
        return None  # termina numa palavra funcional = fragmento
    return joined.upper()


def _hook_options(text: str) -> list[str]:
    """Frase inteira; depois as primeiras orações (separadas por vírgula); depois cada oração sozinha."""
    t = text.strip()
    parts = [p.strip() for p in re.split(r"[,;:]", t) if p.strip()]
    opts = [t]
    for k in range(1, len(parts)):
        opts.append(", ".join(parts[:k]))
    opts += parts
    return opts


def _hook_text(c: Clip, lang_texts: dict, scores: dict | None = None) -> str:
    """Gancho: a frase-pico (ou a sua primeira oração) se for curta, completa e limpa; senão a melhor
    outra frase forte do corte; senão um texto pronto por categoria e idioma."""
    order = [c.peak] if c.peak else []
    rest = [u for u in c.units if u is not c.peak]
    if scores:
        rest.sort(key=lambda u: -scores.get(u["id"], (0, ""))[0])
    for u in order + rest[:8]:
        if not (u and u.get("text")):
            continue
        if u is not c.peak and not (scores and scores.get(u["id"], (0, ""))[0] >= 30):
            continue
        valid = [h for h in (_hook_ok(o) for o in _hook_options(u["text"])) if h]
        best = max(valid, key=lambda h: len(h.split()), default=None)  # a opção mais informativa
        if best and len(best.split()) >= 3:
            return best
        if best and u is c.peak:
            fallback_short = best  # 2 palavras: guardar, mas tentar algo melhor nas outras frases
    if "fallback_short" in locals():
        return fallback_short
    return lang_texts["hook"].get(c.category, lang_texts["hook"]["default"])
