# -*- coding: utf-8 -*-
import importlib.metadata as md
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PY_EXE = Path(os.environ.get("IGARAPE_PYTHON", r"C:\Users\99andsouza\AppData\Local\Programs\Python\Python310\python.exe"))
SRC = ROOT / "IgarapeDailyCockpit"
OUT = ROOT / "build" / "IgarapeDailyCockpit"
COMPAT = ROOT / ".freeze_compat"
LOG = ROOT / "freeze_erro.log"
SELFTEST = ROOT / "freeze_selftest.json"


def fail(msg: str, code: int = 1):
    print("\nERRO:", msg)
    print("Log:", LOG)
    raise SystemExit(code)


def run(cmd, *, env=None, capture_log=False):
    print("\n>", subprocess.list2cmdline([str(x) for x in cmd]))
    if capture_log:
        with LOG.open("w", encoding="utf-8", errors="replace") as fh:
            proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
                fh.write(line)
            return proc.wait()
    return subprocess.run(cmd, cwd=ROOT, env=env).returncode


def copytree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


print("=" * 60)
print(" IGARAPE DAILY COCKPIT - FREEZE SEM POWERSHELL SCRIPT")
print(" Python 3.10 + cx_Freeze 6.15.16 + camada pywebview compat")
print("=" * 60)

if not PY_EXE.exists():
    fail(f"Python 3.10 nao encontrado em {PY_EXE}")
for required in [SRC / "main.py", SRC / "ui" / "cockpit.html", SRC / "ui" / "captura.html", ROOT / "preparar_runtime_whisper.py"]:
    if not required.exists():
        fail(f"Arquivo obrigatorio nao encontrado: {required}")

print("\n[1/8] Validando Python / cx_Freeze / LIEF...")
if sys.version_info[:2] != (3, 10):
    fail(f"Este script precisa rodar no Python 3.10. Atual: {sys.version}")
try:
    cxf = md.version("cx-Freeze")
    lief = md.version("lief")
except Exception as exc:
    fail(f"Nao foi possivel validar cx_Freeze/LIEF: {exc}")
print("Python:", sys.executable)
print("cx_Freeze:", cxf)
print("LIEF:", lief)
if cxf != "6.15.16" or lief != "0.12.3":
    fail("Use cx_Freeze 6.15.16 e LIEF 0.12.3 neste Python")

print("\n[2/8] Preparando camada LOCAL compativel com cx_Freeze...")
if COMPAT.exists():
    shutil.rmtree(COMPAT)
COMPAT.mkdir(parents=True, exist_ok=True)
compat_pkgs = [
    "pywebview==5.4",
    "pythonnet==3.0.3",
    "clr-loader==0.2.6",
    "cffi==1.16.0",
    "pycparser==2.21",
    "proxy_tools==0.1.0",
    "bottle==0.13.4",
    "typing_extensions==4.16.0",
]
cmd = [str(PY_EXE), "-m", "pip", "install", "--disable-pip-version-check", "--no-deps", "--upgrade", "--target", str(COMPAT), *compat_pkgs]
if run(cmd) != 0:
    fail("Falha ao preparar .freeze_compat")

env_freeze = os.environ.copy()
env_freeze["PYTHONPATH"] = str(COMPAT)
check = [str(PY_EXE), "-c", "import webview,cffi,pycparser,clr_loader,pythonnet; print('webview:',webview.__file__); print('cffi:',cffi.__file__); print('pycparser:',pycparser.__file__)"]
if run(check, env=env_freeze) != 0:
    fail("Camada .freeze_compat nao pode ser importada")

print("\n[3/8] Limpando build anterior...")
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

