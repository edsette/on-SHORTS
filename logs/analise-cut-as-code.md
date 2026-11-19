# Análise do Cut-as-Code — Fase 3

- **Data:** 2026-11-19
- **Repositório:** https://github.com/WhiteTowerAI/cut-as-code (ramo `main`, último push 2026-11-05, licença MIT)
- **Método:** leitura remota via API do GitHub / raw (nada foi clonado, instalado ou executado do repositório). Os documentos lidos ficaram numa pasta temporária fora do projeto.
- **Estado:** apenas análise. Nenhuma instalação ou alteração foi feita.

---

## 1. O que é

Conjunto de **skills de edição de vídeo para agentes** (Claude Code, Codex, OpenClaw). O agente escreve as decisões de edição em ficheiros JSON legíveis ("code is the edit"), o utilizador revê em páginas HTML locais e no fim é feito um único render com FFmpeg. Tudo local, sem upload para a cloud.

Estrutura base: **todas as skills dependem de transcrição com timestamps por palavra**. O transcript é o formato partilhado entre skills.

## 2. Estrutura do repositório

| Pasta / ficheiro | Conteúdo | Tamanho |
|---|---|---|
| `README.md`, `CLAUDE.md` (= `AGENTS.md`, idênticos) | Documentação e regras para agentes | 10 KB / 15 KB |
| `.mcp.json` | Servidor MCP `cut-as-code-editor` → `node ./runtime/mcp.cjs` (1 ferramenta: `open_editor`) | — |
| `.codex-plugin/plugin.json` | Manifesto de plugin (Codex) | — |
| `runtime/` | Editor Hub (Node `.cjs`) + serviço de protocolo (Python) + testes | ~0,6 MB |
| `ui/` | Editor no browser (React 19 + Vite 6 + Tailwind 4 + Playwright) | ~8 MB |
| `launcher/` | `Cut as Code Editor.cmd` + `launcher.cjs` | — |
| `scripts/` | Build do plugin / compliance | — |
| `skills/` | 10 skills (ver abaixo) | ~285 MB |
| **Total** | **32 985 ficheiros**, ~263 MB no GitHub | |

Não existe `requirements.txt`, `package.json` na raiz nem build global. Os scripts são executados diretamente.

### Tamanho por skill

| Skill | Ficheiros | Tamanho |
|---|---:|---:|
| video-add-motion-graphics | 27 254 | **280,6 MB** (recipes: codrops 245 MB, line-md 20 MB) |
| video-add-captions | 78 | 1,7 MB |
| video-add-b-roll | 14 | 1,1 MB |
| video-add-content-cards | 19 | 0,6 MB |
| video-to-shorts | 22 | 0,4 MB |
| video-understand | 17 | 0,2 MB |
| video-cut | 15 | 0,1 MB |
| video-color-grade | 8 | <0,1 MB |
| video-edit-compare | 3 | <0,1 MB |
| cut-as-code (router) | 1 | <0,1 MB |

## 3. Skills disponíveis (10)

| Skill | Função |
|---|---|
| `/cut-as-code` | Ponto de entrada: retoma o projeto e encaminha para a skill certa |
| `/video-understand` | Probe, transcrição por palavra, análise, compreensão semântica — **pré-requisito de quase todas** |
| `/video-cut` | Corte bruto (keep/drop em JSON), varispeed, render e auto-verificação |
| `/video-color-grade` | Looks de cor, escolha, LUT `.cube` |
| `/video-add-b-roll` | Cutaways de media local ou Pexels (precisa de API key) |
| `/video-add-captions` | Legendas por palavra (7 estilos, karaoke opcional) via HyperFrames |
| `/video-add-content-cards` | Títulos, lower-thirds, estatísticas, citações, CTAs via HyperFrames |
| `/video-add-motion-graphics` | Animações a partir de 1 513 recipes locais via HyperFrames |
| `/video-to-shorts` | Escolha de momentos, extração horizontal e versão vertical 9:16 |
| `/video-edit-compare` | Original vs. final lado a lado no relógio da fonte (QA) |

