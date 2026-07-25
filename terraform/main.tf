terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }


# Tells Terraform to store its memory in AWS instead of the Jenkins VM
  backend "s3" {
    bucket = "ems-terraform-state-itiss" # bucket nano
    key    = "devsecops/terraform.tfstate"  # The file path inside the bucket
    region = "eu-north-1"
    dynamodb_table = "terraform-state-lock" # <-- Adds the concurrency lock
    encrypt        = true                   # <-- Secures your state file at rest
  }
}



provider "aws" {
  region = "eu-north-1" 
}

# Automatically fetches the exact Ubuntu 22.04 AMI for your specific region
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
}

# Security Group: Allows SSH (22), App UI (8080), and Full Outbound Access
resource "aws_security_group" "app_sg" {
  name        = "ems-app-sg"
  description = "Security group for DevSecOps Python Flask Application"

  ingress {
    description = "SSH Access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Flask Application Web UI and REST API"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Essential: Allows the server to download Docker and pull images
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ems-app-sg"
  }
}

# EC2 Instance Provisioning
resource "aws_instance" "app_server" {
  ami                    = data.aws_ssm_parameter.ubuntu.value
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name               = "ems-jenkins-key"

  user_data = <<-EOF
              #!/bin/bash
              export DEBIAN_FRONTEND=noninteractive
              curl -fsSL https://get.docker.com -o get-docker.sh
              sh get-docker.sh

              systemctl start docker
              systemctl enable docker

              docker run -d --name ems-app -p 8080:8080 vrushabhghodke/ems-app:latest
              EOF

  tags = {
    Name = "DevSecOps-App-Server"
  }
}

# Output IP address for Jenkins stage execution
output "ec2_public_ip" {
  value = aws_instance.app_server.public_ip
}
