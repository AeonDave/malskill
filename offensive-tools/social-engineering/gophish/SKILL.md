---
name: gophish
description: "Open-source phishing campaign framework with web UI for creating credential harvesting campaigns, tracking click-through rates, and managing targets. Use when asked to set up a phishing campaign, create credential harvesting pages, send spear-phishing emails, or generate phishing infrastructure."
license: MIT
compatibility: "Linux, Windows, macOS. Download prebuilt binary from GitHub releases. Requires inbound TCP 443/80 and SMTP relay. No OS dependencies."
metadata:
  author: AeonDave
  version: "1.0"
---

# GoPhish

Full phishing campaign framework — manage targets, templates, landing pages, and capture credentials via web UI.

## Quick Start

```bash
# Start GoPhish (default: admin UI on :3333, phishing on :80)
./gophish

# Custom config
./gophish --config config.json

# Access admin UI
# https://127.0.0.1:3333 (default admin:gophish, change on first login)
```

## Configuration (config.json)

```json
{
  "admin_server": {
    "listen_url": "127.0.0.1:3333",
    "use_tls": true,
    "cert_path": "gophish_admin.crt",
    "key_path": "gophish_admin.key"
  },
  "phish_server": {
    "listen_url": "0.0.0.0:443",
    "use_tls": true,
    "cert_path": "/etc/letsencrypt/live/phish.example.com/fullchain.pem",
    "key_path": "/etc/letsencrypt/live/phish.example.com/privkey.pem"
  },
  "db_name": "sqlite3",
  "db_path": "gophish.db"
}
```

## Campaign Workflow

1. **Sending Profile** — configure SMTP relay (host, port, from, username, password)
2. **Email Template** — HTML/text body with `{{.FirstName}}`, `{{.URL}}`, `{{.Tracker}}`
3. **Landing Page** — clone target login page; enable Capture Credentials + Redirect to
4. **User & Group** — import CSV: `First Name, Last Name, Email, Position`
5. **Campaign** — link all above, set send schedule, launch

## Email Template Variables

| Variable | Description |
|----------|-------------|
| `{{.FirstName}}` | Target first name |
| `{{.LastName}}` | Target last name |
| `{{.Email}}` | Target email |
| `{{.Position}}` | Target job title |
| `{{.From}}` | Sending address |
| `{{.URL}}` | Unique phishing link (auto-generated) |
| `{{.Tracker}}` | Open-tracking pixel |
| `{{.RId}}` | Unique recipient ID |

## Common Workflows

```bash
# Import targets from CSV
# CSV format: First Name,Last Name,Email,Position
cat > targets.csv << 'EOF'
First Name,Last Name,Email,Position
John,Doe,jdoe@target.com,Developer
EOF

# API: list campaigns
curl -k -H "Authorization: Bearer API_KEY" https://127.0.0.1:3333/api/campaigns/

# API: get campaign results
curl -k -H "Authorization: Bearer API_KEY" https://127.0.0.1:3333/api/campaigns/1/results
```

## SMTP Relay Options

- **Sendgrid / Mailgun** — free tier available
- **Self-hosted Postfix** — configure SPF/DKIM/DMARC for deliverability
- **SMTP2GO** — good deliverability, free tier

## Infrastructure Tips

- Register lookalike domain (e.g., `target-helpdesk.com`)
- Set up Let's Encrypt TLS on phishing server
- Add SPF, DKIM, DMARC records for sending domain
- Use email warmup for better inbox placement

## Resources

| File | When to load |
|------|--------------|
| `references/campaign-setup.md` | Full setup guide: SMTP config, DNS records, landing page cloning, API usage |
