# THOR Automation

Ansible-based orchestration of **authorized** Nextron THOR scans on Windows and Linux endpoints from a Linux controller. One command deploys the licensed scanner, starts scans, retrieves JSON/HTML/TXT reports, and writes per-host manifests and a run summary.

> **Independent community automation.** Not affiliated with or endorsed by Nextron Systems. THOR binaries and license files are proprietary and **not included**. Use only with appropriate authorization and valid licenses.

## Status

Version **1.1 (publication draft)**. The original implementation completed an end-to-end test with **one Windows and one Linux host** on 24 Oct 2026. The portable copy and configuration templates have passed syntax/static checks; **70–80 host operation has not been load-tested**. Review scanner options and license compatibility before use.

## Requirements

- Linux controller, Python 3, `ansible-core` 2.20.1, `pywinrm`, Ansible collections `ansible.windows` and `community.windows`.
- Windows: reachable WinRM with suitable administrative credentials; Linux: reachable SSH and, where needed, sudo access.
- Legitimately acquired Nextron THOR ZIP archives for each OS and host-valid `.lic` files.
- Packages contain expected scanner executable and signatures.
- An authorized environment with sufficient network capacity and disk space for artifacts.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

The repository can live anywhere; paths are derived from the location of `thor-automation.sh`. To run Ansible directly from another shell, set `THOR_BASE_DIR` to the repository root or use the default path resolution provided in inventory group vars.

## Configure

1. Run `cp ansible/inventory/hosts.ini.example ansible/inventory/hosts.ini` and populate `ansible/inventory/hosts.ini`: retain `[controller] localhost ansible_connection=local`, and add aliases to `[windows]` and/or `[linux]`. **Do not commit your real inventory.**
2. For each target create `ansible/inventory/host_vars/<alias>/thor.yml` with `thor_package` matching its package filename. Windows also needs `thor_package_mode: separate` (or `bundled`, if applicable). See `ansible/inventory/host_vars/EXAMPLES.md`.
3. Put THOR ZIP files under `packages/windows/` and `packages/linux/`. Put valid `.lic` files under `licenses/`. None are distributed with this repository. **The current deployment logic copies every locally available license to each target; only put license files there that you are authorized to distribute to all configured targets.**
4. Set the actual remote installation paths or transport options by editing `ansible/inventory/group_vars/{windows,linux}.yml`. Protect Vault files and WinRM transport. The included Windows WinRM template uses **unencrypted HTTP/5985 with NTLM** for laboratory parity. For production prefer WinRM HTTPS/5986 with certificate validation and appropriate authentication, or a secured management network.
5. Ensure only authorized endpoints are in the inventory.

## Run

```bash
./thor-automation.sh
```

Prompts for the Ansible Vault password, executes separate Windows and Linux deploy/scan/collect stages (one Vault prompt), then saves outputs to:

```text
results/raw/<host>/<UTC-run-id>/thor.json
results/raw/<host>/<UTC-run-id>/thor.html
results/raw/<host>/<UTC-run-id>/thor.txt
results/raw/<host>/<UTC-run-id>/manifest.json
logs/runs/<UTC-run-id>/run.json
logs/runs/<UTC-run-id>/targets.json
logs/runs/<UTC-run-id>/hosts/<host>.json
logs/runs/<UTC-run-id>/events/<host>/*.json
logs/runs/<UTC-run-id>/ansible.log
logs/runs/<UTC-run-id>/summary.txt
```

`manifest.json` includes SHA-256 hashes of collected reports. The summary checks that the manifest metadata exists and matches the run, **but does not recompute report hashes**. To verify integrity manually, run `python3 scripts/create_manifest.py --host X --run-id ID --results-dir results/raw/X/ID --verify` (the current CLI requires all three parameters).

A nonzero Ansible run exit code is propagated by the launcher. The summary prioritizes a collected report over older error events and may categorize hosts as `RECUPERADO`, `INCOMPLETO`, `FALLIDO`, `INACCESIBLE`, or `SIN ESTADO`. `FAILED - RETRYING` lines from asynchronous polling can be temporary.

## Recover previously generated reports

The playbook supports collection-only recovery of an existing run ID. From `ansible/`:

```bash
THOR_BASE_DIR="$(cd .. && pwd)" ansible-playbook site.yml --ask-vault-pass \
  --tags collect_windows,collect_linux \
  -e thor_requested_run_id=YYYYMMDDTHHMMSSZ -e thor_recovery=true
```

This does **not** rerun THOR. Ensure remote reports are still present for the specified ID.

## Operational and security limitations

- The original v1.0 pipeline was tested with 2 endpoints. The broader v1.1 scans and split execution have only passed static validation in the lab; scaling, CPU/load and network transfer must be validated for the intended environment. Default Ansible `forks=5`.
- Windows and Linux stages execute separately, in order. If the Windows Ansible call fails, the Linux call is still attempted. Within each OS group, execution remains subject to Ansible play failure semantics.
- The run's `targets.json` snapshots the inventory groups; it does **not** account for `--limit`, so filtered runs can report unprocessed hosts as unknown.
- Hosts with no collected state, no error event and missing report are shown as `SIN ESTADO`; `run.json` initializes but is not updated to a terminal overall status.
- Scanner defaults now use normal (not quick) scanning: Windows uses `--allhds --require-admin`, Linux uses `--require-admin`. These request broad checks including process and rootkit modules, subject to THOR configuration, OS limitations, permissions and licensing. Scans are **not** forensic acquisition or proof of total coverage. Validate real module execution in THOR logs before operational use. Timeout is 8 hours per endpoint.
- Every available `.lic` is copied to each scanner folder; investigate a host-scoped license mapping for restricted deployments. Existing licenses on hosts are not removed automatically.
- Restrict access to all reports and controller logs, which may contain machine and security details.

## License

The Ansible automation and helper scripts are made available under the MIT License (see `LICENSE`). Nextron THOR binaries, signatures and license material are not covered by this license.
