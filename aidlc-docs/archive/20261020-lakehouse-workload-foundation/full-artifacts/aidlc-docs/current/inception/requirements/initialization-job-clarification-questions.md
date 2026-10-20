# Initialization Job Clarification

This change affects the current sample workload contract. Please choose the intended behavior before implementation.

## Question 1: Initialization behavior

What should the renamed `init_environment` job do on each run?

A) Idempotently create the configured Nessie namespace and storage prefix only; remove the synthetic sample table write. For S3-compatible storage, initialize the prefix using the Hadoop filesystem API.

B) Idempotently create the configured Nessie namespace and storage prefix, then keep writing the existing `sample_spark_job_output` table as a smoke test.

C) Other (please describe after [Answer]: tag below)

[Answer]: B

**Recorded from user response**: `2` selects option B — create the namespace and prefix idempotently, then retain the sample table write as a smoke test.
