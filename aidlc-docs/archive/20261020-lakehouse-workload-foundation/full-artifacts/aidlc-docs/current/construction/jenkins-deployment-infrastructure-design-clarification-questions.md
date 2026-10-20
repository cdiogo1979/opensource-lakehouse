# Infrastructure Design Clarification Questions: `jenkins-deployment`

Your sync answer selects an Airflow API or managed deployment service and also specifies `/main` and `/uat` directories. Those could be remote filesystem destinations or directories populated by the managed service; the distinction affects the infrastructure mapping.

## Clarification Question 1: Meaning of `/main` and `/uat`

How should the deployment destinations be interpreted?

A) They are remote filesystem directories on the Airflow hosts; a managed file-transfer adapter should publish each branch's artifacts there

B) They are logical destination names handled by the Airflow API or a managed deployment service; no direct remote filesystem access is assumed

C) The managed service receives an API request and places the files into those directories; keep the service and placement mechanism externally configured

D) Other (please describe after `[Answer]:`)

[Answer]: D if there is a airflow api that can handle it then B other wise A
