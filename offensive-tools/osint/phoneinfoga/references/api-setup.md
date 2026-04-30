# PhoneInfoga — API Setup & Phone Lookup Sources

## Config File

```yaml
# ~/.phoneinfoga/config.yaml

numverify_api_key: ""     # https://numverify.com — free tier: 100 req/month
googlecse_api_key: ""     # https://console.developers.google.com
googlecse_cx: ""          # Custom Search Engine ID from cse.google.com
```

## NumVerify Setup

1. Register at https://numverify.com (free: 100 req/month)
2. Copy API key from dashboard
3. Add to config

Provides: carrier name, line type (mobile/landline/VoIP), country validation, local format.

## Google Custom Search Engine

1. Go to https://cse.google.com/create/new
2. Set "Sites to search" = `*.com` or leave open for web-wide
3. Enable "Search the entire web"
4. Copy Search engine ID (cx)
5. Get API key from https://console.cloud.google.com → Custom Search JSON API

Free: 100 queries/day.

## Alternative Phone Lookup Sources

### Manual / Web

| Source | URL | Use |
|--------|-----|-----|
| Truecaller | truecaller.com | Crowdsourced name lookup |
| Sync.me | sync.me | Social media linked to phone |
| eyecon | eyecon.mobi | Caller ID database |
| That'sThem | thatsthem.com | US reverse lookup |
| Spokeo | spokeo.com | US people search (paid) |
| BeenVerified | beenverified.com | US comprehensive lookup |

### Telegram OSINT (phone → account)

```python
# If target uses Telegram — find by phone (requires Telethon)
from telethon.sync import TelegramClient

client = TelegramClient('session', api_id, api_hash)
with client:
    result = client(ImportContactsRequest([InputPhoneContact(
        client_id=0, phone='+14151234567', first_name='x', last_name='y'
    )]))
    if result.users:
        print(result.users[0].username, result.users[0].id)
```

### WhatsApp Check

```bash
# WhatsApp uses phone as primary ID — check if number active
# Use WA web with puppeteer or manual check: wa.me/+14151234567
```

### Google Dork Templates

```
# Direct search
"+1 415 123 4567"
"+14151234567"
"(415) 123-4567"

# Social media
"+14151234567" site:linkedin.com OR site:facebook.com OR site:twitter.com

# Business directory
"+14151234567" site:yelp.com OR site:yellowpages.com

# Remove noise
"+14151234567" -site:whitepages.com -site:zabasearch.com -site:peoplefinders.com

# WhatsApp/Telegram mentions
"+14151234567" "whatsapp" OR "telegram" OR "signal"
```

## International Format Reference

PhoneInfoga requires E.164 format (`+<country_code><number>`):

| Country | Format | Example |
|---------|--------|---------|
| USA/Canada | `+1` | `+14151234567` |
| UK | `+44` | `+447911123456` |
| Italy | `+39` | `+393331234567` |
| Germany | `+49` | `+4915901234567` |
| France | `+33` | `+33612345678` |

```bash
# Convert Italian number 333 1234567
phoneinfoga scan -n +393331234567
```
