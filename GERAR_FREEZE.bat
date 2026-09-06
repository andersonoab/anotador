@echo off
setlocal
cd /d "%~dp0"

if defined IGARAPE_PYTHON (
  set "PY=%IGARAPE_PYTHON%"
) else (
  set "PY=C:\Users\99andsouza\AppData\Local\Programs\Python\Python310\python.exe"
)

if not exist "%PY%" (
  echo ERRO: Python 3.10 nao encontrado em:
  echo %PY%
  if not defined CI pause
  exit /b 1
)

"%PY%" "%~dp0gerar_freeze.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo FREEZE NAO CONCLUIDO. Codigo: %RC%
  if not defined CI pause
  exit /b %RC%
)

echo FREEZE CONCLUIDO.
if not defined CI pause
exit /b 0
