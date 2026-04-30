# Sherlock — Username Techniques & Pivot Strategies

## Username Generation from Real Name

Given: `John Michael Doe`, born 1983, email `jdoe83@company.com`

```
# Name patterns
johndoe, john.doe, john_doe, jdoe, j.doe, j_doe
doejohn, doe.john, doe_john
johnmichaeldoe, jmd

# With birth year
johndoe83, john.doe83, jdoe1983, jdoe83
johndoe1983, johndoe_83

# Common suffixes/prefixes
_johndoe, johndoe_, real_johndoe, official_johndoe
xjohndoe, johndoex, johndoe_real

# Gaming/handle variants
j0hndoe, j0hn_d0e (l33t)
johndoe_gaming, johndoe_official
```

### Automate with Username Wordlist Tools

```bash
# usernamer (from name to usernames)
pip install usernamer
usernamer "John Doe"

# generate manually
python3 -c "
name = 'johndoe'
year = '83'
variants = [name, name+year, name+'_'+year, name[:4], name[0]+name.split('doe')[1]+year]
print('\n'.join(variants))
"
```

## Pivot Chain After Finding Accounts

1. **GitHub profile found** → check repos for email leaks, API keys, commit metadata
   ```bash
   curl https://api.github.com/users/<username>/events/public | jq '.[].payload.commits[].author'
   ```

2. **Twitter/X found** → extract followers, mentions, location data, linked sites

3. **LinkedIn found** → employer, colleagues, job history → new targets for spear phish

4. **Reddit found** → post history reveals interests, location, personal details
   ```bash
   # Reddit comment history
   curl "https://www.reddit.com/user/<username>/comments.json?limit=100" | jq '.data.children[].data | {body:.body, sub:.subreddit}'
   ```

5. **Steam/gaming found** → real name often in profile, friend lists reveal associates

6. **Gravatar found** → email hash → real email recovery
   ```python
   import hashlib
   email = "target@example.com"
   h = hashlib.md5(email.strip().lower().encode()).hexdigest()
   print(f"https://www.gravatar.com/{h}.json")
   ```

## Platform-Specific Tips

### GitHub

```bash
# Find email from commits
curl "https://api.github.com/users/<username>/events" | \
  jq '.[].payload.commits[]?.author | select(.email != null) | .email' | sort -u

# All repos
curl https://api.github.com/users/<username>/repos | jq '.[].full_name'
```

### LinkedIn (without auth — Google dorking)

```
site:linkedin.com/in "john doe" "company name"
site:linkedin.com/in johndoe
```

### Instagram

```bash
# Public profile scraper (Osintgram)
git clone https://github.com/Datalux/Osintgram
python3 main.py <username>
# Commands: info, followers, followings, hashtags, photos, location
```

### Facebook

```
site:facebook.com "john doe"
# Search by phone: facebook.com/search/top?q=<phone>
# Search by email: facebook.com/search/top?q=<email>
```

## Aggregating Results into Pipeline

```bash
# Run sherlock + save JSON
sherlock johndoe83 --json --output johndoe_results.json --print-found

# Extract platform names + URLs
jq 'to_entries[] | select(.value.status.status == "Claimed") | {platform: .key, url: .value.url_user}' johndoe_results.json

# Feed URLs into eyewitness for screenshots
eyewitness --urls johndoe_urls.txt --web
```

## OSINT Username Lookup Websites (Manual)

| Site | Use |
|------|-----|
| `whatsmyname.app` | Visual username checker |
| `namecheckr.com` | Domain + social availability |
| `namechk.com` | Social media availability |
| `pipl.com` | People search (paid) |
| `spokeo.com` | US people search |