print("\n[4/8] Gerando EXE pelo padrao cx_Freeze...")
args = [
    str(PY_EXE), "-m", "cx_Freeze", str(SRC / "main.py"),
    "--base-name", "Win32GUI",
    "--target-dir", str(OUT),
    "--target-name", "IgarapeDailyCockpit.exe",
    "--packages", "webview,cffi,pycparser,clr_loader,pythonnet,pystray,PIL,openpyxl,keyring,sounddevice,soundfile,numpy",
    "--includes", "clr,_cffi_backend,keyring.backends.Windows,pystray._win32",
    "--excludes", "faster_whisper,av,ctranslate2,tokenizers,onnxruntime,huggingface_hub",
    "--include-msvcr",
]
code = run(args, env=env_freeze, capture_log=True)
if code != 0:
    try:
        tail = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        print("\nULTIMAS 80 LINHAS DO FREEZE:\n" + "\n".join(tail))
    except Exception:
        pass
    fail(f"cx_Freeze retornou codigo {code}")
exe = OUT / "IgarapeDailyCockpit.exe"
if not exe.exists():
    fail("cx_Freeze terminou sem criar o EXE")

print("\n[5/8] Copiando UI e runtimes dinamicos...")
copytree(SRC / "ui", OUT / "ui")
for rel_src, rel_dst in [
    (Path("pythonnet/runtime"), Path("lib/pythonnet/runtime")),
    (Path("clr_loader/ffi/dlls"), Path("lib/clr_loader/ffi/dlls")),
    (Path("webview/js"), Path("lib/webview/js")),
    (Path("webview/lib"), Path("lib/webview/lib")),
]:
    src = COMPAT / rel_src
    if src.exists():
        copytree(src, OUT / rel_dst)

print("\n[6/8] Copiando runtime Whisper do Python que ja funciona...")
if run([str(PY_EXE), str(ROOT / "preparar_runtime_whisper.py"), str(OUT / "lib")]) != 0:
    fail("Falha ao copiar runtime do faster-whisper")

print("\n[7/8] Copiando modelo Whisper base do cache local, quando disponivel...")
snaproot = Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-base" / "snapshots"
modeldest = OUT / "models" / "faster-whisper-base"
if snaproot.exists():
    snaps = [p for p in snaproot.iterdir() if p.is_dir()]
    snaps.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if snaps:
        modeldest.parent.mkdir(parents=True, exist_ok=True)
        copytree(snaps[0], modeldest)
        print("Modelo copiado de:", snaps[0])
else:
    print("ATENCAO: cache local do modelo nao encontrado. O EXE podera usar o cache Hugging Face normal.")

print("\n[8/8] Self-test do EXE congelado...")
if SELFTEST.exists():
    SELFTEST.unlink()
env_test = os.environ.copy()
env_test.pop("PYTHONPATH", None)
env_test["IGARAPE_FREEZE_SELFTEST"] = "1"
env_test["IGARAPE_SELFTEST_OUTPUT"] = str(SELFTEST)
try:
    proc = subprocess.Popen([str(exe)], cwd=OUT, env=env_test)
    proc.wait(timeout=30)
except subprocess.TimeoutExpired:
    proc.kill()
    fail("Self-test do EXE nao terminou em 30 segundos")

if not SELFTEST.exists():
    fail("EXE abriu, mas nao gerou o arquivo de self-test")
try:
    result = json.loads(SELFTEST.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"Nao foi possivel ler o self-test: {exc}")

print("frozen........:", result.get("frozen"))
print("cockpit.html..:", result.get("cockpit_html"))
print("captura.html..:", result.get("captura_html"))
print("imports.......:")
for name, status in result.get("imports", {}).items():
    print(f"  {name:<20} {status}")
if not result.get("ok"):
    fail("Self-test encontrou recurso/import quebrado. Veja freeze_selftest.json")

print("\n" + "=" * 60)
print(" FREEZE CONCLUIDO E SELF-TEST APROVADO")
print("=" * 60)
print("EXE:", exe)
print("UI :", OUT / "ui")
print("Log:", LOG)
print("Teste:", SELFTEST)
