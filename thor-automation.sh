#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export THOR_BASE_DIR="$BASE_DIR"
ANSIBLE_DIR="$BASE_DIR/ansible"
LOGS_DIR="$BASE_DIR/logs"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$LOGS_DIR/runs/$RUN_ID"

if [[ -e "$RUN_DIR" ]]; then
    echo "ERROR: La ejecución $RUN_ID ya existe." >&2
    exit 1
fi

mkdir -m 700 "$RUN_DIR"

export THOR_RUN_ID="$RUN_ID"

echo
echo "=========================================="
echo "       THOR AUTOMATION"
echo "=========================================="
echo "Ejecucion: $RUN_ID"
echo

cd "$ANSIBLE_DIR"

# Ejecutar despliegue, analisis y recuperacion.
if ansible-playbook site.yml \
    --ask-vault-pass \
    -e "thor_requested_run_id=$RUN_ID" \
    2>&1 | tee "$RUN_DIR/ansible.log"
then
    RESULT=0
else
    RESULT=1
fi

echo
echo "=========================================="
echo "       RESUMEN FINAL"
echo "=========================================="

python3 "$BASE_DIR/scripts/run_summary.py" "$RUN_ID" \
    | tee "$RUN_DIR/summary.txt" || RESULT=1

echo
echo "Informes: $BASE_DIR/results/raw"
echo "Registro: $RUN_DIR/ansible.log"
echo "Resumen:  $RUN_DIR/summary.txt"

exit "$RESULT"
