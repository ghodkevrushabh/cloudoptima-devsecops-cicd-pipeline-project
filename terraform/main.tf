terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-north-1" # Change to your preferred AWS region (e.g., us-east-1) if needed
}

# Automatically fetch the latest official Ubuntu 22.04 LTS AMI for your region
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["098965243132"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group: Allows SSH (22), App UI (8080), and Full Outbound Access
resource "aws_security_group" "app_sg" {
  name        = "em-system-flask-sg"
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

  # Essential: Allows the server to download Docker and pull images from Docker Hub
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "em-system-flask-sg"
  }
}

# EC2 Instance Provisioning
resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro" # Tested by OPA policy
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              export DEBIAN_FRONTEND=noninteractive
              
              # Install Docker
              curl -fsSL https://get.docker.com -o get-docker.sh
              sh get-docker.sh
              
              systemctl start docker
              systemctl enable docker
              
              # Pull and run the Flask container
              docker run -d --name ems-app -p 8080:8080 vrushabhghodke/em-system-app:latest
              EOF

  tags = {
    Name = "DevSecOps-Flask-App-Server"
  }
}

# Output IP address for Jenkins stage execution
output "ec2_public_ip" {
  value = aws_instance.app_server.public_ip
}
