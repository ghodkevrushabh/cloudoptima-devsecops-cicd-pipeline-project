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

        stage('2: Unit Test & Code Coverage') {
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

        stage('3. SAST (SonarQube)') {
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

        stage('4. Build & SCA (Trivy)') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:latest -f employee-management/Dockerfile employee-management'
                sh 'trivy image --timeout 15m --severity HIGH,CRITICAL ${IMAGE_NAME}:latest'
            }
        }

        stage('5. Push to Registry') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh 'docker push ${IMAGE_NAME}:latest'
                }
            }
        }

        stage('6. IaC Security (Checkov)') {
            steps {
                sh 'docker run --rm -v "${WORKSPACE}/terraform":/tf bridgecrew/checkov -d /tf --soft-fail'
            }
        }

	stage('7. OPA Policy Enforcement') {
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
	
	stage('8. FinOps (Infracost)') {
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
	stage('9. Terraform Deploy') {
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
        stage('10. Infrastructure Hardening (Ansible)') {
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

        stage('11. Generate TLS Certificates') {
            steps {
                echo "Generating ephemeral self-signed certificates for Nginx..."
                dir('employee-management') {
                    sh '''
                    mkdir -p nginx/certs
                    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                      -keyout nginx/certs/server.key \
                      -out nginx/certs/server.crt \
                      -subj "/C=IN/ST=Maharashtra/L=IACSDakurdi/O=EMS Security/CN=emsapp.com"
                    '''
                }
            }
        }

        stage('12. Deploy App to EC2 (CD)') {
            environment {
                AWS_ACCESS_KEY_ID     = credentials('aws-access-key')
                AWS_SECRET_ACCESS_KEY = credentials('aws-secret-key')
            }
            steps {
                script {
                    // 1. Fetch the IP from the terraform directory
                    def ec2_ip = ""
                    dir('terraform') {
                        ec2_ip = sh(script: "terraform output -raw ec2_public_ip", returnStdout: true).trim()
                    }

                    if (ec2_ip == "") {
                        error("Deployment Failed: No EC2 Public IP found. Is the instance running?")
                    }

                    echo "🚀 Connecting to ${ec2_ip} to deploy latest code..."

                    // 2. Switch to the app directory and deploy
                    dir('employee-management') {
                        sh """
                        # Create the target directory on the EC2 instance
                        ssh -i /var/lib/jenkins/.ssh/ems-key.pem -o StrictHostKeyChecking=no ubuntu@${ec2_ip} "mkdir -p /home/ubuntu/ems-app"

                        # Securely copy the files
                        scp -i /var/lib/jenkins/.ssh/ems-key.pem -o StrictHostKeyChecking=no -r docker-compose.yml prometheus.yml loki-config.yml promtail-config.yml nginx/ ubuntu@${ec2_ip}:/home/ubuntu/ems-app/

                        # Execute docker-compose on the remote server
                        ssh -i /var/lib/jenkins/.ssh/ems-key.pem -o StrictHostKeyChecking=no ubuntu@${ec2_ip} "cd /home/ubuntu/ems-app && docker-compose down && docker-compose up -d --build"
                        """
                    }
                    
                    echo "✅ CD COMPLETE: Encrypted application is live at https://${ec2_ip}/"
                }
            }
        }
    }
}
