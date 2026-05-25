# Compression evidence for 1337

Use this when changing 1337's compression policy or evaluating claims that a prompt/skill saves tokens.

## Evidence snapshot

- Max Taylor's 2026 `cc-compression-bench` compared baseline, `Be brief.`, Caveman lite/full/ultra over 24 dev prompts, judged by rubric. `Be brief.` matched baseline quality and Caveman token range: baseline 636 mean tokens, brief 419, lite 401, full 404, ultra 449.
- All arms hit 100% key points and zero `must_avoid` traps. Raw compression did not prove a Caveman correctness win.
- Caveman's remaining differentiators were structure, intensity switching, persistence, and Auto-Clarity safety escape.
- Failure modes: lite dropped a required term once; ultra inflated setup/security answers when safety escape/tool-first behavior triggered.
- HN/Reddit discussion highlighted input-token overhead, single-run variance, and need for multi-turn drift tests.
- Adam Sohn's repeated same-prompt lambda benchmark showed large run-to-run variance even when every output passed.
- `adam-s/testing-claude-agent` found tests and stable first approaches dominate token-to-green more than long instruction files.
- Chain-of-Draft supports compact intermediate drafts, but only if essential state is preserved.

## 1337 design rules

- Optimize token-to-green, not shortest message.
- Treat `be brief` as enough for simple output shortening; use 1337 for stable operator shape, routing, verification, and persistence.
- Preserve exact terms, commands, errors, paths, hashes, IOCs, CVEs, and user-required wording before compression.
- Keep `full` as stable default. Use `ultra` only for explicit max-compression or token crisis.
- Compression must not cause tool-first overreach, skipped verification, missing warnings, or lost multi-turn state.
- Keep the skill lean; each rule has recurring input-token cost.

## Sources

- https://www.maxtaylor.me/articles/i-benchmarked-caveman-against-two-words
- https://github.com/max-taylor/cc-compression-bench
- https://github.com/max-taylor/cc-compression-bench/blob/main/docs/caveman-findings.md
- https://news.ycombinator.com/item?id=47954745
- https://old.reddit.com/r/ClaudeAI/comments/1sytl0c/i_benchmarked_caveman_against_the_prompt_be_brief/
- https://adamsohn.com/lambda-variance/
- https://github.com/adam-s/testing-claude-agent
- https://arxiv.org/html/2502.18600v1
- https://github.com/juliusbrussee/caveman
