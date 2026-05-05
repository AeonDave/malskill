---
name: openssl
description: "OpenSSL CLI for encryption, decryption, digesting, certificate inspection, and key handling. Use when working with PEM/DER material, password-based symmetric crypto, TLS certificates, RSA key sanity checks, or quick cryptographic transformations from the shell."
compatibility: "Linux, macOS, Windows; OpenSSL CLI installed"
metadata:
  author: AeonDave
  version: "1.0"
---

# OpenSSL

Swiss Army knife for practical crypto plumbing. Also a terrific way to learn that syntax is a form of weather.

## When to use OpenSSL

Use OpenSSL when you need to:

- encrypt or decrypt data with a known algorithm and secret
- hash or HMAC files quickly from the terminal
- inspect X.509 certificates or PEM/DER material
- check private-key structure or convert key formats

## Quick Start

```bash
# SHA-256 digest
openssl dgst -sha256 file.bin

# Inspect a certificate
openssl x509 -in cert.pem -text -noout

# Check an RSA private key
openssl rsa -in key.pem -check
```

## High-Value Workflows

### Symmetric decryption

```bash
openssl enc -aes-256-cbc -d -in cipher.bin -out plain.txt -pbkdf2 -pass pass:secret
openssl enc -aes-128-cbc -in plain.txt -out cipher.bin -pbkdf2 -pass pass:secret
```

### Certificates and key material

```bash
openssl x509 -in cert.pem -text -noout
openssl pkey -in key.pem -text -noout
openssl rsa -pubin -in pub.pem -text -noout
```

### Format conversion

```bash
openssl x509 -in cert.pem -outform der -out cert.der
openssl x509 -inform der -in cert.der -out cert.pem
```

## Practical Notes

- Prefer explicit algorithms and modern flags like `-pbkdf2` instead of trusting old defaults.
- `dgst`, `enc`, `x509`, `pkey`, and `rsa` cover most day-to-day shell work.
- Pair with `cyberchef`, `sagemath`, or application-specific tooling when the task moves beyond basic transforms.

## Caveats

- OpenSSL syntax varies across versions and legacy tutorials age badly.
- Bad assumptions about IVs, salts, padding, or input format break otherwise correct commands.
- The CLI can mutate key material or output formats in ways that are easy to miss; keep originals.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use `openssl help` and the version-matched man pages for command-specific flags.
