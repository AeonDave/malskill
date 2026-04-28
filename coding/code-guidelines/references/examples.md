# Examples

Concrete before/after examples for each of the five code guidelines principles.
Load this file when a principle needs illustration.

## Table of Contents

1. [Think Before Coding](#1-think-before-coding)
2. [Simplicity First](#2-simplicity-first)
3. [Surgical Changes](#3-surgical-changes)
4. [Goal-Driven Execution](#4-goal-driven-execution)
5. [Self-Review Before Returning](#5-self-review-before-returning)
6. [Anti-Patterns Summary](#anti-patterns-summary)

---

## 1. Think Before Coding

### Hidden Assumptions

**Request:** "Add a feature to export user data"

❌ LLM assumes: export ALL users, writes to a local file, infers fieldnames.

✅ Surface assumptions first:

```
Before implementing, I need to clarify:

1. Scope: export all users or a filtered subset? (privacy implications)
2. Format: download in browser, background job, or API endpoint?
3. Fields: which user fields? (some may be sensitive)
4. Volume: how many users typically? (affects approach)

Simplest path: an API endpoint returning paginated JSON.
What's your preference?
```

### Multiple Interpretations

**Request:** "Make the search faster"

❌ LLM silently adds caching, indexes, and async in one 200-line commit.

✅ Present interpretations:

```
"Make the search faster" could mean:

1. Faster response time (< 100ms) — add DB indexes, cache frequent queries
2. Higher throughput — add async, connection pooling
3. Faster perceived speed (UX) — show partial results, progressive loading

Current search takes ~500ms for typical queries.
Which aspect matters most?
```

---

## 2. Simplicity First

### Over-abstraction

**Request:** "Add a function to calculate discount"

❌ LLM delivers `DiscountStrategy` ABC, `PercentageDiscount`, `FixedDiscount`,
`DiscountConfig` dataclass, and `DiscountCalculator` — 80+ lines for one operation.

✅ One function until complexity is actually needed:

```python
def calculate_discount(amount: float, percent: float) -> float:
    """Calculate discount amount. percent should be 0-100."""
    return amount * (percent / 100)
```

### Speculative Features

**Request:** "Save user preferences to database"

❌ LLM adds optional cache, validator, merge flag, notification callback —
none of which were requested.

✅ Just what was asked:

```python
def save_preferences(db, user_id: int, preferences: dict):
    db.execute(
        "UPDATE users SET preferences = ? WHERE id = ?",
        (json.dumps(preferences), user_id)
    )
```

Add caching, validation, and merging only when the requirement actually emerges.

---

## 3. Surgical Changes

### Drive-by Refactoring

**Request:** "Fix the bug where empty emails crash the validator"

❌ LLM also "improves" email regex, adds username length/alphanumeric checks,
rewrites comments, and adds a docstring — none of which were requested.

✅ Fix only the reported crash:

```diff
  def validate_user(user_data):
      # Check email format
-     if not user_data.get('email'):
+     email = user_data.get('email', '')
+     if not email or not email.strip():
          raise ValueError("Email required")

-     if '@' not in user_data['email']:
+     if '@' not in email:
          raise ValueError("Invalid email")

      # Check username
      if not user_data.get('username'):
          raise ValueError("Username required")

      return True
```

Only the empty-email lines changed.

### Style Drift

**Request:** "Add logging to the upload function"

❌ LLM adds type hints, changes single quotes to double quotes, rewrites
the boolean return, reformats whitespace — matching personal style, not project style.

✅ Match existing style; add only the logger calls:

```diff
+ import logging
+ logger = logging.getLogger(__name__)
+
  def upload_file(file_path, destination):
+     logger.info(f'Starting upload: {file_path}')
      try:
          with open(file_path, 'rb') as f:
              data = f.read()
          response = requests.post(destination, files={'file': data})
          if response.status_code == 200:
+             logger.info(f'Upload successful: {file_path}')
              return True
          else:
+             logger.error(f'Upload failed: {file_path}, status={response.status_code}')
              return False
      except Exception as e:
-         print(f"Error: {e}")
+         logger.exception(f'Upload error: {file_path}')
          return False
```

Single quotes, no type hints, original boolean pattern — unchanged.

---

## 4. Goal-Driven Execution

### Vague vs. Verifiable

**Request:** "Fix the authentication system"

❌ LLM states "I'll review the code, identify issues, make improvements,
and test the changes" — no success criteria, no way to know when done.

✅ Define verifiable goals:

```
To "fix authentication" I need to define success criteria.
What specific issue are we solving?

If the issue is "users stay logged in after password change":

Plan:
1. Write test: change password → verify old session invalidated
   Verify: test fails (reproduces bug)
2. Implement: invalidate sessions on password change
   Verify: test passes
3. Check edge cases: multiple sessions, concurrent changes
   Verify: additional tests pass
4. Verify no regression: existing auth tests still pass

What's the specific auth issue you're seeing?
```

### Multi-Step with Verification

**Request:** "Add rate limiting to the API"

❌ LLM implements full rate limiting with Redis, multiple strategies,
config system, and monitoring in one 300-line commit. No verification steps.

✅ Incremental with explicit verification:

```
Plan for rate limiting:

1. Add basic in-memory rate limiting (single endpoint)
   Verify: 100 requests → first 10 succeed, rest get 429

2. Extract to middleware (apply to all endpoints)
   Verify: rate limits apply to /users and /posts; existing tests pass

3. Add Redis backend (multi-server)
   Verify: rate limit persists across app restarts; two instances share counter

4. Add per-endpoint configuration
   Verify: /search allows 10/min, /users allows 100/min

Each step is independently verifiable. Start with step 1?
```

### Test-First Bug Fix

**Request:** "The sorting breaks when there are duplicate scores"

❌ LLM immediately changes sort logic without confirming the bug.

✅ Reproduce first, then fix:

```python
# 1. Write a test that reproduces the issue
def test_sort_with_duplicate_scores():
    scores = [
        {'name': 'Alice', 'score': 100},
        {'name': 'Bob',   'score': 100},
        {'name': 'Charlie', 'score': 90},
    ]
    result = sort_scores(scores)
    # Run 10 times — fails with inconsistent ordering for duplicates

# 2. Fix with stable sort
def sort_scores(scores):
    """Sort by score descending, then name ascending for ties."""
    return sorted(scores, key=lambda x: (-x['score'], x['name']))

# Verify: test passes consistently
```

---

## 5. Self-Review Before Returning

### Output Review Checklist

**Request:** "Add input sanitization to the registration endpoint"

❌ Generated output contains:
- Sanitization logic added ✓
- Type annotations added to the entire file
- All string literals converted from single to double quotes
- A new `validate_email` helper extracted (not requested)

✅ Correct self-review catches this before returning:

```
Self-review:
- Line 12-14: sanitization added ✓ (traces to request)
- Line 3-9: type annotations added ✗ (not requested, reverting)
- Line 22: quote style changed ✗ (style drift, reverting)
- validate_email helper: ✗ (speculative abstraction, removing)

Revised diff: only lines 12-14 changed.
```

### Sycophancy Check

**Request:** "Use a global variable to store the database connection"

❌ Sycophantic response: implements global `db` without comment.

✅ Correct response pushes back:

```
Global state for a database connection creates hidden coupling
and makes testing difficult. A common alternative is to pass
the connection explicitly or use a context object.

If you have a specific constraint (e.g. script with single entry point),
I can implement the global version — just confirm.
```

---

## Anti-Patterns Summary

| Principle | Anti-Pattern | Fix |
|---|---|---|
| Think Before Coding | Silently assumes file format, fields, scope | List assumptions explicitly; ask for clarification |
| Simplicity First | Strategy pattern for a single discount calculation | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds type hints while fixing a bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |
| Self-Review | Returns output without checking diff for orthogonal changes | Re-read every changed line; revert anything not traceable to the request |

---

## Key Insight

The "overcomplicated" examples are not obviously wrong — they follow design patterns
and best practices. The problem is **timing**: they add complexity before it is needed.

**Good code solves today's problem simply, not tomorrow's problem prematurely.**
