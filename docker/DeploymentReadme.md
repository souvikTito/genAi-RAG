# Lambda Deployment Guide

## Quick Deployment (Full Pipeline)
```bash
cd genai/docker
./deploy_all_lambdas.sh  # Builds, pushes to ECR, and updates Lambda
```

## Manual Step-by-Step
```bash
# 1. Build Docker image
sudo docker build -f genai/docker/doc_processing.Dockerfile -t doc-lambda .

# 2. Tag for ECR
sudo docker tag doc-lambda:latest 613640794830.dkr.ecr.us-east-2.amazonaws.com/mpg-document-processing:latest

# 3. Login to ECR
aws ecr get-login-password --region us-east-2 | sudo docker login --username AWS --password-stdin 613640794830.dkr.ecr.us-east-2.amazonaws.com

# 4. Push to ECR
sudo docker push 613640794830.dkr.ecr.us-east-2.amazonaws.com/mpg-document-processing:latest

# 5. Update Lambda
aws lambda update-function-code --function-name mpg-document-processing-lambda --image-uri 613640794830.dkr.ecr.us-east-2.amazonaws.com/mpg-document-processing:latest --region us-east-2
```

## Quick Update (Image Already in ECR)
```bash
cd genai/docker
./deploy_only_lambda.sh  # Updates Lambda with existing ECR image
```




