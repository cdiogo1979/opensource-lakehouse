pipeline {
    agent any

    stages {
        stage('Validate') {
            steps {
                sh 'python3 -m compileall -q airflow_bundle_client.py dags notebooks'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'python3 -m pytest -q'
            }
        }
    }

    post {
        always {
            echo 'Repository CI completed. Airflow bundle refresh and DAG parsing are monitored in Airflow.'
        }
    }
}
