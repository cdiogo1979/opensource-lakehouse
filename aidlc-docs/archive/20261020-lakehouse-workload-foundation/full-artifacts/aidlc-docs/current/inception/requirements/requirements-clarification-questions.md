# Requirements Clarification Questions

Your answers establish Airflow as the orchestrator, exported Python Spark scripts, `dev`/`uat`/`prod` YAML configuration, and starter examples. You also said the Airflow instance should sync with the `master` and `uat` branches. Please clarify the expected scope of that sync.

## Question 1: Branch Sync Scope
What should this initial feature do about syncing Airflow with Git branches?

A) Set up only the repository folders and examples; document that Airflow syncs from `master` and `uat`, with CI/CD implementation deferred

B) Include CI/CD configuration that deploys/syncs the Airflow DAGs from those branches

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Branch to Environment Mapping
How should branches map to the environment-specific configs and Airflow instance?

A) `master` maps to `prod`, `uat` maps to `uat`; `dev` is used locally or from a separate development branch

B) `master` maps to `dev`, `uat` maps to `uat`; production mapping is deferred

C) Branch-to-environment mapping should be documented as a follow-up decision

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3: Airflow Task Execution
How should the sample DAG run the exported Spark `.py` script?

A) Submit it to a separately managed Spark cluster using `SparkSubmitOperator`

B) Run it on the Airflow worker with `PythonOperator`

C) Use a different operator or execution service (specify below)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4: GitHub Actions Deployment Mechanism
The repository's `origin` is GitHub, and you selected CI/CD deployment from `master` and `uat`. How should GitHub Actions make DAG and notebook files available to each Airflow instance?

A) Use an Airflow Git integration (`git-sync` or equivalent) on each instance; GitHub Actions validates the repo and the instances follow their configured branches

B) Use GitHub Actions to copy/sync files to each Airflow deployment over SSH/SFTP; connection details and credentials will be supplied through GitHub secrets

C) Use GitHub Actions to publish DAGs through an Airflow API or deployment service; endpoint and authentication details will be supplied through GitHub secrets

D) Other (please describe after [Answer]: tag below)

[Answer]: D , we should use jenkins pipeline

## Question 5: Production Branch Name
The checked-out repository and its GitHub remote currently use `main`, while the requested production sync branch is `master`. Which should the CI workflow target?

A) Target `master` as requested; branch creation or renaming is outside this feature

B) Target the existing `main` branch for production and `uat` for UAT

C) Target both `main` and `master` for production until the branch convention is settled

D) Other (please describe after [Answer]: tag below)

[Answer]:B