Ordem canónica: `cut → color-grade → b-roll → captions → content-cards → motion-graphics`.
Fluxo com Shorts: `understand → to-shorts (plano + revisão) → captions → content-cards → motion-graphics → render principal → to-shorts (extração final)`.

## 4. Dependências por skill (análise de imports de 70 scripts + SKILL.md)

Bibliotecas Python de terceiros encontradas: **apenas `faster_whisper` e `PIL` (Pillow)**. Tudo o resto é biblioteca padrão. (`numpy` só é usado por `video-color-grade`, que não está na lista.)

| Skill | FFmpeg/FFprobe | Python libs | Node / outros | Modelo IA |
|---|---|---|---|---|
| video-understand | ✅ | faster-whisper, Pillow | — | Whisper (descarrega no 1.º uso) |
| video-cut | ✅ | faster-whisper (via understand) | yt-dlp (opcional, só para URLs) | Whisper |
| video-to-shorts | ✅ | Pillow | — | — (usa transcript existente) |
| video-add-captions | ✅ | Pillow | Node ≥ 22, `npx hyperframes`, Chrome headless | — |
| video-add-content-cards | ✅ | (stdlib) | Node ≥ 22, `npx hyperframes`, Chrome headless | — |
| video-add-motion-graphics | ✅ | Pillow | Node ≥ 22, `npx hyperframes`, Chrome headless + **sub-skills externas** `hyperframes`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, `hyperframes-cli` (não incluídas no repo) | — |
| video-edit-compare | ✅ | Pillow | — | — |
| Editor Hub / MCP (opcional) | — | Python stdlib | Node; UI precisa de `npm install` + build (React/Vite) | — |

**HyperFrames** (registo npm, consultado só para leitura): `hyperframes@0.9.70`, `engines.node >= 22`, ~25 MB + dependências (puppeteer-core, esbuild, …). É obtido via `npx` na primeira utilização e descarrega um `chrome-headless-shell` próprio. Se esse não servir, usa o Chrome do sistema (variável `CHROME`).

### Estado face ao que já está instalado

| Requisito | Estado |
|---|---|
| FFmpeg / FFprobe 9.0.2 | ✅ já instalado — **não duplicar** |
| Python 3.12.10 + `.venv` | ✅ já instalado — **não duplicar** |
| Node 26.13.1 (≥ 22) / npm 11.20 | ✅ já instalado — **não duplicar** |
| yt-dlp | ✅ já instalado |
| Google Chrome 157 | ✅ já instalado (pode servir de fallback ao HyperFrames) |
| **faster-whisper** (no `.venv`) | ❌ em falta |
| **Pillow** (no `.venv`) | ❌ em falta |
| **HyperFrames** (npx, sob demanda) | ❌ em falta (descarga automática no 1.º uso) |
| **chrome-headless-shell** | ❌ em falta (descarga automática pelo HyperFrames) |
| **Modelo Whisper** | ❌ em falta (descarga automática no 1.º uso — **requer a tua autorização**) |
| Sub-skills `hyperframes-*` | ❌ em falta — só necessárias para motion-graphics; origem a confirmar |
| CUDA Toolkit | ⛔ não necessário (não instalar) |
| numpy | ⛔ não necessário para as 7 skills escolhidas |

## 5. Compatibilidade com Windows 11

