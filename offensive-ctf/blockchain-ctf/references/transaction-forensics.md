# Transaction Forensics

Use this reference when a blockchain task is about tracing on-chain value flow rather than exploiting contract logic.

## Intake checklist

- Identify network or chain family: UTXO, account-based EVM, token transfer logs, or mixed artifacts.
- Collect transaction IDs, addresses, timestamps, amounts, token contract addresses, and any explorer/API constraints.
- Work read-only first: explorer API, RPC calls, exported CSV/JSON, local parsing, and graph reconstruction.
- Preserve raw responses so every hop can be replayed or independently checked.

## UTXO tracing workflow

1. Fetch transaction details and list all inputs and outputs.
2. Identify likely change output versus payment output:
   - change often returns to a new address controlled by the sender
   - round amounts are often payments or peel outputs
   - the larger output often continues a peel chain, but verify with timing and later spends
3. Follow spend links forward until the success oracle, terminal address, or suspicious fan-out appears.
4. Build a table per hop: txid, input value, output index, output value, address, time, and reason for choosing the next hop.
5. Validate by reproducing the final address, amount, embedded data, OP_RETURN, or explorer-visible state requested by the task.

## Account-chain tracing workflow

1. Fetch normal transactions, internal transactions, token transfers, and logs separately when the explorer exposes them as different endpoints.
2. Normalize values and decimals; token transfers may not match native currency balances.
3. Reconstruct graph edges: from, to, value, token, timestamp, method/function selector, and transaction hash.
4. Use heuristics cautiously:
   - amount correlation: input approximately equals output minus fees
   - timing correlation: related outputs appear shortly after inputs
   - fan-out/fan-in: mixers, splitters, or staged distribution
   - round values: often deposits, withdrawals, or peel amounts
   - high-volume entities: exchanges/faucets/noisy services can create false paths
5. Validate by tracing to a requested address, event, balance, note, memo, calldata field, or recovered secret.

## Data hidden in transactions

Check these fields before assuming exploit logic:

- UTXO scripts and OP_RETURN data
- EVM calldata, event logs, topics, revert strings, and contract creation bytecode
- token transfer metadata or memo-like fields on chains that support them
- repeated low-value transactions where amounts encode bytes
- timestamp intervals, output indexes, or address suffixes used as covert channels

## Common pitfalls

- Following the wrong UTXO output because a single peel-chain heuristic was treated as proof.
- Ignoring internal transactions on EVM chains.
- Mixing token decimals and native currency decimals.
- Treating an exchange, faucet, or high-volume service address as an attacker-controlled endpoint.
- Broadcasting transactions when the task only requires read-only tracing.
