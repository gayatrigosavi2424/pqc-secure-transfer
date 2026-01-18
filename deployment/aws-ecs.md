# AWS ECS Deployment Guide

Deploy your PQC Secure Transfer System on Amazon Web Services using Elastic Container Service (ECS).

## 🎯 Architecture Overview

```
Internet → ALB → ECS Service → ECS Tasks (Containers)
                     ↓
                 EFS (Key Storage) + CloudWatch (Monitoring)
```

## 📋 Prerequisites

- AWS CLI installed and configured
- Docker installed locally
- AWS account with appropriate permissions

## 🚀 Step-by-Step Deployment

### Step 1: Build and Push Docker Image

```bash
# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name pqc-secure-transfer --region us-east-1

# Build and tag image
docker build -t pqc-secure-transfer .
docker tag pqc-secure-transfer:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/pqc-secure-transfer:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/pqc-secure-transfer:latest
```

### Step 2: Create ECS Task Definition

Create `aws-task-definition.json`:

```json
{
  "family": "pqc-secure-transfer",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "pqc-secure-transfer",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/pqc-secure-transfer:latest",
      "portMappings": [
        {
          "containerPort": 8765,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "PQC_KEY_STORE_PATH",
          "value": "/app/keys"
        },
        {
          "name": "PQC_ALGORITHM",
          "value": "Kyber768"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "efs-keys",
          "containerPath": "/app/keys"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/pqc-secure-transfer",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "python -c \"import pqc_secure_transfer; print('OK')\" || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "volumes": [
    {
      "name": "efs-keys",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-xxxxxxxxx",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}
```

### Step 3: Create EFS File System for Key Storage

```bash
# Create EFS file system
aws efs create-file-system \
    --creation-token pqc-keys-$(date +%s) \
    --performance-mode generalPurpose \
    --throughput-mode provisioned \
    --provisioned-throughput-in-mibps 100 \
    --encrypted \
    --tags Key=Name,Value=pqc-secure-transfer-keys

# Create mount targets (replace subnet-ids and security-group-id)
aws efs create-mount-target \
    --file-system-id fs-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --security-groups sg-xxxxxxxxx
```

### Step 4: Create ECS Cluster and Service

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name pqc-secure-transfer-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://aws-task-definition.json

# Create service
aws ecs create-service \
    --cluster pqc-secure-transfer-cluster \
    --service-name pqc-secure-transfer-service \
    --task-definition pqc-secure-transfer:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxxx,subnet-yyyyyyyyy],securityGroups=[sg-xxxxxxxxx],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/pqc-tg/xxxxxxxxx,containerName=pqc-secure-transfer,containerPort=8765
```

### Step 5: Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
    --name pqc-secure-transfer-alb \
    --subnets subnet-xxxxxxxxx subnet-yyyyyyyyy \
    --security-groups sg-xxxxxxxxx

# Create target group
aws elbv2 create-target-group \
    --name pqc-secure-transfer-tg \
    --protocol HTTP \
    --port 8765 \
    --vpc-id vpc-xxxxxxxxx \
    --target-type ip \
    --health-check-path /health

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:<account-id>:loadbalancer/app/pqc-secure-transfer-alb/xxxxxxxxx \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/pqc-secure-transfer-tg/xxxxxxxxx
```

## 🔧 CloudFormation Template

For automated deployment, use this CloudFormation template:

