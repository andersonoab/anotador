$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

$PY = "C:\Users\99andsouza\AppData\Local\Programs\Python\Python310\python.exe"
$SRC = Join-Path $ROOT "IgarapeDailyCockpit"
$OUT = Join-Path $ROOT "build\IgarapeDailyCockpit"
$COMPAT = Join-Path $ROOT ".freeze_compat"
$LOG = Join-Path $ROOT "freeze_erro.log"

function Falhar($mensagem) {
    Write-Host ""
    Write-Host "ERRO: $mensagem" -ForegroundColor Red
    Write-Host "Log: $LOG"
    exit 1
}

Write-Host "============================================================"
Write-Host " IGARAPE DAILY COCKPIT - FREEZE VALIDADO"
Write-Host " Python 3.10 + cx_Freeze 6.15.16 + camada pywebview compat"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path $PY)) { Falhar "Python 3.10 não encontrado em $PY" }
if (-not (Test-Path (Join-Path $SRC "main.py"))) { Falhar "main.py não encontrado em $SRC" }
if (-not (Test-Path (Join-Path $SRC "ui\cockpit.html"))) { Falhar "ui\cockpit.html não encontrado" }
if (-not (Test-Path (Join-Path $SRC "ui\captura.html"))) { Falhar "ui\captura.html não encontrado" }

Write-Host "[1/8] Validando Python / cx_Freeze / LIEF..."
& $PY -c "import sys,importlib.metadata as m; print(sys.executable); print(sys.version); print('cx_Freeze',m.version('cx-Freeze')); print('LIEF',m.version('lief')); assert sys.version_info[:2]==(3,10); assert m.version('cx-Freeze')=='6.15.16'; assert m.version('lief')=='0.12.3'"
if ($LASTEXITCODE -ne 0) { Falhar "Use Python 3.10 com cx_Freeze 6.15.16 e LIEF 0.12.3" }

Write-Host ""
Write-Host "[2/8] Preparando camada LOCAL compatível com o cx_Freeze..."
Remove-Item $COMPAT -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $COMPAT | Out-Null

# --no-deps é proposital: evita o resolver comparar cffi 1.16 local do Freeze
# com outras aplicações instaladas no Python global. Nada abaixo altera o global.
& $PY -m pip install --disable-pip-version-check --no-deps --upgrade --target $COMPAT `
    pywebview==5.4 `
    pythonnet==3.0.3 `
    clr-loader==0.2.6 `
    cffi==1.16.0 `
    pycparser==2.21 `
    proxy_tools==0.1.0 `
    bottle==0.13.4 `
    typing_extensions==4.16.0
if ($LASTEXITCODE -ne 0) { Falhar "Falha ao preparar .freeze_compat" }

$env:PYTHONPATH = (Resolve-Path $COMPAT).Path
& $PY -c "import webview,cffi,pycparser,clr_loader,pythonnet; print('webview:',webview.__file__); print('cffi:',cffi.__file__); print('pycparser:',pycparser.__file__)"
if ($LASTEXITCODE -ne 0) { Falhar "Camada .freeze_compat não pode ser importada" }

Write-Host ""
Write-Host "[3/8] Limpando build anterior..."
Remove-Item $OUT -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

Write-Host ""
Write-Host "[4/8] Gerando EXE pelo mesmo padrão dos seus outros projetos..."
$ARGUMENTOS = @(
    "-m", "cx_Freeze",
    (Join-Path $SRC "main.py"),
    "--base-name", "Win32GUI",
    "--target-dir", $OUT,
    "--target-name", "IgarapeDailyCockpit.exe",
    "--packages", "webview,cffi,pycparser,clr_loader,pythonnet,pystray,PIL,openpyxl,keyring,sounddevice,soundfile,numpy",
    "--includes", "clr,_cffi_backend,keyring.backends.Windows,pystray._win32",
    "--excludes", "faster_whisper,av,ctranslate2,tokenizers,onnxruntime,huggingface_hub",
    "--include-msvcr"
)

& $PY @ARGUMENTOS 2>&1 | Tee-Object -FilePath $LOG
$CODIGO = $LASTEXITCODE
if ($CODIGO -ne 0) {
    Write-Host ""
    Write-Host "ULTIMAS 80 LINHAS DO FREEZE:" -ForegroundColor Yellow
    Get-Content $LOG -Tail 80
    Falhar "cx_Freeze retornou código $CODIGO"
}
if (-not (Test-Path (Join-Path $OUT "IgarapeDailyCockpit.exe"))) { Falhar "cx_Freeze terminou sem criar o EXE" }

Write-Host ""
Write-Host "[5/8] Copiando recursos que são dinâmicos no Windows..."
# UI: colocada explicitamente ao lado do EXE. main.py corrigido procura aqui
# quando sys.frozen=True. Isso elimina o 404 de /ui/cockpit.html e captura.html.
$UIOUT = Join-Path $OUT "ui"
Remove-Item $UIOUT -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $UIOUT | Out-Null
Copy-Item (Join-Path $SRC "ui\*") $UIOUT -Recurse -Force

