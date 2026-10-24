# Per-host settings (examples only)

Create a directory matching each **inventory alias**, for example `host_vars/windows01/` or `host_vars/linux01/`.

For Windows, create `host_vars/windows01/thor.yml`:

```yaml
---
thor_package_mode: separate
thor_package: thor-windows_VERSION.zip
```

For Linux, create `host_vars/linux01/thor.yml`:

```yaml
---
thor_package: thor-linux_VERSION.zip
```

Create `credentials.yml` locally for each host **and immediately encrypt it** with Ansible Vault before committing anything. Example plaintext variables (DO NOT COMMIT):

```yaml
ansible_user: YOUR_USERNAME
ansible_password: YOUR_PASSWORD
# For Linux hosts that require sudo:
ansible_become_password: YOUR_SUDO_PASSWORD
```

Encrypt files with `ansible-vault encrypt inventory/host_vars/<host>/credentials.yml`. Check that no plaintext credential exists before staging. Better still, use SSH keys for Linux and supply secrets with an external secret manager.
