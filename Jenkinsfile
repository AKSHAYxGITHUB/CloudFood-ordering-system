pipeline {
    agent any

    environment {
        IMAGE_NAME = "foodorder-app"
        IMAGE_TAG  = "${env.GIT_COMMIT.take(7)}"
    }

    stages {
        stage('Build') {
            steps {
                sh 'docker build -t $IMAGE_NAME:$IMAGE_TAG -f docker/Dockerfile .'
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest
                    pytest tests/ -v
                '''
            }
        }

        stage('Security Scan') {
            steps {
                sh 'trivy image --exit-code 1 --severity CRITICAL,HIGH $IMAGE_NAME:$IMAGE_TAG'
                sh '''
                    . .venv/bin/activate
                    pip install safety
                    safety check -r requirements.txt
                '''
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                sshagent(['app-server-ssh-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no -J ubuntu@$BASTION_HOST ubuntu@$APP_SERVER_HOST '
                            docker pull $REGISTRY/$IMAGE_NAME:$IMAGE_TAG &&
                            docker stop foodorder-app || true &&
                            docker rm foodorder-app || true &&
                            docker run -d --name foodorder-app --env-file /opt/foodorder/.env -p 5000:5000 $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                        '
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline succeeded: build -> test -> security scan -> deploy.'
        }
        failure {
            echo 'Pipeline failed - check the stage logs above.'
        }
    }
}
