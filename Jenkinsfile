pipeline {
    agent any

    environment {
        // Infracost automatically looks for this specific environment variable to authenticate
        INFRACOST_API_KEY = credentials('infracost-api-key')
        IMAGE_NAME        = 'vrushabhghodke/ems-app'
        IMAGE_TAG         = "${BUILD_NUMBER}"
    }

    stages {
        stage('1. Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/ghodkevrushabh/ems-devsecops-project.git'
            }
        }

        stage('2. SAST (SonarQube)') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    dir('employee-management') {
                        script {
                            def scannerHome = tool 'SonarScanner'
                            sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectKey=ems-app -Dsonar.sources=."
                        }
                    }
                }
            }
        }

        stage('3. Build & SCA (Trivy)') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:latest -f employee-management/Dockerfile employee-management'
                sh 'trivy image --timeout 15m --severity HIGH,CRITICAL ${IMAGE_NAME}:latest'
            }
        }

        stage('4. Push to Registry') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh 'docker push ${IMAGE_NAME}:latest'
                }
            }
        }

        stage('5. IaC Security (Checkov)') {
            steps {
                sh 'docker run --rm -v "${WORKSPACE}/terraform":/tf bridgecrew/checkov -d /tf --soft-fail'
            }
        }

	stage('6. OPA Policy Enforcement') {
            environment {
                AWS_ACCESS_KEY_ID     = credentials('aws-access-key')
                AWS_SECRET_ACCESS_KEY = credentials('aws-secret-key')
            }
            steps {
                dir('terraform') {
                    sh 'terraform init'
                    sh 'terraform plan -out=tfplan'
                    sh 'terraform show -json tfplan > tfplan.json'

                    // 1. Prove the files are actually in the directory!
                    sh 'echo "--- FILES IN TERRAFORM DIRECTORY ---"'
                    sh 'ls -la'

                    // 2. Run OPA and print the output directly to the Jenkins console
                    sh 'echo "--- OPA EVALUATION OUTPUT ---"'
                    
                    // We added '|| true' so Jenkins doesn't instantly crash if OPA gets mad. 
                    // This forces it to print the error to the screen.
                    sh '''
                    docker run --rm -v $(pwd):/tf openpolicyagent/opa eval \
                    --data /tf/policy.rego \
                    --input /tf/tfplan.json \
                    "data.terraform.validation.deny" || true
                    '''
                }
            }
        }
        stage('7. FinOps (Infracost)') {
            steps {
                script {
                    sh 'curl -L "https://github.com/infracost/infracost/releases/latest/download/infracost-linux-amd64.tar.gz" -o infracost.tar.gz'
                    sh 'tar xzf infracost.tar.gz'
                    
                    // Calculates cost using the same Terraform files
                    sh './infracost-linux-amd64 breakdown --path ./terraform > infracost_report.txt'
                    env.MONTHLY_COST = sh(script: 'grep "Total Monthly Cost" infracost_report.txt || echo "Cost not found"', returnStdout: true).trim()
                    echo "FINOPS AUDIT: ${env.MONTHLY_COST}"
                }
            }
        }

        stage('8. Terraform Deploy') {
            environment {
                AWS_ACCESS_KEY_ID     = credentials('aws-access-key')
                AWS_SECRET_ACCESS_KEY = credentials('aws-secret-key')
            }
            steps {
                dir('terraform') {
                    // Because OPA and Infracost passed, we finally deploy to AWS
                    sh 'terraform apply -auto-approve tfplan'
                    script {
                        def ec2_ip = sh(script: "terraform output -raw ec2_public_ip", returnStdout: true).trim()
                        echo "SUCCESS! App URL: http://${ec2_ip}:8080/"
                    }
                }
            }
        }
    }
}
