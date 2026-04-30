# capa capability-driven triage

## Interpretation workflow

1. Review ATT&CK/MBC mapping.
2. Group capabilities by investigation impact:
   - immediate containment (persistence, lateral movement)
   - credential/data theft
   - C2 communications
3. Validate top findings with `-vv` evidence locations.

## Practical triage shortcuts

- High count in communication + persistence namespaces -> prioritize IR containment.
- Packed warning -> collect dynamic sandbox report and rerun capa.
- Use namespace clusters to define next RE tasks (config extraction, C2 recovery, etc.).

## Avoid these mistakes

- Treating one capability as definitive malware family proof.
- Ignoring environmental context (benign admin tools can match some behaviors).
- Skipping corroboration with memory/network/disk artifacts.

## Correlation targets

- Process tree/memory plugins (Volatility3).
- Network logs (Zeek/Wireshark).
- Disk artifacts and execution traces (Autopsy/TSK).
