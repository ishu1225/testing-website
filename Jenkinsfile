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
                sh 'export AWS_PAGER="" && kubectl apply -f k8s/ --validate=false'
            }
        }
    }
}