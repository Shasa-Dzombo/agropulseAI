# 🌿 AgroPulse Horticulture Platform - Production Deployment Guide

Complete step-by-step guide to deploy AgroPulse greenhouse management platform to production.

## Deployment Options

1. **AWS (Recommended)** - Full featured, scalable for commercial greenhouses
2. **Azure** - Alternative cloud provider with IoT Hub integration
3. **DigitalOcean** - Simple, cost-effective for small-scale growers
4. **On-Premise** - Full control for enterprise greenhouse operations

---

## Option 1: AWS Deployment (Recommended)

### Prerequisites
- AWS Account
- AWS CLI installed and configured
- Docker installed
- Domain name (optional)

### Step 1: Database Setup (RDS PostgreSQL)

```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier agropulse-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username agropulse \
  --master-user-password YOUR_SECURE_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxx \
  --publicly-accessible

# Get endpoint
aws rds describe-db-instances \
  --db-instance-identifier agropulse-db \
  --query 'DBInstances[0].Endpoint.Address'
```

### Step 2: S3 Bucket for Images

```bash
# Create S3 bucket
aws s3 mb s3://agropulse-images-prod

# Enable CORS
aws s3api put-bucket-cors --bucket agropulse-images-prod --cors-configuration file://s3-cors.json
```

`s3-cors.json`:
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

### Step 3: Deploy SageMaker Model

```bash
# Upload your trained model to S3
aws s3 cp model.tar.gz s3://agropulse-models/

# Create SageMaker endpoint
aws sagemaker create-model \
  --model-name agropulse-crop-disease-model \
  --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.12-cpu-py38,ModelDataUrl=s3://agropulse-models/model.tar.gz \
  --execution-role-arn arn:aws:iam::ACCOUNT:role/SageMakerRole

# Create endpoint
aws sagemaker create-endpoint \
  --endpoint-name agropulse-ai-model \
  --endpoint-config-name agropulse-endpoint-config
```

### Step 4: ECR & Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name agropulse

