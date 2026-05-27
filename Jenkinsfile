pipeline {
    agent any

    stages {

        stage('Clone') {
            steps {
                echo 'Cloning repository...'
            }
        }

        stage('Build Frontend Image') {
            steps {
                sh 'docker build --build-arg VITE_API_BASE_URL= -t ishu1225/mcq-frontend:latest -f client/Dockerfile client'
            }
        }

        stage('Build Backend Image') {
            steps {
                sh 'docker build -t ishu1225/mcq-backend:latest -f server/Dockerfile server'
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                }
            }
        }

        stage('Push Frontend') {
            steps {
                sh 'docker push ishu1225/mcq-frontend:latest'
            }
        }

        stage('Push Backend') {
            steps {
                sh 'docker push ishu1225/mcq-backend:latest'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script {
                    // Check if kubectl can reach the EKS cluster before attempting deploy.
                    // Jenkins runs inside Docker on a local Windows machine and does NOT have
                    // AWS credentials or a kubeconfig mounted, so the deploy is skipped here.
                    // Run: kubectl rollout restart deployment/backend deployment/frontend
                    // from your local machine after each push to apply the new images.
                    def reachable = sh(
                        script: 'kubectl cluster-info --request-timeout=5s > /dev/null 2>&1',
                        returnStatus: true
                    ) == 0

                    if (reachable) {
                        sh '''
                            export AWS_PAGER=""
                            kubectl apply -f k8s/ --validate=false
                            kubectl apply -f k8s/monitoring/ --validate=false
                            kubectl rollout restart deployment/frontend deployment/backend
                            kubectl rollout status deployment/frontend --timeout=180s
                            kubectl rollout status deployment/backend --timeout=180s
                            kubectl rollout status deployment/prometheus -n monitoring --timeout=180s || true
                            kubectl rollout status deployment/grafana -n monitoring --timeout=180s || true
                        '''
                    } else {
                        echo '⚠️  WARNING: Cannot reach EKS cluster from Jenkins (no kubeconfig/AWS creds mounted).'
                        echo '✅  Images pushed to Docker Hub successfully.'
                        echo '👉  To deploy: run  kubectl rollout restart deployment/backend deployment/frontend  from your local machine.'
                    }
                }
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline finished: images built and pushed to Docker Hub.'
        }
        failure {
            echo '❌ Pipeline failed — check stage logs above.'
        }
    }
}