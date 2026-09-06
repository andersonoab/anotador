# -*- coding: utf-8 -*-
"""Copia para o build o runtime EXATO do faster-whisper já instalado.

Evita pedir ao cx_Freeze 6.15.16 para analisar PyAV/CTranslate2/ONNX e evita
reinstalar/atualizar dependências durante o build. A origem é o mesmo Python
que já executa e transcreve o Cockpit normalmente.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import sysconfig
from collections import deque
from importlib import metadata
from pathlib import Path

try:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"ERRO: pacote 'packaging' indisponível: {exc}")


ROOT_DISTS = ["faster-whisper"]


def _dentro(caminho: Path, raiz: Path) -> bool:
    try:
        caminho.relative_to(raiz)
        return True
    except ValueError:
        return False


def _fechamento_dependencias(roots):
    fila = deque(roots)
    vistos = {}
    while fila:
        pedido = fila.popleft()
        chave = canonicalize_name(pedido)
        if chave in vistos:
            continue
        try:
            dist = metadata.distribution(pedido)
        except metadata.PackageNotFoundError:
            raise SystemExit(
                f"ERRO: distribuição '{pedido}' não está instalada no Python {sys.executable}"
            )
        vistos[chave] = dist
        for linha in dist.requires or []:
            try:
                req = Requirement(linha)
                if req.marker and not req.marker.evaluate():
                    continue
                fila.append(req.name)
            except Exception:
                # Uma linha de metadata incomum não deve impedir a cópia do root.
                continue
    return list(vistos.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("destino")
    args = ap.parse_args()

    destino = Path(args.destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)

    raizes = []
    for p in {sysconfig.get_paths().get("purelib"), sysconfig.get_paths().get("platlib")}:
        if p:
            q = Path(p).resolve()
            if q.exists() and q not in raizes:
                raizes.append(q)

    dists = _fechamento_dependencias(ROOT_DISTS)
    total = 0
    copiados = 0
    ignorados = 0

    print("[runtime] Python:", sys.executable)
    print("[runtime] Destino:", destino)
    print("[runtime] Distribuições:")

    for dist in sorted(dists, key=lambda d: canonicalize_name(d.metadata.get("Name", ""))):
        nome = dist.metadata.get("Name") or "?"
        versao = dist.version
        print(f"  - {nome}=={versao}")
        for item in dist.files or []:
            total += 1
            src = Path(dist.locate_file(item)).resolve()
            if not src.is_file():
                ignorados += 1
                continue

            raiz = next((r for r in raizes if _dentro(src, r)), None)
            if raiz is None:
                # Ignora Scripts/ e arquivos fora de site-packages.
                ignorados += 1
                continue

            rel = src.relative_to(raiz)
            dst = destino / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copiados += 1

    obrigatorios = [
        destino / "faster_whisper",
        destino / "av",
        destino / "ctranslate2",
        destino / "onnxruntime",
        destino / "tokenizers",
        destino / "huggingface_hub",
    ]
    faltando = [str(p.name) for p in obrigatorios if not p.exists()]

    print(f"[runtime] Arquivos metadata: {total}")
    print(f"[runtime] Copiados: {copiados}")
    print(f"[runtime] Ignorados fora de site-packages: {ignorados}")
    if faltando:
        raise SystemExit("ERRO: runtime incompleto; faltando: " + ", ".join(faltando))
    print("[runtime] Whisper/PyAV/CTranslate2/ONNX: OK")


if __name__ == "__main__":
    main()
