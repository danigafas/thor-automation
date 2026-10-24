DOCUMENTATION = r'''
---
name: thor_status
type: aggregate
short_description: Registra errores de ejecucion de THOR Automation
description:
  - Registra tareas fallidas y equipos inaccesibles.
  - Almacena los eventos en archivos JSON por equipo.
  - No modifica los estados finales de recuperacion.
  - Solo registra eventos si THOR_RUN_ID identifica una ejecucion existente.
requirements:
  - Python 3
'''

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ansible.plugins.callback import CallbackBase


BASE_DIR = Path(os.environ.get("THOR_BASE_DIR", Path(__file__).resolve().parents[2])) / "logs" / "runs"


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "thor_status"
    CALLBACK_NEEDS_ENABLED = True

    def _record_event(self, host, status, task_name):
        run_id = os.environ.get("THOR_RUN_ID", "")

        if not re.fullmatch(r"\d{8}T\d{6}Z", run_id):
            return

        run_dir = BASE_DIR / run_id

        # No crear registros para ejecuciones desconocidas.
        if not (run_dir / "targets.json").is_file():
            return

        # Evitar que un nombre de host pueda introducir rutas.
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", host):
            return

        event_dir = run_dir / "events" / host
        event_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        event = {
            "host": host,
            "run_id": run_id,
            "status": status,
            "task": task_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        event_file = event_dir / f"{uuid4().hex}.json"

        event_file.write_text(
            json.dumps(event, indent=2) + "\n",
            encoding="utf-8",
        )
        event_file.chmod(0o600)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not ignore_errors:
            self._record_event(
                result._host.get_name(),
                "failed",
                result._task.get_name(),
            )

    def v2_runner_on_unreachable(self, result):
        self._record_event(
            result._host.get_name(),
            "unreachable",
            result._task.get_name(),
        )