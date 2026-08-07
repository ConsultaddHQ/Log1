pipeline {
    agent any
    parameters {
        choice(
            name: 'env',
            choices: ['dev', 'staging', 'prod'],
            description: 'Environment to deploy'
        )
    }
    stages {
        stage('Deployment'){
            steps {
                   sh "./deployment/deploy.sh ${params.env}"
            }
        }
    }
}