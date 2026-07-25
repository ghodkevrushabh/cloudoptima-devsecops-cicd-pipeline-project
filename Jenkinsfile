pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('docker-hub-credentials')
        SONAR_TOKEN           = credentials('sonarqube-token')
        INFRACOST_API_KEY     = credentials('infracost-api-key')
        IMAGE_NAME            = 'vrushabhghodke/ems-app'
        IMAGE_TAG             = "${BUILD_NUMBER}"
    }

    stages {
        stage('1. Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/ghodkevrushabh/ems-devsecops-project.git'
            }
        }


	stage('2. SAST (SonarQube)') {
            steps {
                // 1. Tell Jenkins to inject the Server URL and Token secretly
                withSonarQubeEnv('SonarQube') {
                    dir('employee-management') {
                        script {
                            // 2. Tell Jenkins to grab the scanner tool automatically
                            def scannerHome = tool 'SonarScanner'
                            
                            // 3. Run the scan
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
            // Add this environment block!
            environment {
                AWS_ACCESS_KEY_ID     = credentials('aws-access-key')
                AWS_SECRET_ACCESS_KEY = credentials('aws-secret-key')
            }
            steps {
                dir('terraform') {
                    sh 'terraform init'
                    // Now it has the keys it needs to generate the plan
                    sh 'terraform plan -out=tfplan'
                    sh 'terraform show -json tfplan > tfplan.json'
                    
                    sh '''
                    docker run --rm -v $(pwd):/tf openpolicyagent/opa eval \
                    --data /tf/policy.rego \
                    --input /tf/tfplan.json \
                    "data.terraform.validation.deny" > opa_results.json
                    '''
                    
                    sh 'grep -q "OPA POLICY VIOLATION" opa_results.json && { echo "OPA Policy Failed!"; cat opa_results.json; exit 1; } || echo "OPA Policy Passed!"'
                }
            }
        }

        stage('7. FinOps (Infracost)') {
            steps {
                script {
                    sh 'curl -L "https://github.com/infracost/infracost/releases/latest/download/infracost-linux-amd64.tar.gz" -o infracost.tar.gz'
                    sh 'tar xzf infracost.tar.gz'
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
                    sh 'terraform apply -auto-approve tfplan'
                    script {
                        def ec2_ip = sh(script: "terraform output -raw ec2_public_ip", returnStdout: true).trim()
                        echo "SUCCESS! App URL: http://${ec2_ip}:8080/employees"
                    }
                }
            }
        }
    }
}
