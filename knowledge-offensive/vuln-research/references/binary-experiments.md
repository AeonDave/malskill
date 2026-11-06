# Binary and emulation experiments

Load when a vulnerability hypothesis depends on reconstructed code, a direct function harness, or an emulated environment.

## Connect the representations

Tie source, symbols, disassembly, decompiler output, and runtime traces to the same artifact/build. Record image identity and module-relative locations; distinguish file offsets, image addresses, and relocated runtime addresses. Do not carry an address or inferred type across builds without remapping it.

Use pseudocode to formulate a question. Where the conclusion depends on signedness, width, layout, calling convention, aliasing, or object lifetime, inspect the relevant instructions and runtime values. Recover only the callers, callees, and state needed for that decision; guessed names and prototypes remain annotations.

A local data-flow result does not establish an externally reachable path. Trace the caller boundary and check the analysis model: indirect calls, wrapper guards, sanitizer annotations, missing libraries, and intra- versus inter-procedural coverage. For example, [VulHunt's data-flow skill](https://github.com/vulhunt-re/skills/blob/52a1443464bd94ede2e265241f5af0f2722b47e1/plugins/vulhunt/skills/dataflow-analysis/SKILL.md) describes intra-procedural propagation; the researcher still has to establish caller context and validate annotations.

## Make the experiment representative

Write down the path and observation the harness is intended to reproduce. Preserve the relevant contract:

- Argument types, lengths and units, buffer ownership, object initialization, and lifetime.
- Architecture/ABI, loader state, libraries or system interfaces, and relevant privilege/execution mode.
- Files/configuration, protocol or session state, callbacks, concurrency, and external state when the path depends on them.
- Reset between attempts: memory, handles, queues, persistent state, random/time inputs, and any state the harness intentionally retains.

A direct call can reveal a local defect while bypassing checks that govern real callers. A stub or patch can make a path reachable that the original target never takes. Record these differences beside the result; establish the missing connection before attributing that result to the deployment.

For emulation, compare the relevant normal behavior with a native run, fuller model, device trace, or other reference when one exists; otherwise record fidelity as unverified. Check outputs and important state transitions, not just process survival. Identify what is modeled, stubbed, altered, or unknown. [FIRM-AFL, §§3–4, 5.1 and 6](https://www.usenix.org/system/files/sec19-zheng_0.pdf), illustrates fidelity checks and execution-model constraints; its support and performance results are not guarantees for another harness.

## Attribute the failure

1. Replay a normal input and the suspect input from known initial states. Verify target entry and the observation point for both.
2. Locate the first divergence: loader/emulator, wrapper or stub, intended target code, or later consumer. Save relevant values, input/state, and the faulting instruction if there is a fault.
3. Check whether instrumentation, an altered allocator, timing, or missing environment caused the effect. Remove or vary a suspected confounder when it can distinguish the explanations.
4. Reduce the case without silently removing the prerequisite. For races or stateful failures, retain the operation ordering and observed reproduction frequency.
5. Recheck in the most representative available context. If only a modified harness reproduces it, report that evidence level and the unresolved target condition.

Use a debugger, disassembler, tracer, emulator, or instrumenter that exposes the needed evidence. Do not require a particular product or build a full machine model when a narrower faithful experiment answers the question.
