# 🌿 AgroPulse Horticulture Platform - Quick Start Guide

## Overview

This guide helps you quickly set up and use AgroPulse for greenhouse and horticultural operations:
- Greenhouse Management (Climate Control)
- Environmental Monitoring (Temperature, Humidity, CO2, PAR, pH, EC)
- Hydroponic Systems (Nutrient Management)
- Digital Chama (Grower Cooperatives)
- AI-Powered Crop Health Monitoring

## Prerequisites

- Python 3.9+
- PostgreSQL 14+
- Node.js 16+ (for smart contracts)
- Git

## Step 1: Database Migration

### Create Alembic Migration

```bash
# Navigate to project root
cd c:\Users\Codeternal\Desktop\AgroPulse

# Generate migration for new models
alembic revision --autogenerate -m "Add advanced features: blockchain, chama, interventions"

# Review the generated migration file
# Location: alembic/versions/XXXX_add_advanced_features.py

# Apply migration
alembic upgrade head
```

### Verify Tables Created

```sql
-- Connect to PostgreSQL
psql -U postgres -d agropulse

-- Check new tables
\dt

-- Expected tables:
-- crop_health_passports
-- passport_access_permits
-- chama_groups
-- chama_memberships
-- chama_outbreak_analyses
-- treatment_options
-- treatment_efficacy
```

## Step 2: Seed Treatment Database

### Run Seed Script

```python
# Create file: scripts/seed_treatments.py

from app.database import AsyncSession, engine
from app.models.advanced_features import TreatmentOption
import asyncio

async def seed_treatments():
    async with AsyncSession(engine) as session:
        treatments = [
            # Fall Armyworm Treatments (Maize)
            TreatmentOption(
                name="Lambda-cyhalothrin 2.5% EC",
                active_ingredient="Lambda-cyhalothrin",
                treatment_type="chemical",
                crop_type="maize",
                disease_type="fall_armyworm",
                efficacy_data={
                    "low": 0.95,
                    "medium": 0.98,
                    "high": 0.95
                },
                unit_cost_ksh=2400.0,
                application_rate_per_ha=0.5,
                time_to_effect_days=2,
                organic_certified=False,
                safety_rating=3,
                manufacturer="Brand X",
                active=True
            ),
            TreatmentOption(
                name="BT Biopesticide",
                active_ingredient="Bacillus thuringiensis",
                treatment_type="biological",
                crop_type="maize",
                disease_type="fall_armyworm",
                efficacy_data={
                    "low": 0.90,
                    "medium": 0.88,
                    "high": 0.85
                },
                unit_cost_ksh=1000.0,
                application_rate_per_ha=1.0,
                time_to_effect_days=3,
                organic_certified=True,
                safety_rating=5,
                manufacturer="BioTech Kenya",
                active=True
            ),
            TreatmentOption(
                name="Neem Oil",
                active_ingredient="Azadirachtin",
                treatment_type="organic",
                crop_type="maize",
                disease_type="fall_armyworm",
                efficacy_data={
                    "low": 0.85,
                    "medium": 0.82,
                    "high": 0.78
                },
                unit_cost_ksh=400.0,
                application_rate_per_ha=2.0,
                time_to_effect_days=5,
                organic_certified=True,
                safety_rating=5,
                manufacturer="Organic Solutions",
                active=True
            ),
            
            # Add more treatments for other diseases...
        ]
        
        for treatment in treatments:
            session.add(treatment)
        
        await session.commit()
        print(f"✅ Seeded {len(treatments)} treatment options")

if __name__ == "__main__":
    asyncio.run(seed_treatments())
```

```bash
# Run seed script
python scripts/seed_treatments.py
```

## Step 3: Configure Environment Variables

### Update `.env` file

```bash
# Blockchain Configuration
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_CHAIN_ID=137
POLYGON_PRIVATE_KEY=your_private_key_here
CONTRACT_ADDRESS_PASSPORT=0x...  # After deployment

# IPFS Configuration
IPFS_PROVIDER=pinata
PINATA_API_KEY=your_pinata_api_key
PINATA_SECRET_KEY=your_pinata_secret

# Or self-hosted IPFS
# IPFS_API_URL=http://localhost:5001

# Quantum Services (optional)
AWS_BRAKET_ENABLED=true
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1

# Notification Services
FIREBASE_API_KEY=your_firebase_key
WHATSAPP_API_TOKEN=your_whatsapp_token
TELEGRAM_BOT_TOKEN=your_telegram_token
```

## Step 4: Deploy Smart Contracts (Testnet)

### Install Dependencies

```bash
cd smart-contracts
npm install
```

### Create Contract

