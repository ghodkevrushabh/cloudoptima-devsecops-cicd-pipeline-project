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

        stage('1.5: Unit Test & Code Coverage') {
            steps {
                sh '''
                echo "Running Python Unit Tests..."
                
                # Navigate into the subfolder where your application files live
                cd employee-management
                
                python3 -m venv venv
                . venv/bin/activate
                pip install -r requirements.txt
                python3 -m pytest --cov=. --cov-report=xml:coverage.xml
                '''
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
                    // -input=false prevents any future interactive prompts from crashing Jenkins
                    // -force-copy automatically migrates the state to S3
		    sh 'terraform init -input=false -force-copy'
                    sh 'terraform plan -out=tfplan'
                    sh 'terraform show -json tfplan > tfplan.json'

                    // 1. Prove the files are actually in the directory!
                    sh 'echo "--- FILES IN TERRAFORM DIRECTORY ---"'
                    sh 'ls -la'

                    // 2. Run OPA and print the output directly to the Jenkins console
                    sh 'echo "--- OPA EVALUATION OUTPUT ---"'
                    
		    sh 'docker run --rm -v $(pwd):/tf openpolicyagent/opa eval --data /tf/policy.rego --input /tf/tfplan.json "data.terraform.validation.deny" > opa_results.json'
                }
            }
        }
	
	stage('7. FinOps (Infracost)') {
            steps {
                script {
                    // Download and extract Infracost
                    sh 'curl -sL "https://github.com/infracost/infracost/releases/latest/download/infracost-linux-amd64.tar.gz" -o infracost.tar.gz'
                    sh 'tar xzf infracost.tar.gz'
                    
                    echo "================ FINOPS AUDIT REPORT ================"
                    // Run Infracost directly to print the full cost breakdown table to the console!
                    sh './infracost-linux-amd64 breakdown --path ./terraform'
                    echo "====================================================="
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
                    script {
                        // Capture the output of the apply command
                        def apply_output = sh(script: 'terraform apply -auto-approve -input=false tfplan', returnStdout: true).trim()
                        echo apply_output // Print standard terraform logs
                        
                        def ec2_ip = sh(script: "terraform output -raw ec2_public_ip", returnStdout: true).trim()

                        echo "====================================================="
                        if (apply_output.contains("0 added, 0 changed, 0 destroyed")) {
                            echo "✅ INFRASTRUCTURE: EC2 is already deployed and stable."
                            echo "🔄 CD PIPELINE: Ready to push application changes to existing server."
                        } else {
                            echo "✅ INFRASTRUCTURE: Successfully provisioned new EC2 resources."
                        }
                        
                        if (ec2_ip == "") {
                            echo "⚠️ WARNING: EC2 Public IP is missing! Start your instance in AWS."
                        } else {
                            echo "🚀 LIVE APP URL: http://${ec2_ip}:8080/"
                        }
                        echo "====================================================="
                    }
                }
            }
        }
        stage('8.5. Infrastructure Hardening (Ansible)') {
            steps {
                echo "Running OS Hardening Playbook..."
                sh '''
                # Move into the ansible directory
                cd ansible
                
                # Run the playbook against the EC2 inventory
                ansible-playbook -i inventory.ini hardening.yml
                '''
            }
        }
	stage('9. Deploy App to EC2 (CD)') {
            // ADD THIS ENVIRONMENT BLOCK:
            environment {
                AWS_ACCESS_KEY_ID     = credentials('aws-access-key')
                AWS_SECRET_ACCESS_KEY = credentials('aws-secret-key')
            }
            steps {
                dir('terraform') {
                    script {
                        def ec2_ip = sh(script: "terraform output -raw ec2_public_ip", returnStdout: true).trim()

                        if (ec2_ip == "") {
                            error("Deployment Failed: No EC2 Public IP found. Is the instance running?")
                        }

                        echo "🚀 Connecting to ${ec2_ip} to deploy latest code..."
			withCredentials([sshUserPrivateKey(credentialsId: 'ec2-ssh-key', keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER')]) {
			    sh """
			    # 1. Securely copy config files from employee-management to EC2
                            scp -o StrictHostKeyChecking=no -i \$SSH_KEY ../employee-management/docker-compose.yml ../employee-management/prometheus.yml ../employee-management/loki-config.yml ../employee-management/promtail-config.yml \${SSH_USER}@${ec2_ip}:/home/ubuntu/                            
                            # 2. SSH into EC2, fix permissions, and launch stack
                            ssh -o StrictHostKeyChecking=no -i \$SSH_KEY \${SSH_USER}@${ec2_ip} '
                                # Install Docker & Docker Compose if missing
                                if ! command -v docker &> /dev/null; then
                                    echo "Installing Docker..."
                                    sudo apt-get update -y
                                    sudo apt-get install -y docker.io docker-compose-v2
                                    sudo systemctl start docker
                                    sudo systemctl enable docker
                                fi

                                # Fix docker socket permissions for ubuntu user
                                sudo usermod -aG docker ubuntu || true
                                sudo chmod 666 /var/run/docker.sock || true

                                # Stop old standalone container if running
                                sudo docker stop ems-app || true
                                sudo docker rm ems-app || true

                                # Pull latest image and start entire stack
                                sudo docker compose pull
                                sudo docker compose up -d
                            '
                            """
                        }
                        echo "✅ CD COMPLETE: New application code is live at http://${ec2_ip}:8080/"
                    }
                }
            }
        }
    }
}
