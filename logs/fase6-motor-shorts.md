# Fase 6 — Motor de produção de Shorts

- **Data:** 2026-11-19
- **Estado:** motor implementado e testado de ponta a ponta com um **vídeo sintético** (não havia nenhum vídeo real no PC). **Teste com vídeo real pendente.** A validação em PT-BR/PT-PT da Fase 4 também continua pendente. A Fase 5 não foi pedida.
- **100% local:** faster-whisper (GPU), FFmpeg (libass, NVENC, loudnorm), numpy. Sem chamadas ao Claude nem a APIs. **Nada é publicado.**

## 1. Utilização

```powershell
.\.venv\Scripts\python.exe scripts\make_shorts.py <vídeo.mp4 | URL> --name <projeto> `
    --count 3 --duration 30 --lang pt-BR --format 9:16 --style gaming
```

| Parâmetro | Valores | Por omissão |
|---|---|---|
| `--count` | quantidade de cortes | 3 |
| `--duration` | duração alvo (s). Intervalo = 0,7×–1,3× (máx. 90 s), ajustável com `--min-duration` / `--max-duration` | 30 |
| `--lang` | `auto`, `pt-BR`, `pt-PT`, `en` (transcrição + textos do gancho/CTA/metadados) | auto |
| `--format` | `9:16` (1080×1920), `1:1`, `4:5`, `16:9` | 9:16 |
| `--style` | `gaming`, `minimal`, `viral` | gaming |
| `--rights-confirmed` | **obrigatório para links** (direitos de uso comercial) | — |
| `--credit` | texto de crédito/fonte na descrição | (do yt-dlp, se houver) |
| `--no-teaser`, `--encoder auto/nvenc/x264`, `--dry-run` | opções | — |

Saídas em `projects/<projeto>/` (pasta fora do Git):

```
input/              fonte (links descarregados aqui + .info.json de proveniência)
analysis/           transcrição/análise/momentos — reutilizados (cache por tamanho+mtime+modelo)
shorts/<estilo>/    short-NN.mp4 · short-NN.json (tudo) · short-NN.txt (título/descrição/hashtags) · report.md
review/<estilo>/    short-NN.jpg (folha de contacto com 6 frames)
work/<estilo>/      .ass e filtergraphs (regeneráveis)
```

## 2. Como funciona (os 12 requisitos)

| # | Requisito | Implementação |
|---|---|---|
| 1 | Analisar o vídeo completo | `analyze_video.run_analysis`: transcrição large-v3-turbo na GPU, frases, picos de volume, cortes de cena (limiar 0,22, calibrado), momentos. Cache para não repetir |
| 2 | Momentos interessantes | Léxico PT/EN (engraçado/surpreendente/interessante) + picos de volume + exclamações + ritmo + cenas (Fase 4) |
| 3 | Melhores segmentos | Todas as janelas frase→frase dentro do intervalo de duração. Score = pico + 0,35×soma + densidade de fala + força nos primeiros 3 s + picos/cenas − desvio da duração alvo − pausas longas |
| 4 | Evitar repetidos | Seleção gulosa sem sobreposição temporal **e** rejeição por semelhança de texto (Jaccard > 0,45) |
| 5 | Gancho | (a) Título-gancho animado nos primeiros 2,4–2,8 s: a frase-pico (≤ 7 palavras) ou um texto por categoria/idioma; (b) **teaser/cold open**: se o pico não está nos 3 primeiros segundos, abre com ≤ 3,2 s do pico (gaming/viral), com flash de transição. O teaser é removido se exceder a duração máxima |
| 6 | Cortes naturais | Limites sempre em fronteiras de frase. −0,15 s antes da 1.ª palavra e +0,35 s depois da última, sem invadir as frases vizinhas. Timestamps refinados por energia (Fase 4) |
| 7 | 9:16 | **smart**: crop que segue o centro do movimento (diferença de frames a 4 fps, HUD ignorado, suavização de 2 s, saltos só em cortes de cena). **blur**: frame inteiro sobre fundo desfocado. Fonte já no formato: cover |
| 8 | Legendas sincronizadas | ASS (libass) palavra a palavra a partir dos timestamps, mapeadas para o tempo de saída (incluindo o teaser) |
| 9 | Destaque de palavras | Palavra ativa (karaoke) com cor/escala. Palavras-chave (léxico, números, nomes próprios, ênfase) coloridas por categoria |
| 10 | Zoom/efeitos | Zoom-punch em picos de volume e momentos fortes (máx. 4–5, ≥ 2,5 s de intervalo), shake em picos fortes, push-in lento (viral), flash na transição |
| 11 | MP4 | H.264 `h264_nvenc` (fallback libx264), AAC 192k, loudnorm −14 LUFS, `+faststart`, fps padrão (≤ 60). Verificação automática com ffprobe (resolução, áudio, duração ±0,25 s) |
| 12 | Títulos/descrições/hashtags | Heurístico local: gancho + emoji por categoria + tema (ex.: GTA 6 / Vice City); descrição com as 2 primeiras frases + crédito; hashtags (#shorts + tema + categoria + estilo + palavras-chave); variantes YouTube/TikTok/Instagram |

### Estilos

| | Gaming dinâmico | Minimalista | Viral com motion graphics |
|---|---|---|---|
| Enquadramento | crop inteligente | frame inteiro + fundo desfocado | crop inteligente |
| Legendas | Impact, 2 palavras, maiúsculas, palavra ativa verde | Segoe UI Semibold, 5 palavras, discretas | Arial Black, 3 palavras, palavra ativa amarela 120% |
| Gancho | caixa amarela com pop | caixa escura com fade | caixa vermelha com pop + rotação |
| Teaser + flash | sim | não | sim |
| Zoom / shake | punch 10%, shake 10 px | não | punch 14%, push-in 6%, shake 7 px |
| Extras | — | — | barra de progresso animada, CTA final animado |

Os motion graphics são desenhados em ASS (formas vetoriais animadas com `\t`, `\move`, `\clip`), renderizados pelo libass dentro do mesmo passo do FFmpeg. Não precisa de HyperFrames/Chrome.

## 3. Testes realizados

**Fonte de teste:** "gameplay" sintético de 99,8 s, 1920×1080, 30 fps, gerado localmente. Tem 17 falas TTS (en-US) com momentos engraçados, surpreendentes e interessantes, 2 explosões fortes, objetos em movimento em zonas diferentes do ecrã por cena, um HUD estático e **uma fala repetida** (para testar a deduplicação).

| Teste | Resultado |
|---|---|
| Análise | 224 palavras, 9 momentos, 2 picos, 4 cortes de cena. Transcrição em 2,4–2,7 s (GPU) |
| Cache | 2.ª e 3.ª execuções (outros estilos) sem nova transcrição |
| Seleção (3 × 25 s) | 3 cortes sem sobreposição, todos a começar e acabar em frases completas; a fala repetida não gerou um corte duplicado |
| Gaming 9:16 | 3/3 OK — 30,9 / 24,0 / 22,5 s, NVENC, 6–8 s de render cada |
| Minimal 9:16 | 3/3 OK — 4–5 s de render cada |
| Viral 9:16 | 3/3 OK — 6–8 s de render cada |
| Viral 1:1 com teaser | `short-02`: teaser 39,0–41,3 s + principal 27,7–48,9 s; flash na transição (2,32 s); 4 zoom-punches; 30/1 fps |
| Gaming 4:5 | OK 1080×1350 |
| Minimal 16:9 com libx264 | OK 1920×1080 (fallback de encoder validado) |
| Loudness | −15,1 LUFS integrado (alvo −14; loudnorm de 1 passagem) |
| Crop inteligente | Centro medido 0,78–0,80 numa cena com o objeto em x = 0,78; o objeto fica enquadrado (verificado nas folhas de contacto) |
| Link sem `--rights-confirmed` | recusado com mensagem |
| Publicação | nenhuma (`"published": false` em todos os JSON) |

### Problemas encontrados e corrigidos durante o teste

1. Teaser podia exceder a duração máxima → removido automaticamente nesse caso.
2. Limiar de cena 0,35 falhava cortes reais (scores 0,10–0,39) → 0,22, incluído na impressão digital da cache.
3. `avg_frame_rate` irregular em fontes concatenadas gerava 44745/1496 fps → `r_frame_rate` arredondado a uma taxa padrão.
4. Títulos com "| There" e hashtags `#vice #city #wait` → palavras em maiúscula no início de frase deixam de contar como nome próprio, filtro de palavras genéricas e de fragmentos do tema.
5. (Teste) o vídeo sintético inicial não tinha movimento real nem explosões altas o suficiente → regenerado. O motor não precisou de alterações para isso.