**Boa compatibilidade.** O repositório é desenvolvido em Windows:
- Os SKILL.md já usam PowerShell e `npx.cmd`. O CLAUDE.md tem uma secção "Windows / ffmpeg gotchas".
- `projectlib.py` trata o file-locking em Windows (`msvcrt`) e em Unix (`fcntl`).
- Caminhos com `C:` são contornados executando o FFmpeg com `cwd` na pasta do ficheiro. Usa-se Pillow em vez de `drawtext`.
- O caminho mais longo no repo tem 180 caracteres. Com a raiz `C:\Users\eusette\GTA6-SHORTS\vendor\cut-as-code\` (46 caracteres) fica em ~226 < 260. **Funciona com LongPaths desativado**, desde que a pasta de clonagem não seja mais funda.

Pontos de atenção:
1. **`npm.ps1` bloqueado:** usar sempre `npm.cmd` / `npx.cmd` (os SKILL.md já o fazem).
2. **`check_structure.ps1`** (self-check das legendas) é chamado com `powershell.exe -ExecutionPolicy Bypass -File …`. Isto só afeta esse processo e não altera a política do sistema.
3. **`video-cut` tem exemplos em bash** (`\` de continuação, `grep`). É preciso adaptá-los para PowerShell, como o próprio CLAUDE.md avisa.
4. **27 000 ficheiros pequenos** (motion-graphics) tornam o clone lento no Windows por causa do Defender. Usar *sparse checkout* se não forem usados.

## 6. Integração com Claude Code

- **Skills:** cada `skills/<nome>/SKILL.md` tem frontmatter `name`/`description` e funciona como slash-command no Claude Code (`/video-understand`, etc.). O Claude Code descobre skills em `.claude/skills/` do projeto ou em `~/.claude/skills/`.
- **Instalação oficial:** `npx skills add WhiteTowerAI/cut-as-code` (ou ClawHub). Os scripts referem caminhos `skills/<nome>/scripts/...` a partir da raiz do repo. Os imports cruzados (`projectlib.py`) dependem de as skills serem pastas irmãs, pelo que o layout tem de ser preservado.
- **CLAUDE.md** do repo só se aplica se o Claude Code trabalhar dentro dessa pasta. Para o nosso projeto convém um CLAUDE.md próprio, que remeta para ele.
- **MCP (opcional):** `.mcp.json` usa um caminho relativo (`./runtime/mcp.cjs`). No nosso projeto será preciso um `.mcp.json` com o caminho absoluto. Dá apenas `open_editor`, que abre o editor visual no browser. A UI tem de ser compilada (`ui/` com React/Vite), o que não é necessário para o pipeline.
- **Revisão humana obrigatória:** várias skills param ("Present + STOP") e esperam que copies um resumo gerado por uma página HTML. Existe um modo `agent` (decisão delegada) se autorizares explicitamente.

## 7. Incompatibilidades e riscos

| # | Problema | Impacto | Mitigação |
|---|---|---|---|
| 1 | **O sistema assenta na fala.** A escolha de Shorts, as legendas e os cards dependem do transcript | Gameplay de GTA sem narração dá poucos candidatos e nenhumas legendas | Gravar com **comentário/voz-off** (OBS com microfone) ou usar material com fala. Para gameplay sem fala, a escolha de momentos terá de ser visual (fora do âmbito destas skills) |
| 2 | `transcribe.py` usa **CPU fixo** (`device="cpu"`, int8) | Transcrição mais lenta; a RTX 4060 não é usada | Aceitável no i5-13500H. GPU é opcional mais tarde (exige alterar o script + ~1,5 GB de bibliotecas CUDA via pip, sem Toolkit) |
| 3 | Modelo por omissão `base.en` é **só inglês** | Português não é reconhecido | Usar `medium --lang auto` (como no SKILL.md) ou `--lang pt` |
| 4 | O render final usa **`libx264` (CPU)**, não NVENC | Render mais lento | OK para Shorts curtos. O renderer aceita `video_codec` como output-constraint (possível NVENC, por verificar) |
| 5 | Motion-graphics exige 5 **sub-skills HyperFrames externas** e pesquisa de imagens licenciadas | Skill incompleta sem elas; carga de licenças | Deixar para o fim |
| 6 | HyperFrames + Chrome headless consomem bastante RAM | Com 16 GB, não correr ao mesmo tempo que o Whisper | As skills já correm em sequência |
| 7 | `video-to-shorts/check_review_ui.py` tem **2 falhas conhecidas** (documentado no CLAUDE.md) | Self-check com 2 falhas que não são nossas | Ignorar essas 2 falhas e registá-las |
| 8 | Node 26 é mais recente do que o mínimo testado (22) | Risco baixo | Validar com os `check_*.mjs` |
| 9 | Direitos de autor (clips GTA VI, yt-dlp com `player_client=android`) | Risco de strikes/ToS | Preferir gameplay próprio e uso transformativo |
| 10 | O repo é público e ativo (34 estrelas, versão ainda a mudar) | Possíveis alterações que partem o pipeline | **Fixar o commit** (submódulo) e atualizar de propósito |

## 8. Arquitetura recomendada

```
C:\Users\eusette\GTA6-SHORTS\           ← repo on-SHORTS (GitHub edsette/on-SHORTS)
├── .venv\                              ← Python 3.12 + faster-whisper + Pillow
├── .claude\skills\                     ← junctions para as skills do vendor (descoberta pelo Claude Code)
├── vendor\cut-as-code\                 ← submódulo Git fixado num commit (código intacto, sem edições)
├── projects\<nome-do-video>\           ← projetos de vídeo (input/ review/ final/ work/) — ignorado no Git
├── models\faster-whisper\              ← cache partilhada de modelos (ignorada no Git)
├── CLAUDE.md                           ← regras do nosso pipeline (PowerShell, npm.cmd, línguas, ordem das skills)
└── logs\
```

Princípios:
- **Não editar o código do vendor.** Adaptações (GPU, língua) ficam em wrappers no nosso repo.
- **Projetos fora do vendor** (o CLAUDE.md do Cut-as-Code exige uma raiz de projeto explícita, nunca a raiz do repo).
- **Uma cache de modelos partilhada** (`--cache-dir`), para não descarregar o Whisper uma vez por projeto.

## 9. Skills prioritárias

| Prioridade | Skill | Porquê |
|---|---|---|
| 1 | `video-understand` | Obrigatória para todas as outras |
| 1 | `video-to-shorts` | Objetivo principal: 9:16 para Shorts/TikTok/Reels |
| 1 | `video-add-captions` | Legendas são essenciais em Shorts (estilo `shorts`, karaoke) |
| 2 | `video-cut` | Limpar gravações longas com comentário antes de escolher os Shorts |
| 2 | `video-add-content-cards` | Títulos/CTAs (tema `apex` adequado a gaming) |
| 2 | `video-edit-compare` | Controlo de qualidade |
| 3 | `video-add-motion-graphics` | Pesada (280 MB, sub-skills externas, regras rígidas) — depois |
| — | `video-color-grade`, `video-add-b-roll` | Fora do âmbito pedido |

## 10. Comandos de instalação documentados (NÃO executados)

```powershell
# 1) Trazer o Cut-as-Code como submódulo fixado (~550 MB com histórico; ver opção sparse abaixo)
cd C:\Users\eusette\GTA6-SHORTS
git submodule add https://github.com/WhiteTowerAI/cut-as-code.git vendor/cut-as-code

