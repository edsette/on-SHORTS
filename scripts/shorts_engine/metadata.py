"""Títulos, descrições e hashtags gerados localmente (heurístico, sem LLM).

Base: texto do corte, gancho, categoria, palavras-chave (frequência sem stopwords + nomes próprios)
e um dicionário de temas conhecidos (ex.: GTA). Os textos são um ponto de partida para revisão humana.
"""

from __future__ import annotations

import re
from collections import Counter

from .select import STOP, Clip, norm

TOPICS = [  # (regex sobre texto normalizado, hashtags)
    (r"\bgta\b|grand theft auto", ["gta6", "gtavi", "gta"]),
    (r"vice city", ["vicecity"]),
    (r"\btrailer\b", ["trailer"]),
    (r"\brockstar\b", ["rockstargames"]),
    (r"\bgameplay\b|\bjogo\b|\bgame\b", ["gameplay", "gaming"]),
]

EMOJI = {"engracado": "😂", "surpreendente": "🤯", "interessante": "👀", "default": "🔥"}


GENERIC = set("""okay alright anyway well right yeah guys today something thing things really actually
there here then when where which while about because every single always still even wait look
let know want going gonna""".split()) | set("""
pessoal galera entao agora gente coisa coisas hoje tipo bem""".split())


def keywords(text: str, k: int = 6) -> list[str]:
    cnt: Counter = Counter()
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", sent)
        for i, w in enumerate(words):
            nw = norm(w)
            if nw in STOP or nw in GENERIC or len(nw) < 4:
                continue
            proper = i > 0 and w[:1].isupper()   # maiúscula a meio da frase = nome próprio
            cnt[nw] += 3 if proper else (2 if any(c.isdigit() for c in w) else 1)
    return [w for w, _ in cnt.most_common(k)]


def _title_case(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s.isupper() else s


def build(clip: Clip, texts: dict, lang: str, style_name: str, source_credit: str | None) -> dict:
    text = clip.text
    nt = norm(text)
    topic_tags: list[str] = []
    for rx, tags in TOPICS:
        if re.search(rx, nt):
            topic_tags += [t for t in tags if t not in topic_tags]
    kws = keywords(text)
    cat = clip.category if clip.category in texts["tags"] else "default"
    cat_tags = texts["tags"].get(cat, [])
    style_tags = {"gaming": ["gaming", "gamer"], "minimal": [], "viral": ["viral", "fyp"]}[style_name]
    kw_tags = [re.sub(r"[^a-z0-9]", "", k) for k in kws
               if len(k) >= 5 and not any(k in t for t in topic_tags) and k not in GENERIC][:2]
    hashtags = ["shorts"] + topic_tags + cat_tags + style_tags + kw_tags
    seen, tags = set(), []
    for h in hashtags:
        if h and h not in seen:
            seen.add(h)
            tags.append("#" + h)
    tags = tags[:10]

    emoji = EMOJI.get(cat, EMOJI["default"])
    hook = _title_case(clip.hook_text)
    if any(t.startswith("gta") or t == "vicecity" for t in topic_tags):
        topic = "GTA 6"
        tags_topic = ["gta6", "vicecity"]
        topic_tags = tags_topic + [t for t in topic_tags if t not in tags_topic]
        hashtags[1:1] = [t for t in tags_topic if t not in hashtags]
        seen, tags = set(), []
        for h in hashtags:
            if h and h not in seen:
                seen.add(h)
                tags.append("#" + h)
        tags = tags[:10]
    else:
        topic = kws[0].capitalize() if kws else ""
    title = f"{hook} {emoji}" + (f" | {topic}" if topic and topic.lower() not in hook.lower() else "")
    title = title[:95]

    first = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(first[:2])[:220]
    credit = f"\n\n{texts['credit']}: {source_credit}" if source_credit else ""
    description = f"{summary}\n\n{texts['desc_more']}{credit}\n\n{' '.join(tags)}"
    tiktok = f"{hook} {emoji} {' '.join(tags[:6])}"[:150]
    return {
        "title": title,
        "description": description,
        "hashtags": tags,
        "keywords": kws,
        "captions": {"youtube_shorts": title, "tiktok": tiktok,
                     "instagram_reels": f"{hook} {emoji}\n\n{summary}\n\n{' '.join(tags)}"},
        "language": lang,
    }
