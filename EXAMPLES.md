# AgroPulse API Usage Examples

## Table of Contents
1. [Authentication](#authentication)
2. [Farm Management](#farm-management)
3. [Sensor Registration](#sensor-registration)
4. [Alert Creation (ESP32-CAM)](#alert-creation)
5. [Payment & Permit Purchase](#payment--permit-purchase)
6. [AI Diagnosis](#ai-diagnosis)
7. [Quantum Optimization](#quantum-optimization)
8. [Chatbot Assistant](#chatbot-assistant)

---

## Authentication

### Register New Farmer
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "email": "farmer@example.com",
    "full_name": "John Doe",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "phone_number": "254712345678",
    "email": "farmer@example.com",
    "full_name": "John Doe",
    "role": "farmer",
    "is_active": true,
    "created_at": "2025-10-31T10:00:00Z"
  }
}
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "password": "securepassword123"
  }'
```

---

## Farm Management

### Create Farm
```bash
curl -X POST "http://localhost:8000/api/v1/auth/farms" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sunshine Farm",
    "location": "Kiambu County",
    "latitude": -1.1743,
    "longitude": 36.8857,
    "size_acres": 5.5,
    "crop_type": "Maize"
  }'
```

### Get User Farms
```bash
curl -X GET "http://localhost:8000/api/v1/auth/farms" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Sensor Registration

### Register ESP32-CAM Sensor
```bash
curl -X POST "http://localhost:8000/api/v1/sensors?farm_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32-001",
    "sensor_type": "esp32_cam",
    "name": "North Field Sensor",
    "location": "Zone A",
    "latitude": -1.1743,
    "longitude": 36.8857
  }'
```

Response includes API key for the sensor:
```json
{
  "id": 1,
  "farm_id": 1,
  "device_id": "ESP32-001",
  "sensor_type": "esp32_cam",
  "name": "North Field Sensor",
  "status": "active",
  "api_key": "agro_abcdef123456...",
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

## Alert Creation

### Create Alert (from ESP32-CAM)
```bash
curl -X POST "http://localhost:8000/api/v1/sensors/alerts" \
  -H "X-API-Key: agro_abcdef123456..." \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": 1,
    "zone_id": 1,
    "alert_type": "yellow_spot_detected",
    "severity": "medium",
    "description": "Unusual yellowing detected in Zone A",
    "confidence_score": 0.75,
    "latitude": -1.1743,
    "longitude": 36.8857
  }'
```

### Get Farm Alerts
```bash
curl -X GET "http://localhost:8000/api/v1/sensors/alerts?farm_id=1&status=pending" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Acknowledge Alert
```bash
curl -X PATCH "http://localhost:8000/api/v1/sensors/alerts/1/acknowledge" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Payment & Permit Purchase

### Initiate M-Pesa Payment (50 KSh for Diagnosis)
```bash
curl -X POST "http://localhost:8000/api/v1/payments/initiate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50,
    "payment_method": "mpesa",
    "phone_number": "254712345678",
    "description": "AI Crop Diagnosis Permit"
  }'
```

Response:
```json
{
  "id": 1,
  "amount": 50,
  "currency": "KES",
  "payment_method": "mpesa",
  "status": "processing",
  "created_at": "2025-10-31T10:00:00Z"
}
```

**Note:** After payment is confirmed via M-Pesa, a blockchain permit is automatically minted and sent to your account.

### Get My Permits
```bash
curl -X GET "http://localhost:8000/api/v1/payments/permits" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
[
  {
    "id": 1,
    "permit_token_id": "0x1a2b3c...",
    "transaction_hash": "0xabc123...",
    "status": "minted",
    "permit_type": "diagnosis",
    "is_used": false,
    "created_at": "2025-10-31T10:05:00Z"
  }
]
```

---

## AI Diagnosis

### Upload Images
```bash
# Upload first image
curl -X POST "http://localhost:8000/api/v1/diagnoses/upload-image" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@leaf_image_1.jpg"

# Returns: {"success": true, "image_url": "https://..."}
```

### Submit Diagnosis Request
```bash
curl -X POST "http://localhost:8000/api/v1/diagnoses" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": 1,
    "permit_token_id": "0x1a2b3c...",
    "image_urls": [
      "https://s3.amazonaws.com/.../image1.jpg",
      "https://s3.amazonaws.com/.../image2.jpg",
      "https://s3.amazonaws.com/.../image3.jpg"
    ],
    "metadata": {
      "camera_model": "iPhone 13",
      "timestamp": "2025-10-31T10:00:00Z",
      "weather": "sunny"
    },
    "triage_diagnosis": "Fall Armyworm",
    "triage_confidence": 0.85
  }'
```

Response:
```json
{
  "id": 1,
  "status": "processing",
  "created_at": "2025-10-31T10:10:00Z"
}
```

### Get Diagnosis Results
```bash
curl -X GET "http://localhost:8000/api/v1/diagnoses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "id": 1,
  "status": "completed",
  "primary_diagnosis": "Fall Armyworm (Spodoptera frugiperda)",
  "category": "pest",
  "confidence_score": 0.92,
  "alternative_diagnoses": [
    {
      "diagnosis": "Leaf Blight",
      "confidence": 0.05,
      "category": "fungal"
    }
  ],
  "affected_area_percentage": 35.5,
  "severity_level": "moderate",
  "treatment_recommendations": [
    {
      "product_name": "Lambda-cyhalothrin 5% EC",
      "category": "pesticide",
      "dosage": "20ml per 20L water",
      "application_method": "Foliar spray",
      "estimated_cost_ksh": 450,
      "safety_notes": "Wear protective gear. Do not spray during rain."
    }
  ],
  "preventive_measures": [
    "Plant early maturing varieties",
    "Maintain field hygiene",
    "Use pheromone traps for monitoring"
  ],
  "estimated_yield_impact": -15.0,
  "processing_time_seconds": 4.2,
  "completed_at": "2025-10-31T10:10:15Z"
}
```

---

## Quantum Optimization

### Request Optimal Scouting Plan
```bash
curl -X POST "http://localhost:8000/api/v1/optimization/scouting-plan" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": 1,
    "available_budget_ksh": 500,
    "available_time_hours": 2,
    "alert_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
  }'
