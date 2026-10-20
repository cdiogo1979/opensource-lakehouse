# Build Instructions

## Prerequisites

- Python 3 supported by the repository dependencies.
- Install development and test dependencies with `python3 -m pip install -r requirements-dev.txt`.

## CI Build Validation

The Jenkinsfile runs these repository checks:

```sh
python3 -m compileall -q airflow_bundle_client.py dags notebooks
python3 -m pytest -q
```

These steps compile the client, Airflow DAG source/helpers, and Spark workload files, then run the unit and property-based test suite. The AI-DLC Build and Test workflow additionally requires:

```sh
scripts/code_quality.sh all
```

That script invokes Ruff, Black, Flake8, and Bandit. It reads tool settings from `pyproject.toml`. Ensure its target list matches directories present in this repository; see the summary for the latest run result. Airflow providers, Spark, catalog, and storage services are external runtime dependencies and are not built by this pipeline.

## Build and Test Result

On 2026-10-20, compile validation passed and pytest reported 48 passed in the `test_aidlc` Python environment. The required code-quality script ran but failed; details are in the Build and Test summary.