## 4. Limitações

- **Não testado com vídeo real** nem com **áudio em português**. Gameplay real tem câmara em movimento, música e HUD complexo: o crop por movimento pode precisar de afinação (ex.: seguir a personagem em vez do horizonte).
- Sem deteção de rostos/personagens. O crop segue o movimento, não "quem fala". Para facecam ou vlog, o estilo `minimal` (blur) é mais seguro.
- Os metadados são por regras; para títulos mais criativos, rever à mão (ou, opcionalmente, pedir sugestões ao Claude de forma pontual).
- Emojis nos títulos dependem da plataforma; as legendas no vídeo não usam emojis (o libass não renderiza emoji a cores).
- Loudnorm de uma passagem: ±1 LU do alvo.
- **Direitos:** o motor só aceita links com `--rights-confirmed`. Isso é uma declaração do utilizador, não uma verificação. Clips de GTA VI e conteúdo de terceiros continuam sujeitos a direitos de autor e às regras das plataformas.

## 5. Para concluir a fase

Correr com **um vídeo real** (de preferência gameplay próprio com comentário em português):

```powershell
.\.venv\Scripts\python.exe scripts\make_shorts.py projects\real\input\<clip>.mp4 --name real --count 3 --duration 30 --lang pt-BR --style gaming
```

Depois rever `projects/real/shorts/gaming/report.md`, as folhas de contacto em `review/` e os MP4.
