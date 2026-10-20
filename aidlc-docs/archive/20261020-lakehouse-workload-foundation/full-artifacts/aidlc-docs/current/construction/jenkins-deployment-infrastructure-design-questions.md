# Infrastructure Design Questions: `jenkins-deployment`

Please answer each question by filling in its `[Answer]:` tag. These answers determine how much of the external Jenkins/Airflow boundary can be mapped now. “Other” is available for a custom answer.

## Question 1: Artifact Sync Mechanism

How should the pipeline transfer `configs/`, `dags/`, and `notebooks/` to Airflow?

A) Keep the mechanism as an externally configured adapter; select the transport when the Airflow platform details are available (Recommended)

B) Airflow instances pull the selected branch through a repository sync integration

C) Jenkins pushes files over SSH/SFTP using managed credentials

D) Publish through an Airflow API or managed deployment service

E) Other (please describe after `[Answer]:`)

[Answer]: D , main build to the /main directory and uat build to the /uat directory

## Question 2: Hosting and Network Boundary

What should this repository assume about Jenkins-to-Airflow network access?

A) Jenkins agents and Airflow targets are externally managed; platform operators provide private/network connectivity (Recommended)

B) Include network or deployment-agent provisioning artifacts in this repository

C) Specify a hosting provider and target topology now (describe it after `[Answer]:`)

D) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 3: Jenkins Agent Capabilities

What should the deployment unit assume is available on Jenkins agents?

A) A managed agent provides Python 3, the selected Jenkins lock capability, and tools required by the external adapter (Recommended)

B) Add a repository-managed agent image/container to provide Python and deployment tools

C) Do not require Python on the agent; implement policy and validation only in Jenkins Pipeline Groovy

D) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 4: Deployment Monitoring

What deployment visibility should this feature provide?

A) Jenkins build status and secret-safe build logs are sufficient; external alerting is platform-managed (Recommended)

B) Add a notification or monitoring integration, with its service and credentials supplied externally

C) Other (please describe after `[Answer]:`)

[Answer]: A
