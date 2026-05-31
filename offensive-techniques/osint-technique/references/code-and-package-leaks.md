# Code & Package Registry Leak Hunting

Reference for systematically hunting target-attributed secrets across public code hosts and package registries. Methodology link: `osint-technique/SKILL.md` §19+§44.

---

## 1. GitHub Code-Search Dorks — 13 templates

Replace `{target}` (root domain stem like `acme`), `{domain}` (full root like `acme.com`), `{company}` (`Acme Corporation`).

```
"{target}" filename:.env
"{target}" filename:.env.example
"{target}" filename:config
"{target}" AWS_ACCESS_KEY_ID
"{target}" AWS_SECRET_ACCESS_KEY
"{target}" password
"{target}" api_key
"{target}" secret
"{target}" authorization: Bearer
"{target}" filename:id_rsa
"{target}" filename:.git-credentials
"{target}" filename:wp-config.php
"@{domain}" password
```

**Requirements:** GitHub PAT (read-only repo scope is enough); concurrency ≤5; respect rate limit.

**Per-result flow**
1. Fetch fragment via GitHub Contents API.
2. Run `references/secret-patterns-and-validators.md` §1 (48-pattern catalog).
3. Hit → `SECRET_LEAK` finding with catalog severity, evidence = repo URL + path + last-4 of secret.
4. Optional deep: clone tempdir, `trufflehog` / `gitleaks` full history (often catches deleted leaks).

**Adjacent platforms** (same dork shape, different APIs): GitLab Snippets/CI, Bitbucket Snippets, Gitea, Sourcehut, Codeberg, Pastebin/Pastee, Gist (GitHub Search API doesn't fully cover gists — query via `https://gist.github.com/search`).

---

## 2. Package registry sweep

For each registry: list packages owned/published by target → list all historical versions → download archive → extract → run secret catalog → flag findings.

Older versions are gold — many devs ship leak, notice, publish fix in next version, but **don't unpublish**.

### 2.1 npm
```bash
npm search "<keyword>"
npm view @<scope>/<package>
# Org enumeration
curl -s "https://registry.npmjs.org/-/org/<org>/package" | jq .
# All versions metadata
curl -s "https://registry.npmjs.org/<package>" | jq '.versions | keys[]'
# Download a version's tarball
npm pack <package>@<version>
tar -xzf <package>-<version>.tgz && cd package/
# Scan
```
Common leaks: `.env` shipped in tarball, `package.json` `scripts` referencing CI secrets, hardcoded keys in `dist/` builds, source maps with `sourcesContent`.

### 2.2 PyPI
```bash
# Metadata + version history
curl -s "https://pypi.org/pypi/<package>/json" | jq '.releases | keys[]'
# Download
pip download <package>==<version> --no-deps -d /tmp/pkg
unzip /tmp/pkg/*.whl -d /tmp/pkg/x
# or
tar -xzf /tmp/pkg/*.tar.gz
```
Common leaks: `setup.py` URLs, test fixtures with live creds, accidentally-bundled `.pypirc` / `.netrc`.

### 2.3 RubyGems
```bash
curl -s "https://rubygems.org/api/v1/gems/<gem>.json"
gem fetch <gem> && gem unpack <gem>-<version>.gem
```

### 2.4 Cargo
```bash
curl -s "https://crates.io/api/v1/crates/<crate>" | jq .
# Download
curl -L -o /tmp/c.crate "https://crates.io/api/v1/crates/<crate>/<version>/download"
tar -xzf /tmp/c.crate
```

### 2.5 Packagist (Composer)
```bash
curl -s "https://packagist.org/packages/<vendor>/<package>.json"
```

### 2.6 NuGet, Maven Central
- `https://www.nuget.org/packages?q=<target>`
- `https://search.maven.org/?q=<target>`
- Maven Central REST: `https://search.maven.org/solrsearch/select?q=g:<group>&rows=200&wt=json`

### 2.7 Container registries
- Docker Hub: `https://hub.docker.com/v2/repositories/<user-or-org>/?page_size=100`
- Public catalog (self-hosted): `GET /v2/_catalog`
- GHCR / ECR Public / Quay: same OCI distribution spec
- Per-layer scan: `skopeo copy docker://<image> dir:/tmp/x` → walk layer tarballs → run secret catalog

### 2.8 Typosquat surveillance
For every package the target owns, generate near-name candidates (char swap, dash↔underscore, separator add/remove, common typo) and check whether already registered by a non-target party.

```bash
# Target package: acme-utils
for c in acme-util acmeutils acme_utils acme.utils ac-me-utils acme-uitls acme-utiles; do
  npm view "$c" 2>&1 | head -2
done
```
Registered to non-target → MEDIUM `TYPOSQUAT_CANDIDATE` (supply-chain risk; advise defensive registration).

---

## 3. Output schema

```json
{
  "finding": "SECRET_LEAK|TYPOSQUAT_CANDIDATE",
  "registry": "npm|pypi|rubygems|cargo|packagist|nuget|maven|dockerhub|github|gitlab|gist|pastebin",
  "package": "<name>",
  "version": "<version>",
  "file_path": "<path/inside/archive>",
  "secret_pattern": "<catalog#>",
  "secret_truncated": "****<last4>",
  "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL",
  "url": "<canonical url>"
}
```

## 4. Hard rules
- Only read public artifacts. Do not authenticate against private packages.
- Never validate `package:publish`-scoped tokens — that scope writes by definition.
- Truncate every secret in evidence (last 4 chars).
- Older non-current versions = highest hit rate; always walk history.
