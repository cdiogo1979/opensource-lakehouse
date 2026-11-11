# Code Generation Plan — Notebook Task Arguments Without Widgets

- [x] 1. Branch `notebook-task-args` from `origin/main`.
- [x] 2. `notebooks/common/cli.py`: `parse_task_args` reads only the notebook's `TASK_ARGS_VALUES` dict in Jupyter (`_notebook_values`: dict required, declared names only, string values); `task_args()` returns `[]` in a kernel; `WIDGETS_VARIABLE` and `_widget_values` removed; the command-line path is unchanged (FR-1 to FR-3).
- [x] 3. `notebooks/common/jupyter_input_widget_helper.py` deleted; `generate_tpch.py`, `bronze_ingestion.py`, `silver_processing.py`: `WIDGET_LIST` and the widget `%run` cell replaced by a `TASK_ARGS_VALUES` dict with a working example (`region`); title, Task arguments and Execution texts updated (FR-4).
- [x] 4. Tests: `test_task_arguments.py` (dict only, never the kernel argv, Airflow never reads TASK_ARGS, error lines, P4 over dict and command line); `test_jupyter_scripts.py` (widget-helper tests removed; no notebook uses widgets, every notebook with `TASK_ARGS_DEFINITION` sets a `TASK_ARGS_VALUES` dict); the three notebook tests check that each committed example parses and passes the notebook's own checks.
- [x] 5. README (layout, sources, Working in Jupyter, TPC-H, silver lookback) and AGENTS.md (helpers, entry-point rule, Task arguments section) (FR-5).
- [x] 6. CR-1: `TASK_ARGUMENTS` renamed `TASK_ARGS_DEFINITION` and `TASK_ARGS` renamed `TASK_ARGS_VALUES` (parser variable, notebooks, tests, README, AGENTS.md), each with a comment in the notebooks saying what it is.
