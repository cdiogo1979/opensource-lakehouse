# Jenkins and Airflow Bundle Deployment Functional Design

## Airflow Git Bundles

One Airflow 3 deployment is designed to use three Git DAG Bundles: `lakehouse-dev` tracks a selected feature branch, `lakehouse-uat` tracks `uat`, and `lakehouse-prod` tracks `main`. Each bundle checks out the repository root and uses the same `dags/`, `configs/`, and `notebooks/` paths. DAG runs retain bundle version identity so the DAG and Spark dependencies come from the same Git commit.

The stable bundle name selects environment config and DAG prefix: `lakehouse-main`/`lakehouse-prod` → `prod.yml` and `main-`; `lakehouse-uat` → `uat.yml` and `uat-`; other bundle names → `dev.yml` and `dev-`. The current local Airflow instance was observed using `lakehouse-main`, while the example three-bundle configuration uses `lakehouse-prod` for the `main` ref. This platform difference must be checked when applying deployment configuration.

## Development branch client

`airflow_bundle_client.py` reads a deployment-owned YAML settings file and an Airflow bundle JSON config. It validates Git ref syntax, rejects protected refs, enforces configured feature prefixes, changes only `lakehouse-dev.tracking_ref`, writes atomically, and invokes a trusted argument-vector apply/reload command. If apply fails, it restores the old config and reapplies it. A successful apply does not prove Airflow has fetched or parsed the branch.

Git credentials remain in Airflow connections/secrets backends. The operator client is not a public DAG and is not automatically run by Jenkins. Selected branch code runs with Airflow/Spark privileges, so branch selection is limited to trusted operators.

## Jenkins responsibility

The Jenkinsfile compiles the Python client, DAGs, and workloads, then runs pytest. Jenkins is a CI gate only; it does not copy/upload files, mutate bundle refs, or manage Airflow Git credentials. Airflow polls configured refs, parses bundle commits, and records the version used by each DAG run.

## Deployment prerequisites and unverified behavior

The Airflow deployment owner must supply the Git URL/connection, provider-compatible Airflow 3 version, bundle config and refresh interval, supported apply/reload command, Docker daemon mapping, Spark image/master/network, catalog target, S3 authorization, and operator permissions. Live validation of the `.airflowignore` fix and selected bundle-version path is pending. See the archived Deploy handoff for the exact accepted limitations and ordered validation steps.
