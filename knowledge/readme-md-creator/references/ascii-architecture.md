# ASCII Architecture Guidance

Use ASCII architecture only when a small text diagram helps readers understand a flow faster than prose.

## When to include it

Include a compact ASCII diagram when:

- the project has 3 or more meaningful components
- data or request flow matters
- readers need a quick mental model before setup
- the repository does not already have a better architecture image nearby

## When not to include it

Do not include ASCII architecture when:

- the app is effectively one component
- the same information is obvious from one short paragraph
- the diagram would exceed a compact width or become hard to read
- the architecture is uncertain or inferred rather than verified

## Rules

- Keep width roughly under 80–100 characters.
- Show one flow at a time.
- Use stable component names that exist in the repo or docs.
- Add one sentence below the diagram explaining the flow.
- Prefer boxes and arrows over decorative art.

## Good patterns

### Request flow

```text
Browser
  |
  v
Web app (`packages/webapp`)
  |
  v
API (`packages/api`)
  |
  +--> Database
  |
  `--> External service
```

### Workspace map

```text
repo/
├─ app/        # user-facing application
├─ packages/   # reusable modules
└─ docs/       # detailed documentation
```

### Pipeline view

```text
Source files -> Build step -> Output artifacts -> Deployment target
```

## Bad patterns

- huge diagrams with every dependency and folder
- arrows going in all directions without labels
- banner-like ASCII art that adds no information
- pseudo-network maps made from guesswork

## Fallback strategy

If a diagram is useful but ASCII becomes messy:

1. replace it with a short bullet list of components, or
2. reference an image already present in the repository
