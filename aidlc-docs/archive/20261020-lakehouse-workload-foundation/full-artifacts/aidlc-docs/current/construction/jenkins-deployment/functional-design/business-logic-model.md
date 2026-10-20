# Business Logic Model: `jenkins-deployment`

## Scope

This unit defines three Git DAG Bundles in one Airflow 3 deployment and includes an operator CLI that selects which feature branch feeds the dev bundle. Jenkins remains CI and branch gating for UAT/production; it does not upload artifacts.

## Bundle Mapping

| Bundle | Tracking ref | DAG directory |
|---|---|---|
| `lakehouse-dev` | Operator-selected, validated feature branch | `dags/` (`ENVIRONMENT="dev"`) |
| `lakehouse-uat` | Fixed `uat` | `dags/` (`ENVIRONMENT="uat"`) |
| `lakehouse-prod` | Fixed `main` | `dags/` (`ENVIRONMENT="prod"`) |

All bundles include `configs/` and `notebooks/` from the same repository checkout and keep the repository root as bundle root.

## Branch Selection Flow

1. Operator runs `airflow_bundle_client.py` with an explicit feature branch selection or requests the current dev ref.
2. The client validates the ref as a valid Git branch and rejects protected/reserved refs. It reads deployment configuration and changes only the `tracking_ref` of `lakehouse-dev`.
3. The client writes updated configuration atomically and invokes the configured deployment apply operation. The apply operation updates Airflow's bundle configuration and reloads/restarts the Dag processor as required by the hosting platform.
4. If apply fails, the client restores the prior configuration and reports failure. It never changes UAT or production refs.
5. Airflow fetches and parses the selected feature branch on refresh. New dev runs use the parsed branch commit; existing runs keep their recorded bundle version.

## Failure and Readiness Outcomes

- **Rejected**: Invalid, protected, or disallowed ref; no deployment configuration is changed.
- **Applied**: Configuration apply/reload succeeds and the client reports the selected ref. This does not claim the branch has parsed successfully.
- **Apply failed**: The prior selected ref is restored where possible; the client returns failure and reports a safe diagnostic.
- **Bundle not ready**: Airflow Git fetch/authentication/parse error remains visible in Airflow diagnostics; client apply success is not equivalent to DAG parse readiness.

## Testable Properties (PBT-01)

- **Invariant**: The selector changes only `lakehouse-dev.tracking_ref`; UAT remains `uat`, production remains `main`.
- **Invariant**: Reserved or invalid refs never invoke the deployment apply operation.
- **Invariant**: Successful selection writes the requested feature ref and invokes apply exactly once.
- **Invariant**: Apply failure restores the previous configuration and exits nonzero.
- **Invariant**: Configuration replacement is atomic and logs contain no credentials.
- **Examples**: Current-ref display, valid feature-ref update, protected-ref rejection, missing configuration, apply failure rollback, and malformed bundle list.
- **External verification**: Airflow ref reload, Git fetch/parse, and versioned Spark application access require the actual Airflow deployment integration.
