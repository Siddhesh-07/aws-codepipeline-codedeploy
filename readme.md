# AWS CodePipeline Health Check API

A Python Flask health check API deployed on AWS EC2, with a fully automated CI/CD pipeline using AWS CodePipeline and CodeBuild. Every push to `main` triggers the pipeline which builds and deploys the app automatically.

---

## Architecture

```
git push to GitHub (main)
        │
        ▼
AWS CodePipeline
        │
        ├── Stage 1: Source
        │   └── Pulls code from GitHub via CodeConnections
        │
        ├── Stage 2: Build (CodeBuild)
        │   └── Installs dependencies via buildspec.yml
        │
        └── Stage 3: Deploy (CodeBuild)
                └── SSHs into EC2, copies files, restarts app
                            │
                            ▼
                    EC2 (Amazon Linux 2023)
                    Flask app managed by systemd
                            │
                            ▼
                    GET /health → JSON response
```

---

## API Endpoints

**GET /health**
```json
{
  "status": "healthy",
  "timestamp": "2026-06-06T11:52:37.970446",
  "uptime": "0h 0m 7s",
  "host": "ip-10-0-8-109.ec2.internal",
  "version": "1.0.1"
}
```

**GET /**
```json
{
  "message": "Health Check API is running",
  "endpoint": "/health"
}
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| AWS CodePipeline | Pipeline orchestration |
| AWS CodeBuild | Build and deploy execution |
| AWS SSM Parameter Store | Secure SSH key storage |
| AWS S3 | Pipeline artifact storage |
| AWS EC2 (Amazon Linux 2023) | Application server |
| systemd | Process management |
| Python + Flask | Application framework |
| GitHub | Source control |

---

## Project Structure

```
├── app.py                  # Flask health check app
├── requirements.txt        # Python dependencies
├── buildspec.yml           # CodeBuild build stage instructions
├── buildspec-deploy.yml    # CodeBuild deploy stage instructions
├── tests/
│   └── test_app.py         # pytest tests
└── scripts/
    ├── start.sh
    └── stop.sh
```

---

## Setup Guide

### 1. IAM Roles

**CodeBuild-Deploy-Role** (for CodeBuild):
- AmazonS3FullAccess
- AmazonEC2FullAccess
- CloudWatchLogsFullAccess
- AmazonSSMReadOnlyAccess
- AWSCodeBuildAdminAccess

**AWSCodePipelineServiceRole** (auto-created, add these):
- AWSCodeStarFullAccess
- AmazonS3FullAccess
- AWSCodeBuildAdminAccess
- Inline policy: codeconnections:UseConnection

---

### 2. S3 Artifact Bucket

Create a private S3 bucket for CodePipeline artifacts:
```
health-check-artifacts-<your-account-id>
```

---

### 3. EC2 Instance

- AMI: Amazon Linux 2023
- Instance type: t2.micro
- Security Group: SSH (22), HTTP (80), Custom TCP (5000)
- IAM Profile: EC2-CodeDeploy-Role

---

### 4. SSM Parameter Store

Store your EC2 private key:
- Name: `/health-check/ec2-ssh-key`
- Type: SecureString
- Value: contents of your `.pem` file

---

### 5. systemd Service on EC2

```bash
sudo tee /etc/systemd/system/healthcheck.service > /dev/null <<EOF
[Unit]
Description=Health Check Flask App
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
ExecStart=/usr/bin/python3 /home/ec2-user/app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable healthcheck
sudo systemctl start healthcheck
sudo systemctl status healthcheck
```

---

### 6. CodeBuild Projects

**health-check-build:**
- Source: GitHub repo, branch: main
- Buildspec: `buildspec.yml`
- Service role: CodeBuild-Deploy-Role
- Purpose: Install dependencies, run build

**health-check-deploy:**
- Source: GitHub repo, branch: main
- Buildspec: `buildspec-deploy.yml`
- Service role: CodeBuild-Deploy-Role
- Environment variables:

| Name | Value | Type |
|------|-------|------|
| EC2_HOST | your EC2 public IP | Plaintext |
| EC2_USER | ec2-user | Plaintext |

---

### 7. CodePipeline

Create pipeline with 3 stages:

**Stage 1 — Source:**
- Provider: GitHub (Version 2) via CodeConnections
- Repository: your GitHub repo
- Branch: main
- Output: SourceArtifact

**Stage 2 — Build:**
- Provider: AWS CodeBuild
- Project: health-check-build
- Input: SourceArtifact
- Output: BuildArtifact

**Stage 3 — Deploy:**
- Provider: AWS CodeBuild
- Project: health-check-deploy
- Input: BuildArtifact

---

## buildspec.yml

```yaml
version: 0.2

phases:
  install:
    commands:
      - pip3 install flask pytest

  build:
    commands:
      - echo "Build successful"

artifacts:
  files:
    - '**/*'
  discard-paths: no
```

---

## buildspec-deploy.yml

```yaml
version: 0.2

phases:
  install:
    commands:
      - mkdir -p ~/.ssh
      - aws ssm get-parameter --name "/health-check/ec2-ssh-key" --with-decryption --query "Parameter.Value" --output text > ~/.ssh/deploy_key
      - chmod 600 ~/.ssh/deploy_key
      - ssh-keyscan -H $EC2_HOST >> ~/.ssh/known_hosts

  build:
    commands:
      - ssh -i ~/.ssh/deploy_key $EC2_USER@$EC2_HOST "mkdir -p /home/ec2-user/app"
      - scp -i ~/.ssh/deploy_key -r * $EC2_USER@$EC2_HOST:/home/ec2-user/app/
      - ssh -i ~/.ssh/deploy_key $EC2_USER@$EC2_HOST "cd /home/ec2-user/app && sudo yum install python3-pip -y && pip3 install -r requirements.txt && sudo systemctl restart healthcheck"

  post_build:
    commands:
      - echo "Deployment complete"
```

---

## How to Deploy

Push to main then click Release Change in CodePipeline:

```bash
git add .
git commit -m "your changes"
git push
```

Verify deployment:
```bash
curl http://YOUR-EC2-IP:5000/health
```

---

## Key Design Decisions

**SSM Parameter Store for SSH key:** Environment variables strip newlines from `.pem` files making them invalid. SSM Parameter Store preserves exact formatting including newlines.

**systemd over nohup:** `nohup` processes die when the SSH session that started them closes. systemd manages the process independently of SSH sessions and auto-restarts it if it crashes.

**CodeBuild for deploy stage:** Using a second CodeBuild project for deployment via SSH is simpler and free tier compatible compared to CodeDeploy.

---

## Possible Improvements


- [ ] Add pytest properly to build stage
- [ ] Use Gunicorn instead of Flask development server
- [ ] Add HTTPS via Application Load Balancer + ACM certificate
- [ ] Store infrastructure as code using Terraform
- [ ] Add CloudWatch alarms for health check failures
