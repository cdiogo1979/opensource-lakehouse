# NFR Requirements: `jenkins-deployment`

## Security and Data Protection

- No credentials, tokens, passwords, private keys, or secret target values may be committed or printed in logs.
- Airflow Git access uses a Git connection or approved secrets backend. Bundle configuration contains branch refs but no credential values.
- The branch-selection CLI is an operator control over code executed by Airflow. Restrict execution to trusted operators and select only authorized feature refs; do not expose it as an unauthenticated DAG parameter or public endpoint.
- The CLI must change only the development bundle ref and must not accept protected refs `dev`, `uat`, or `main`.

## Reliability and Version Consistency

- Configure three distinct versioned Git bundles: `lakehouse-dev` with operator-selected ref, `lakehouse-uat` fixed to `uat`, and `lakehouse-prod` fixed to `main`.
- The client writes configuration atomically, applies changes through the deployment-specific backend, and restores the previous dev ref if apply fails. UAT/prod settings remain byte-for-byte unchanged.
- Keep Git bundle versioning enabled so each DAG run is associated with a commit and reruns can preserve that version according to Airflow policy.
- DAG, config, helpers, and Spark application for a run must come from the same bundle version. No mutable shared checkout or release marker may be used.
- Branch switch visibility follows configuration apply/reload, bundle fetch, and successful parsing; no immediate readiness SLA is claimed.
- Client apply success means deployment configuration/reload completed. Airflow bundle parse health must be checked separately and errors remain visible in Airflow.

## Operational Clarity

- The client reports the current and requested dev ref, configuration apply outcome, and next readiness check without claiming Airflow has parsed the new branch.
- The deployment backend command/config path is externally supplied for the target Airflow topology; credentials are provided through the platform's secret mechanism.
- Exact UAT-to-production commit promotion is a repository release process choice; separate branch tracking does not enforce same-SHA promotion.

## Maintainability and Testability

- Each Git bundle checks out one `dags/` folder and its branch-matched `configs/` and `notebooks/`; preserve a distinct environment-prefixed DAG ID in each branch version.
- Test branch validation, reserved-ref rejection, dev-only mutation, atomic config writes, apply invocation, rollback, and secret-safe output with pytest/Hypothesis.
- Airflow 3 and a compatible Git provider are required. Do not pin actual runtime/provider versions until the platform compatibility matrix is selected.

## Performance and Availability

- No numeric branch-switch duration or availability target was supplied. Completion depends on the deployment apply/reload and subsequent Airflow fetch/parse.
- Airflow, Git hosting, repository reachability, configuration manager, and Spark availability are externally operated.
