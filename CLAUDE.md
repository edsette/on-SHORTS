# CLAUDE.md — on-SHORTS (GTA6-SHORTS)

Sistema local de produção de YouTube Shorts / TikTok / Instagram Reels com o Claude Code como agente.
O motor de edição é o **Cut-as-Code** em `vendor/cut-as-code` (submódulo Git fixado).

## Ambiente

- Windows 11, PowerShell 5.1, i5-13500H, 16 GB RAM, RTX 4060 Laptop 8 GB (NVENC disponível).
- Python: **sempre** `.\.venv\Scripts\python.exe` (3.12). Nunca o Python global nem o do GOG Galaxy.
- Node 26 / npm 11: usar **`npm.cmd` e `npx.cmd`** (o `npm.ps1` é bloqueado pela política de execução).
- FFmpeg/FFprobe 9.0.2 (Gyan), yt-dlp, Deno no PATH. Não instalar duplicados.
- Não alterar políticas de execução nem definições do Windows. Não instalar o CUDA Toolkit.

## Regras do Cut-as-Code

- Ler `vendor/cut-as-code/CLAUDE.md` e o `SKILL.md` completo de cada skill antes de a usar.
- **Não editar ficheiros em `vendor/`.** Adaptações vão para `scripts/` deste repo.
- Os comandos das skills correm a partir de `vendor/cut-as-code` (os caminhos `skills/...` são relativos a essa raiz). Substituir `python` por `..\..\.venv\Scripts\python.exe`.
- Os projetos de vídeo vivem em `projects/<nome>/` (raiz de projeto explícita, nunca o repo nem o vendor).
- Ordem: `video-understand` → `video-to-shorts` (plano) → `video-add-captions` → `video-add-content-cards` → render principal → `video-to-shorts` (extração).
- Respeitar os "Present + STOP": nunca simular uma resposta humana. O modo `agent` só com delegação explícita.
- Exemplos em bash nos SKILL.md (sobretudo `video-cut`) têm de ser convertidos para PowerShell.

## Motor de Shorts (Fase 6)

- Comando principal: `.\.venv\Scripts\python.exe scripts\make_shorts.py <vídeo|URL> --name <proj> --count N --duration S --lang pt-BR|pt-PT|en|auto --format 9:16|1:1|4:5|16:9 --style gaming|minimal|viral`
- Código em `scripts/shorts_engine/` (select, reframe, captions, render, metadata, source, styles). Documentação: `logs/fase6-motor-shorts.md`.
- **Nunca publicar automaticamente.** Links só com `--rights-confirmed` (direitos comerciais confirmados pelo utilizador).
- Usar `--dry-run` para ver a seleção sem renderizar. A análise fica em cache em `projects/<proj>/analysis/`.
- Rever sempre `review/<estilo>/short-NN.jpg` e o `report.md` antes de entregar.

## Transcrição

- **Preferir `scripts/analyze_video.py`** (GPU, `large-v3-turbo`, frases, momentos, timestamps refinados). Gera `transcript.json` no formato canónico do Cut-as-Code, utilizável no lugar do `transcribe.py` do vendor. Ver `logs/fase4-transcricao.md`.
- GPU: CUDA via `nvidia-cublas-cu12` (pip, no `.venv`). O script adiciona as DLLs ao PATH. Sem CUDA Toolkit.
- Modelos em `models/faster-whisper/`: `large-v3-turbo` (GPU, por omissão) e `medium` (CPU/fallback).
- O `transcribe.py` do vendor usa CPU/int8. O modelo por omissão `base.en` é só inglês: usar **`medium --lang auto`** (ou `--lang pt`).
- Modelo instalado: `medium` (1,46 GB) em `models/faster-whisper`.
- **Manter `av==18.1.0`**: o PyAV 19 é incompatível com o faster-whisper 1.2.1 (`metadata_errors`). Não atualizar o `av` sem testar.
- Cache de modelos partilhada: `--cache-dir <raiz-do-repo>\models\faster-whisper`.
- **Não descarregar modelos novos sem autorização do utilizador** (indicar tamanho e finalidade).

## Git

- `projects/`, `models/`, `.venv/`, `.claude/skills/` (junctions) e media não são versionados.
- Depois de clonar: `git submodule update --init` e `powershell -ExecutionPolicy Bypass -File scripts\setup-skills.ps1`.
