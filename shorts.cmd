@echo off
rem GTA6-SHORTS - comando simples. Duplo clique para o assistente, ou: shorts --ajuda
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente Python em falta: .venv
  echo        Ver README.md, secção "Depois de clonar este repositório".
  if "%~1"=="" pause
  exit /b 2
)
if /i "%~1"=="--ajuda" (
  ".venv\Scripts\python.exe" scripts\shorts_cli.py --help
  exit /b 0
)
".venv\Scripts\python.exe" scripts\shorts_cli.py %*
set RC=%ERRORLEVEL%
if "%~1"=="" (
  echo.
  pause
)
exit /b %RC%
