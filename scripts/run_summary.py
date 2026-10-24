#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path


BASE_DIR = Path(os.environ.get("THOR_BASE_DIR", Path(__file__).resolve().parent.parent))
RESULTS_DIR = BASE_DIR / "results" / "raw"
ANSIBLE_DIR = BASE_DIR / "ansible"


def get_run_hosts(run_id):
    targets_file = (
        BASE_DIR
        / "logs"
        / "runs"
        / run_id
        / "targets.json"
    )

    if not targets_file.is_file():
        raise FileNotFoundError(
            f"No existe el inventario de la ejecución: {targets_file}"
        )

    with targets_file.open(encoding="utf-8") as f:
        targets = json.load(f)

    if targets.get("run_id") != run_id:
        raise ValueError("El identificador de targets.json no coincide")

    hosts = set(targets.get("windows", []))
    hosts.update(targets.get("linux", []))

    return sorted(hosts)


def has_manifest(host, run_id):
    path = RESULTS_DIR / host / run_id / "manifest.json"

    if not path.is_file():
        return False

    try:
        with path.open(encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    return (
        manifest.get("run_id") == run_id
        and manifest.get("host") == host
        and manifest.get("status") == "reports_verified"
    )

def get_host_status(host, run_id):
    state_file = (
        BASE_DIR
        / "logs"
        / "runs"
        / run_id
        / "hosts"
        / f"{host}.json"
    )

    if not state_file.is_file():
        return "unknown"

    try:
        with state_file.open(encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return "unknown"

    if (
        state.get("host") != host
        or state.get("run_id") != run_id
    ):
        return "unknown"

    return state.get("status", "unknown")

def get_host_error(host, run_id):
    events_dir = (
        BASE_DIR
        / "logs"
        / "runs"
        / run_id
        / "events"
        / host
    )

    if not events_dir.is_dir():
        return None

    events = []

    for event_file in events_dir.glob("*.json"):
        try:
            with event_file.open(encoding="utf-8") as f:
                event = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if (
            event.get("host") == host
            and event.get("run_id") == run_id
            and event.get("status") in ("failed", "unreachable")
        ):
            events.append(event)

    if not events:
        return None

    # Seleccionar el último error registrado.
    return max(
        events,
        key=lambda event: event.get("timestamp", "")
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()

    hosts = get_run_hosts(args.run_id)

    collected = []
    incomplete = []
    failed = []
    unreachable = []
    unknown = []

    for host in hosts:
        status = get_host_status(host, args.run_id)
        error = get_host_error(host, args.run_id)

        if status == "collected" and has_manifest(host, args.run_id):
            collected.append(host)

        elif status == "collected":
            incomplete.append(host)

        elif error and error["status"] == "unreachable":
            unreachable.append((host, error["task"]))

        elif error and error["status"] == "failed":
            failed.append((host, error["task"]))

        else:
            unknown.append(host)

    print()
    print("=" * 55)
    print("THOR AUTOMATION - RESUMEN DE EJECUCION")
    print("=" * 55)
    print(f"Ejecucion: {args.run_id}")
    print()
    print(f"Equipos previstos:       {len(hosts)}")
    print(f"Informes recuperados:    {len(collected)}")
    print(f"Resultados incompletos:  {len(incomplete)}")
    print(f"Fallos:                  {len(failed)}")
    print(f"Inaccesibles:            {len(unreachable)}")
    print(f"Estado desconocido:      {len(unknown)}")
    print()

    for host in collected:
        print(f"  [RECUPERADO] {host}")

    for host in incomplete:
        print(f"  [INCOMPLETO] {host}")

    for host, task in failed:
        print(f"  [FALLIDO] {host} - {task}")

    for host, task in unreachable:
        print(f"  [INACCESIBLE] {host} - {task}")

    for host in unknown:
        print(f"  [SIN ESTADO] {host}")


if __name__ == "__main__":
    main()