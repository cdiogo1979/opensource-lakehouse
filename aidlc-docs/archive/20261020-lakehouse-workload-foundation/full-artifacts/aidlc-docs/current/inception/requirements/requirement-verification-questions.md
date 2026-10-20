# Requirements Verification Questions

Please answer each question by filling in the `[Answer]:` line. For multiple-choice questions, use a letter; choose the final `Other` option and describe your answer when needed.

## Question 1: Orchestration and Repository Convention
The repository guide currently describes a Databricks layout, including `jobs/<project>/`. Your request calls for Airflow DAGs in `dags/`. What should this initial feature establish?

A) Use Airflow as the orchestrator, with `configs/`, `notebooks/`, and `dags/`; update `AGENTS.md` to make this the authoritative convention

B) Keep Databricks jobs as the orchestrator and add the requested `dags/` directory for a later Airflow integration

C) Support both Airflow and Databricks as first-class orchestrators, with separate job definitions

D) Other (please describe after [Answer]: tag below)

[Answer]: D , this is a different project , no databricks. It still runs jupyter notebooks which are exported as .py files and then dags to execute them . The objective is for the airfkow instance to be synced with the master branch and uat branches .

## Question 2: Notebook Organization and Execution
How should Python Spark code be organized and how should Airflow execute it?

A) Keep reusable Python modules under `notebooks/`; DAGs submit those scripts to a Spark cluster

B) Keep Databricks notebook source files under `notebooks/`; DAGs trigger Databricks jobs

C) Keep notebooks under `notebooks/`; DAGs execute them using an Airflow Spark operator against an external Spark cluster

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3: Environment Configuration
Which environments should the initial `configs/` layout support?

A) `dev`, `test`, and `prod`

B) `dev` and `prod`

C) Create the environment layout without choosing names yet

D) Other (please describe after [Answer]: tag below)

[Answer]: D , dev , uat and prod

## Question 4: Configuration Format
What format should environment-specific configuration use?

A) YAML files

B) JSON files

C) Python modules

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5: Initial Deliverable Scope
Should this feature create only the directory structure and placeholders, or include starter examples?

A) Directories and minimal `.gitkeep` placeholders only

B) Directories plus sample environment configuration, a sample Spark script, and a sample Airflow DAG

C) Directories and documentation describing how to add files, without sample workload code

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6: Security Baseline Extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8: Resiliency Baseline Extension
Should the resiliency baseline be applied as directional design-time guidance for this project?

A) Yes — apply the resiliency baseline (recommended for business-critical workloads, as an informed starting point to validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects)

C) Other (please describe after [Answer]: tag below)

[Answer]: B
