# on-SHORTS (GTA6-SHORTS)

Sistema local de produção automática de **YouTube Shorts**, **TikTok** e **Instagram Reels**, usando o **Claude Code** como agente principal.

## Ambiente alvo

- Windows 11 · Intel i5-13500H · 16 GB RAM
- NVIDIA RTX 4060 Laptop (8 GB VRAM) — CUDA 13.4 (driver), NVENC para exportação acelerada

## Ferramentas

| Ferramenta | Versão |
|---|---|
| Git | 2.56 |
| Python | 3.12 (venv em `.venv`) |
| Node.js / npm | 26 LTS / 11 |
| FFmpeg / FFprobe | 9.0.2 (Gyan full build, `h264_nvenc` / `hevc_nvenc` / `av1_nvenc`) |
| yt-dlp | 2026.10.26 |

## Configuração rápida

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Gyan.FFmpeg -e
winget install --id yt-dlp.yt-dlp -e

git clone https://github.com/edsette/on-SHORTS.git
cd on-SHORTS
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Depois de clonar este repositório:

```powershell
git submodule update --init
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
powershell -ExecutionPolicy Bypass -File scripts\setup-skills.ps1
```

## Estrutura

```
vendor/cut-as-code/   Motor de edição (submódulo, não editar)
.claude/skills/       Junctions para as skills do vendor (geradas, não versionadas)
scripts/              Scripts próprios (setup-skills.ps1, …)
projects/             Projetos de vídeo (não versionados)
models/               Modelos e caches (não versionados)
logs/                 Relatórios de cada fase
```

## Estado

- [x] Fase 1 — Diagnóstico do ambiente (`logs/diagnostico-inicial.md`)
- [x] Fase 2 — Instalação das ferramentas base (`logs/instalacao-fase2.md`)
- [x] Fase 3 — Análise e instalação do Cut-as-Code (`logs/analise-cut-as-code.md`, `logs/instalacao-fase3.md`)
- [~] Fase 4 — Transcrição local na GPU e análise de momentos (`logs/fase4-transcricao.md`) — validada em EN, PT pendente
- [~] Fase 6 — Motor de produção de Shorts (`logs/fase6-motor-shorts.md`) — testado com vídeo sintético, vídeo real pendente

- [x] Fase 7 — Interface simplificada (`logs/fase7-interface.md`)
- [x] Fase 8 — Teste de produção com vídeo real PT-BR (`logs/fase8-teste-producao.md`) — 10/10 critérios após correções

## Gerar Shorts

**Ver [COMO-USAR.md](COMO-USAR.md).** Em resumo: duplo clique em `shorts.cmd`, ou no Claude Code:

```
/shorts
Vídeo: C:\videos\gameplay.mp4
Cortes: 8
Duração: 45 segundos
Idioma: Português BR
Estilo: Gaming dinâmico
```

Resultados em `output/<projeto>/<pedido>/export/`. Predefinições em `config/shorts.toml`. Nada é publicado automaticamente.

## Notas

Ficheiros de media (`.mp4`, `.wav`, etc.), `.venv/`, `node_modules/` e `.env` não são versionados — ver `.gitignore`.
