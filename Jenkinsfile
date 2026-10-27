pipeline {
    agent any

    stages {
        stage('Install test dependencies') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --disable-pip-version-check -r requirements-dev.txt
                '''
            }
        }

        stage('Validate') {
            steps {
                sh '.venv/bin/python -m compileall -q airflow_bundle_client.py dags notebooks'
            }
        }

        stage('Unit tests') {
            steps {
                sh '.venv/bin/python -m pytest -q'
            }
        }
    }

    post {
        always {
            echo 'Repository CI completed. Airflow bundle refresh and DAG parsing are monitored in Airflow.'
        }
    }
}
