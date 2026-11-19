# Instalação — Fase 3 (Cut-as-Code)

- **Data:** 2026-11-19
- **Opção escolhida:** clone completo (submódulo)
- **Configurações do Windows:** nenhuma alterada. Sem CUDA Toolkit. Sem modelos de IA descarregados.

## Feito

| Passo | Resultado |
|---|---|
| Submódulo `vendor/cut-as-code` | Commit `a96c13e` (Merge PR #40 `feat/integration`, 2026-10-07). Árvore de trabalho: 295 MB |
| `pip install faster-whisper Pillow` no `.venv` | faster-whisper 1.2.1, ctranslate2 4.9.0, Pillow 13.0.0, onnxruntime 1.32.0, av 19.0.2, numpy 2.5.5 (lista completa em `requirements.lock.txt`). `.venv` com 301 MB |
| Junctions `.claude/skills/` | 7 skills: cut-as-code, video-understand, video-cut, video-to-shorts, video-add-captions, video-add-content-cards, video-edit-compare. Recriáveis com `scripts/setup-skills.ps1` |
| `CLAUDE.md` do projeto | Regras: Python do `.venv`, `npm.cmd`/`npx.cmd`, sem editar o vendor, projetos em `projects/`, transcrição `medium --lang auto` |
| `.gitignore` | + `projects/`, `models/`, `.claude/skills/` |

## Self-checks do vendor (executados a partir de `vendor/cut-as-code`)

| Verificação | Resultado |
|---|---|
| `video-understand/check_protocol_extensions.py` | ✅ passou (8 grupos) |
| `video-cut/check_project_protocol.py` | ✅ passou |
| `video-add-captions/check_caption_style_config.mjs` | ✅ passou |
| `video-add-captions/check_caption_interaction.mjs` | ✅ todas passaram |
| `unittest video-cut/tests/test_inspect_bounds.py` | ✅ 6 testes OK |
| `unittest video-edit-compare/tests/test_make_compare.py` | ✅ 1 teste OK |
| `video-to-shorts/check_project_protocol.py` | ⚠️ 37/39 OK — **2 erros já conhecidos** (`fake_render()` sem `video_preset`, documentado no CLAUDE.md do vendor) |
| `video-add-captions/check_project_protocol.py` | ⚠️ falha: `No module named 'PIL'` num subprocesso |

### Causa da falha das legendas

O teste chama `subprocess.run(["python", ...])`. No Windows, o `python.exe` de um venv é um redirecionador para o Python base. O processo filho procura `python` primeiro na pasta do executável real (`Python312\`), que não tem Pillow. Mesmo com o `.venv` à frente no PATH, o resultado é o mesmo.

- Afeta **apenas este teste** e o fallback de `prepare_transcript.py`, que tem a opção `--python` para indicar o interpretador.
- O pipeline normal invoca os scripts diretamente com o Python do `.venv` e não é afetado.
- Soluções possíveis, ainda não aplicadas: instalar Pillow também no Python global, ou ignorar este teste.

## Modelo Whisper (autorizado pelo utilizador)

| Item | Resultado |
|---|---|
| Modelo | `Systran/faster-whisper-medium` (snapshot `08e178d`) |
| Local | `models/faster-whisper/` (não versionado) |
| Tamanho | 1 460 MB (`model.bin` 1 457 MB) |
| Primeiro carregamento | 65 s (inclui download) |

Aviso do `huggingface_hub` sobre symlinks no Windows: inofensivo. Sem symlinks, a cache copia ficheiros em vez de os ligar; com um único modelo não há duplicação. Pode ser silenciado com `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.

### Correção de compatibilidade: PyAV

- `faster-whisper 1.2.1` chama `av.open(..., metadata_errors="ignore")`, argumento que já **não existe no PyAV 19.0.2** (`TypeError`).
- Testei as versões por ordem decrescente: **`av==18.1.0`** é a mais recente que funciona. Fixada no `.venv` e em `requirements.lock.txt`. `pip check` sem conflitos.

### Teste de ponta a ponta do `transcribe.py` do vendor

- Áudio: frase sintetizada pela voz do Windows (Microsoft David, en-US; não há vozes PT instaladas), 8,5 s, convertida para 16 kHz mono com FFmpeg.
- Comando: `transcribe.py audio16k.wav transcript medium --lang auto --cache-dir models\faster-whisper`
- Resultado: exit 0 em **12,0 s** (CPU/int8, com o carregamento do modelo). Língua detetada `en` (p=0,993). 1 segmento, **24 palavras com timestamps**. Texto correto ("…Grand Theft Auto 6 trailer set in Vice City").

## Pendente

- **HyperFrames 0.9.70** (`npx.cmd --yes hyperframes@0.9.70`): o pré-carregamento foi recusado pelo classificador de permissões do Claude Code. É descarregado automaticamente no 1.º uso das legendas/cards, ou manualmente com:
  ```powershell
  $env:npm_config_cache = "$PWD\models\npm-cache"; npx.cmd --yes hyperframes@0.9.70 --version
  ```
- Primeiro teste de ponta a ponta com um clip curto com voz.
