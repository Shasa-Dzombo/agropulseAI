# 🚀 AgroPulse Quick Start Guide

Get your AgroPulse backend running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+ (or use Docker)
- Git

## Option 1: Quick Start (Development)

### 1. Clone and Setup

```cmd
cd c:\Users\Codeternal\Desktop\AgroPulse

REM Create virtual environment
python -m venv venv
venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```cmd
REM Copy example env file
copy .env.example .env

REM Edit .env file with your settings (use Notepad)
notepad .env
```

**Minimum required settings:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/agropulse
SECRET_KEY=your-secret-key-change-this
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=your-bucket
BLOCKCHAIN_RPC_URL=https://rpc-mumbai.maticvigil.com/
PERMIT_CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
PRIVATE_KEY=your-blockchain-private-key
FLUTTERWAVE_SECRET_KEY=your-flutterwave-key
```

### 3. Setup Database

```cmd
REM Create database
psql -U postgres -c "CREATE DATABASE agropulse;"

REM Run migrations (if using Alembic)
alembic upgrade head

REM Or let SQLAlchemy create tables on startup
```

### 4. Run the Server

```cmd
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

🎉 **Your API is now running!**

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Option 2: Docker (Recommended for Production)

### 1. Start All Services

```cmd
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend
- Celery worker
- Nginx reverse proxy

### 2. Check Status

```cmd
docker-compose ps
docker-compose logs -f backend
```

### 3. Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## First Steps

### 1. Register a Farmer

```cmd
curl -X POST "http://localhost:8000/api/v1/auth/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"phone_number\": \"254712345678\", \"email\": \"test@example.com\", \"full_name\": \"Test Farmer\", \"password\": \"password123\"}"
```

Copy the `access_token` from the response.

### 2. Create a Farm

```cmd
curl -X POST "http://localhost:8000/api/v1/auth/farms" ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"Test Farm\", \"location\": \"Kiambu\", \"size_acres\": 5}"
```

### 3. Register a Sensor

```cmd
curl -X POST "http://localhost:8000/api/v1/sensors?farm_id=1" ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"device_id\": \"ESP32-001\", \"sensor_type\": \"esp32_cam\", \"name\": \"North Sensor\"}"
```

Save the `api_key` for your ESP32-CAM.

---

## Testing the System

### Test Alert Creation (Simulate ESP32-CAM)

```cmd
curl -X POST "http://localhost:8000/api/v1/sensors/alerts" ^
  -H "X-API-Key: YOUR_SENSOR_API_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"farm_id\": 1, \"alert_type\": \"yellow_spot\", \"severity\": \"medium\", \"confidence_score\": 0.75}"
```

### View Alerts

```cmd
curl -X GET "http://localhost:8000/api/v1/sensors/alerts?farm_id=1" ^
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Development Tools

### Interactive API Testing

Visit http://localhost:8000/docs for Swagger UI where you can:
- Test all endpoints
- See request/response schemas
- Execute API calls directly from browser

### Database Access

```cmd
REM Connect to PostgreSQL
psql -U postgres agropulse

REM View tables
\dt

REM Check users
SELECT * FROM users;
```

### View Logs

```cmd
REM Docker
docker-compose logs -f backend

REM Local
REM Logs appear in console where uvicorn is running
```

---

## Common Issues

### Issue: Database Connection Failed

**Solution:**
```cmd
REM Check PostgreSQL is running
docker-compose ps db

REM Or for local PostgreSQL
net start postgresql-x64-15
```

### Issue: Import Errors

**Solution:**
```cmd
REM Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Port 8000 Already in Use

**Solution:**
```cmd
REM Use a different port
uvicorn main:app --port 8001

REM Or kill the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## Next Steps

1. **Configure AWS Services**
   - Set up S3 bucket for image storage
   - Deploy SageMaker endpoint for AI models
   - Configure Amazon Braket for quantum optimization

2. **Deploy Smart Contract**
   ```bash
   cd contracts
   # Deploy AgroPulsePermit.sol to Polygon Mumbai testnet
   # Update PERMIT_CONTRACT_ADDRESS in .env
   ```

3. **Setup Payment Gateway**
   - Register at Flutterwave
   - Get API keys
   - Configure M-Pesa
   - Update .env with credentials

4. **Deploy to Production**
   - Use AWS ECS/Fargate or EC2
   - Set up RDS PostgreSQL
   - Configure CloudFront CDN
   - Enable HTTPS with Let's Encrypt

---

## Production Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Use production database (RDS/managed PostgreSQL)
- [ ] Enable HTTPS/SSL
- [ ] Set DEBUG=False
- [ ] Configure proper CORS origins
- [ ] Set up monitoring (CloudWatch/Prometheus)
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline
- [ ] Deploy smart contract to mainnet
- [ ] Configure production payment gateway

---

## Need Help?

- 📚 Full Documentation: `README.md`
- 💻 API Examples: `EXAMPLES.md`
- 🔧 Troubleshooting: Check logs with `docker-compose logs`
- 💬 Community: [GitHub Issues]

**Happy Farming! 🌾**
