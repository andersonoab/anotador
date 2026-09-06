IGARAPE DAILY COCKPIT - FREEZE SEM POWERSHELL SCRIPT

IMPORTANTE
- Em ambiente corporativo, a politica do Windows pode bloquear arquivos .ps1.
- Nao altere ExecutionPolicy e nao use Bypass.
- Use GERAR_FREEZE.bat.
- O BAT chama gerar_freeze.py com o Python 3.10 ja usado nos seus RPAs.

COMO GERAR
1. Extraia todo o ZIP.
2. Abra CMD ou PowerShell nessa pasta.
3. Execute:

   .\GERAR_FREEZE.bat

O processo valida:
- Python 3.10
- cx_Freeze 6.15.16
- LIEF 0.12.3
- camada local compativel de pywebview/pythonnet/cffi/pycparser
- copia da UI ao lado do EXE
- runtime do faster-whisper/PyAV/CTranslate2
- self-test do EXE congelado

SAIDA
build\IgarapeDailyCockpit\IgarapeDailyCockpit.exe

O GERAR_FREEZE.ps1 foi mantido apenas como referencia do fluxo anterior.
Para este computador, use GERAR_FREEZE.bat.
