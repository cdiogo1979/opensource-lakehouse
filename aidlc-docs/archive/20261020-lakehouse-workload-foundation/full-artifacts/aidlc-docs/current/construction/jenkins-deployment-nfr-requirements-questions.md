# NFR Requirements Questions: `jenkins-deployment`

Please answer each question by filling in its `[Answer]:` tag. These choices set recovery and concurrency expectations for the Jenkins sync stage. “Other” is available for a custom answer.

## Question 1: Sync Failure Recovery

If the configured sync adapter fails after it may have copied some files, what should the pipeline require?

A) Fail the build without automatic retry or rollback; report the failure safely and leave recovery to a controlled rerun after checking the target (Recommended)

B) Retry the sync a bounded number of times; the retry limit and delay must be configurable

C) Require the adapter to provide atomic sync or rollback before this pipeline can report deployment status

D) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 2: Concurrent Deployments to One Environment

If more than one Jenkins build targets the same Airflow environment at the same time, what behavior should be required?

A) Serialize deployments per environment so only one sync to that target runs at a time (Recommended)

B) Allow concurrent deployments and rely on the sync adapter to handle conflicts

C) Cancel older queued/running builds when a newer build targets the same environment

D) Other (please describe after `[Answer]:`)

[Answer]: A
