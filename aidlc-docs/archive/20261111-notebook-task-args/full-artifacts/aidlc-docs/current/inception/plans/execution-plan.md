# Execution Plan — Notebook Task Arguments Without Widgets

| Stage | Decision | Reason |
|---|---|---|
| Reverse Engineering | Skip | Focused read done at workspace detection |
| User Stories, Application Design, Units | Skip | Within the existing workload-foundation component; one unit |
| Functional Design | Skip | Rules fully stated in FR-1 to FR-3 |
| NFR / Infrastructure Design | Skip | No NFR or infrastructure change |
| Code Generation | Execute | Parser, notebooks, helper removal, docs, tests |
| Build and Test | Execute | code_quality.sh, pytest, a Jupyter-style check of each notebook's arguments |
| Deploy | Execute | PR description; merging to `uat` and `main` stays with the owner |

## Steps
1. Branch `notebook-task-args` from `origin/main`.
2. `cli.py`: `task_args` and `parse_task_args` read the `TASK_ARGS` dict in Jupyter (FR-1, FR-2); remove `WIDGETS_VARIABLE` and `_widget_values`; command-line path unchanged (FR-3).
3. Delete `jupyter_input_widget_helper.py`; update the three notebooks (FR-4).
4. Tests: update `test_task_arguments.py` (P3 to P6, P4 over dict and command line), the three notebook tests, and remove the widget-helper tests in `test_jupyter_scripts.py`.
5. README, AGENTS.md (FR-5).

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md` | UPDATE | Task-argument sources in Jupyter |
| `aidlc-docs/knowledge/opensource-lakehouse/application-design.md` | UPDATE | Helper list and notebook standard |
| `aidlc-docs/knowledge/tpch/application-design.md` | UPDATE | Notebook argument cells |
