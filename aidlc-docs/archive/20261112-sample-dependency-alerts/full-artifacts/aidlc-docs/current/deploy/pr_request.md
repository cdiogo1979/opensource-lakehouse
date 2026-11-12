# PR request — Security alerts: what they cover and how to act

## Problem
Dependabot alerts are on, but the repository didn't say what they cover (only its extras and test tools), where alerts for the packages the code runs on appear (the platform), or how to fix one without overriding the platform's lock.

## Solution
- README: a "Security alerts" section: coverage of `requirements.txt` and `requirements-dev.txt` (unpinned test tools noted), what the platform repository covers, fixing through a normal pull request checked against the platform lock, dismissing with a reason; alerts only, no update PRs.
- AGENTS.md: rules for dependency fixes (normal change; never pin or override a platform package here; dismiss only with a reason).

## Verification
pytest 110 passed, 2 skipped; code quality PASS.

## Deployment
None (documentation).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
