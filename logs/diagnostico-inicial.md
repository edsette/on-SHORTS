# Diagnóstico inicial do ambiente — GTA6-SHORTS

- **Data:** 2026-11-19
- **Fase:** 1 — Diagnóstico (nada foi instalado, alterado ou eliminado)
- **Método:** todos os valores abaixo foram obtidos com comandos reais (PowerShell 5.1, CIM/WMI, `nvidia-smi`, registo de programas instalados, procura de executáveis no disco).

---

## 1. Sistema

| Item | Resultado |
|---|---|
| Windows | Windows 11 Pro, versão **26H2**, build **26300.9974**, 64-bit |
| Equipamento | GIGABYTE G5 KF5 (portátil) |
| Processador | Intel Core **i5-13500H** — 12 núcleos / 16 threads |
| Arquitetura | x64 (AMD64) |
| RAM | **15,7 GB** total — ~6,5 GB livres no momento do teste |
| Disco | 1 × NVMe SSD GIGABYTE AG450E1024-G (954 GB) — **C: 180,6 GB livres** de 952,8 GB |
| PowerShell | 5.1 (PowerShell 7 não instalado) |
| Gestor de pacotes | **winget v1.29.380** disponível (Chocolatey e Scoop ausentes) |
| WSL | Não instalado |
| Caminhos longos (LongPathsEnabled) | **Desativado (0)** |

## 2. GPU / CUDA

| Item | Resultado |
|---|---|
| GPU dedicada | **NVIDIA GeForce RTX 4060 Laptop GPU**, **8 GB VRAM** (8188 MiB) |
| GPU integrada | Intel Iris Xe Graphics (driver 32.0.101.7082) — portátil híbrido (Optimus) |
| Driver NVIDIA | **617.42** (32.0.16.1742, data 30/09/2026), modo WDDM |
| CUDA suportado pelo driver | **CUDA 13.4** (`nvidia-smi`) |
| `nvcuda.dll` | Presente (32.0.16.1742) → **CUDA disponível ao nível do driver** |
| NVENC (`nvEncodeAPI64.dll`) | Presente → codificação de vídeo por hardware disponível (H.264 / HEVC / AV1) |
| CUDA Toolkit (`nvcc`) | **Não instalado** (sem pasta `NVIDIA GPU Computing Toolkit`, sem variáveis `CUDA_PATH`) |
| Limite de potência | 60 W máx. (12 W em idle, 62 °C no teste) |

> Nota: o WMI reporta "4 GB" de VRAM por limitação do campo de 32 bits; o valor real (8 GB) vem do `nvidia-smi`.

## 3. Ferramentas de desenvolvimento

| Ferramenta | Estado | Versão / observação |
|---|---|---|
| Git | ❌ Em falta | — |
| Node.js | ❌ Em falta | — |
| npm | ❌ Em falta | — |
| Python | ❌ Em falta | `python.exe` / `python3.exe` no PATH são apenas o **atalho da Microsoft Store** (ficheiro de 0 bytes) — `python --version` devolve "Python was not found" |
| pip / py launcher | ❌ Em falta | — |
| FFmpeg | ❌ Em falta | — |
| FFprobe | ❌ Em falta | — |
| yt-dlp | ❌ Em falta | — |
| winget | ✅ Instalado | v1.29.380 |
| nvidia-smi | ✅ Instalado | driver 617.42 |
| VS Code, Docker, conda, uv, pipx | ❌ Em falta | — |

## 4. Ferramentas/dependências já existentes que podem ser aproveitadas

