#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export THOR_BASE_DIR="$BASE_DIR"
ANSIBLE_DIR="$BASE_DIR/ansible"
LOGS_DIR="$BASE_DIR/logs"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$LOGS_DIR/runs/$RUN_ID"
mkdir -p "$LOGS_DIR/runs"
if [[ -e "$RUN_DIR" ]]; then
    echo "ERROR: Execution $RUN_ID already exists." >&2
    exit 1
fi
mkdir -m 700 "$RUN_DIR"
export THOR_RUN_ID="$RUN_ID"

# Keep the single Vault prompt for both OS phases. Temporary file in memory.
if [[ ! -d /dev/shm || ! -w /dev/shm ]]; then
    echo "ERROR: /dev/shm is required for temporary Vault credentials." >&2
    exit 1
fi
VAULT_FILE="$(mktemp /dev/shm/thor-vault.XXXXXXXX)"
trap 'rm -f "$VAULT_FILE"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
IFS= read -r -s -p "Vault password: " VAULT_PASSWORD
echo
printf '%s\n' "$VAULT_PASSWORD" > "$VAULT_FILE"
unset VAULT_PASSWORD

cd "$ANSIBLE_DIR"
echo "THOR AUTOMATION - Run: $RUN_ID"
RESULT=0

# Separate Ansible calls: an unreachable Windows host cannot stop Linux.
if ansible-playbook site.yml \
  --vault-password-file "$VAULT_FILE" \
  --tags deploy_windows,scan_windows,collect_windows \
  -e "thor_requested_run_id=$RUN_ID" \
  -e "thor_recovery=false" \
  2>&1 | tee "$RUN_DIR/ansible.log"; then
  echo "[OK] Windows stage complete"
else
  echo "[WARN] Windows stage exited with errors"
  RESULT=1
fi

if ansible-playbook site.yml \
  --vault-password-file "$VAULT_FILE" \
  --tags deploy_linux,scan_linux,collect_linux \
  -e "thor_requested_run_id=$RUN_ID" \
  -e "thor_recovery=true" \
  2>&1 | tee -a "$RUN_DIR/ansible.log"; then
  echo "[OK] Linux stage complete"
else
  echo "[WARN] Linux stage exited with errors"
  RESULT=1
fi

if python3 "$BASE_DIR/scripts/run_summary.py" "$RUN_ID" \
   | tee "$RUN_DIR/summary.txt"; then
  echo "Summary generated"
else
  echo "[ERROR] Could not generate summary"
  RESULT=1
fi

echo "Reports: $BASE_DIR/results/raw"
echo "Log:     $RUN_DIR/ansible.log"
echo "Summary: $RUN_DIR/summary.txt"
exit "$RESULT"
