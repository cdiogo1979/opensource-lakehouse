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
                sh '.venv/bin/python -m compileall -q dags notebooks'
            }
        }

        stage('Validate workflows') {
            steps {
                // The lakehouse platform's rules for workflows/*.json and the dags/ stub,
                // provided by the platform Jenkins (the same checks Airflow applies).
                sh '''
                    command -v lakehouse-validate-workflows >/dev/null || { echo "lakehouse-validate-workflows is not installed on this Jenkins" >&2; exit 1; }
                    lakehouse-validate-workflows .
                '''
            }
        }

        stage('Code Analysis') {
            parallel {
                stage('Lint and Formatting') {
                    steps {
                        sh 'PATH=".venv/bin:$PATH" scripts/code_quality.sh lint'
                    }
                }
                stage('Flake8 Style Check') {
                    steps {
                        sh 'PATH=".venv/bin:$PATH" scripts/code_quality.sh flake8'
                    }
                }
                stage('Bandit Security Scan') {
                    steps {
                        sh 'PATH=".venv/bin:$PATH" scripts/code_quality.sh bandit'
                    }
                }
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
