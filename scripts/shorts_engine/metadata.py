"""Títulos, descrições e hashtags gerados localmente (heurístico, sem LLM).

Base: gancho, categoria, texto do corte **e o título/canal da fonte** (o tema do vídeo raramente é
dito em voz alta), nomes próprios e um dicionário de temas conhecidos. Textos de publicação ficam
sem palavrões (ver profanity.py). São um ponto de partida para revisão humana.
"""

from __future__ import annotations

import re
from collections import Counter

from . import profanity
from .select import STOP, Clip, norm

TOPICS = [  # (regex sobre texto normalizado, hashtags, nome para o título)
    (r"\bgta ?(6|vi)\b|grand theft auto (6|vi)\b", ["gta6", "gtavi"], "GTA 6"),
    (r"\bgta\b|grand theft auto", ["gta"], "GTA"),
    (r"\bleonida\b", ["leonida"], None),
    (r"vice city", ["vicecity"], None),
    (r"\btrailer\b", ["trailer"], None),
    (r"\brockstar\b", ["rockstargames"], None),
    (r"\bgameplay\b|\bjogo\b|\bgame\b|\bjogando\b", ["gameplay"], None),
]

EMOJI = {"engracado": "😂", "surpreendente": "🤯", "interessante": "👀", "default": "🔥"}

GENERIC = set("""okay alright anyway well right yeah guys today something thing things really actually
there here then when where which while about because every single always still even wait look
let know want going gonna chat""".split()) | set("""
pessoal galera entao agora gente coisa coisas hoje tipo bem velho velha mano mana cara caras meu minha
nossa deus olha olhe vamos vai vou ainda acho sabe sei quer queria pode posso tava estava tô to ta
bonito bonita legal muito pouco aqui ali isso isto aquilo outro outra mesmo mesma alan""".split())


def keywords(text: str, k: int = 6) -> list[tuple[str, bool]]:
    """(palavra, é_nome_próprio) por relevância. Nomes próprios = maiúscula a meio da frase."""
    cnt: Counter = Counter()
    proper: dict[str, bool] = {}
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", sent)
        for i, w in enumerate(words):
            nw = norm(w)
            if nw in STOP or nw in GENERIC or len(nw) < 4 or profanity.is_profane_word(w):
                continue
            is_prop = i > 0 and w[:1].isupper()
            proper[nw] = proper.get(nw, False) or is_prop
            cnt[nw] += 3 if is_prop else (2 if any(c.isdigit() for c in w) else 1)
    return [(w, proper[w]) for w, _ in cnt.most_common(k)]


def _title_case(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s.isupper() else s


def build(clip: Clip, texts: dict, lang: str, style_name: str, source_credit: str | None,
          source_title: str | None = None) -> dict:
    text = clip.text
    ctx = norm(text + " " + (source_title or ""))
    topic_tags: list[str] = []
    topic_name = ""
    for rx, tags, name in TOPICS:
        if re.search(rx, ctx):
            if name and not topic_name:
                topic_name = name
            topic_tags += [t for t in tags if t not in topic_tags]
    if "gta6" in topic_tags and "gta" in topic_tags:
        topic_tags.remove("gta")

    kws = keywords(text)
    cat = clip.category if clip.category in texts["tags"] else "default"
    cat_tags = texts["tags"].get(cat, [])
    style_tags = {"gaming": ["gaming"], "minimal": [], "viral": ["viral"]}[style_name]
    # palavras-chave como hashtag: só nomes próprios (personagens, lugares, marcas), nunca gíria
    kw_tags = [re.sub(r"[^a-z0-9]", "", w) for w, is_prop in kws
               if is_prop and len(w) >= 4 and not any(w in t for t in topic_tags)][:2]
    seen, tags = set(), []
    for h in ["shorts"] + topic_tags + cat_tags + style_tags + kw_tags:
        if h and h not in seen and not profanity.has_profanity(h):
            seen.add(h)
            tags.append("#" + h)
    tags = tags[:8]

    emoji = EMOJI.get(cat, EMOJI["default"])
    hook = profanity.censor(_title_case(clip.hook_text))
    title = f"{hook} {emoji}" + (f" | {topic_name}" if topic_name and topic_name.lower() not in hook.lower() else "")
    title = title[:95]

    first = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = profanity.censor(" ".join(first[:2])[:220])
    credit = f"\n\n{texts['credit']}: {source_credit}" if source_credit else ""
    description = f"{summary}\n\n{texts['desc_more']}{credit}\n\n{' '.join(tags)}"
    tiktok = f"{hook} {emoji} {' '.join(tags[:6])}"[:150]
    return {
        "title": title,
        "description": description,
        "hashtags": tags,
        "keywords": [w for w, _ in kws],
        "captions": {"youtube_shorts": title, "tiktok": tiktok,
                     "instagram_reels": f"{hook} {emoji}\n\n{summary}\n\n{' '.join(tags)}"},
        "language": lang,
    }
