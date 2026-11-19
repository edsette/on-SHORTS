"""Filtro de palavrões (PT-BR, PT-PT, EN) para títulos, ganchos, descrições e hashtags.

As legendas no vídeo mantêm a fala original. Títulos e textos de publicação devem ficar limpos,
porque palavrões no título/miniatura reduzem o alcance e a monetização nas plataformas.
"""

from __future__ import annotations

import re
import unicodedata

WORDS = {
    # PT
    "porra", "caralho", "carai", "caraio", "krl", "crl", "merda", "puta", "putaria", "puto", "putos",
    "foda", "fodase", "foda-se", "fodasse", "foder", "fodido", "fodida", "fudeu", "fudido", "fodeu",
    "cacete", "buceta", "boceta", "cu", "cuzao", "viado", "fdp", "pqp", "vsf", "tnc", "arrombado",
    "arrombada", "bosta", "piroca", "caralhos", "merdas",
    # EN
    "fuck", "fucking", "fucked", "fucker", "motherfucker", "shit", "shitty", "bitch", "asshole",
    "dick", "wtf", "bullshit",
}


def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", _n(text))


def is_profane_word(word: str) -> bool:
    w = _n(re.sub(r"[^\wÀ-ÿ-]", "", word))
    return w in WORDS or w.replace("-", "") in WORDS


def has_profanity(text: str) -> bool:
    return any(t in WORDS or t.replace("-", "") in WORDS for t in _tokens(text))


def clean_word_count(text: str) -> int:
    return sum(1 for t in _tokens(text) if t not in WORDS and t.replace("-", "") not in WORDS)


def censor(text: str) -> str:
    """'Puta merda, que isso' -> 'P*** m****, que isso'"""
    def rep(m: re.Match) -> str:
        w = m.group(0)
        return w[0] + "*" * (len(w) - 1) if is_profane_word(w) else w
    return re.sub(r"[\wÀ-ÿ]+(?:-[\wÀ-ÿ]+)?", rep, text)