```yaml
# Save as aws-cloudformation.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'PQC Secure Transfer System on ECS'

Parameters:
  ImageURI:
    Type: String
    Description: ECR Image URI
    Default: '<account-id>.dkr.ecr.us-east-1.amazonaws.com/pqc-secure-transfer:latest'

Resources:
  # VPC and Networking
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true

  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: pqc-secure-transfer-cluster

  # Task Definition
  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: pqc-secure-transfer
      Cpu: 1024
      Memory: 2048
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      ExecutionRoleArn: !Ref ExecutionRole
      TaskRoleArn: !Ref TaskRole
      ContainerDefinitions:
        - Name: pqc-secure-transfer
          Image: !Ref ImageURI
          PortMappings:
            - ContainerPort: 8765
          Environment:
            - Name: PQC_ALGORITHM
              Value: Kyber768
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref LogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: ecs

  # ECS Service
  ECSService:
    Type: AWS::ECS::Service
    Properties:
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: 2
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          SecurityGroups:
            - !Ref SecurityGroup
          Subnets:
            - !Ref PublicSubnet1
            - !Ref PublicSubnet2
          AssignPublicIp: ENABLED

  # Security Group
  SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for PQC Secure Transfer
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8765
          ToPort: 8765
          CidrIp: 0.0.0.0/0

  # IAM Roles
  ExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole

  # CloudWatch Log Group
  LogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: /ecs/pqc-secure-transfer
      RetentionInDays: 30

Outputs:
  ServiceURL:
    Description: URL of the PQC Secure Transfer service
    Value: !Sub 'http://${ECSService}.${AWS::Region}.elb.amazonaws.com:8765'
```

Deploy with:
```bash
aws cloudformation create-stack \
    --stack-name pqc-secure-transfer \
    --template-body file://aws-cloudformation.yaml \
    --capabilities CAPABILITY_IAM \
    --parameters ParameterKey=ImageURI,ParameterValue=<your-ecr-uri>
```

## 📊 Monitoring and Scaling

### Auto Scaling Configuration

```bash
# Create auto scaling target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/pqc-secure-transfer-cluster/pqc-secure-transfer-service \
    --min-capacity 1 \
    --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/pqc-secure-transfer-cluster/pqc-secure-transfer-service \
    --policy-name pqc-cpu-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        }
    }'
```

### CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "PQC-HighCPU" \
    --alarm-description "High CPU utilization" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

## 💰 Cost Optimization

### Fargate Spot
```bash
# Use Fargate Spot for cost savings
aws ecs create-service \
    --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
    # ... other parameters
```

### Reserved Capacity
- Consider ECS Reserved Instances for predictable workloads
- Use Savings Plans for flexible compute usage

## 🔒 Security Best Practices

1. **Network Security**
   - Use private subnets for ECS tasks
   - Configure security groups with minimal required access
   - Enable VPC Flow Logs

2. **Data Encryption**
   - Enable EFS encryption at rest
   - Use AWS KMS for key management
   - Enable CloudTrail for audit logging

3. **Access Control**
   - Use IAM roles with least privilege
   - Enable AWS Config for compliance monitoring
   - Implement AWS WAF for web application protection

## 🚀 Deployment Commands Summary

```bash
# Quick deployment script
#!/bin/bash

# 1. Build and push image
docker build -t pqc-secure-transfer .
docker tag pqc-secure-transfer:latest $ECR_URI:latest
docker push $ECR_URI:latest

# 2. Deploy with CloudFormation
aws cloudformation create-stack \
    --stack-name pqc-secure-transfer \
    --template-body file://aws-cloudformation.yaml \
    --capabilities CAPABILITY_IAM \
    --parameters ParameterKey=ImageURI,ParameterValue=$ECR_URI:latest

# 3. Wait for deployment
aws cloudformation wait stack-create-complete --stack-name pqc-secure-transfer

# 4. Get service URL
aws cloudformation describe-stacks \
    --stack-name pqc-secure-transfer \
    --query 'Stacks[0].Outputs[?OutputKey==`ServiceURL`].OutputValue' \
    --output text
```

## 📈 Expected Costs (us-east-1)

| Component | Monthly Cost (2 tasks) |
|-----------|------------------------|
| Fargate (1 vCPU, 2GB) | ~$30 |
| ALB | ~$20 |
| EFS (100GB) | ~$30 |
| CloudWatch Logs | ~$5 |
| **Total** | **~$85/month** |

Your PQC Secure Transfer System is now running on AWS with enterprise-grade scalability and security! 🚀