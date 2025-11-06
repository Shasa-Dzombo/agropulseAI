# Advanced Features API Documentation

This document provides comprehensive documentation for the 7 core integration layers that transform AgroPulse from a simple diagnostic tool into a complete precision horticulture ecosystem.

## Table of Contents

1. [Overview](#overview)
2. [Digital Health Passport (Core Idea 5)](#digital-health-passport)
3. [Chama Outbreak Prediction (Core Idea 6)](#chama-outbreak-prediction)
4. [AI Intervention Optimization (Core Idea 7)](#ai-intervention-optimization)
5. [Complete Diagnostic Workflow](#complete-diagnostic-workflow)
6. [Authentication](#authentication)
7. [Error Handling](#error-handling)

---

## Overview

The Advanced Features API implements the final integration layer that connects:

- **Edge Intelligence** (ESP32 Sentry Stakes): 99% accuracy diagnostics
- **Mobile Intelligence** (Phone NPU): 90% accurate instant triage
- **Cloud AI**: Full diagnostic models + quantum optimization
- **Blockchain Trust** (Polygon): Immutable health records
- **Community Intelligence** (Chama): Outbreak prediction
- **Financial Intelligence**: ROI-optimized treatments

All endpoints are prefixed with `/api/v1/advanced`

---

## Digital Health Passport

### Create Blockchain Passport

**Endpoint**: `POST /api/v1/advanced/passport/create`

**Authentication**: Required (Bearer token)

**Description**: Creates an immutable Digital Health Passport anchored on Polygon blockchain. The passport includes cryptographic hash, IPFS storage, and NFT permit token for access control.

**Use Cases**:
- Bulk buyers verify crop health before purchase → justify premium pricing
- Banks use verified crop health as collateral → de-risk loans
- Export quality verification with immutable records

**Request Body**:
```json
{
  "diagnosis": {
    "disease": "Fall Armyworm",
    "confidence": 0.92,
    "severity": "medium",
    "treatment": "Apply BT biopesticide within 48 hours",
    "yield_loss": 25
  },
  "capture_data": {
    "image": "ipfs://Qm...",  // or base64
    "stress_map": [0.5, 0.6, 0.8, 0.9],
    "frames_stacked": 12,
    "noise_reduction": 0.68,
    "temperature": 28.5,
    "humidity": 75.0,
    "gps_lat": -1.286389,
    "gps_lon": 36.817223,
    "field_id": 42
  }
}
```

**Response** (201 Created):
```json
{
  "passport_id": 123,
  "passport_hash": "0xabc123def456...",
  "permit_token_id": 4567,
  "blockchain_tx_hash": "0x789def...",
  "ipfs_url": "ipfs://Qm...",
  "farmer_wallet": "0x456abc...",
  "verification_url": "https://polygonscan.com/tx/0x789def..."
}
```

**Cost**: ~$0.02 gas fee (Polygon L2)

---

### Grant Third-Party Access

**Endpoint**: `POST /api/v1/advanced/passport/{passport_id}/grant-access`

**Authentication**: Required (Bearer token)

**Description**: Grant time-limited access to third parties (buyers, banks, researchers) to view crop health passport.

**Request Body**:
```json
{
  "third_party_id": 789,
  "third_party_type": "buyer",  // buyer, bank, researcher
  "duration_days": 7,
  "access_level": "read_only"
}
```

**Response** (200 OK):
```json
{
  "permit_id": 456,
  "expires_at": "2025-11-07T12:00:00Z",
  "verification_url": "https://api.agropulse.com/passport/123/verify?permit=456"
}
```

**Use Cases**:
- **Buyer**: "Show me your last 5 harvest health records to justify premium price"
- **Bank**: "Grant us access to verify crop health for loan application"
- **Researcher**: "Contribute anonymized data to regional disease study"

---

### Verify Passport Authenticity

**Endpoint**: `GET /api/v1/advanced/passport/verify/{passport_hash}`

**Authentication**: None (public endpoint)

**Description**: Anyone can verify passport authenticity via blockchain query. Returns trust score and blockchain timestamp.

**Response** (200 OK):
```json
{
  "valid": true,
  "passport_hash": "0xabc123...",
  "blockchain_timestamp": "2025-10-26T12:00:00Z",
  "trust_score": 0.99
}
```

**Trust Score**:
- **0.99**: Blockchain-verified immutable record
- **0.90**: Cloud AI diagnosis (no blockchain)
- **0.85**: On-device NPU triage
- **0.70**: Manual farmer report

---

## Chama Outbreak Prediction

### Analyze Community Outbreaks

**Endpoint**: `POST /api/v1/advanced/chama/{chama_id}/analyze-outbreaks`

**Authentication**: Required (Bearer token, must be Chama member)

**Description**: Analyzes community-wide outbreak patterns using anonymized diagnostic data. Detects disease clusters, predicts spread, and sends proactive alerts to at-risk farmers.

**Request Body** (optional):
```json
{
  "lookback_days": 14
}
```

**Response** (200 OK):
```json
{
  "status": "analyzed",
  "active_clusters": [
    {
      "disease": "downy_mildew",
      "center_lat": -1.28,
      "center_lon": 36.82,
      "case_count": 12,
      "avg_severity": 2.5,
      "spread_days": 5
    }
  ],
  "spread_analysis": {
    "avg_spread_km_per_day": 2.8,
    "growth_rate_cases_per_day": 1.5,
    "doubling_time_days": 4.7,
    "intervention_urgency": "high"
  },
  "outbreak_predictions": [
    {
      "disease": "downy_mildew",
      "forecast_days": 7,
      "predicted_spread_km": 19.6,
      "direction": "northeast",
      "confidence": 0.85
    }
  ],
  "at_risk_farmers": 8,
  "proactive_alerts_sent": 8
}
```

**Alert Example**:
```
⚠️ Warning: Downy Mildew detected 3km upwind from your location.

Current conditions:
• Humidity: 85% (favorable for spread)
• Wind: 5 km/h northeast
• Temperature: 22°C

Recommended action:
Preventative scan in Zones A & C within 48 hours.

Community stats:
• 12 confirmed cases in 5km radius
• Spread rate: 2.8 km/day
• Urgency: HIGH
```

**Privacy**: GPS coordinates anonymized to 0.01° precision (~1km) for data sharing.

**Urgency Levels**:
- **critical** (>0.75): Immediate action required, outbreak accelerating
- **high** (>0.50): Action within 48 hours recommended
- **medium** (>0.25): Monitor situation, preventative scan advised
- **low**: No immediate threat

---

### Get Outbreak History

**Endpoint**: `GET /api/v1/advanced/chama/{chama_id}/outbreak-history?limit=10`

**Authentication**: Required (Bearer token)

**Description**: Retrieves historical outbreak analysis results to identify trends and seasonal patterns.

**Response** (200 OK):
```json
{
  "chama_id": 15,
  "analyses": [
    {
      "analysis_date": "2025-10-25T12:00:00Z",
      "cluster_count": 3,
      "alerts_sent": 12,
      "urgency_level": "high",
      "dominant_diseases": ["downy_mildew", "fall_armyworm"]
    }
  ],
  "trend": "outbreak_intensity_increasing",
  "recommendation": "Increase monitoring frequency to weekly"
}
```

---

## AI Intervention Optimization

### Recommend Treatment Options

**Endpoint**: `POST /api/v1/advanced/treatment/recommend`

**Authentication**: Required (Bearer token)

**Description**: Generates AI-optimized treatment recommendations with full cost-benefit analysis. Ranks options by composite score (40% ROI + 30% efficacy + 30% speed).

**Request Body**:
```json
{
  "diagnosis": {
    "disease": "fall_armyworm",
    "confidence": 0.92,
    "severity": "medium",
    "estimated_yield_loss_percent": 25
  },
  "crop_type": "maize",
  "field_area_ha": 2.5,
  "farmer_budget_ksh": 5000,
  "preferences": {
    "organic_only": false,
    "fast_acting": true
  }
}
```

**Response** (200 OK):
```json
{
  "status": "optimized",
  "no_action_scenario": {
    "estimated_revenue_loss_ksh": 10500
  },
  "treatment_options": [
    {
      "rank": 1,
      "treatment_name": "Lambda-cyhalothrin 2.5% EC",
      "active_ingredient": "Lambda-cyhalothrin",
      "treatment_type": "chemical",
      "efficacy": 0.95,
      "total_cost_ksh": 1500,
      "expected_savings_ksh": 9000,
      "roi": 6.0,
      "time_to_effect_days": 2,
      "organic_certified": false,
      "explanation": "✅ Best overall value: 6.0× ROI with 95% efficacy"
    },
    {
      "rank": 2,
      "treatment_name": "BT Biopesticide",
      "active_ingredient": "Bacillus thuringiensis",
      "treatment_type": "biological",
      "efficacy": 0.88,
      "total_cost_ksh": 1300,
      "expected_savings_ksh": 7800,
      "roi": 6.0,
      "time_to_effect_days": 3,
      "organic_certified": true,
      "explanation": "🌿 Organic option: Lower cost but slightly lower efficacy"
    },
    {
      "rank": 3,
      "treatment_name": "Neem Oil",
      "active_ingredient": "Azadirachtin",
      "treatment_type": "organic",
      "efficacy": 0.82,
      "total_cost_ksh": 1000,
      "expected_savings_ksh": 7000,
      "roi": 7.0,
      "time_to_effect_days": 5,
      "organic_certified": true,
      "explanation": "💰 Budget option: Highest ROI but slower effect"
    }
  ],
  "recommendation_summary": "💊 Recommended: Lambda-cyhalothrin. Investment: 1,500 KSh → Savings: 9,000 KSh (6× ROI)"
}
```

**ROI Calculation**:
```
ROI = (Yield Saved × Market Price - Treatment Cost) / Treatment Cost

Where:
  Yield Saved = Baseline Yield × Yield Loss % × Treatment Efficacy
  
Example:
  Baseline: 40 bags/ha × 2.5 ha = 100 bags
  Loss: 25% without treatment = 25 bags
  Efficacy: 95% = save 23.75 bags
  Price: 3,500 KSh/bag
  Savings: 23.75 × 3,500 = 83,125 KSh
  Cost: 1,500 KSh
  ROI: (83,125 - 1,500) / 1,500 = 54× 
  
  (Note: Real-world ROI accounts for partial efficacy, application costs, etc.)
```

---

### Report Treatment Efficacy

**Endpoint**: `POST /api/v1/advanced/treatment/{treatment_id}/report-efficacy`

**Authentication**: Required (Bearer token)

**Description**: Farmers report real-world treatment results to improve recommendations for the community.

**Request Body**:
```json
{
  "field_id": 42,
  "disease_treated": "fall_armyworm",
  "crop_type": "maize",
  "severity_before": "medium",
  "severity_after": "low",
  "days_to_effect": 3,
  "estimated_yield_saved_percent": 20,
  "farmer_satisfaction_rating": 4,
  "actual_cost_ksh": 1450
}
```

**Response** (200 OK):
```json
{
  "status": "recorded",
  "efficacy_id": 789,
  "message": "Thank you! Your feedback helps improve recommendations for the community.",
  "community_impact": "Your data contributes to better treatment recommendations for 1,200+ farmers in your region"
}
```

---

## Complete Diagnostic Workflow

### Integrated Endpoint

**Endpoint**: `POST /api/v1/advanced/complete-diagnosis`

**Authentication**: Required (Bearer token)

**Description**: **THE KILLER ENDPOINT!** Integrates all 7 core ideas into one seamless workflow:

1. Receives 99% accurate diagnosis from mobile/Sentry
2. Creates blockchain Digital Health Passport
3. Analyzes Chama outbreak risk
4. Generates AI-optimized treatment recommendations
5. Returns complete action plan

**Request Body**:
```json
{
  "diagnosis": {
    "disease": "Fall Armyworm",
    "confidence": 0.92,
    "severity": "moderate",
    "treatment": "Apply BT-based biopesticide...",
    "yield_loss_percent": 25
  },
  "capture_data": {
    "image": "ipfs://Qm...",
    "stress_map": [0.5, 0.6, 0.8, 0.9],
    "frames_stacked": 12,
    "temperature": 28.5,
    "humidity": 75.0,
    "gps_lat": -1.286389,
    "gps_lon": 36.817223
  },
  "field_info": {
    "field_id": 42,
    "crop_type": "maize",
    "area_hectares": 2.5
  },
  "chama_id": 15,
  "farmer_budget_ksh": 5000,
  "treatment_preferences": {
    "organic_only": false
  }
}
```

**Response** (201 Created):
```json
{
  "status": "complete",
  "workflow_id": 123,
  "timestamp": "2025-10-26T14:30:00Z",
  
  "diagnosis": {
    "disease": "Fall Armyworm",
    "confidence": 0.92,
    "severity": "moderate",
    "blockchain_verified": true,
    "passport_hash": "0xabc123...",
    "verification_url": "https://polygonscan.com/tx/0x..."
  },
  
  "community_intelligence": {
    "status": "analyzed",
    "active_clusters": 2,
    "urgency_level": "high",
    "at_risk": true,
    "message": "⚠️ 2 disease clusters detected in your community."
  },
  
  "financial_analysis": {
    "no_action_loss_ksh": 10500,
    "recommended_treatment_cost_ksh": 1500,
    "expected_savings_ksh": 9000,
    "roi": 6.0
  },
  
  "recommended_actions": [
    {
      "priority": 1,
      "action": "Apply Lambda-cyhalothrin 2.5% EC",
      "cost": 1500,
      "expected_outcome": "Save 9,000 KSh",
      "timeline": "2 days to effect"
    },
    {
      "priority": 2,
      "action": "Monitor field daily for treatment effectiveness",
      "cost": 0,
      "timeline": "Next 7 days"
    },
    {
      "priority": 3,
      "action": "Report results to improve community recommendations",
      "cost": 0,
      "timeline": "After 7 days"
    }
  ],
  
  "treatment_options": [
    {
      "rank": 1,
      "treatment_name": "Lambda-cyhalothrin 2.5% EC",
      "efficacy": 0.95,
      "total_cost_ksh": 1500,
      "roi": 6.0
    }
  ],
  
  "data_assets": {
    "blockchain_passport_id": 123,
    "permit_token_id": 4567,
    "can_monetize": true,
    "use_cases": [
      "Share with buyer for premium pricing",
      "Submit to bank for loan application",
      "Export quality verification"
    ]
  },
  
  "next_steps_summary": "✅ Your diagnosis is blockchain-verified and immutable.\n\n💊 Recommended: Lambda-cyhalothrin 2.5% EC\n   • Cost: 1,500 KSh\n   • Expected savings: 9,000 KSh\n   • ROI: 6.0×\n\n🎯 Action: Purchase treatment within 24 hours for best results.\n\n🔐 Your Digital Health Passport can be shared with buyers/banks to prove crop quality."
}
```

---

## Authentication

All endpoints (except public verification) require authentication via Bearer token:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Get token via `/api/v1/auth/login` endpoint.

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_type": "validation_error"
}
```

### Common Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created (passport, handshake)
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

---

## Integration Examples

### Python Client

```python
import requests

# Login
auth_response = requests.post(
    "https://api.agropulse.com/api/v1/auth/login",
    json={"phone": "+254712345678", "password": "secret"}
)
token = auth_response.json()["access_token"]

# Complete diagnosis workflow
headers = {"Authorization": f"Bearer {token}"}
diagnosis_response = requests.post(
    "https://api.agropulse.com/api/v1/advanced/complete-diagnosis",
    headers=headers,
    json={
        "diagnosis": {
            "disease": "Fall Armyworm",
            "confidence": 0.92,
            "severity": "moderate"
        },
        "capture_data": {...},
        "field_info": {
            "field_id": 42,
            "crop_type": "maize",
            "area_hectares": 2.5
        }
    }
)

result = diagnosis_response.json()
print(f"Blockchain passport: {result['diagnosis']['passport_hash']}")
print(f"Recommended treatment: {result['treatment_options'][0]['treatment_name']}")
print(f"Expected ROI: {result['financial_analysis']['roi']}×")
```

### JavaScript/TypeScript Client

```typescript
const axios = require('axios');

// Complete workflow
const response = await axios.post(
  'https://api.agropulse.com/api/v1/advanced/complete-diagnosis',
  {
    diagnosis: {
      disease: 'Fall Armyworm',
      confidence: 0.92,
      severity: 'moderate'
    },
    field_info: {
      field_id: 42,
      crop_type: 'maize',
      area_hectares: 2.5
    }
  },
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

console.log(`ROI: ${response.data.financial_analysis.roi}×`);
```

---

## Rate Limits

- **Diagnosis endpoints**: 10 requests/minute per user
- **Verification endpoints**: 100 requests/minute (public)
- **Chama analysis**: 5 requests/hour per Chama
- **Treatment recommendations**: 20 requests/minute per user

---

## Support

For API support:
- Email: api@agropulse.com
- WhatsApp: +254-XXX-XXXXXX
- Documentation: https://docs.agropulse.com

---

## Changelog

### v1.0.0 (2025-10-26)
- Initial release of Advanced Features API
- Blockchain Digital Health Passport
- Chama Outbreak Prediction
- AI Intervention Optimization
- Complete Diagnostic Workflow integration
