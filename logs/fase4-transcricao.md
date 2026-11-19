# Fase 4 — Inteligência e transcrição local

- **Data:** 2026-11-19
- **Estado:** pipeline instalado e **validado em inglês**. **Validação em PT-BR e PT-PT pendente**: não existe áudio/vídeo em português no PC nem vozes TTS portuguesas instaladas.
- **Sem APIs externas pagas.** Tudo corre localmente (faster-whisper + FFmpeg + numpy).

## 1. Avaliação e instalação

| Componente | Estado | Notas |
|---|---|---|
| FFmpeg / FFprobe 9.0.2 | ✅ já existia | Extração de áudio, `silencedetect`, deteção de cena (`select=gt(scene,…)`) |
| faster-whisper 1.2.1 / CTranslate2 4.9.0 | ✅ já existia (Fase 3) | `av==18.1.0` fixado (o PyAV 19 é incompatível) |
| **GPU (CUDA) para o faster-whisper** | ✅ **ativada** | O CTranslate2 exige `cublas64_12.dll`. Instalado `nvidia-cublas-cu12 12.9.2.10` (+ `nvidia-cuda-nvrtc-cu12`) **via pip no `.venv`** (~915 MB). **Sem CUDA Toolkit.** O cuDNN incluído no CTranslate2 bastou |
| Modelo `large-v3-turbo` (mobiuslabsgmbh/faster-whisper-large-v3-turbo) | ✅ descarregado | **1 547 MB** em `models/faster-whisper/`. Multilíngue (PT-BR, PT-PT, EN). Escolhido para a RTX 4060 |
| Modelo `medium` (Systran) | ✅ já existia | 1 460 MB. Alternativa em CPU / fallback |
| Análise de áudio e timestamps | ✅ implementada | `scripts/analyze_video.py` (numpy + FFmpeg). Sem bibliotecas extra |
| Diarização de oradores (pyannote) | ⛔ não instalada | Exige PyTorch (~2,5 GB), conta Hugging Face e aceitar termos de modelos restritos. Desproporcionado para gameplay com 1 narrador. Em vez disso: segmentação em "falas" por pausas |
| Modelos maiores (`large-v3`, 3,1 GB) | ⛔ não descarregados | O turbo tem precisão semelhante e é 3-4× mais rápido |

### Porquê `large-v3-turbo`

- Mesmo encoder do `large-v3` (melhor reconhecimento de português e de nomes próprios) com só 4 camadas no decoder, daí ser rápido.
- **VRAM medida:** pico de 3 095 MiB no sistema (cerca de 0,7 GB em repouso), ou seja ~2,4 GB para o modelo em float16. Sobra margem nos 8 GB.
- RAM: o processo fica muito abaixo dos 16 GB. Os pesos estão na GPU.

## 2. Script: `scripts/analyze_video.py`

```powershell
.\.venv\Scripts\python.exe scripts\analyze_video.py VIDEO --out projects\<nome>\analysis `
    [--model large-v3-turbo] [--device auto|cuda|cpu] [--lang auto|pt|en] `
    [--variant auto|pt-BR|pt-PT|en] [--no-scenes] [--no-refine]
```

| Saída | Conteúdo |
|---|---|
| `transcript.json` | **Formato canónico do Cut-as-Code** (`segments[] → words[]` com `start/end/word/prob`) + `device`, `variant`, `boundary_refined`. Validado com o `analyze.py` do vendor (exit 0) |
| `transcript.srt` | Legendas por segmento |
| `analysis.json` | Falas (turnos por pausa), picos de volume (z-score robusto), cortes de cena, curva de volume a 0,5 s, ritmo de fala, tempos e RTF |
| `moments.json` | Momentos `engracado` / `surpreendente` / `interessante` com score 0-100 e sinais + **janelas candidatas a Short** (20-60 s, alinhadas a frases) |
| `summary.md` | Resumo legível |

### Como os momentos são detetados (heurístico, explicável)

A unidade é a **frase**: o Whisper junta várias frases num só segmento, por isso o texto é cortado nas palavras terminadas em `. ! ?` ou em pausas.

| Sinal | Usado para |
|---|---|
| Léxico PT-BR / PT-PT / EN (ex.: "kkk", "rsrs", "ha ha", "hilário"; "caramba", "meu deus", "eita", "fogo", "bolas", "no way"; "olha", "repara", "easter egg", "did you know") | as 3 categorias |
| Pico de volume (z ≥ 2,5) até 1,5 s **antes** da frase (a reação vem depois do evento) | surpreendente / engraçado |
| Exclamações, perguntas | surpreendente / interessante |
| Fala acelerada (z > 1 no ritmo palavras/s) | surpreendente / interessante |
| Corte de cena próximo | surpreendente / interessante |

Os momentos são uma **shortlist** para o `/video-to-shorts`. A decisão editorial continua a ser do agente/utilizador, como o Cut-as-Code exige.

### Refinamento de timestamps (`refine_boundaries`)

O Whisper marca o início das palavras **~0,2-0,5 s cedo** depois de pausas, o que dá cortes "sujos" em Shorts. O script corrige cada palavra junto a uma pausa para a transição real silêncio→voz (ou voz→silêncio) na energia do áudio a 10 ms, com 20 ms de margem antes e 30 ms depois. É conservador: só atua quando há silêncio real (< -50 dB) e uma transição clara. Em áudio com música ou ruído de jogo contínuo não mexe em nada. Os valores originais ficam em `start_raw`/`end_raw`. Desativável com `--no-refine`.

