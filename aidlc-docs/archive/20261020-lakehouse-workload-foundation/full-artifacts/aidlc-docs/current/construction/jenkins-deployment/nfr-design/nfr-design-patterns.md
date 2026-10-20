# NFR Design Patterns: `jenkins-deployment`

## Bundle Isolation and Versioning

- Configure independently named `GitDagBundle` entries: dev tracks an operator-selected feature ref, UAT tracks `uat`, and production tracks `main`.
- Each Git bundle checks out the single root `dags/` directory plus root `configs/` and `notebooks/` from its selected ref. Keep bundle root at repository root (`subdir` unset) so sibling paths resolve predictably.
- Keep bundle versioning enabled. DAG runs and task execution must use the commit version captured for the run; resolve config and Spark source from that checkout.
- Confirm Docker daemon access to the task's run-pinned bundle checkout and read-only bind mount into the Spark job image before declaring deployment ready. Do not silently fall back to a mutable local dags folder or `/opt/jobs` copy.
- Branch polling uses a platform-configured refresh interval. Report fetch/auth/parse errors through Airflow's normal component logs and DAG import diagnostics.

## Credential Protection

- Put Git credentials in an Airflow connection or approved secrets backend and reference its connection ID from bundle configuration.
- Do not embed tokenized URLs, keys, or passwords in `dag_bundle_config_list`; use a read-only repository identity and trusted host verification.
- Configure the provider and credentials in all components that need to fetch versioned bundles, especially the DAG processor and task execution environment as required by the selected Airflow setup.

## Development Ref Control

- Restrict the branch-selection client to trusted operators. Reject `dev`, `uat`, and `main` so development testing cannot alter shared branch mappings.
- Update only the dev bundle's tracking ref with an atomic configuration write, then invoke the deployment-specific apply/reload operation. Restore the previous ref if apply fails.
- Keep client apply status separate from Airflow bundle parse status. Verify the selected branch and parsed commit in Airflow before testing a workload.
- Do not expose arbitrary branch selection through an unauthenticated DAG parameter or public endpoint.

## Jenkins Boundary

- Jenkins may run branch policy and repository CI for `uat`/`main`, but it does not publish content, select an Airflow transport, bind deployment credentials, or claim the Airflow bundle has refreshed.
- Airflow Git fetch/parse readiness is monitored independently; no SFTP locking, retry, rollback, or atomic rename logic applies.

## Testability and Operations

- Exercise pure branch-to-environment mapping, bundle config shape, environment-specific DAG IDs, and root-relative artifact selection using example and property-based tests.
- In Build and Test, validate Airflow imports against the selected provider/runtime and run an integration check that confirms DAG, YAML, and Spark application use the same bundle commit.
- Document actual Airflow version, provider installation, Git connection, repository reachability, refresh interval, and promotion controls as platform inputs. No numeric propagation SLO is specified.
