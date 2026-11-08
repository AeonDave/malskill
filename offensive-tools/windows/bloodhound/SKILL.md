---
name: bloodhound
description: "Auth/lab ref: Install BloodHound CE, import collector data, and analyze identity relationships and paths."
license: GPL-3.0
compatibility: "BloodHound Community Edition; compatible collectors and a Docker-compatible runtime for the standard installation."
metadata:
  author: AeonDave
  version: "3.1"
---

# BloodHound CE

## Install and import

Start the container runtime, download and unpack the platform-specific [BloodHound CLI release](https://github.com/SpecterOps/bloodhound-cli/releases), then run `./bloodhound-cli install` (Windows: `.\bloodhound-cli.exe install`). Save the generated admin password, sign in at `http://localhost:8080/ui/login`, and change the password when prompted. The [official quickstart](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart) covers prerequisites, updates and recovery.

Choose a collector compatible with the deployed CE version. For Active Directory, download SharpHound from the CE interface's **Download Collectors** and use the [SharpHound skill](../sharphound/SKILL.md). Upload the resulting ZIP or JSON through **Quick Upload** or **Administration → Data Collection → File Ingest**, and check ingestion status and errors before analysis. Use the official sample data to explore the interface without collecting an environment.

The third-party [BloodHound.py CE branch](https://github.com/dirkjanm/BloodHound.py/tree/bloodhound-ce) is an alternative collector with its own feature coverage. Install `bloodhound-ce` in an isolated environment, e.g. `pipx install bloodhound-ce`, and inspect `bloodhound-ce-python --help`. The legacy `bloodhound` package provides `bloodhound-python` and targets legacy BloodHound; avoid mixing their Python environments.

## Analyze and qualify

In **Explore**, search for a principal, inspect its memberships and privileges, and use Pathfinding or saved queries to examine relationships. Record the source and collection time, collector version, scope, failures and coverage with each finding. Validate significant relationships and current state against authoritative sources: collection permissions, unreachable hosts and incomplete methods can leave gaps; absence of an edge is not proof of absence.

Session edges are time-sensitive observations. Load [references/cypher-queries-and-api.md](references/cypher-queries-and-api.md) when checking edge direction or writing a small read-only Cypher query.
