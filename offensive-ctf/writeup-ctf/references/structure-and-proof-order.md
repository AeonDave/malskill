# Writeup Structure and Proof Order

Load when turning notes, commands, and solver output into a final writeup.

## One-page structure

Keep the main path in this order:

1. Objective
2. Starting artifacts and scope
3. Key observation that changed direction
4. Minimal solve path
5. Verification signal
6. Solver or command sequence
7. Lessons worth keeping

If the writeup cannot fit this structure cleanly, it is usually mixing proof with noise.

## Main path rules

- Write from evidence, not memory.
- Prefer one complete solve path over multiple half-explained alternatives.
- Keep the path to 1–3 short phases unless the proof genuinely needs more structure.
- Every step should answer: what was seen, what was done, what changed.
- Name the exact oracle that proved success: flag, output, event, storage diff, decoded value, or reproduced behavior.

## Dead ends

Keep failed paths only when they teach something reusable.

Format:

- hypothesis
- check run
- why it failed
- why the next path was chosen

Do not dump full trial-and-error history.

## Reproducibility minimum

A reader should be able to rerun the solve from the writeup with:

- the input artifact or challenge data
- one solver script or one concise command sequence
- any required environment note that changes the result
- the expected success signal

## Common pitfalls

- opening with the flag before the proof path exists
- mixing guesses and confirmed facts in the same sentence
- posting huge terminal transcripts instead of the decisive lines
- listing every command ever tried instead of the commands that proved the solve
- hiding the real oracle behind screenshots only
