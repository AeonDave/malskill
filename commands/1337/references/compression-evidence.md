# Compression evidence for 1337

Use this when changing 1337's compression policy or evaluating claims that a prompt/skill saves tokens.

## Evidence snapshot

- Max Taylor's 2026 `cc-compression-bench` compared baseline, `Be brief.`, Caveman lite/full/ultra over 24 dev prompts, judged by rubric. `Be brief.` matched baseline quality and Caveman token range: baseline 636 mean tokens / 0.985 score, brief 419 / 0.985, lite 401 / 0.976, full 404 / 0.975, ultra 449 / 0.970.
- All arms hit 100% key points and zero `must_avoid` traps. Raw compression did not prove a Caveman correctness win, and `be brief.` tied or led on both axes.
- Caveman's remaining differentiators were structure, intensity switching, persistence (SessionStart/UserPromptSubmit hooks), and the Auto-Clarity safety escape — not the compression itself.
- Failure modes: lite dropped a required term once; ultra inflated and distorted setup/security answers when the safety escape/tool-first behavior triggered. Ultra was the longest of the three Caveman arms on average.
- arXiv 2604.00025 ("Brevity Constraints Reverse Performance Hierarchies"): brevity lifts large models +26.3pp by cutting overelaboration, but a strict direct-answer format causes accuracy decline in BOTH model sizes — "some reasoning is beneficial." Max compression of reasoning is a documented harm, not a free win.
- Multi-turn degradation (ICLR 2026, ~39% accuracy loss): answer-bloat, lost-in-middle, and premature-answer failure modes. Terse output becomes next-turn context; over-compressing decision-relevant reasoning in history hurts long, multi-step (kill-chain) work.
- Token reality (Pillitteri field test): the headline 75% is marketing. Prose is ~25% of a session; net session savings land around 4-10%. Prose compression is the weakest token lever.
- Tool-output/context compression is the dominant token lever (RTK, context-mode, repomix, codegraph, lean-ctx, etc.). Optimize tokens-per-task, not tokens-per-message; naive per-request compression can raise total cost via re-fetch and lost context.
- HN/Reddit discussion highlighted input-token overhead, single-run variance, cargo-culting ("prompt homeopathy"), and the reasoning-gap critique that dropping laid-out reasoning from history degrades successive turns.
- Adam Sohn's repeated same-prompt lambda benchmark showed large run-to-run variance (8k-17k tokens) even when every output passed; the bench is single-run per arm-prompt, so small deltas are noise.
- `adam-s/testing-claude-agent` found tests and stable first approaches dominate token-to-green more than long instruction files.
- Chain-of-Draft supports compact intermediate drafts, but only if essential state is preserved.

## 1337 design rules

- Optimize token-to-green, not shortest message.
- Compression is not the value proposition. Treat `be brief` as enough for simple shortening; 1337 earns its place via operator identity, stable shape, forced reasoning, routing, evidence discipline, verification, persistence, and the safety escape.
- Defer token-saving to the tool-output/context layer; do not chase prose tokens at the cost of state.
- Preserve exact terms, commands, errors, paths, hashes, IOCs, CVEs, and user-required wording before any trimming.
- Trim format, not decision-relevant reasoning. Keep the decisive "why" in visible output or the kill-chain ledger (direct-answer harm + multi-turn context starvation).
- Single fixed mode, no intensity levels. Levels added complexity without a measured win, and the strictest setting empirically distorted security-sensitive answers — 1337's core domain. One consistent operator shape; exactness/safety overrides terseness on risky spans.
- The structured edge is forced hypothesis-before-action, evidence-gated claims, a living ledger, ranked next-move selection, and anti-fabrication — these counter the documented LLM failure modes (premature commitment, answer-bloat, lost-in-middle, thrash).
- Terseness must not cause tool-first overreach, skipped verification, missing warnings, or lost multi-turn state.
- Keep the skill lean; each rule has recurring input-token cost.

## Sources

- https://www.maxtaylor.me/articles/i-benchmarked-caveman-against-two-words
- https://github.com/max-taylor/cc-compression-bench
- https://github.com/max-taylor/cc-compression-bench/blob/main/docs/caveman-findings.md
- https://news.ycombinator.com/item?id=47954745
- https://old.reddit.com/r/ClaudeAI/comments/1sytl0c/i_benchmarked_caveman_against_the_prompt_be_brief/
- https://www.reddit.com/r/ClaudeCode/comments/1t8461y/which_token_optimizer_would_you_recommend/
- https://arxiv.org/abs/2604.00025
- https://arxiv.org/html/2604.00025v1
- https://beam.ai/agentic-insights/iclr-2026-llms-lose-accuracy-in-multi-turn-conversations
- https://www.zenml.io/llmops-database/evaluating-context-compression-strategies-for-long-running-ai-agent-sessions
- https://pasqualepillitteri.it/en/news/846/claude-code-caveman-mode-token-saving
- https://medium.com/@shahsoumil519/graphify-vs-caveman-two-clever-tools-that-make-your-ai-coding-assistant-way-smarter-c6cd91378c59
- https://adamsohn.com/lambda-variance/
- https://github.com/adam-s/testing-claude-agent
- https://arxiv.org/html/2502.18600v1
- https://github.com/juliusbrussee/caveman
