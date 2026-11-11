# Build and Test Summary — Notebook Task Arguments Without Widgets

| Check | Result |
|---|---|
| `scripts/code_quality.sh all` (Ruff, Black, Flake8, Bandit) | PASS |
| `python3 -m pytest -q` | 105 passed, 2 skipped (DuckDB not installed locally) |
| P4 (Hypothesis): the `TASK_ARGS_VALUES` dict and the command line give the same arguments | PASS |
| Airflow path: command-line args used; no args gives the declared defaults; `TASK_ARGS` never read | PASS (test) |

Not run here: a real Jupyter kernel (IPython is not installed locally; the tests simulate the kernel namespace). User check: in JupyterHub, run `generate_tpch.py` with its committed `TASK_ARGS_VALUES`, then change `entity` and rerun.
