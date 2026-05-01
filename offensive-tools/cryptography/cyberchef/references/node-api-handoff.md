# CyberChef Reference — Node API Handoff

Use this when a validated web recipe must become an agentic, repeatable pipeline.

## Install

```bash
npm install --save cyberchef
```

## Basic operation usage

```javascript
const chef = require("cyberchef");
console.log(chef.fromBase64("U28gbG9uZyBhbmQgdGhhbmtzIGZvciBhbGwgdGhlIGZpc2gu"));
```

## Compose operations with Dish

```javascript
const result = new chef.Dish("Medium rare, please.")
  .apply(chef.ROT13)
  .apply(chef.toHex)
  .toString();
```

## `bake` for recipe execution

`chef.bake` supports operation functions, operation names, and exported web recipe JSON.

```javascript
const recipe = [
  { op: "To Base64", args: ["A-Z"] },
  { op: "Sort", args: ["Nothing (separate chars)", true, "Alphabetical (case sensitive)"] }
];

const out = await chef.bake("input", recipe);
console.log(out.toString());
```

## Argument mapping pitfalls

- Web UI labels become camelCase argument keys in API mode.
- Option strings are case-sensitive.
- Prefer reading allowed options from `chef.<operation>.args` or `chef.help(...)`.

## Exclusions

Most operations are available; flow-control operations are excluded in Node API.

## Agentic migration pattern

1. Stabilize recipe in web UI.
2. Export recipe JSON.
3. Execute same recipe with `chef.bake` in Node.
4. Add file I/O and batch loops.
5. Add strict output assertions to prevent silent corruption.