```

Response:
```json
{
  "id": 1,
  "status": "completed",
  "optimal_path": [3, 7, 1, 14, 9, 5, 11, 2, 15, 4],
  "estimated_cost": 500,
  "estimated_time_hours": 1.75,
  "risk_coverage_percentage": 92.5,
  "priority_alerts": [
    {
      "alert_id": 3,
      "zone_name": "Zone C",
      "alert_type": "severe_wilting",
      "severity": "high",
      "risk_score": 3.8,
      "estimated_cost_ksh": 50,
      "estimated_time_minutes": 30
    }
  ],
  "skipped_alerts": [6, 8, 10, 12, 13],
  "reasoning": "Quantum optimization selected 10 highest priority alerts that cover 92.5% of farm risk within your 500 KSh budget and 2-hour time constraint.",
  "quantum_backend": "aws_braket",
  "processing_time_seconds": 12.5,
  "completed_at": "2025-10-31T10:15:00Z"
}
```

---

## Chatbot Assistant

### Ask Chatbot for Advice
```bash
curl -X POST "http://localhost:8000/api/v1/optimization/chatbot" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have 15 alerts but only 500 KSh. What should I do?",
    "farm_id": 1
  }'
```

Response:
```json
{
  "response": "You have 15 pending alerts. With your 500 KSh budget, I recommend creating an optimal scouting plan. I can use quantum computing to find the mathematically perfect path that covers the maximum risk. Would you like me to create this plan?",
  "suggested_actions": [
    "Create quantum-optimized scouting plan",
    "View all alerts",
    "Purchase more permits"
  ]
}
```

---

## Python SDK Example

```python
import requests

class AgroPulseClient:
    def __init__(self, api_url, access_token):
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_alerts(self, farm_id):
        response = requests.get(
            f"{self.api_url}/api/v1/sensors/alerts",
            params={"farm_id": farm_id},
            headers=self.headers
        )
        return response.json()
    
    def purchase_permit(self, phone_number):
        response = requests.post(
            f"{self.api_url}/api/v1/payments/initiate",
            json={
                "amount": 50,
                "payment_method": "mpesa",
                "phone_number": phone_number,
                "description": "AI Diagnosis Permit"
            },
            headers=self.headers
        )
        return response.json()
    
    def request_diagnosis(self, permit_token_id, image_urls):
        response = requests.post(
            f"{self.api_url}/api/v1/diagnoses",
            json={
                "permit_token_id": permit_token_id,
                "image_urls": image_urls
            },
            headers=self.headers
        )
        return response.json()
    
    def get_scouting_plan(self, farm_id, budget, time_hours, alert_ids):
        response = requests.post(
            f"{self.api_url}/api/v1/optimization/scouting-plan",
            json={
                "farm_id": farm_id,
                "available_budget_ksh": budget,
                "available_time_hours": time_hours,
                "alert_ids": alert_ids
            },
            headers=self.headers
        )
        return response.json()

# Usage
client = AgroPulseClient("http://localhost:8000", "YOUR_ACCESS_TOKEN")
alerts = client.get_alerts(farm_id=1)
print(f"You have {len(alerts)} alerts")

# Request optimal plan
plan = client.get_scouting_plan(
    farm_id=1,
    budget=500,
    time_hours=2,
    alert_ids=[a['id'] for a in alerts]
)
print(f"Optimal plan covers {plan['risk_coverage_percentage']}% of risk")
```

---

## Mobile App Integration (Flutter/React Native)

```dart
// Flutter example
class AgroPulseService {
  final String baseUrl = 'https://api.agropulse.com';
  final String accessToken;
  
  AgroPulseService(this.accessToken);
  
  Future<List<Alert>> getAlerts(int farmId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/sensors/alerts?farm_id=$farmId'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
    
    if (response.statusCode == 200) {
      final List data = json.decode(response.body);
      return data.map((e) => Alert.fromJson(e)).toList();
    }
    throw Exception('Failed to load alerts');
  }
  
  Future<void> initiateMpesaPayment(String phone, double amount) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/payments/initiate'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'amount': amount,
        'payment_method': 'mpesa',
        'phone_number': phone,
      }),
    );
    
    // Handle M-Pesa STK push...
  }
}
```

---

## Webhook Testing

### Simulate Flutterwave Webhook
```bash
curl -X POST "http://localhost:8000/api/v1/payments/webhook/flutterwave" \
  -H "Content-Type: application/json" \
  -H "verif-hash: YOUR_SECRET_HASH" \
  -d '{
    "txRef": "AGRO-ABC123",
    "status": "successful",
    "amount": 50,
    "currency": "KES",
    "id": "12345",
    "flwRef": "FLW-MOCK-REF"
  }'
```

---

For more examples, visit: https://docs.agropulse.com
