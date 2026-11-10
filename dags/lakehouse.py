# Airflow DAGs for this repository, built by the lakehouse platform from workflows/*.json.
from lakehouse_dags import load_workflows

load_workflows(globals(), __file__)