## 3. Teste real (inglês)

**Ficheiro:** vídeo de 39,1 s, 1280×720, gerado localmente. Tem 5 frases com a voz TTS do Windows (en-US), uma explosão de ruído de 1,2 s e 6 cortes de cor (mudanças de cena). Não havia vídeos no PC.

### Transcrição

| Configuração | Transcrição | RTF | Carregar modelo | Palavras | Prob. média |
|---|---:|---:|---:|---:|---:|
| **large-v3-turbo, GPU float16** | **1,47 s** | **0,038** | 2,3 s | 83 | 0,988 |
| medium, GPU float16 | 2,11 s | 0,054 | 2,2 s | 83 | — |
| medium, CPU int8 | 17,67 s | 0,452 | 6,5 s | 83 | — |

- Texto 100% correto, incluindo "Grand Theft Auto 6" e "Vice City". Língua detetada `en` (p = 1,0).
- GPU ≈ **12× mais rápida** que CPU. Projeção com o turbo: 10 min de vídeo em ~25 s.

### Precisão dos timestamps (contra os onsets reais medidos no áudio)

| Fronteira | Whisper bruto | Após refinamento | Máximo após refinamento |
|---|---:|---:|---:|
| Inícios de frase (n = 13) | 353 ms de erro médio | **48 ms** | 210 ms |
| Fins de frase (n = 15) | 96 ms | **47 ms** | 160 ms |

Os casos sem silêncio real à volta (palavras a meio da frase) ficam com o valor do Whisper.
Caso especial verificado: "Oh my god" logo após a explosão. O refinamento ignora o ruído e encaixa no início real da voz (16,41 s, contra o real de ~16,42 s).

### Momentos detetados (todos os esperados, nenhum falso positivo)

| Início | Fim | Categoria | Score | Frase | Sinais |
|---:|---:|---|---:|---|---|
| 24,41 | 26,51 | engraçado | 80 | Ha ha ha, that was hilarious. | léxico: ha ha ha, hilarious |
| 16,41 | 17,12 | surpreendente | 75 | Oh my god. | léxico + pico de volume z = 4,5 (explosão) + corte de cena |
| 10,65 | 13,39 | interessante | 55 | Did you know there is a hidden easter egg…? | léxico ×3 + pergunta + fala acelerada |
| 8,15 | 9,78 | interessante | 50 | Look at this detail on the left. | léxico + corte de cena |
| 30,36 | 31,28 | engraçado | 40 | That is so funny. | léxico |
| 17,97 | 18,48 | surpreendente | 30 | No way. | léxico |
| 21,66 | 22,63 | surpreendente | 30 | That was insane. | léxico |

Janelas candidatas: `win-001` 21,46–38,25 s (engraçado, 80) e `win-002` 7,95–29,65 s (interessante, 55). O vídeo de teste é curto, por isso uma das janelas fica abaixo de 20 s e é marcada com `fits_short_20_90s: false`.

## 4. Problemas encontrados e corrigidos

1. `cublas64_12.dll` em falta → `nvidia-cublas-cu12` via pip. As DLLs são adicionadas ao PATH pelo próprio script (`_add_cuda_dlls`).
2. `numpy.bool_` não serializável em JSON → conversão de tipos numpy.
3. Segmentos do Whisper com várias frases escondiam momentos → pontuação por frase.
4. "ha ha ha" com espaços não era reconhecido → regex de riso tolerante a espaços e pontuação.
5. Inícios ~0,4 s adiantados → refinamento por energia, com proteção contra ruído (exige uma transição real).
6. Reação depois de um som forte perdia o pico → janela de picos de 1,5 s antes da frase.
7. Silêncio absoluto pode gerar texto inventado ("Thank you.") quando o VAD está desligado → o script usa sempre `vad_filter=True`.

## 5. Limitações conhecidas

- **PT-BR / PT-PT não validados** (sem material de teste). O Whisper não distingue variantes no código de língua (`pt`). `--variant` só ajusta o *prompt* inicial (ortografia/pontuação) e fica registado nos metadados.
- **Sem diarização**: "falas" = blocos de voz separados por pausas, não identificação de quem fala.
- Riso **sem palavras** (gargalhada) só é detetado via pico de volume ou se o Whisper o transcrever ("haha", "[risos]"). Não há classificador acústico de riso.
- Gameplay **sem narração** dá poucos momentos: os sinais visuais limitam-se a cortes de cena e picos de volume.
- O teste usa voz sintética (dicção limpa). Áudio real com música e ruído de jogo terá menor precisão; o refinamento de timestamps é desativado automaticamente nesses trechos.

## 6. Próximo passo obrigatório (antes da Fase 5)

Validar com **um clip real em português** (ideal: 1-3 min de gameplay teu com comentário, PT-BR ou PT-PT). Colocar em `projects/<nome>/input/` e correr:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_video.py projects\<nome>\input\<clip>.mp4 --out projects\<nome>\analysis --variant pt-BR
```

Critérios: texto revisto à mão com ≥ 95% das palavras corretas, inícios/fins de frase sem cortar sílabas, momentos coerentes com o que acontece no vídeo.
