# PR request — Notebook task arguments without widgets

## Problem
In Jupyter, a notebook's task arguments came from input widgets (a `%run` helper and a `WIDGET_LIST`), with a `TASK_ARGS` list as a fallback. Widget values live only in the kernel: they are lost on restart, never saved in the notebook, and can't be set in a headless run.

## Solution
- **`TASK_ARGS_VALUES` dict**: in Jupyter, a notebook sets its arguments next to the declaration, for example `TASK_ARGS_VALUES = {"entity": "region", "scale_factor": "0.01"}`. Values are strings, as Airflow passes them; names left out take their defaults; an undeclared name, a non-string value or a missing required argument raises with the usage line.
- **Airflow unchanged**: arguments come only from the workflow's `args`; `TASK_ARGS_VALUES` is never read outside a kernel, and no `args` means the declared defaults.
- **Removed**: `notebooks/common/jupyter_input_widget_helper.py`, the widget handling in `cli.py`, and the widget cells of `generate_tpch.py`, `bronze_ingestion.py` and `silver_processing.py`, each of which now has a working `TASK_ARGS` example.
- README, AGENTS.md and tests updated.

## Verification
`scripts/code_quality.sh all` passes; pytest 105 passed, 2 skipped; the property test P4 checks that the dict and the command line agree. Not run here: a real Jupyter kernel (check in JupyterHub).

## Deployment
Merge to `uat`, check a `tpch_medallion` UAT run, then to `main`. No platform change; `ipywidgets` stays available in the platform.

## Risks
Notebooks outside this repository that use `WIDGET_LIST` or a `TASK_ARGS` list must switch to the dict.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
