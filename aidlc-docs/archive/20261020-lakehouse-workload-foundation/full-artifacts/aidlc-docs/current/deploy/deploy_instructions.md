# Deployment and Validation Instructions

These ordered steps are a handoff only. No repository push, PR creation, Airflow config change, DAG trigger, or environment deployment has been performed.

## 1. Review the code and verification limitations

- **Target**: proposed PR and CI checks.
- **Prerequisites**: review the complete solution in `pr_request.md`. Confirm whether the accepted Flake8/Bandit findings can remain or should be resolved before release.
- **Execution**: run `scripts/code_quality.sh all` and the Jenkinsfile compile/test stages from the repository root.
- **Validation**: latest results are Ruff/Black pass, two Flake8 E203 warnings, 67 low-severity Bandit findings, compile pass, and 48 tests pass. The warning/security results remain reported as findings, not passes.
- **Failure handling**: stop promotion if new findings appear or the reviewer rejects the documented waiver.

## 2. Review and merge the repository change

- **Target**: approved Git branch/ref(s).
- **Prerequisites**: review all local changes and confirm branch policy. The current working tree is based on `main` at `97f02ef` and has not been committed or pushed.
- **Execution**: create and merge a PR through the repository's normal Git hosting process. Include the environment YAMLs, generic loader/CLI, Spark job, DAG helpers and ignore rules, bundle client/config examples, Jenkins CI, tests, quality configuration, and guidance.
- **Validation**: confirm the merged commit contains all intended paths and CI results. No Git hosting credentials or branch protections were supplied to this handoff.
- **Failure handling**: do not continue if a required component or config is missing from the merged revision. Revert through the normal reviewed Git process; do not edit Airflow's bundle cache manually.

## 3. Configure Airflow Git DAG Bundles and the operator client

- **Target**: the Airflow 3 deployment's `[dag_processor] dag_bundle_config_list` and trusted operator host.
- **Prerequisites**: compatible Git and Docker providers, repository URL, Airflow Git connection/secrets backend, refresh interval, a trusted apply/reload command, and permissions for an operator to update the bundle config. Keep credentials outside repository files.
- **Execution**:
  1. Use `airflow_bundle_config.example.json` as the secret-free shape for `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod`. Set the dev ref to the selected feature ref, UAT to `uat`, and production to `main`; preserve repository-root bundle checkout so each ref includes `dags/`, `configs/`, and `notebooks/`.
  2. Apply this config through the deployment's supported mechanism (environment variables, Airflow config, Compose, Helm, or other platform manager) and perform the documented processor reload/restart if required.
  3. Copy `airflow_bundle_client.example.yml` to a deployment-owned path. Set the writable bundle config path, allowed feature-branch prefixes, and a trusted argv-style apply/reload command containing `{config_path}`.
  4. From the trusted operator host, inspect and, when authorized, select a feature branch:

     ```sh
     python3 airflow_bundle_client.py --settings /path/to/client.yml show
     python3 airflow_bundle_client.py --settings /path/to/client.yml select --branch feature/<approved-branch>
     ```

- **Validation**: confirm the client changes only `lakehouse-dev.tracking_ref`; UAT and production remain fixed. A successful apply command does not prove that Airflow has fetched or parsed the selected branch.
- **Failure handling**: stop if the deployment apply/reload fails or UAT/production refs change. The client restores the prior config on apply failure; investigate the platform apply operation before retrying.

## 4. Wait for bundle refresh and validate DAG parsing

- **Target**: Airflow DAG processor for each configured bundle.
- **Prerequisites**: the merged commit and bundle config are reachable; the refresh interval has elapsed.
- **Execution**: from the Airflow Compose project, list each bundle and inspect import errors:

  ```sh
  docker compose exec airflow-dag-processor airflow dags list -B lakehouse-dev -o plain
  docker compose exec airflow-dag-processor airflow dags list -B lakehouse-uat -o plain
  docker compose exec airflow-dag-processor airflow dags list -B lakehouse-prod -o plain
  docker compose exec airflow-dag-processor airflow dags list-import-errors
  ```

  The currently observed local deployment instead has a `lakehouse-main` bundle. If it remains configured, also run `airflow dags list -B lakehouse-main -o plain`; this name maps to the `main` prefix and `prod.yml`.

- **Validation**: expect `dev-init_environment`, `uat-init_environment`, and `main-init_environment` for the three example bundle names. Confirm they load from the intended commit, shared helpers are excluded from DAG discovery, and the import-error list is clean. Each run must resolve DAG, config, helpers, and workload from that same versioned commit.
- **Failure handling**: do not trigger any DAG if bundle versions are stale, the DAG IDs/config mapping is wrong, or import errors remain. The previously observed live bundle reported a direct helper import error; verify that `.airflowignore` has reached the fetched commit.

## 5. Confirm environment data targets

- **Target**: `configs/dev.yml`, `configs/uat.yml`, and `configs/prod.yml` as selected by each bundle name.
- **Prerequisites**: each environment owner confirms the storage path, database/catalog name, and authorized runtime identity. The current `prod.yml` documents a local RustFS/Nessie Compose target; do not assume it is production infrastructure.
- **Execution**: inspect each config in the merged commit and compare it with approved environment values. Do not put secret values in YAML. Confirm Spark S3A support, region, Nessie connectivity, bucket access, Docker mount access, image, master, and network settings.
- **Validation**: `lakehouse-dev` uses `dev.yml`; `lakehouse-uat` uses `uat.yml`; `lakehouse-prod` and the observed `lakehouse-main` use `prod.yml`. Confirm dev/UAT/prod targets are isolated and authorized.
- **Failure handling**: do not trigger a DAG if an environment target is a placeholder, local-only value, or otherwise unapproved. Resolve config through the reviewed Git process.

## 6. Manually test the initializer

- **Target**: start with `dev-init_environment` from the approved selected feature branch and the `dev.yml` target. Run UAT or production only after their owners separately authorize those targets.
- **Prerequisites**: steps 1–5 pass for the chosen environment. The configured Docker daemon can bind-mount the bundle-version checkout, and the Spark job image has the required Spark and S3 support.
- **Execution**: manually trigger the environment's `init_environment` DAG in the Airflow UI. The DAG first validates config, then runs `spark-submit` through `DockerOperator`.
- **Validation**: confirm the task uses the same bundle version as the DAG, creates the configured namespace if absent, and writes the two-row synthetic `sample_spark_job_output` table at the configured child path. Check Airflow/Spark logs and catalog/storage state.
- **Failure handling**: stop on config, mount, catalog, or storage errors. No automatic data rollback is designed. Only the dedicated smoke table is overwritten on retry; preserve logs and involve the data owner before manual recovery.

## Unverified scope and waiver

The user accepted a verification waiver for AI-DLC continuation. It is recorded as `VERIFICATION_WAIVED`, not passed. The `.airflowignore` fix has not been confirmed in live Airflow; Spark/Nessie/object-storage integration was not run; two Flake8 warnings and 67 low-severity Bandit findings remain. This waiver permits preparation of the handoff, but it does not prove runtime behavior or authorize a release.
