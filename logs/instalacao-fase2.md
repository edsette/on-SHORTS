# Instalação — Fase 2

- **Data:** 2026-11-19
- **Método:** `winget install --id <ID> -e --silent --source winget` (hash do instalador verificado pelo winget em todos)
- **Configurações do Windows:** nenhuma alterada (LongPaths e aliases da Store ficam como estavam)

## Instalado

| Ferramenta | ID winget | Versão | Localização |
|---|---|---|---|
| Git | Git.Git | 2.56.0.windows.4 | `C:\Program Files\Git\cmd\git.exe` |
| Python (+ py launcher) | Python.Python.3.12 | 3.12.10 | `%LOCALAPPDATA%\Programs\Python\Python312\` |
| Node.js LTS | OpenJS.NodeJS.LTS | 26.13.1 | `C:\Program Files\nodejs\` |
| npm | (com o Node) | 11.20.0 | `C:\Program Files\nodejs\` |
| FFmpeg / FFprobe | Gyan.FFmpeg | 9.0.2 full_build | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\ffmpeg-9.0.2-full_build\bin\` |
| yt-dlp | yt-dlp.yt-dlp | 2026.10.26 | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\yt-dlp.yt-dlp_...\` |

### Instalado automaticamente como dependência do yt-dlp

| Ferramenta | ID winget | Versão | Nota |
|---|---|---|---|
| Deno | DenoLand.Deno | 2.9.8 | Runtime JS usado pelo yt-dlp para alguns sites |
| FFmpeg (yt-dlp) | yt-dlp.FFmpeg | N-127043 (2026-09-30) | 2.ª cópia do FFmpeg; está **depois** do Gyan no PATH, por isso `ffmpeg` resolve para o Gyan 9.0.2 |

## Verificações

- `python` → Python 3.12.10 real (o atalho da Store em `WindowsApps` fica em 2.º lugar no PATH e já não interceta).
- `ffmpeg -encoders` → `h264_nvenc`, `hevc_nvenc`, `av1_nvenc` disponíveis.
- Teste NVENC: render de 3 s, 1080×1920 a 60 fps com `h264_nvenc` → exit 0; o ffprobe confirma h264 1080×1920 60/1, 3,0 s.

## Projeto

- `git init -b main` → repositório criado.
- `.gitignore` criado (venv, node_modules, .env, media, temporários).
- `.venv` criado com Python 3.12.10, pip 25.0.1.

## Pendentes / notas

- **Identidade Git não configurada** (`user.name` / `user.email`) — necessária antes do primeiro commit.
- **npm no PowerShell:** a política de execução não está definida (por omissão é *Restricted*), por isso `npm` num terminal PowerShell normal pode falhar ao carregar `npm.ps1`. Para contornar sem alterar o Windows, usar `npm.cmd`. Para resolver: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (alteração de configuração — requer autorização).
- Abrir novos terminais para que o PATH atualizado seja carregado.
- LongPathsEnabled continua desativado.