# Build and push
docker build -t agropulse .
docker tag agropulse:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/agropulse:latest
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/agropulse:latest
```

### Step 5: ECS/Fargate Deployment

Create `task-definition.json`:
```json
{
  "family": "agropulse",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "agropulse-backend",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/agropulse:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DATABASE_URL", "value": "postgresql+asyncpg://..."},
        {"name": "AWS_REGION", "value": "us-east-1"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "FLUTTERWAVE_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/agropulse",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Deploy:
```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS cluster
aws ecs create-cluster --cluster-name agropulse-cluster

# Create service
aws ecs create-service \
  --cluster agropulse-cluster \
  --service-name agropulse-service \
  --task-definition agropulse:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=agropulse-backend,containerPort=8000
```

### Step 6: Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name agropulse-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Create target group
aws elbv2 create-target-group \
  --name agropulse-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /health

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

### Step 7: Route 53 (DNS)

```bash
# Create hosted zone
aws route53 create-hosted-zone --name api.agropulse.com

# Add A record pointing to ALB
aws route53 change-resource-record-sets --hosted-zone-id Z123456 --change-batch file://dns-record.json
```

### Step 8: Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
  --name agropulse/production/secret-key \
  --secret-string "your-production-secret-key"

aws secretsmanager create-secret \
  --name agropulse/production/blockchain-key \
  --secret-string "your-blockchain-private-key"

aws secretsmanager create-secret \
  --name agropulse/production/flutterwave \
  --secret-string '{"secret_key":"xxx","public_key":"yyy"}'
```

---

## Option 2: DigitalOcean Deployment (Simple & Cost-Effective)

### Step 1: Create Droplet

```bash
# Using doctl CLI
doctl compute droplet create agropulse-prod \
  --image docker-20-04 \
  --size s-2vcpu-4gb \
  --region nyc1 \
  --ssh-keys YOUR_SSH_KEY_ID

# Get IP
doctl compute droplet list
```

### Step 2: Setup Server

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Install dependencies
apt update && apt upgrade -y
apt install -y docker.io docker-compose postgresql-client

# Clone repository
git clone https://github.com/yourusername/agropulse.git
cd agropulse

# Create .env file
nano .env
# (paste your production environment variables)

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### Step 3: Setup Nginx + SSL

```bash
# Install Nginx
apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx
nano /etc/nginx/sites-available/agropulse
```

```nginx
server {
    listen 80;
    server_name api.agropulse.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
ln -s /etc/nginx/sites-available/agropulse /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Get SSL certificate
certbot --nginx -d api.agropulse.com
```

### Step 4: Setup Managed Database (Optional)

```bash
# Create managed PostgreSQL
doctl databases create agropulse-db \
  --engine pg \
  --region nyc1 \
  --size db-s-1vcpu-1gb

# Get connection string
doctl databases connection agropulse-db

# Update .env with connection string
# Restart services
docker-compose restart
```

---

## Option 3: Azure Deployment

### Step 1: Azure PostgreSQL

```bash
# Create resource group
az group create --name agropulse-rg --location eastus

# Create PostgreSQL
az postgres flexible-server create \
  --resource-group agropulse-rg \
  --name agropulse-db \
  --location eastus \
  --admin-user agropulse \
  --admin-password YOUR_PASSWORD \
  --sku-name Standard_B1ms \
  --storage-size 32
```

### Step 2: Container Registry

```bash
# Create container registry
az acr create \
  --resource-group agropulse-rg \
  --name agropulseregistry \
  --sku Basic

# Build and push
az acr build \
  --registry agropulseregistry \
  --image agropulse:latest .
```

### Step 3: Container Instances

```bash
# Create container instance
az container create \
  --resource-group agropulse-rg \
  --name agropulse-backend \
  --image agropulseregistry.azurecr.io/agropulse:latest \
  --cpu 2 \
  --memory 4 \
  --dns-name-label agropulse-api \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    DATABASE_URL="postgresql+asyncpg://..." \
  --secure-environment-variables \
    SECRET_KEY="xxx" \
    FLUTTERWAVE_SECRET_KEY="yyy"
```

---

## Blockchain Deployment

### Deploy Smart Contract to Polygon Mainnet

```bash
# Install Hardhat
npm install --save-dev hardhat @nomiclabs/hardhat-waffle

# Create deployment script
npx hardhat run scripts/deploy.js --network polygon
```

`scripts/deploy.js`:
```javascript
async function main() {
  const AgroPulsePermit = await ethers.getContractFactory("AgroPulsePermit");
  const permit = await AgroPulsePermit.deploy();
  await permit.deployed();
  
  console.log("AgroPulsePermit deployed to:", permit.address);
}

main();
```

Update `.env`:
```env
PERMIT_CONTRACT_ADDRESS=0x...  # Your deployed contract address
BLOCKCHAIN_NETWORK=polygon
BLOCKCHAIN_RPC_URL=https://polygon-rpc.com/
```

---

## Post-Deployment Checklist

- [ ] Database backup configured
- [ ] SSL certificate installed
- [ ] Environment variables secured
- [ ] Monitoring setup (CloudWatch/Datadog)
- [ ] Alerts configured
- [ ] Log aggregation enabled
- [ ] Auto-scaling configured
- [ ] Health checks working
- [ ] Domain DNS configured
- [ ] Payment gateway tested
- [ ] Blockchain verified
- [ ] API documentation deployed
- [ ] Rate limiting enabled
- [ ] CORS configured properly
- [ ] Webhooks configured
- [ ] Backup/disaster recovery tested

---

## Monitoring & Maintenance

### CloudWatch Alarms (AWS)

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name agropulse-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name agropulse-errors \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

### Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily via cron

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="agropulse_backup_$TIMESTAMP.sql"

# Backup database
pg_dump $DATABASE_URL > $BACKUP_FILE

# Upload to S3
aws s3 cp $BACKUP_FILE s3://agropulse-backups/

# Keep only last 30 days
find . -name "agropulse_backup_*.sql" -mtime +30 -delete
```

---

## Scaling Guide

### Horizontal Scaling (ECS)

```bash
# Update service desired count
aws ecs update-service \
  --cluster agropulse-cluster \
  --service agropulse-service \
  --desired-count 5
```

### Auto-Scaling

```bash
# Create auto-scaling policy
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/agropulse-cluster/agropulse-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Scale on CPU
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/agropulse-cluster/agropulse-service \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-config.json
```

---

## Cost Optimization

### Estimated AWS Costs (Monthly)

| Service | Configuration | Cost |
|---------|--------------|------|
| ECS Fargate | 2 tasks (0.5 vCPU, 1GB) | $30 |
| RDS PostgreSQL | db.t3.micro | $15 |
| S3 Storage | 100GB + requests | $5 |
| SageMaker | On-demand inference | $50 |
| Load Balancer | ALB | $20 |
| **Total** | | **~$120/month** |

### Optimization Tips

1. Use Spot Instances for non-critical tasks
2. Enable S3 Intelligent-Tiering
3. Use CloudFront CDN for images
4. Implement caching with Redis
5. Use reserved instances for predictable load

---

## Troubleshooting

### Common Issues

**Issue**: Container won't start
```bash
# Check logs
docker-compose logs backend
# or
aws ecs describe-tasks --cluster agropulse-cluster --tasks TASK_ID
```

**Issue**: Database connection fails
```bash
# Test connectivity
psql -h YOUR_DB_HOST -U agropulse -d agropulse

# Check security groups/firewall
telnet YOUR_DB_HOST 5432
```

**Issue**: High memory usage
```bash
# Check container stats
docker stats

# Increase memory limits in task definition
```

---

For support, contact: devops@agropulse.com
