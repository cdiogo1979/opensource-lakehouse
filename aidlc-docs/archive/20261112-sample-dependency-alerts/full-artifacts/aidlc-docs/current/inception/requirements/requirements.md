# Requirements — Sample Dependency Alerts

Depth: minimal (documentation; no automation).

## Request
"make this as two intents, one for each repo" (Dependabot alerts turned on for both repositories).

## Answer
**Alerts only, plus triage notes**: no Dependabot update PRs.

## Findings
The dependency graph sees 10 packages: `requirements.txt` (the product's extras, e.g. duckdb) and `requirements-dev.txt` (test tools), and the GitHub Actions entry. The packages the code runs on (pandas, pyarrow, PySpark, ...) come from the platform's workload lock, so their alerts belong to the platform repository (intent 20261112-infra-vulnerability-coverage).

## Requirements
- **FR-1** README: a "Security alerts" section: what the alerts here cover (the extras and the test tools) and what they don't (the platform's packages, images and Spark: alerts in the platform repository); how to fix one (bump the pin in `requirements.txt` or `requirements-dev.txt` within the platform lock's constraints; CI checks `requirements.txt` against the lock; a fix needing a platform package goes to the platform as its own intent); how to dismiss (with a reason, e.g. test-only or not reachable).
- **FR-2** AGENTS.md: the rule that a dependency fix is a normal change (branch, PR, CI, `uat`, `main`), and that platform packages are never pinned or overridden here.
