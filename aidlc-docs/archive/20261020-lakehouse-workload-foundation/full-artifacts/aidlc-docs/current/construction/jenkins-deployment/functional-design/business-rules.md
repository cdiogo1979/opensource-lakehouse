# Business and Validation Rules: `jenkins-deployment`

## Branch and Bundle Rules

1. The shared Airflow deployment has three uniquely named GitDagBundles: `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod`.
2. The development bundle tracks an operator-selected feature branch. UAT always tracks `uat`; production always tracks `main`.
3. The client may modify only `lakehouse-dev.tracking_ref`. It rejects protected refs (`dev`, `uat`, `main`), malformed branch names, and refs outside the approved feature-branch policy.
4. Each selected ref contains one `dags/` folder plus `configs/` and `notebooks/`. The DAG source in the feature branch, `uat`, and `main` declares `dev`, `uat`, and `prod` identities respectively; DAG IDs and Spark job names remain unique.
5. The client applies the bundle configuration through the target deployment's supported mechanism and requests the required DAG processor reload/restart. It reports success only after the configuration apply operation succeeds; bundle parse readiness is a separate Airflow outcome.
6. Jenkins gates UAT and production changes but does not transfer artifacts or manage Airflow Git credentials.

## Bundle, Version, and Secret Rules

1. Airflow Git credentials are referenced through an Airflow connection or approved secrets backend. Bundle configuration may contain the selected ref but not credential values.
2. DAG bundle versioning remains enabled. Each DAG run uses the Git commit recorded for that run; do not inject a deployment release marker into DAG source.
3. DAG code and its Spark application/config must come from the same bundle version. The implementation verifies task-runner access to the versioned checkout and Spark submission file visibility.
4. The branch-selection client is an operator tool, not a public DAG parameter or automatic Jenkins deployment. Restrict access to trusted operators because selecting a ref changes code executed by Airflow.
5. The client must log old/new dev refs and apply outcome without secrets. Preserve the previous selected ref if configuration update or restart fails; never alter UAT or production settings.
6. A branch update becomes available after Airflow reloads the configured ref, fetches it, and successfully parses its DAGs. No immediate readiness guarantee is made.