| Encontrado | Aproveitamento |
|---|---|
| **OBS Studio 32.2.2** | Útil para gravar gameplay/capturas em alta qualidade com NVENC. Inclui bibliotecas FFmpeg internas (avcodec-62, etc.), mas **não** fornece `ffmpeg.exe` — não substitui o FFmpeg. |
| **NVIDIA App 11.0.9 + ShadowPlay** | Gravação instantânea/"replay" de gameplay com NVENC — fonte de clips. |
| **Visual C++ Redistributables 2012/2013/2022 (v14.51)** | Necessários para muitos pacotes Python com extensões nativas (PyTorch, etc.) — já presentes. |
| **.NET 6 Desktop Runtime** | Sem uso direto previsto. |
| Python 3.13.7 em `C:\Program Files\GOG Galaxy\python\` | **Não usar** — é interno ao GOG Galaxy, sem pip/PATH; mexer nele pode partir o GOG. |
| Google Chrome / Edge WebView2 | Úteis para automação de browser/upload, se necessário mais tarde. |

Não foram encontrados projetos anteriores de programação (sem pastas de código, `node_modules`, venvs, ou executáveis de Git/Node/FFmpeg/yt-dlp no perfil do utilizador ou em Program Files). A pasta `Videos` está vazia. A pasta do projeto `GTA6-SHORTS` estava vazia (não é um repositório Git).

## 5. Problemas de compatibilidade / riscos

1. **Python falso no PATH:** os aliases da Microsoft Store (`python.exe`, `python3.exe` em `WindowsApps`) podem intercetar o comando `python` mesmo depois de instalar o Python real. Solução: instalar o Python do python.org (que inclui o `py` launcher) e usar `py -3.12` / venv do projeto; opcionalmente desativar os aliases em *Definições → Aplicações → Definições avançadas → Aliases de execução* (alteração de configuração do Windows — só com a tua autorização).
2. **Caminhos longos desativados:** pode causar erros em `npm install` e em alguns pacotes pip com caminhos > 260 caracteres. Ativar exige alterar o registo do Windows (requer autorização). Mitigação sem alterar o Windows: manter o projeto num caminho curto (o atual `C:\Users\eusette\GTA6-SHORTS` é aceitável).
3. **Git ausente:** o Claude Code no Windows usa o Git Bash para executar comandos shell no CLI; sem Git também não há controlo de versões do projeto. Prioridade máxima.
4. **RAM de 16 GB:** suficiente para FFmpeg, Whisper e scripts, mas limita LLMs locais grandes e edição de vídeo pesada em paralelo. Evitar correr vários modelos de IA em simultâneo.
5. **VRAM de 8 GB:** bom para Whisper (large-v3/turbo via faster-whisper), upscaling leve e NVENC. Modelos de geração de imagem/vídeo grandes ficarão no limite.
6. **Portátil híbrido (Intel + NVIDIA):** garantir que o portátil está ligado à corrente durante renderizações (limite de 60 W na GPU) e que os processos de IA usam a GPU NVIDIA.
7. **Python 3.13 vs 3.12:** algumas bibliotecas de IA/vídeo ainda têm melhor suporte em **Python 3.12** — recomendado 3.12 para o projeto.
8. **CUDA Toolkit não é necessário de início:** o PyTorch e o faster-whisper (CTranslate2) trazem o runtime CUDA nos próprios pacotes; o driver 617.42 (CUDA 13.4) é suficientemente recente. Só instalar o Toolkit se algum pacote precisar de compilar código CUDA.
9. **Espaço em disco (180 GB livres):** adequado para começar, mas footage de gameplay ocupa muito. Definir política de limpeza/arquivo de brutos desde o início.
10. **Conteúdo/direitos:** clips de GTA VI e material descarregado com yt-dlp (trailers, vídeos de terceiros) estão sujeitos a direitos de autor e às políticas do YouTube/TikTok/Instagram. Preferir gameplay próprio e material oficial com uso transformativo.

## 6. Recomendações para este computador

- Usar **winget** para todas as instalações (oficial, já presente, sem gestores extra).
- Usar o **FFmpeg build "full" do Gyan** (inclui `ffprobe` e suporte a `h264_nvenc` / `hevc_nvenc` / `av1_nvenc`) — encoding de Shorts acelerado por GPU.
- Python **3.12** do python.org + **ambiente virtual (`.venv`) dentro do projeto**; yt-dlp instalado no venv (fácil de atualizar com pip) ou via winget.
- Node.js **LTS** (para scripts/ferramentas JS e o CLI do Claude Code, se desejado).
- Gravar gameplay com **OBS (já instalado)** usando NVENC, em 1080p60 ou superior, para depois recortar em 9:16.
- Opcional: PowerShell 7 e VS Code.

## 7. Plano de instalação proposto (Fase 2 — aguarda autorização)

Por ordem, cada passo verificado com `--version` antes de avançar:

| # | Ferramenta | Comando previsto |
|---|---|---|
| 1 | Git for Windows | `winget install --id Git.Git -e` |
| 2 | Python 3.12 (com `py` launcher) | `winget install --id Python.Python.3.12 -e` |
| 3 | Node.js LTS (inclui npm) | `winget install --id OpenJS.NodeJS.LTS -e` |
| 4 | FFmpeg + FFprobe (build full, NVENC) | `winget install --id Gyan.FFmpeg -e` |
| 5 | yt-dlp | `winget install --id yt-dlp.yt-dlp -e` (ou `pip install yt-dlp` no venv) |
| 6 | Reabrir terminal e verificar | `git --version`, `py -3.12 --version`, `node -v`, `npm -v`, `ffmpeg -version`, `ffprobe -version`, `yt-dlp --version` |
| 7 | Teste NVENC | `ffmpeg -hide_banner -encoders` → confirmar `h264_nvenc` |
| 8 | Estrutura do projeto | `git init`, `.gitignore`, criar `.venv` com `py -3.12 -m venv .venv` |
| 9 | (Mais tarde) PyTorch CUDA / faster-whisper no venv | teste `torch.cuda.is_available()` |

**Decisões que dependem de ti (alteram configurações do Windows):**
- Ativar caminhos longos (LongPathsEnabled).
- Desativar os aliases `python.exe`/`python3.exe` da Microsoft Store.
- Opcionais: PowerShell 7, VS Code.
