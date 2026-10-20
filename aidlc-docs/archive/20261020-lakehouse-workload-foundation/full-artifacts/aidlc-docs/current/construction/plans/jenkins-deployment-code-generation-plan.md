# Code Generation Plan: `jenkins-deployment`

## Plan Status

**Approved by the user; code generation complete and awaiting review.** This plan supersedes the earlier SFTP/API publisher plan and includes a repository-owned dev branch-selection client. Runtime integration and tests remain for Build and Test.

## Unit Context

- **Purpose**: Use three Airflow 3 Git DAG Bundles in one Airflow deployment. An operator client selects the feature branch for dev; UAT and production remain fixed to `uat` and `main`. Jenkins provides CI and branch gates only.
- **Requirements**: FR-4/FR-5 and Git bundle, operator control, security, version consistency, and test requirements.
- **Bundle mapping**: `lakehouse-dev` -> operator-selected feature ref; `lakehouse-uat` -> `uat`; `lakehouse-prod` -> `main`.
- **Bundle content**: Each bundle includes the same paths, `dags/`, `configs/`, and `notebooks/`, from its configured Git ref; repository root is the bundle root. The bundle name supplies environment identity, and the shared DAG factory derives the configured DAG ID prefix and job environment.
- **Client boundary**: `airflow_bundle_client.py` validates the requested Git ref, changes only `lakehouse-dev.tracking_ref` in the deployment-managed bundle config, atomically writes config, invokes a configured deployment apply/reload command, and restores the previous ref/config if apply fails. It reports config apply status separately from Airflow fetch/parse readiness.
- **External prerequisites**: Airflow 3, compatible Git and Docker providers, Git connection/secrets backend, feature branch access, refresh interval, writable bundle config, platform-specific apply/reload command, operator authorization, Docker daemon visibility of bundle checkouts, Spark image/master/network.
- **Critical runtime contract**: A run must resolve its DAG, config, helper code, and Spark application from the same recorded bundle commit. The Docker daemon must be able to bind-mount that exact checkout into the Spark job image. If direct access is unsupported, implement run-version-addressed immutable staging rather than a mutable global path.

## Interfaces and Contracts

- Client command interface: select a feature branch for dev or display the current selection. Protect `dev`, `uat`, and `main`; validate refs using Git's branch-name rules and require at least one configured feature-ref prefix.
- Client configuration contains only the bundle config path, dev bundle name, and an argument-vector apply/reload command; no secrets or shell interpolation. The actual config path and command are supplied by the Airflow deployment owner.
- Only the dev bundle `tracking_ref` may change. UAT remains `uat`, production remains `main`, and all other bundle entries are preserved.
- Apply succeeds only when the configured command exits successfully. The client does not claim the selected branch has been fetched or parsed; Airflow bundle diagnostics are the readiness source.
- The client has no Airflow UI dependency and does not expose branch changes as an unauthenticated DAG parameter. Restrict the executable/config path to trusted operators.
- Bundle versioning remains enabled. No injected `RELEASE_ID`, SFTP path, or mutable shared artifact path is used.
- Jenkins does not publish artifacts or hold Airflow Git credentials.

## Planned Files and Steps

1. [x] **Branch-scoped workload DAG** — Per the user's clarification, use one `dags/` folder in each Git ref, with `ENVIRONMENT` and DAG/job ID identity declared by that branch (`dev` in the selected feature branch, `uat` in `uat`, and `prod` in `main`). All three bundles check out `dags/`, `configs/`, and `notebooks/` from their own ref.
2. [x] **Bundle-aware artifact resolution** — DAG paths derive from the bundle DAG file location, so config, helpers, and Spark application use sibling paths from the DAG's Git checkout. Docker daemon host-path visibility remains a Build and Test gate; if unavailable, revise the plan to add immutable commit-addressed staging.
3. [x] **Airflow Git bundle configuration example** — Added a secret-free three-bundle config example with dev feature ref, fixed `uat` and `main`, sparse directories, Git connection ID, illustrative refresh interval, and repository URL placeholder. `AIRFLOW_BUNDLES.md` documents replacing/emptying default local DAG discovery.
4. [x] **Dev branch-selection client** — Created `airflow_bundle_client.py` with `show` and `select --branch <feature-ref>`. It reads external non-secret settings, validates branch syntax, required feature-ref prefixes, and protected refs, changes only dev, writes atomically, invokes an argv-style apply command without a shell, restores the prior config and reapplies on failure, and reports apply status separately from Airflow parse readiness. Added client settings example and tests.
5. [x] **Jenkins CI boundary** — Replaced deployment and sync stages with repository syntax validation and unit tests. Jenkins no longer binds Airflow credentials, uses deployment locks, uploads files, or claims Airflow refresh readiness.
6. [x] **Retire SFTP/API publisher** — Removed `airflow_deployment_adapter.py`, `jenkins_deployment.py`, `requirements-deploy.txt`, and SFTP/API policy tests. Removed obsolete release marker and manual SFTP contract.
7. [x] **Tests** — Replaced publisher tests with pytest/Hypothesis coverage for bundle config, dev-only ref mutation, invalid/protected refs, safe apply arguments, and rollback. Tests were generated but not run.
8. [x] **Guidance and operator instructions** — Updated `AGENTS.md` and added `AIRFLOW_BUNDLES.md` for client usage, branch access, provider/Git setup, refresh/version behavior, apply/reload integration, operator restrictions, monitoring, and Spark path verification. Documents that Airflow UI has no native tracking-ref selector.
9. [x] **AIDLC and generation summary** — Updated requirements/design traceability, this plan, generation summary, state, and audit. Runtime integration and test execution remain deferred to Build and Test.

## Verification Boundary

Generate tests but do not execute them during Code Generation. Build and Test validates Python syntax, policy/client tests, configuration shape, DAG imports, the target-specific apply command in a controlled Airflow environment, and same-run-version access to Spark application/config artifacts. No production deployment or unapproved external project modification is part of this plan.

## Approval

This approved revised plan was the single source of truth for the replacement implementation. The exact approval input is recorded in `aidlc-docs/current/audit.md`.
