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
                sh 'docker build -t ishu1225/mcq-frontend:latest ./client'
            }
        }

        stage('Build Backend Image') {
            steps {
                sh 'docker build -t ishu1225/mcq-backend:latest ./server'
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
                sh 'kubectl apply -f k8s/'
            }
        }
    }
}