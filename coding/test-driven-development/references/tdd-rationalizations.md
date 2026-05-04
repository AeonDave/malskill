# TDD Rationalizations

Use this when speed, confidence, or sunk cost makes test-first discipline feel optional.

| Shortcut | Reality |
|---|---|
| “Too simple to test” | Small code still breaks; a focused test is usually cheap. |
| “I will test after” | Tests-after are biased by the implementation and may only document what was built. |
| “Manual testing is faster” | Manual checks are not repeatable and vanish under refactor pressure. |
| “Keep the old code as reference” | Adapting existing code can become tests-after in disguise. |
| “This is exploratory exploit work” | Spikes are valid, but claims of reliability need a reproducer or harness. |
| “Existing code has no tests” | Add characterization around the behavior you are changing. |

## Legitimate exceptions

- throwaway spike explicitly discarded after learning,
- generated code where generator tests are the real target,
- pure configuration with a separate validation command,
- emergency hotfix where the operator explicitly accepts risk.

Even then, record the verification debt and add a reproducer or test before broadening the claim.

## Offensive-development adaptations

- Exploit primitives: write a harness that proves the primitive or preserves the crash/leak input.
- Fuzzing: minimize and pin the crashing sample before claiming a bug class.
- Payload/loader work: assert ABI, artifact format, and cleanup behavior with the smallest local harness.
- Network tools: use captured transcripts or local protocol fakes before live replay.
