# Encoders and Stagers

## 1) Stager selection

### Single-stage

Use when:
- payload is small enough for transport constraints
- environment is stable
- minimal moving parts are preferred

Trade-off: less flexibility once delivered.

### Two-stage

Use when:
- initial vector has strict size limits
- second-stage can be streamed/retrieved reliably
- architecture-specific bodies are needed from one bootstrap

Trade-off: transport reliability and partial-read handling become critical.

---

## 2) Encoder strategy

Use encoders to satisfy concrete constraints:

- bad-byte avoidance
- transport-safe character set
- simple static transformations for delivery channels

Do not add encoding by default. Every decoder stub increases complexity, size, and debugging cost.

### Practical rule

Pick the smallest decoder that satisfies the transport constraint. Validate decoded bytes against original payload hash before execution in test harnesses.

---

## 3) Polymorphism/metamorphism

Polymorphic/metamorphic approaches can evade simple signatures but often create unstable payload behavior if over-engineered.

Guidelines:
- keep mutation deterministic per build profile
- preserve strict regression tests for entry/decoder behavior
- avoid runtime self-rewrite patterns you cannot emulate/debug repeatedly

Reference baseline: MITRE ATT&CK T1027.014 frames polymorphic code as a stealth technique with strong behavioral detection implications.

---

## 4) Common failure modes

- Decoder clobbers registers needed by next stage
- Incorrect stage length handling (short read / overread)
- Misaligned jump into decoded body
- Memory permissions not updated before transfer-of-control
- Encoding expands payload beyond delivery limits

---

## 5) Validation matrix

For each encoded/staged variant, run:

1. static byte checks (badchars/size)
2. decode equivalence check (decoded bytes == expected)
3. emulator run for control-flow and memory writes
4. runtime test on target OS/arch

Only promote variants that pass all four gates.