#    Alternativa leve: sem a biblioteca codrops de motion-graphics (-245 MB)
#    git clone --filter=blob:none --sparse https://github.com/WhiteTowerAI/cut-as-code.git vendor/cut-as-code
#    git -C vendor/cut-as-code sparse-checkout set --no-cone '/*' '!/skills/video-add-motion-graphics/recipes/codrops/'

# 2) Dependências Python, só no .venv (sem tocar no Python global)
.\.venv\Scripts\python.exe -m pip install faster-whisper Pillow
.\.venv\Scripts\python.exe -c "import faster_whisper, PIL; print('ok')"

# 3) Expor as skills ao Claude Code (junctions — não precisam de admin nem alteram o Windows)
New-Item -ItemType Directory -Force .claude\skills
foreach ($s in 'cut-as-code','video-understand','video-cut','video-to-shorts','video-add-captions','video-add-content-cards','video-edit-compare') {
  cmd /c mklink /J ".claude\skills\$s" "vendor\cut-as-code\skills\$s"
}

# 4) HyperFrames (sob demanda; cache npm local ao projeto)
$env:npm_config_cache = "$PWD\models\npm-cache"
npx.cmd --yes hyperframes@0.9.70 --version
#    (o 1.º render descarrega o chrome-headless-shell; alternativa: $env:CHROME = "C:\Program Files\Google\Chrome\Application\chrome.exe")

