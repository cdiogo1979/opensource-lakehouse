# AI-DLC State Tracking

## Project Information
- **Project Type**: Brownfield
- **Start Date**: 2026-11-11T02:45:00Z
- **Current Stage**: DEPLOY - Deploy
- **Intent**: A `tpch` subproject with bronze and silver notebooks: bronze generates TPC-H data with the existing DuckDB generator and saves it to bronze tables; silver merges bronze changes into silver tables using bronze CDC. Check the naming conventions for tables and workflows; follow the standard notebook structure; update AGENTS.md as needed, including which Jupyter helpers notebooks use.
- **Intent ID**: 20261111-tpch-medallion
- **Previous Intent**: 20261020-lakehouse-workload-foundation (closed; its archive folder was removed in commit 8b322d2)

## Workspace State
- **Existing Code**: Yes
- **Programming Languages**: Python (Jupytext notebooks, pytest/Hypothesis)
- **Build System**: none; `scripts/code_quality.sh` and pytest; CI in `Jenkinsfile`
- **Workspace Root**: /Users/carlosdiogo/code_repo/opensource-lakehouse-sample-dp
- **Reverse Engineering Needed**: Yes — focused on the subproject layout, notebook standard, TPC-H generator, and platform table constraints.

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Focused Reverse Engineering — approved on 2026-11-11 (with the P2 model).
- [x] Requirements Analysis — approved on 2026-11-11 (with CR-1).
- [ ] User Stories — SKIP.
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Application Design — approved on 2026-11-11 (D3 names in notebooks, D8 temporary edit).
- [ ] Units Generation — SKIP (one unit, `tpch`).
- [x] Functional Design — approved on 2026-11-11.
- [ ] NFR Requirements, NFR Design, Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-11.
- [x] Build and Test — approved on 2026-11-11 (verification complete).
- [x] Deploy — handoff approved on 2026-11-11; closure approved.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q7: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q7: A) |
| Resiliency Baseline | No | Requirements Analysis (Q7: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- **Lifecycle Phase**: DEPLOY
- **Current Stage**: Deploy
- **Next Stage**: Intent closure
- **Status**: Closure approved; compaction in progress.

## Follow-ups
- Platform intent (opensource-lakehouse-infra): workflow JSON params inserted into task args at run time without templating, so a silver lookback can be set when triggering a run (user, 2026-11-11: "Temporary edit now, params later").

- Platform: a parallelism limit per workflow (for example `max_active_tasks`) and per-job Spark memory, so a DAG run's tasks can't exhaust the shared Spark container (found in Build and Test, 2026-11-11).

- Platform: StarRocks loses its runtime LDAP bind pattern when the FE restarts (seen 2026-11-11 after memory pressure); re-apply it automatically (for example from the FE healthcheck or a scheduled reconcile) instead of only at `lakehouse.sh start`.

- Platform: raise JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT above 2G (each notebook with a Spark session holds about 1 to 1.5 GiB until its kernel shuts down; two at once were OOM-killed on 2026-11-11).

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY - Deploy",
  "failure": "Manifest artifact does not exist: /Users/carlosdiogo/code_repo/opensource-lakehouse-sample-dp/aidlc-docs/knowledge/tpch/application-design.md",
  "intent_id": "20261111-tpch-medallion",
  "name": "TPC-H Medallion Subproject",
  "previous_intent": "20261020-lakehouse-workload-foundation",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->
