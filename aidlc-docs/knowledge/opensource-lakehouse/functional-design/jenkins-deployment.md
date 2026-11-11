# Functional Design — CI and Deployment (Jenkins and Airflow bundles)

How changes are checked and reach Airflow. Architecture: [`../application-design.md`](../application-design.md). Replaces the retired design (three `lakehouse-*` bundles, the bundle client).

## Airflow bundles (platform-owned)
- Each data product with a `repo` gets two Git bundles: `<product>-main` tracks the prod branch (`main`) and `<product>-uat` tracks `uat` (refresh every 300 s, sparse `dags`, `workflows`, `notebooks`, `configs`, root files included). DAG IDs are `<bundle>-<name>`; `dev` has no bundle (Jupyter only).
- A change reaches UAT by merging or pushing to `uat`, and production by merging into `main`. A DAG appears within about five minutes after the push.

## Jenkins (platform-owned jobs, this repository's `Jenkinsfile`)
- `<product>_ci` builds the prod and UAT branches; `<product>_cd` builds branches with an open pull request.
- Stages: install `requirements-dev.txt` and the repository's `requirements.txt` constrained by the platform lock; `compileall` of `dags` and `notebooks`; `lakehouse-validate-workflows .` (workflow JSON v1, the `dags/` stub, the `requirements.txt` rules); `scripts/code_quality.sh lint`, `flake8`, `bandit` in parallel; `pytest -q`.
- Jenkins is a CI gate only: it publishes nothing and never changes branches or bundles.

## Local checks
`.venv/bin/python -m compileall -q dags notebooks`, `PATH=".venv/bin:$PATH" scripts/code_quality.sh all`, `.venv/bin/python -m pytest -q`; the validator with a platform checkout: `PYTHONPATH=<platform>/infra/airflow python3 -m lakehouse_dags.validate .`. A `.venv` created before the repository rename keeps scripts pointing at the old path: recreate it.

## Verification
2026-11-11: `default_cd` on the `tpch-medallion` pull request SUCCESS; UAT `default-uat-tpch_medallion` 21/21.
