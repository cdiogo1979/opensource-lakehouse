# Intent Summary: Notebook Task Arguments Without Widgets

## Intent
Notebook Task Arguments Without Widgets (`20261111-notebook-task-args`)

## Objective
Remove the Jupyter input widgets for task arguments while keeping a way to set a notebook's parameters in Jupyter.

## Date
2026-11-11

## Scope
Included: notebooks/common/cli.py, removal of jupyter_input_widget_helper.py, the three notebooks with task arguments, their tests, README, AGENTS.md, canonical knowledge. Excluded: the platform's ipywidgets (stays), Airflow workflow params (platform follow-up), commit and push (not requested).

## Units / workstreams
notebook-task-args

## Major requirements
- FR-1/FR-2: in Jupyter, task arguments come only from a TASK_ARGS_VALUES dict of string values; undeclared names, non-strings and non-dicts are errors with the usage line.
- FR-3: Airflow unchanged; it never reads TASK_ARGS_VALUES and falls back to the declared defaults.
- FR-4/FR-5: widget helper and cells removed; notebooks carry a working example; docs and knowledge updated.
- CR-1: TASK_ARGUMENTS renamed TASK_ARGS_DEFINITION and TASK_ARGS renamed TASK_ARGS_VALUES, each commented in the notebooks.

## Architecture and design decisions
- One Jupyter source (the dict) instead of widgets plus a list fallback.
- String values only, matching what Airflow passes, so both paths parse identically (P4).

## Implementation decisions
- cli._notebook_values validates the dict; task_args() returns [] in a kernel.
- Each notebook test checks that its committed TASK_ARGS_VALUES example passes the notebook's own checks.

## Deviations
- Requirements and plan approved together; code generation and build and test presented together.

## Verification
construction/build-and-test/build-and-test-summary.md: scripts/code_quality.sh all PASS; pytest 105 passed, 2 skipped; P4 (dict vs command line) passes; the Airflow path never reads TASK_ARGS_VALUES. Not run: a real Jupyter kernel (IPython not installed locally); to check in JupyterHub after the branch is pushed.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md
- aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/knowledge/tpch/application-design.md

## Superseded decisions
- Jupyter input widgets (WIDGET_LIST, jupyter_input_widget_helper.py, LAKEHOUSE_WIDGETS) and the TASK_ARGS list form, superseded by the TASK_ARGS_VALUES dict.

## Archived artifacts
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/notebooks/common/cli.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/notebooks/workload/sample/other/generate_tpch.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/notebooks/workload/tpch/bronze/bronze_ingestion.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/notebooks/workload/tpch/silver/silver_processing.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/tests/workload_foundation/test_task_arguments.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/tests/workload_foundation/test_jupyter_scripts.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/tests/workload_foundation/test_generate_tpch.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/tests/tpch/test_bronze_ingestion.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/tests/tpch/test_silver_processing.py
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/README.md
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/AGENTS.md
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/aidlc-docs/knowledge/tpch/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-notebook-task-args/full-artifacts/`
