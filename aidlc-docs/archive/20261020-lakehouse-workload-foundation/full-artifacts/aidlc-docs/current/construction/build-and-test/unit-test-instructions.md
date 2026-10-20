# Unit Test Instructions

Run the test suite from the repository root:

```sh
python3 -m pytest -q
```

`requirements-dev.txt` supplies pytest, Hypothesis, and PyYAML. The suite covers generic YAML loading and validation, bundle client configuration and ref selection, DAG identity and defaults, workload initialization and smoke-write scope, and Hypothesis properties for generated environment settings and repeated initialization.

The initialization property uses a constrained configuration generator and a small in-memory catalog/table model. Hypothesis seed and shrinking behavior are retained for reproducibility. Example tests complement the property checks for explicit error and boundary cases. The repository does not configure a coverage threshold.

Latest result: **48 passed**.
