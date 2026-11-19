# Fase 8 — Teste de produção

- **Data:** 2026-11-19
- **Fonte:** "BEM VINDO A LEONIDA! - GRAND THEFT AUTO 6 - Parte 1", canal alanzoka (https://www.youtube.com/watch?v=kVy8zSfuRc0), live de 2 h 58 min, licença normal do YouTube. **O utilizador confirmou ter autorização do criador para uso comercial.** O crédito ao canal é incluído automaticamente na descrição.
- **Trecho usado:** primeiros 30 min, 1080p60 (777 MB), escolhido pelo utilizador para o teste.
- **Pedido:** 3 cortes × 45 s · 1080×1920 (9:16) · português brasileiro · Gaming dinâmico · legendas sincronizadas.
- **Comando:** `shorts --video <link> --nome gta6-leonida-parte1 --cortes 3 --duracao "45 segundos" --idioma "Português BR" --estilo "Gaming dinâmico" --formato 9:16 --direitos --trecho "primeiros 30 minutos"`
- **Publicação:** nenhuma.

## 1. Resultado final (depois das correções)

| | short-01 | short-02 | short-03 |
|---|---|---|---|
| Origem | teaser 901,0–903,2 + 861,3–903,4 s | 1379,0–1423,7 s | teaser 1785,1–1787,2 + 1739,8–1787,4 s |
| Duração | 44,3 s | 44,7 s | 49,8 s |
| Conteúdo | Fuga à polícia → mergulho → descobre um jet ski ("tem que fazer ligação direta no jet") | Contemplação: nuvens, câmaras do jogo, "isso é bizarro" | Stealth na quinta: telemóvel no meio da missão → martelo ("vou dar martelada nos caras") |
| Título | Tem que fazer ligação direta no jet 🤯 \| GTA 6 | Meu deus, olha essas nuvens 🤯 \| GTA 6 | Vou dar martelada nos caras, meu deus 🤯 \| GTA 6 |
| Hashtags | #shorts #gta6 #gtavi #leonida #gameplay #inacreditavel #surpresa #gaming | #shorts #gta6 #gtavi #leonida #inacreditavel #surpresa #gaming | #shorts #gta6 #gtavi #leonida #inacreditavel #surpresa #gaming #tiktok |

## 2. Verificação dos 10 critérios (resultado final)

| # | Critério | Estado | Medição |
|---|---|---|---|
| 1 | Os cortes fazem sentido | ✅ | Cada corte tem um mini-arco (fuga → jet ski; câmaras → "bizarro"; stealth → martelo). O corte fraco da 1.ª versão ("Tô, tchau. Nove meses atrás.") foi eliminado pelas penalizações de densidade de fala e de fragmentos |
| 2 | Frases sem cortes | ✅ | Os 3 começam após pausas de 3–10 s e acabam no fim de uma frase, 0,35 s depois da última palavra. Nenhum acaba no fim artificial do trecho descarregado |
| 3 | Legendas sincronizadas | ✅ | Os MP4 finais foram re-transcritos e comparados com os eventos de legenda: erro médio 31–58 ms, p90 ≤ 90 ms. Palavras ditas com legenda: 98–99% |
| 4 | Enquadramento | ✅ | Crop central fixo: a personagem fica inteira no frame (ligeiramente à esquerda, como na câmara de ombro de GTA). Antes, o crop seguia a folhagem e cortava a personagem |
| 5 | Áudio | ✅ | −14,9 / −15,3 / −16,6 LUFS (alvo −14), true peak −1,4 dBFS, sem clipping nem silêncios ≥ 2 s, AAC 48 kHz estéreo a 192 kbps. A fonte estava a −19,9 LUFS |
| 6 | Efeitos | ✅ | 4 zoom-punches por corte (antes: 1, 4 e 1). Teasers de 2,1–2,2 s com frase completa (antes: 0,87 s, "Puta merda."). Sem congelamentos |
| 7 | Duração | ✅ | 44,3 / 44,7 / 49,8 s, com o intervalo novo de 38–52 s (antes: 49,5 / 55,7 / 45,7 s) |
| 8 | Reprodução | ✅ | Os 3 MP4 descodificam do início ao fim sem erros. H.264 High, 1080×1920, 60 fps, `+faststart` |
| 9 | Títulos e descrições | ✅ | Sem palavrões nos títulos, ganchos e descrições (censurados: "p****"). Tema GTA 6 e Leonida vindo do título da fonte. Crédito "Fonte: alanzoka — link". Variantes TikTok/Instagram |
| 10 | Organização | ✅ | `output/gta6-leonida-parte1/` → `input/` (trecho + .info.json), `analysis/`, `gaming_9x16_3x45s_pt-BR/` (`export/`, `review/`, `work/`, `logs/`, `state.json`, `report.md`) |

## 3. Problemas encontrados e correções

| # | Problema (1.ª versão) | Correção | Ficheiro |
|---|---|---|---|
| P1 | O crop seguia o movimento (folhagem, câmara) e a personagem ficava na margem ou saía | Crop central fixo nos estilos gaming/viral (`track_offset = 0`). Ajustável em `config/shorts.toml` → `seguimento_movimento` (0–0,5), com suavização de 4 s | `reframe.py`, `styles.py`, `pipeline.py`, `shorts.toml` |
| P2 | 495 "cortes de cena" falsos em 30 min (intervalo mediano 0,03 s) | Deteções a menos de 1,5 s agrupadas (fica a mais forte) + máximo adaptativo de 8/min. Resultado: 163 cortes, mínimo de 1,5 s, mediano de 4,5 s. Cache das cenas separada da transcrição (não retranscreve) | `analyze_video.py` |
| P3 | 0 picos de volume numa live (som contínuo) | Picos locais: z ≥ 3 face aos 15 s à volta e ≥ 4 dB acima da mediana global, além do critério global. z limitado a 10. Resultado: 24 picos em 30 min | `analyze_video.py` |
| P4 | Título "Puta merda 🔥"; palavrões em ganchos e descrições | Filtro PT/EN (`profanity.py`): ganchos e títulos nunca com palavrões; descrições e textos sociais censurados. As legendas no vídeo mantêm a fala original | `profanity.py`, `select.py`, `metadata.py` |
| P5 | Teaser de 0,87 s só com um palavrão | Teaser de 1,5–3,5 s, a acabar numa palavra (de preferência no fim de uma frase), ≥ 3 palavras e ≥ 2 sem palavrões; senão não há teaser | `select.py` |
| P6 | #gta6 em falta; hashtags #velho #bonito #botar | Tema detetado também no título da fonte; hashtags de palavras-chave só com nomes próprios; gíria comum filtrada; máximo 8 | `metadata.py`, `pipeline.py` |
| P7 | Corte fraco com pouca fala e final solto | Penalização por densidade < 1,2 palavras/s, por início ou fim em fragmento isolado, e por acabar a < 3 s do fim de um trecho descarregado | `select.py` |
| P8 | Durações até +24% acima do pedido | Intervalo 0,85–1,15× (era 0,7–1,3×) e penalização do desvio duplicada | `select.py`, `pipeline.py`, `shorts.toml` |
| P9 | Folha de contacto repetia frames a 60 fps | 1 seek e 1 frame por instante | `render.py` |
| P10 | Contador de palavras destacadas era do vídeo inteiro | Conta só as palavras do corte (agora 12–15 de 74–95) | `captions.py` |
| P11 | Ganchos: "MEU DEUS" (vago), "QUE EU TAVA COM" (fragmento) | Gancho = opção mais informativa (≤ 7 palavras) entre a frase inteira e as primeiras orações; rejeita finais em palavras funcionais ("com", "de", "que"…) | `select.py` |
| P12 | Mensagem "a descarregar" mesmo com o ficheiro já em disco | Só aparece quando há download real | `pipeline.py`, `source.py` |
| — | (nova funcionalidade) | Campo `Trecho:` / `--trecho` ("primeiros 30 minutos", "10:00-40:00") para descarregar só parte de lives longas | `shorts_cli.py`, `source.py`, `pipeline.py` |

## 4. Antes e depois

| | Antes | Depois |
|---|---|---|
| Picos de volume / cortes de cena | 0 / 495 | 24 / 163 |
| Durações | 49,5 / 55,7 / 45,7 s | 44,3 / 44,7 / 49,8 s |
| Títulos | "Ninguém esperava isso", "Puta merda", "Meu deus, tá um cara ali" (sem GTA 6 em 2 de 3) | 3 títulos com conteúdo, sem palavrões, todos com "GTA 6" |
| Teasers | 1 (0,87 s, palavrão) | 2 (2,1–2,2 s, frases completas) |
| Zoom-punches | 1 / 4 / 1 | 4 / 4 / 4 |
| Personagem no frame | cortada ou ausente em vários frames | inteira em todos os frames verificados |
| Tempo de repetição (download e transcrição em cache) | — | ≈ 2 min para os 3 cortes, com recálculo das cenas |

## 5. Limitações conhecidas (não bloqueiam a produção)

- **Legendas do próprio jogo** (texto queimado na imagem, centrado em baixo) ficam cortadas nas laterais pelo crop 9:16. Para cenas com muito diálogo do jogo, o estilo Minimalista (frame inteiro sobre fundo desfocado) evita isto.
- **Falas das personagens do jogo** não são legendadas quando o Whisper as ignora como fundo (cobertura de 98–99% das palavras).
- O streamer fala de forma fragmentada ("no meio da…", "que eu tava com…"); algumas frases incompletas ficam no meio dos cortes, porque fazem parte da fala real.
- Os títulos são heurísticos. A curadoria semântica estilo OpusClip (Hook/Flow/Value/Trend) continua pendente de decisão (IA local, Claude ou regras).
- Os ficheiros têm 1,4–2 MB/s (60 fps, CQ 20): ótimos para upload, mas pesados para guardar.

## 6. Conclusão

Os 10 critérios estão cumpridos com o vídeo real. **O sistema está pronto para produção** com vídeos de gameplay narrados em PT-BR, mantendo a revisão humana antes de publicar (folhas de contacto em `review/`, textos em `export/*.txt`).
