#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPORTS = ("thor.json", "thor.html", "thor.txt")


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def verify_manifest(results_dir):
    manifest_path = results_dir / "manifest.json"

    if not manifest_path.is_file():
        raise FileNotFoundError("No existe manifest.json")

    with manifest_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    for report in manifest["reports"]:
        filename = report["filename"]

        if Path(filename).name != filename:
            raise ValueError(f"Nombre de informe no permitido: {filename}")

        path = results_dir / filename

        if not path.is_file():
            raise FileNotFoundError(f"Falta el informe: {filename}")

        actual_hash = sha256_file(path)

        if actual_hash != report["sha256"]:
            raise ValueError(f"Hash SHA-256 incorrecto: {filename}")

        if path.stat().st_size != report["size"]:
            raise ValueError(f"Tamaño incorrecto: {filename}")

    print("Integridad verificada correctamente.")

def main():
    parser = argparse.ArgumentParser(
        description="Genera un manifiesto de informes THOR"
    )

    parser.add_argument("--host", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-dir", required=True)

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verifica un manifiesto existente sin modificarlo",
    )

    args = parser.parse_args()

    results_dir = Path(args.results_dir)

    if args.verify:
        verify_manifest(results_dir)
        return

    if not results_dir.is_dir():
        parser.error("El directorio de resultados no existe")

    reports = []

    for filename in REPORTS:
        path = results_dir / filename

        if not path.is_file() or path.stat().st_size == 0:
            parser.error(f"Informe ausente o vacío: {filename}")

        reports.append({
            "filename": filename,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    manifest = {
        "run_id": args.run_id,
        "host": args.host,
        "scanner": "THOR",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "reports_verified",
        "reports": reports,
    }

    output = results_dir / "manifest.json"

    output.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    output.chmod(0o600)

    print(f"Manifiesto generado: {output}")


if __name__ == "__main__":
    main()
