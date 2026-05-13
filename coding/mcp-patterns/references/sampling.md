# Sampling

Load this file when considering server-initiated model calls.

## What sampling is

Sampling lets the server ask the client to perform a model call on its behalf.

This is an **optional** capability and host support varies.

## Use sampling when

- the server genuinely needs host-mediated model generation
- the host/client owns the model policy and should remain in control
- the workflow benefits from human-in-the-loop review or approval

## Do not depend on sampling for baseline functionality

A local server should remain useful without it unless the entire product is explicitly designed around sampling support.

## Capability gate

- verify the client declared sampling support before using it
- provide a non-sampling fallback when practical
- document clearly when a feature is sampling-only

## Practical concerns

- user approval and review may be involved
- cost and latency are client/host concerns, not just server concerns
- `includeContext` choices affect both result quality and privacy footprint

## Good uses

- optional summarization or drafting inside a server-managed workflow
- constrained follow-up generation where the host must still mediate the model call

## Bad uses

- making simple local CRUD/search servers unusable without sampling
- hiding expensive model calls behind apparently cheap operations
- assuming a specific desktop host implements the feature the way you want

## Debugging clue

If you see capability or params errors after sending sampling requests, inspect the initialize exchange first. Many “mystery” failures are really unsupported-capability failures.
