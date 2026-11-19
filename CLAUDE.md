# CLAUDE.md — on-SHORTS (GTA6-SHORTS)

Sistema local de produção de YouTube Shorts / TikTok / Instagram Reels a partir de **gameplay narrado**
(foco: GTA 6, streamers BR), com o Claude Code como agente. Motor próprio em `scripts/shorts_engine/`;
o **Cut-as-Code** (`vendor/cut-as-code`, submódulo fixado) fica disponível mas não é alterado.
Repositório: https://github.com/edsette/on-SHORTS (ramo `main`).

## Como retomar depois de `/clear`

1. Ler esta secção e **"Estado atual e próximos passos"** abaixo.
2. Ver o último relatório em `logs/` (`fase8-teste-producao.md` é o mais recente) e `git log --oneline -5`.
3. Continuar pelo primeiro item pendente da lista "Próximos passos". Não refazer fases concluídas.

## Preferências do utilizador (seguir sempre)

- **Responder em português** (o utilizador escreve em PT-BR). Relatórios e documentação em português.
- Trabalhar **por fases**: quando o pedido diz "analisar primeiro" ou "aguardar autorização", **não modificar ficheiros nem instalar nada** até ao "sim". Relatórios de fase em `logs/`.
- **Antes de descarregar modelos de IA ou instalações grandes**: indicar tamanho e finalidade e esperar confirmação.
- **Tudo local e gratuito**: sem APIs pagas, sem dependências pagas, poucas chamadas desnecessárias ao Claude. Aproveitar o que já está instalado; não reinstalar nem duplicar FFmpeg/Python/Node.
- **Nunca publicar** conteúdo. Links só com direitos comerciais confirmados pelo utilizador (`--direitos`).
- Não interromper tarefas em segundo plano. Não alterar o funcionamento do Cut-as-Code.
- Testar sempre com dados reais quando possível, verificar o resultado (frames, áudio, sincronização) e corrigir antes de declarar pronto.
- Fazer commit e push no fim de cada fase concluída (identidade local `edsette <edsette@users.noreply.github.com>`).

## Estado atual e próximos passos

**Concluído (Fases 1–4 e 6–8):** ambiente, Cut-as-Code, transcrição local na GPU (large-v3-turbo),
motor de Shorts (3 estilos, 4 formatos, legendas ASS, NVENC, metadados), interface simples
(`/shorts`, `shorts.cmd`, `config/shorts.toml`, `output/`, retoma), teste de produção real PT-BR
(alanzoka, GTA 6) com 10/10 critérios. A Fase 5 nunca foi pedida. PT-PT ainda não foi validado com áudio real.

**Decisões do utilizador (2026-11-19):**
- **Sem IA local**: não instalar Ollama nem modelos de linguagem locais (decisão explícita do utilizador).
  A curadoria estilo OpusClip (Hook/Flow/Value/Trend, gancho, ideia completa), se for feita, passa pelo
  `/shorts` sem IA local — a forma exata (Claude a escolher entre candidatos no `/shorts`, ou só regras) está por confirmar.
- **Facecam do streamer é obrigatória em muitos clips**: detetar a webcam (normalmente num canto),
  identificar o rosto e enquadrá-lo no Short (layout dividido: facecam em cima, gameplay em baixo,
  ou facecam sobreposta), quando a fonte tiver webcam.
- O resto fica como está por agora.

**Próximos passos (por ordem):**
1. **Facecam**: análise e proposta (deteção do retângulo da webcam nos cantos + deteção facial local,
   ex. OpenCV com detetor YuNet, gratuito; layouts no `reframe.py`/`render.py`; opção em `shorts.toml`
   e no pedido do `/shorts`). Apresentar o plano e as dependências antes de instalar.
2. **Curadoria estilo OpusClip sem IA local** (confirmar com o utilizador: Claude no `/shorts` ou regras), score por critério no relatório.
3. **Dashboard web local** (arquitetura já analisada e aprovada só como proposta: servidor Python stdlib +
   SSE, SPA escura sem build, fila de trabalhos, aprovar/rejeitar clips, monitor CPU/RAM/GPU via ctypes +
   nvidia-smi). Aguarda aprovação para implementar.

**Dados de teste:** `output/gta6-leonida-parte1/` (trecho de 30 min já descarregado e transcrito; reutilizar
com o mesmo pedido + `--refazer`). Este vídeo **não tem facecam**: para testar a facecam é preciso um vídeo com webcam.

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

## Motor de Shorts (Fases 6 e 7)

- **Interface principal:** `/shorts` (skill `.claude/skills/shorts/`) → `.\shorts.cmd --video ... --cortes ... --duracao ... --idioma ... --estilo ...`. Guia: `COMO-USAR.md`. Configuração: `config/shorts.toml`. Resultados: `output/`.
- Pipeline com estado e retoma: `scripts/shorts_engine/pipeline.py`. Correr o mesmo pedido retoma; `--refazer` recomeça; `--listar` mostra o estado.
- Interface avançada: `.\.venv\Scripts\python.exe scripts\make_shorts.py <vídeo|URL> --count N --duration S --lang pt-BR|pt-PT|en|auto --format 9:16|1:1|4:5|16:9 --style gaming|minimal|viral`
- Código em `scripts/shorts_engine/` (select, reframe, captions, render, metadata, source, styles). Documentação: `logs/fase6-motor-shorts.md`.
- **Nunca publicar automaticamente.** Links só com `--rights-confirmed` (direitos comerciais confirmados pelo utilizador).
- Usar `--dry-run` para ver a seleção sem renderizar. A análise fica em cache em `projects/<proj>/analysis/`.
- Rever sempre `review/<estilo>/short-NN.jpg` e o `report.md` antes de entregar.

## Transcrição

- **Preferir `scripts/analyze_video.py`** (GPU, `large-v3-turbo`, frases, momentos, timestamps refinados). Gera `transcript.json` no formato canónico do Cut-as-Code, utilizável no lugar do `transcribe.py` do vendor. Ver `logs/fase4-transcricao.md`.
- GPU: CUDA via `nvidia-cublas-cu12` (pip, no `.venv`). O script adiciona as DLLs ao PATH. Sem CUDA Toolkit.
- Modelos em `models/faster-whisper/`: `large-v3-turbo` (1,55 GB, GPU, por omissão) e `medium` (1,46 GB, CPU/fallback).
- O `transcribe.py` do vendor usa CPU/int8. O modelo por omissão `base.en` é só inglês: usar **`medium --lang auto`** (ou `--lang pt`).
- **Manter `av==18.1.0`**: o PyAV 19 é incompatível com o faster-whisper 1.2.1 (`metadata_errors`). Não atualizar o `av` sem testar.
- Cache de modelos partilhada: `--cache-dir <raiz-do-repo>\models\faster-whisper`.
- **Não descarregar modelos novos sem autorização do utilizador** (indicar tamanho e finalidade).

## Git

- `output/`, `projects/`, `models/`, `.venv/`, as junctions em `.claude/skills/` e media não são versionados. A skill `.claude/skills/shorts/` é versionada.
- Depois de clonar: `git submodule update --init` e `powershell -ExecutionPolicy Bypass -File scripts\setup-skills.ps1`.
