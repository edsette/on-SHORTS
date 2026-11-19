"""Motor local de produção de Shorts (FFmpeg + libass + faster-whisper + numpy).

Módulos:
    styles    — estilos de edição, formatos e textos por idioma
    select    — escolha dos melhores segmentos, deduplicação e gancho
    reframe   — enquadramento 9:16 / 1:1 / 4:5 (crop inteligente por movimento ou fundo desfocado)
    captions  — legendas ASS sincronizadas por palavra, destaques, título-gancho, motion graphics
    render    — filtergraph FFmpeg, zoom/efeitos, encoding NVENC/x264, verificação
    metadata  — títulos, descrições e hashtags (heurístico, sem LLM)
    source    — entrada local ou download (yt-dlp) com confirmação de direitos
"""