```solidity
// smart-contracts/contracts/CropHealthPassport.sol

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract CropHealthPassport is ERC721, Ownable {
    uint256 private _tokenIdCounter;
    
    struct Passport {
        string passportHash;
        uint256 timestamp;
        address farmer;
        bool valid;
    }
    
    mapping(uint256 => Passport) public passports;
    mapping(string => uint256) public hashToTokenId;
    
    event PassportMinted(uint256 indexed tokenId, string passportHash, address farmer);
    event AccessGranted(uint256 indexed tokenId, address thirdParty, uint256 expiresAt);
    
    constructor() ERC721("CropHealthPassport", "CHP") {}
    
    function mintPassport(string memory passportHash, address farmer) 
        public 
        onlyOwner 
        returns (uint256) 
    {
        require(hashToTokenId[passportHash] == 0, "Passport already exists");
        
        _tokenIdCounter++;
        uint256 tokenId = _tokenIdCounter;
        
        _safeMint(farmer, tokenId);
        
        passports[tokenId] = Passport({
            passportHash: passportHash,
            timestamp: block.timestamp,
            farmer: farmer,
            valid: true
        });
        
        hashToTokenId[passportHash] = tokenId;
        
        emit PassportMinted(tokenId, passportHash, farmer);
        
        return tokenId;
    }
    
    function verifyPassport(string memory passportHash) 
        public 
        view 
        returns (bool valid, uint256 timestamp, address farmer) 
    {
        uint256 tokenId = hashToTokenId[passportHash];
        require(tokenId != 0, "Passport not found");
        
        Passport memory passport = passports[tokenId];
        return (passport.valid, passport.timestamp, passport.farmer);
    }
}
```

### Deploy to Polygon Mumbai Testnet

```bash
# Configure Hardhat
npx hardhat run scripts/deploy.js --network mumbai

# Expected output:
# CropHealthPassport deployed to: 0x123abc...

# Update .env with contract address
```

## Step 5: Test Basic Functionality

### Test 1: Create Blockchain Passport

```bash
# Start server
uvicorn main:app --reload

# In another terminal, test endpoint
curl -X POST http://localhost:8000/api/v1/advanced/passport/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "diagnosis": {
      "disease": "Fall Armyworm",
      "confidence": 0.92,
      "severity": "medium"
    },
    "capture_data": {
      "image": "test_image_base64",
      "temperature": 28.5,
      "humidity": 75.0,
      "gps_lat": -1.286389,
      "gps_lon": 36.817223,
      "field_id": 1
    }
  }'

# Expected response:
# {
#   "passport_id": 1,
#   "passport_hash": "0xabc123...",
#   "permit_token_id": 1001,
#   "blockchain_tx_hash": "0x789def...",
#   "verification_url": "https://mumbai.polygonscan.com/tx/0x789def..."
# }
```

### Test 2: Verify Passport

```bash
curl http://localhost:8000/api/v1/advanced/passport/verify/0xabc123...

# Expected response:
# {
#   "valid": true,
#   "passport_hash": "0xabc123...",
#   "blockchain_timestamp": "2025-10-26T12:00:00Z",
#   "trust_score": 0.99
# }
```

### Test 3: Get Treatment Recommendations

```bash
curl -X POST http://localhost:8000/api/v1/advanced/treatment/recommend \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "diagnosis": {
      "disease": "fall_armyworm",
      "confidence": 0.92,
      "severity": "medium",
      "estimated_yield_loss_percent": 25
    },
    "crop_type": "maize",
    "field_area_ha": 2.5,
    "farmer_budget_ksh": 5000
  }'

# Expected response:
# {
#   "status": "optimized",
#   "treatment_options": [
#     {
#       "rank": 1,
#       "treatment_name": "Lambda-cyhalothrin 2.5% EC",
#       "total_cost_ksh": 1500,
#       "roi": 6.0
#     }
#   ]
# }
```

## Step 6: Test Complete Workflow

### Create Test Chama Group

```python
# scripts/create_test_chama.py

from app.database import AsyncSession, engine
from app.models.advanced_features import ChamaGroup, ChamaMembership
import asyncio

async def create_test_chama():
    async with AsyncSession(engine) as session:
        chama = ChamaGroup(
            name="Kiambu Farmers Cooperative",
            region="Kiambu County",
            center_latitude=-1.17139,
            center_longitude=36.83507,
            member_count=10,
            data_sharing_enabled=True,
            outbreak_alerts_enabled=True
        )
        session.add(chama)
        await session.commit()
        print(f"✅ Created Chama: {chama.name} (ID: {chama.id})")

asyncio.run(create_test_chama())
```

### Test Complete Diagnostic Workflow