# Dados de runtime que pythonnet/clr-loader/webview carregam dinamicamente.
if (Test-Path (Join-Path $COMPAT "pythonnet\runtime")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OUT "lib\pythonnet") | Out-Null
    Copy-Item (Join-Path $COMPAT "pythonnet\runtime") (Join-Path $OUT "lib\pythonnet\runtime") -Recurse -Force
}
if (Test-Path (Join-Path $COMPAT "clr_loader\ffi\dlls")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OUT "lib\clr_loader\ffi") | Out-Null
    Copy-Item (Join-Path $COMPAT "clr_loader\ffi\dlls") (Join-Path $OUT "lib\clr_loader\ffi\dlls") -Recurse -Force
}
if (Test-Path (Join-Path $COMPAT "webview\js")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OUT "lib\webview") | Out-Null
    Copy-Item (Join-Path $COMPAT "webview\js") (Join-Path $OUT "lib\webview\js") -Recurse -Force
}
if (Test-Path (Join-Path $COMPAT "webview\lib")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $OUT "lib\webview") | Out-Null
    Copy-Item (Join-Path $COMPAT "webview\lib") (Join-Path $OUT "lib\webview\lib") -Recurse -Force
}

Write-Host ""
Write-Host "[6/8] Copiando o runtime Whisper EXATO do Python que já funciona..."
# Não reinstala Whisper e não pede ao cx_Freeze para analisar PyAV.
# Copia as distribuições e dependências já instaladas neste Python.
& $PY (Join-Path $ROOT "preparar_runtime_whisper.py") (Join-Path $OUT "lib")
if ($LASTEXITCODE -ne 0) { Falhar "Falha ao copiar runtime do faster-whisper" }

Write-Host ""
Write-Host "[7/8] Copiando o modelo Whisper base do cache local, quando disponível..."
$SNAPROOT = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--Systran--faster-whisper-base\snapshots"
$MODELDEST = Join-Path $OUT "models\faster-whisper-base"
if (Test-Path $SNAPROOT) {
    $SNAP = Get-ChildItem $SNAPROOT -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $SNAP) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MODELDEST) | Out-Null
        Remove-Item $MODELDEST -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item $SNAP.FullName $MODELDEST -Recurse -Force
        Write-Host "Modelo copiado de: $($SNAP.FullName)"
    }
} else {
    Write-Host "ATENÇÃO: cache local do modelo não encontrado. O EXE poderá usar o cache Hugging Face normal." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[8/8] Self-test do EXE congelado..."
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$SELFTEST = Join-Path $ROOT "freeze_selftest.json"
Remove-Item $SELFTEST -Force -ErrorAction SilentlyContinue
$env:IGARAPE_FREEZE_SELFTEST = "1"
$env:IGARAPE_SELFTEST_OUTPUT = $SELFTEST

$P = Start-Process -FilePath (Join-Path $OUT "IgarapeDailyCockpit.exe") -PassThru
if (-not $P.WaitForExit(30000)) {
    try { $P.Kill() } catch {}
    Remove-Item Env:IGARAPE_FREEZE_SELFTEST -ErrorAction SilentlyContinue
    Remove-Item Env:IGARAPE_SELFTEST_OUTPUT -ErrorAction SilentlyContinue
    Falhar "Self-test do EXE não terminou em 30 segundos"
}

Remove-Item Env:IGARAPE_FREEZE_SELFTEST -ErrorAction SilentlyContinue
Remove-Item Env:IGARAPE_SELFTEST_OUTPUT -ErrorAction SilentlyContinue

if (-not (Test-Path $SELFTEST)) { Falhar "EXE abriu, mas não gerou o arquivo de self-test" }
$R = Get-Content $SELFTEST -Raw | ConvertFrom-Json
Write-Host "frozen........: $($R.frozen)"
Write-Host "cockpit.html..: $($R.cockpit_html)"
Write-Host "captura.html..: $($R.captura_html)"
Write-Host "imports.......:"
$R.imports.PSObject.Properties | ForEach-Object { Write-Host ("  {0,-20} {1}" -f $_.Name, $_.Value) }
if (-not $R.ok) { Falhar "Self-test encontrou recurso/import quebrado. Veja freeze_selftest.json" }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " FREEZE CONCLUÍDO E SELF-TEST APROVADO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "EXE: $(Join-Path $OUT 'IgarapeDailyCockpit.exe')"
Write-Host "UI : $(Join-Path $OUT 'ui')"
Write-Host "Log: $LOG"
Write-Host "Teste: $SELFTEST"
Write-Host ""
Write-Host "Agora você pode abrir o IgarapeDailyCockpit.exe normalmente."
