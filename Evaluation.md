Valutazione Skill — d:\Sources\malskill
Scala: 1-5. U=Utilità, Q=Qualità, C=Completezza.

https://github.com/mukul975/Anthropic-Cybersecurity-Skills
https://github.com/1ikeadragon/awesome-offsec-claude
https://github.com/SnailSploit/Claude-Red




🔴 PROGRAMMING (nucleo del progetto)
Skill	Righe	Refs	U	Q	C	Note
windows-internals	283 + 9 refs (~4500 tot)	9	5	5	5	Flagship. EPROCESS/tokens/evasion/callbacks tutto
bof/c-bof	503	5	5	5	5	DFR, heap, args — eccellente
bof/cpp-bof	534	4	5	5	5	RAII, DFR, IOCTL — eccellente
asm-offensive-patterns	488	8	5	4	4	Syscall stubs, shellcode, indirect syscalls. Manca ARM64 implant patterns
adaptixc2-dev	351	5	5	4	3	Molto Adaptix-specifico. Manca generic implant architecture
python-reverse	86	6	4	3	3	Bytecode/decompilation utile per RE scripting
asm-patterns	449	2	4	4	3	Buono ma pochi refs per uso security
asm-performance	365	3	3	4	3	SIMD/cache, più perf che sec
asm-testing	388	3	2	3	3	Niche. BOF testing già coperto altrove
rust-performance	84	4	3	3	3	Utile per implant perf in Rust
golang-performance	102	4	3	3	3	Tool dev backend
python-async-patterns	91	5	3	3	3	Utile C2 backend async
c-patterns	92	5	2	2	2	Generico, niente security-focus
cpp-patterns	86	5	2	2	2	Generico
rust-patterns	83	5	2	2	2	Generico
golang-patterns	87	7	2	2	2	Generico
python-patterns	76	7	2	2	2	Generico
code-guidelines	137	1	2	3	2	Troppo generico per sec context
*-testing (4 skill)	67–84	4–7	2	2	2	Framework generici, nessun security harness
arduino / sensors	106 / 71	4/3	1	2	2	Off-topic per offensive sec
🟡 KNOWLEDGE
Skill	Righe	Refs	U	Q	C	Note
malware-analysis	279	7	5	4	4	Workflow + safety solido. Manca dynamic-only path
deep-research-offensive	255	3	4	4	4	CVE + recon + OSINT workflow ben strutturato
skill-creator	268	2	4	4	4	Meta ma fondamentale per qualità repo
zero-day-hunter	129	3	4	3	3	Corto. Manca fuzzing-driven discovery path
cve-search	158	0	3	3	3	No refs. Funzionale
deep-research-generic	232	0	3	3	3	Broad, non specializzato
agent-md-creator	271	3	3	4	4	Infrastruttura Claude workflow
readme-md-creator	191	2	2	3	3	Bassa priorità
🟠 OFFENSIVE TOOLS — RE (categoria più forte)
Skill	Righe	U	Q	C	Note
ghidra	201	5	4	4	Scripting e decompiler ben coperti
windbg	251	5	4	4	KD + user mode, buona depth
x64dbg	193	5	4	4	Plugin coverage buona
frida	259	5	4	4	Intercept/hook/REPL — completo
radare2	233	4	4	4	r2pipe manca un po'
binaryninja	200	4	4	4	IL + plugin OK
gdb	234	4	4	4	pwndbg/peda workflow incluso
dnspy	182	3	4	4	.NET RE solido
binwalk	183	3	4	4	Firmware analysis
🔵 OFFENSIVE TOOLS — Windows/AD
Skill	Righe	U	Q	C	Note
crackmapexec	112	5	3	3	Buon coverage ma CME → netexec migration non citata
rubeus	102	5	3	3	Kerberos workflows OK
mimikatz	54	5	2	2	Troppo corto per strumento così complesso
bloodhound	59	5	2	2	Troppo corto. CE queries mancano
nanodump	100	4	4	4	Detection evasion notes ottimo
coercer	101	4	4	4	Protocolli e NTLM relay ben coperti
certify	47	4	2	2	ESC1-8 mancano, troppo corto
evil-winrm	91	3	3	3	OK
lazagne	90	3	3	3	Moduli coperti
kerbrute / psexec / altri	~80	3	3	3	Standard
🟢 ALTRI TOOL (breve)
Categoria	U media	Q media	C media	Problema principale
Recon (14 skill)	3	3	3	Troppo simili, tutte ~70-100 righe, nessun ref
Network (8 skill)	3	3	3	Ligolo-ng eccellente, resto standard
Cracking (4 skill)	3	3	3	Hashcat buono, altri corti
Web-app (8 skill)	3	2	2	Molto corti (42-67 righe), nessun ref
Vuln-scanners (5)	3	2	2	Nuclei OK, altri superficiali
Evasion (5)	4	3	3	Donut ottimo. Shellter/Veil obsoleti
Social eng. (5)	2	3	3	Bassa utilità per programmazione
OSINT (4)	2	2	2	Molto generici
Priv-esc (3)	3	2	2	Solo tool usage, no programming depth
Data-exfil (3)	2	2	2	Low depth
Cloud (6)	2	2	2	Pacu/Scout OK, resto generico
Wireless (3)	1	2	2	Off-topic per sec programming
SKILL MANCANTI — Priorità
P1 — Alta utilità, gap critico
Skill suggerita	Categoria	Motivo
programming/shellcode-dev	Programming	PIC shellcode, encoders, stager design, RDDI — base di tutto implant dev
programming/pe-manipulation	Programming	PE parsing, process hollowing, DLL injection, reflective loader — gap enorme
programming/linux-internals	Programming	Simmetria con windows-internals: ELF, procfs, namespaces, eBPF, LSM
programming/kernel-driver-dev	Programming	WDM/WDF, IOCTL design, filter driver, kernel debugging workflow
programming/implant-patterns	Programming	Generic implant architecture: sleep, comms loop, staging, config encryption
offensive-tools/c2/havoc	C2	Framework popolare, assente. Sliver etc. eliminati, C2 coverage = zero
programming/heap-exploitation	Programming	Windows heap LFH/VS, glibc tcache/safe-linking, use-after-free patterns
programming/rop-development	Programming	Gadget finding, chain building, ASLR/NX bypass — prerequisito exploit dev
P2 — Utile, mancante
Skill suggerita	Categoria	Motivo
programming/fuzzing	Programming	AFL++/LibFuzzer, harness writing, coverage-guided — per zero-day hunting
programming/network-implant-dev	Programming	Raw sockets, covert channels, DNS/HTTP/ICMP C2 protocol design
programming/edr-internals	Defensive	Come funziona un EDR, telemetria, detection logic — per bypass e difesa
programming/binary-diffing	RE/Programming	BinDiff/Diaphora per patch diffing — essenziale per N-day development
programming/c2-protocol-dev	Programming	Malleable C2, protocol design, encrypted comms, staging protocols
offensive-tools/exploits/metasploit	Tools	Stranamente assente — framework fondamentale
programming/yara-dev	Defensive	YARA rule writing, module API, performance tuning per malware hunting
P3 — Niche ma consistente con direzione del repo
Skill suggerita	Categoria	Motivo
programming/uefi-exploitation	Programming	UEFI bootkit dev, EDK2, DXE driver abuse
programming/wasm-patterns	Programming	WASM per payload delivery, runtime abuse in browser
programming/android-internals	Programming	ART runtime, Binder IPC, SELinux bypass — mobile red team
offensive-tools/containers/docker-escape	Tools	Container escape techniques — cgroups/namespaces/capabilities
programming/crypto-impl	Programming	Implementare crypto primitives correttamente, side-channel awareness
Priorità immediata: shellcode-dev + pe-manipulation + un C2 (havoc/sliver) per rimpiazzare le skill eliminate.