# 5) Self-checks do vendor (sem media)
cd vendor\cut-as-code
..\..\.venv\Scripts\python.exe skills\video-understand\scripts\check_protocol_extensions.py
..\..\.venv\Scripts\python.exe skills\video-cut\scripts\check_project_protocol.py
..\..\.venv\Scripts\python.exe skills\video-add-captions\scripts\check_project_protocol.py
..\..\.venv\Scripts\python.exe skills\video-to-shorts\scripts\check_project_protocol.py
node skills\video-add-captions\scripts\check_caption_style_config.mjs
node skills\video-add-captions\scripts\check_caption_interaction.mjs
```

### Modelos de IA (só com a tua autorização — descarregam no 1.º `transcribe.py`)

| Modelo faster-whisper | Tamanho aprox. | Finalidade | Recomendação |
|---|---:|---|---|
| `base.en` | ~145 MB | Default do script; **só inglês** | Não serve para PT |
| `small` | ~480 MB | Multilíngue, rápido, precisão média | Testes rápidos |
| **`medium`** | **~1,5 GB** | Multilíngue; usado nos exemplos do SKILL.md | **Recomendado (CPU)** |
| `large-v3-turbo` | ~1,6 GB | Multilíngue, mais preciso; útil sobretudo em GPU | Opção futura com GPU |
| `large-v3` | ~3,1 GB | Máxima precisão, lento em CPU | Não recomendado agora |

O VAD (Silero) vem incluído no pacote faster-whisper e não precisa de download separado.

## 11. Estimativa de espaço

| Item | Espaço |
|---|---:|
| Cut-as-Code completo (árvore + `.git`) | ~550 MB (sparse sem codrops: ~300 MB) |
| faster-whisper + ctranslate2 + onnxruntime + av + Pillow no `.venv` | ~300–400 MB |
| HyperFrames + dependências (cache npx) | ~150 MB |
| chrome-headless-shell | ~250 MB |
| Modelo Whisper `medium` | ~1,5 GB |
| **Subtotal da instalação base** | **~2,8 GB** |
| (Opcional) bibliotecas CUDA via pip para Whisper na GPU | +~1,5 GB |
| Por projeto de vídeo (fonte OBS 1080p60 de 10–30 min + PNGs de overlay + renders) | ~5–15 GB |

Disco livre atual: **180,6 GB**. Chega para a instalação e para ~10 projetos em simultâneo. Os `work/cache/` são descartáveis e podem ser limpos após cada entrega.

## 12. Plano proposto para a próxima fase (aguarda autorização)

1. Adicionar o submódulo `vendor/cut-as-code` (completo ou sparse — decisão tua).
2. `pip install faster-whisper Pillow` no `.venv`.
3. Criar as junctions em `.claude/skills/` e um `CLAUDE.md` do projeto.
4. Correr os self-checks do vendor (sem media, sem modelos).
5. **Pedir autorização** e descarregar o modelo `medium` (~1,5 GB) para `models/faster-whisper/`.
6. Teste de ponta a ponta com 1 clip curto (gameplay com voz): understand → to-shorts → captions.
