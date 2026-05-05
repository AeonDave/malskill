---
name: gcloud-cli
description: "Google Cloud CLI for authenticating, configuring projects, and enumerating GCP resources from the terminal. Use when verifying active identity and project scope, listing compute or storage resources, or scripting repeatable GCP recon in authorized environments."
compatibility: "Linux, Windows, macOS; Google Cloud CLI installed"
metadata:
  author: AeonDave
  version: "1.0"
---

# gcloud CLI

Project-aware cloud enumeration for GCP from a shell instead of a tab maze.

## When to use gcloud CLI

Use gcloud when you need to:

- inspect the active account, project, and configuration quickly
- list compute, IAM, and storage resources in a target project
- script GCP recon or validation steps in a reproducible way

## Quick Start

```bash
# Check auth and config
gcloud auth list
gcloud config list

# Enumerate projects and compute instances
gcloud projects list
gcloud compute instances list --project my-project
```

## High-Value Workflows

### Project and identity sanity

```bash
gcloud auth list
gcloud config get-value project
gcloud projects list
```

### Common resource enumeration

```bash
gcloud compute instances list --project my-project
gcloud iam service-accounts list --project my-project
gcloud storage ls
```

### Structured output

```bash
gcloud compute instances list --project my-project --format=json
gcloud projects list --format="table(projectId,name,projectNumber)"
```

## Practical Notes

- Always know which project is active before trusting the output.
- Prefer `--project` in scripts, even if a default project is configured.
- `gcloud storage ls` is a useful first pass for bucket visibility in modern CLI workflows.

## Caveats

- Cross-project visibility depends heavily on the bound identity and active credentials.
- Some service coverage and examples moved over time; prefer current official docs over older blog syntax.
- Empty output often means wrong project or auth context, not absence of resources.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use Google's official gcloud documentation for install, auth flows, and service command groups.
