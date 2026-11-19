"""Estilos de edição, formatos de saída e textos por idioma."""

from __future__ import annotations

# Cores ASS: &HAABBGGRR (alpha, azul, verde, vermelho)
WHITE = "&H00FFFFFF"
BLACK = "&H00000000"
YELLOW = "&H0000E6FF"
GREEN = "&H0050FF50"
RED = "&H004646FF"
CYAN = "&H00FFDC00"
SOFT_YELLOW = "&H0080E8FF"

FORMATS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "16:9": (1920, 1080),
}

STYLES: dict[str, dict] = {
    "gaming": {
        "label": "Gaming dinâmico",
        "reframe": "smart",            # crop 9:16; em gameplay 3.ª pessoa fica centrado (track_offset)
        "track_offset": 0.0,           # 0 = centro fixo (personagem ao centro); até 0.5 = segue o movimento
        "font": "Impact", "font_size": 0.050, "uppercase": True,
        "words_per_caption": 2, "max_chars": 16,
        "primary": WHITE, "outline": BLACK, "outline_w": 0.0045, "shadow": 0.0015,
        "karaoke": True, "active": GREEN, "active_scale": 115,
        "highlight": {"engracado": YELLOW, "surpreendente": RED, "interessante": CYAN, "default": YELLOW},
        "pop": True, "caption_y": 0.68,
        "hook": "box", "hook_back": "&H2000D7FF", "hook_text": BLACK, "hook_secs": 2.6,
        "teaser": True,                 # cold open com o momento-pico
        "zoom_punch": 0.10, "push_in": 0.0, "shake_px": 10, "flash": True,
        "progress": False, "cta": False, "max_punches": 4,
    },
    "minimal": {
        "label": "Minimalista",
        "reframe": "blur",             # vídeo inteiro sobre fundo desfocado
        "font": "Segoe UI Semibold", "font_size": 0.034, "uppercase": False,
        "words_per_caption": 5, "max_chars": 32,
        "primary": WHITE, "outline": BLACK, "outline_w": 0.0, "shadow": 0.0012,
        "karaoke": False, "active": WHITE, "active_scale": 100,
        "highlight": {"default": SOFT_YELLOW},
        "pop": False, "caption_y": 0.80,
        "hook": "fade", "hook_back": "&H80000000", "hook_text": WHITE, "hook_secs": 2.4,
        "teaser": False,
        "zoom_punch": 0.0, "push_in": 0.0, "shake_px": 0, "flash": False,
        "progress": False, "cta": False, "max_punches": 0,
    },
    "viral": {
        "label": "Viral com motion graphics",
        "reframe": "smart",
        "track_offset": 0.0,
        "font": "Arial Black", "font_size": 0.052, "uppercase": True,
        "words_per_caption": 3, "max_chars": 20,
        "primary": WHITE, "outline": BLACK, "outline_w": 0.005, "shadow": 0.002,
        "karaoke": True, "active": YELLOW, "active_scale": 120,
        "highlight": {"engracado": YELLOW, "surpreendente": RED, "interessante": CYAN, "default": CYAN},
        "pop": True, "caption_y": 0.62,
        "hook": "pop", "hook_back": "&H002020FF", "hook_text": WHITE, "hook_secs": 2.8,
        "teaser": True,
        "zoom_punch": 0.14, "push_in": 0.06, "shake_px": 7, "flash": True,
        "progress": True, "cta": True, "max_punches": 5,
    },
}

TEXT = {
    "pt-BR": {
        "hook": {"engracado": "MORRI DE RIR COM ISSO", "surpreendente": "NINGUÉM ESPERAVA ISSO",
                 "interessante": "REPARA NESSE DETALHE", "default": "VOCÊ PRECISA VER ISSO"},
        "cta": "SEGUE PRA MAIS!",
        "desc_more": "Segue para mais cortes!",
        "tags": {"engracado": ["humor", "engracado"], "surpreendente": ["inacreditavel", "surpresa"],
                 "interessante": ["curiosidades", "detalhes"]},
        "credit": "Fonte",
    },
    "pt-PT": {
        "hook": {"engracado": "MORRI A RIR COM ISTO", "surpreendente": "NINGUÉM ESPERAVA ISTO",
                 "interessante": "REPARA NESTE DETALHE", "default": "TENS DE VER ISTO"},
        "cta": "SEGUE PARA MAIS!",
        "desc_more": "Segue para mais cortes!",
        "tags": {"engracado": ["humor", "engracado"], "surpreendente": ["inacreditavel", "surpresa"],
                 "interessante": ["curiosidades", "detalhes"]},
        "credit": "Fonte",
    },
    "en": {
        "hook": {"engracado": "I CAN'T STOP LAUGHING", "surpreendente": "NOBODY EXPECTED THIS",
                 "interessante": "LOOK AT THIS DETAIL", "default": "YOU NEED TO SEE THIS"},
        "cta": "FOLLOW FOR MORE!",
        "desc_more": "Follow for more clips!",
        "tags": {"engracado": ["funny", "comedy"], "surpreendente": ["unexpected", "wow"],
                 "interessante": ["details", "didyouknow"]},
        "credit": "Source",
    },
}


def ui_lang(requested: str, detected: str | None) -> str:
    if requested in TEXT:
        return requested
    if (detected or "").startswith("pt"):
        return "pt-BR"
    return "en"
