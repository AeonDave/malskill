# SaaS & Collaboration Surface OSINT

Load when investigating public collaboration surfaces tied to a target: Postman workspaces, Stack Exchange code pastes, public SaaS workspaces, or chat/community discovery.

---

## 1. Postman public workspace universal search

Public-search endpoint is **unauthenticated** and indexes every workspace marked public.

```bash
curl -sk -m 15 \
  "https://www.postman.com/_api/ws/proxy" \
  -H 'Content-Type: application/json' \
  -H 'X-Entity-Team-Id: 0' \
  -d '{
    "service":"search",
    "method":"POST",
    "path":"/search-all",
    "body":{
      "queryIndices":["collaboration.workspace","runtime.collection","runtime.request"],
      "queryText":"acme.com",
      "size":100,
      "from":0,
      "clientTraceId":"",
      "queryAllIndices":false,
      "domain":"public"
    }
  }' | jq '.data[]'
```

Pagination: bump `from` by 100. If the proxy shape changes (it has historically), inspect a real `https://www.postman.com/explore` search via DevTools Network → copy as cURL → adapt.

### Per-workspace walk
```bash
WS_ID="<workspace-id>"
curl -sk -m 10 "https://www.postman.com/_api/workspace/$WS_ID" | jq .
curl -sk -m 10 "https://www.postman.com/_api/workspace/$WS_ID/collection" | jq '.[].id'
curl -sk -m 10 "https://www.postman.com/_api/workspace/$WS_ID/environment" | jq '.[].id'

COL_ID="<collection-id>"
curl -sk -m 10 "https://www.postman.com/_api/collection/$COL_ID" | jq '.collection.item[]'
```

### Ownership scoring
- Creator/team name mentions target → strong
- Workspace name/description mentions target → strong
- Request URLs match `*.target.com` → strongest (actively used against target's APIs)

Run the secret catalog from `references/secret-patterns-and-validators.md` §1 over every request body, URL, header, env var, pre-request script, and test script.

---

## 2. Stack Exchange sweep

8 sites with highest signal for developer code paste-ins:
```
stackoverflow.com
serverfault.com
dba.stackexchange.com
devops.stackexchange.com
security.stackexchange.com
superuser.com
sharepoint.stackexchange.com
salesforce.stackexchange.com
```

API:
```
GET https://api.stackexchange.com/2.3/search/advanced
   ?site=<site>
   &q=<target>
   &filter=withbody
   &pagesize=100
```

Code-block extraction:
```regex
<pre><code>([\s\S]*?)</code></pre>
```

### Pipeline
1. Query each site for target name / brand / root domain.
2. Extract code blocks from response `body`.
3. Run secret catalog over every block.
4. Cross-reference post author email (when exposed in profile) against email_osint discoveries → confirms employee posting target's internal code.
5. Hostnames from code → upsert as `subdomain` assets.

### Quota
- 300 req/day without a key (`quota_max` returned by the live API; the docs' default is 10,000)
- 10,000 req/day with free API key
- Throttle: 30 req/s per IP; honor the `backoff` field returned in responses

---

## 3. Generic public SaaS collaboration

Dork these like search engines:
```
trello.com
notion.so / notion.site
*.atlassian.net               (Jira / Confluence)
miro.com
asana.com
clickup.com
airtable.com
```

Template:
```
site:{platform} "{target-keyword}"
```

### Common finding classes
- Public Trello board w/ creds in card titles or attached config files
- Public Notion page w/ internal SOPs, API keys in code blocks, customer data
- Public Confluence space w/ onboarding docs containing seed creds
- Public Miro board w/ architecture diagrams revealing internal hostnames

Severity mapping in `references/attack-path-and-severity.md` §4 (MED-HIGH).

---

## 4. Slack / Discord / Telegram / Teams / Mattermost

### 4.1 Slack
- Public workspace directories: Slofile (`https://slofile.com/`), Slacklist, community lists.
- Invite-link discovery dorks:
  ```
  site:join.slack.com "{target}"
  inurl:slack.com inurl:shared_invite "{target}"
  ```
  GitHub: `"join.slack.com/t/<target-stem>" filename:README`
  X/Reddit search for shared invite links.
- Workspace existence (passive probe, no auth): `https://<slug>.slack.com/api/auth.test` without a token returns `not_authed` for live and non-existent subdomains alike, so the response does not distinguish them.
- **Finding (passive):** open invite link that bypasses normal member-approval is itself the OSINT finding → MED severity (workspace boundary control failure). Joining the workspace is live participation, out of scope for OSINT — document the URL and access-control gap.

### 4.2 Discord
- No central public directory.
- DiscordServers.com, Discord.me, Top.gg — third-party directories.
- Dorks: `site:discord.gg "{target}"`, `site:discord.com "{target}"`.
- Resolve invite: `GET https://discord.com/api/v9/invites/<token>?with_counts=true` → server name/ID/member count/channel info.
- Bot enum: with a bot token (#47 in the secret catalog), `GET /users/@me` returns the bot's own User object; it lists no servers.

### 4.3 Telegram
- TGStat (channel analytics + search)
- Telemetr (channel growth + overlaps)
- Combot (group analytics)
- Public channel view: `https://t.me/s/<channel>`
- Invite link dorks: `site:t.me "{target}"`

### 4.4 Microsoft Teams (federation)
- Federation check via Microsoft Graph (auth required).
- Open-federation default = anyone can chat target's users via `<email>@<target>` lookup.
- Detail: `osint-technique/SKILL.md` + `references/identity-fabric-enumeration.md` §7.

### 4.5 Mattermost / Rocket.Chat / self-hosted
- Patterns: `https://mattermost.<target>.com`, `chat.<target>`.
- Open-registration probe: `/signup` accessible without invite → anyone joins.
- Version disclosure: `/api/v4/system/ping` → known CVEs.

---

## 5. Hard rules
- Postman + Stack Exchange searches are read-only public APIs.
- The open-invite link is the Slack/Discord finding; joining the workspace is live participation.
- Bot token enumeration: identity check is read-only; send/post methods have side effects on the workspace.
