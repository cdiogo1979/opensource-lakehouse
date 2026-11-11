# Requirements — Notebook Task Arguments Without Widgets

Depth: minimal (clear request, small change in one component).

## Request
"the idea would be to remove the widgets , but still have a way to set parameters in the notebooks for jupyter"

## Answers
- Q1 cell format: **a `TASK_ARGS` dict** (`{"entity": "orders"}`).
- Q2 committed value: **a working example**, so run-all works in Jupyter.
- Q3 branch: **a new branch from main** (`tpch-medallion` is merged into `origin/main`): `notebook-task-args`.

## Functional requirements
- **FR-1** In Jupyter, a notebook's task arguments come from a `TASK_ARGS` dict in the notebook: argument name to value, for example `{"entity": "orders", "scale_factor": "0.01"}`. It is the only Jupyter source; the list form and widgets are removed.
- **FR-2** Values are strings, as Airflow passes them; a non-string value, a name that is not declared, or a non-dict `TASK_ARGS` is an error that names the problem and shows the usage line. A missing required argument is reported as today. Declared defaults apply to names left out.
- **FR-3** Airflow is unchanged: arguments come only from the command line after `--`; `TASK_ARGS` is never read outside a kernel, and no arguments means the declared defaults.
- **FR-4** Remove `notebooks/common/jupyter_input_widget_helper.py`, the widget branch and `LAKEHOUSE_WIDGETS` handling in `notebooks/common/cli.py`, and the `WIDGET_LIST` and `%run` widget cells in `generate_tpch.py`, `bronze_ingestion.py` and `silver_processing.py`; each gets a `TASK_ARGS` dict with a working example after `TASK_ARGUMENTS`.
- **FR-5** README, AGENTS.md (notebook standard) and the canonical knowledge describe the `TASK_ARGS` dict instead of widgets.

## Non-functional
- **NFR-1** `scripts/code_quality.sh` and pytest pass; the property test P4 checks that the dict in Jupyter and the command line give the same arguments.
- **NFR-2** No platform change: `ipywidgets` stays available in the platform as a general capability.

## Extensions
Security Baseline: no (no security surface change). Property-Based Testing: yes (P4 updated). Resiliency: no.

## Change requests
- **CR-1** (user): rename `TASK_ARGUMENTS` to `TASK_ARGS_DEFINITION` and `TASK_ARGS` to `TASK_ARGS_VALUES`, with comments in the notebooks describing each: the definition (used in Airflow and Jupyter) and the Jupyter-only values.