```bash
curl -X POST http://localhost:8000/api/v1/advanced/complete-diagnosis \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "diagnosis": {
      "disease": "Fall Armyworm",
      "confidence": 0.92,
      "severity": "moderate",
      "yield_loss_percent": 25
    },
    "capture_data": {
      "image": "ipfs://Qm...",
      "temperature": 28.5,
      "humidity": 75.0,
      "gps_lat": -1.286389,
      "gps_lon": 36.817223
    },
    "field_info": {
      "field_id": 1,
      "crop_type": "maize",
      "area_hectares": 2.5
    },
    "chama_id": 1,
    "farmer_budget_ksh": 5000
  }'

# This will:
# 1. Create blockchain passport
# 2. Analyze Chama outbreaks
# 3. Generate treatment recommendations
# 4. Return complete action plan
```

## Step 7: Set Up Scheduled Jobs

### Using Celery

```bash
# Install Celery
pip install celery redis

# Create celery_app.py
```

```python
# celery_app.py
from celery import Celery
from celery.schedules import crontab

app = Celery('agropulse', broker='redis://localhost:6379/0')

@app.task
async def daily_chama_analysis():
    """Run Chama outbreak analysis daily at 4 AM"""
    from app.database import AsyncSession, engine
    from app.services.chama_outbreak_service import chama_outbreak_service
    from app.models.advanced_features import ChamaGroup
    
    async with AsyncSession(engine) as db:
        result = await db.execute(select(ChamaGroup).where(ChamaGroup.outbreak_alerts_enabled == True))
        chamas = result.scalars().all()
        
        for chama in chamas:
            await chama_outbreak_service.analyze_community_outbreaks(
                db=db,
                chama_id=chama.id,
                lookback_days=14
            )

app.conf.beat_schedule = {
    'daily-chama-analysis': {
        'task': 'celery_app.daily_chama_analysis',
        'schedule': crontab(hour=4, minute=0)  # 4:00 AM daily
    }
}
```

```bash
# Start Celery worker
celery -A celery_app worker -l info

# Start Celery beat (scheduler)
celery -A celery_app beat -l info
```

## Step 8: Monitor & Debug

### Check Logs

```bash
# Application logs
tail -f logs/app.log

# Celery logs
tail -f logs/celery.log

# Database queries (in .env set)
LOG_LEVEL=DEBUG
```

### Database Queries

```sql
-- Check blockchain passports
SELECT id, passport_hash, permit_token_id, created_at 
FROM crop_health_passports 
ORDER BY created_at DESC 
LIMIT 10;

-- Check Chama outbreak analyses
SELECT chama_id, analysis_date, urgency_level, 
       jsonb_array_length(active_clusters) as cluster_count
FROM chama_outbreak_analyses
ORDER BY analysis_date DESC;

-- Check treatment recommendations usage
SELECT t.name, COUNT(te.id) as usage_count, AVG(te.satisfaction_rating) as avg_rating
FROM treatment_options t
LEFT JOIN treatment_efficacy te ON t.id = te.treatment_id
GROUP BY t.id, t.name
ORDER BY usage_count DESC;
```

## Step 9: API Documentation

### Access Interactive Docs

```
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

## Troubleshooting

### Issue: Blockchain transaction fails

**Solution**:
```python
# Check wallet balance
web3 = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
balance = web3.eth.get_balance(settings.POLYGON_WALLET_ADDRESS)
print(f"Wallet balance: {web3.from_wei(balance, 'ether')} MATIC")

# Fund wallet if needed (Mumbai testnet faucet)
# https://faucet.polygon.technology/
```

### Issue: IPFS upload fails

**Solution**:
```python
# Test Pinata connection
import requests

response = requests.post(
    "https://api.pinata.cloud/pinning/pinJSONToIPFS",
    json={"test": "data"},
    headers={
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_KEY
    }
)
print(response.json())
```

### Issue: Chama analysis returns no clusters

**Solution**:
```python
# Create test diagnostic data
from app.models.cctv import CCTVCapture, CropHealthReading

# Add at least 3 diagnoses with GPS coordinates within 5km
# to trigger cluster detection
```

## Next Steps

1. **Pilot Testing**: Deploy to 10 farmers in one Chama
2. **Collect Feedback**: Monitor usage patterns and issues
3. **Iterate**: Fix bugs and improve UX based on feedback
4. **Scale**: Gradually expand to more Chamas

## Resources

- **API Documentation**: `/docs` endpoint
- **System Architecture**: `SYSTEM_INTEGRATION_COMPLETE.md`
- **Advanced Features API**: `ADVANCED_FEATURES_API.md`
- **Mobile Sensor Specs**: `MOBILE_PHONE_SENSOR.md`

## Support

For issues or questions:
1. Check logs first
2. Review API documentation
3. Test with curl/Postman
4. Contact: dev@agropulse.com

---

**Status**: Ready for Testing  
**Last Updated**: 2025-10-26
