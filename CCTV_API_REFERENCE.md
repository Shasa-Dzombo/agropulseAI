# 📡 CCTV API Quick Reference

Quick reference for integrating with AgroPulse CCTV endpoints.

---

## Base URL
```
Production: https://api.agropulse.com
Development: http://localhost:8000
```

---

## Authentication

### User Endpoints (JWT)
```bash
Authorization: Bearer <jwt_token>
```

Get token from `/api/v1/auth/login`

### Device Endpoints (API Key)
```bash
X-API-Key: <sensor_api_key>
```

Get API key from `/api/v1/auth/register` or user profile

---

## Endpoints

### 1. Register CCTV Device
**For**: Farmers registering new CCTV hardware

```http
POST /api/v1/cctv
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "farm_id": 1,
  "zone_id": 2,
  "device_serial": "ESP32CAM-001",
  "latitude": -1.286389,
  "longitude": 36.817223,
  "has_nir_led": true,
  "has_red_led": true,
  "nir_led_wavelength": 850,
  "red_led_wavelength": 660,
  "has_macro_lens": false,
  "has_pir_sensor": true,
  "has_environmental_sensor": true
}
```

**Response**:
```json
{
  "id": 1,
  "farm_id": 1,
  "zone_id": 2,
  "device_serial": "ESP32CAM-001",
  "latitude": -1.286389,
  "longitude": 36.817223,
  "has_nir_led": true,
  "has_red_led": true,
  "is_calibrated": false,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 2. Submit Capture
**For**: ESP32-CAM devices sending image captures

```http
POST /api/v1/cctv/{cctv_id}/capture
X-API-Key: <sensor_api_key>
Content-Type: application/json

{
  "image_url": "https://s3.amazonaws.com/agropulse/cctv_1_20240115_103000.jpg",
  "nir_led_active": true,
  "red_led_active": true,
  "target_brightness_nir": 128.5,
  "target_brightness_red": 95.3,
  "ambient_temperature": 25.3,
  "ambient_humidity": 65.2,
  "ambient_light": 1013.25,
  "triage_result": "mild_stress",
  "triage_confidence": 0.75
}
```

**Response**:
```json
{
  "id": 123,
  "cctv_id": 1,
  "image_url": "https://s3...",
  "nir_led_active": true,
  "red_led_active": true,
  "target_brightness_nir": 128.5,
  "target_brightness_red": 95.3,
  "ambient_temperature": 25.3,
  "ambient_humidity": 65.2,
  "triage_result": "mild_stress",
  "triage_confidence": 0.75,
  "created_at": "2024-01-15T10:30:00Z",
  "health_analysis": {
    "health_score": 0.68,
    "ndvi_proxy": 0.52,
    "status": "mild_stress",
    "alert_generated": true
  }
}
```

---

### 3. Calibrate CCTV
**For**: ESP32-CAM auto-calibration with reference target

```http
POST /api/v1/cctv/{cctv_id}/calibrate
X-API-Key: <sensor_api_key>
Content-Type: application/json

{
  "target_type": "gray_card",
  "target_reflectance_known": 0.50,
  "target_brightness_nir": 130.2,
  "target_brightness_red": 125.8,
  "ambient_temperature": 24.5,
  "ambient_humidity": 68.0,
  "ambient_light": 1012.50
}
```

**Response**:
```json
{
  "id": 45,
  "cctv_id": 1,
  "target_type": "gray_card",
  "target_reflectance_known": 0.50,
  "target_brightness_nir": 130.2,
  "target_brightness_red": 125.8,
  "correction_factor_nir": 0.98,
  "correction_factor_red": 1.02,
  "calibration_quality": 0.92,
  "is_active": true,
  "calibrated_at": "2024-01-15T10:00:00Z"
}
```

---

### 4. Get Health Readings
**For**: Farmers viewing historical health data

```http
GET /api/v1/cctv/{cctv_id}/health?limit=50
Authorization: Bearer <jwt_token>
```

**Response**:
```json
[
  {
    "id": 789,
    "cctv_id": 1,
    "capture_id": 123,
    "farm_id": 1,
    "zone_id": 2,
    "normalized_nir": 0.7854,
    "normalized_red": 0.3421,
    "ndvi_proxy": 0.5234,
    "health_score": 0.68,
    "expected_health": 0.75,
    "health_status": "mild_stress",
    "crop_type": "maize",
    "growth_stage": "vegetative",
    "stress_detected": true,
    "stress_level": "low",
    "stress_type": "early_stress",
    "alert_generated": true,
    "alert_id": 456,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 5. Initiate Handshake
**For**: System automatically creating handshake after alert

```http
POST /api/v1/cctv/handshake/alert
X-API-Key: <sensor_api_key>
Content-Type: application/json

{
  "alert_id": 456,
  "cctv_id": 1
}
```

**Response**:
```json
{
  "id": 1,
  "alert_id": 456,
  "cctv_id": 1,
  "farmer_id": 10,
  "status": "alert_sent",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### 6. Acknowledge Alert
**For**: Farmer acknowledging they saw the alert

```http
POST /api/v1/cctv/handshake/{handshake_id}/acknowledge
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "message": "Alert acknowledged",
  "status": "acknowledged"
}
```

---

### 7. Mark Arrival
**For**: Farmer arrived at CCTV location (GPS verified)

```http
POST /api/v1/cctv/handshake/{handshake_id}/arrived
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "latitude": -1.286389,
  "longitude": 36.817223
}
```

**Response**:
```json
{
  "message": "Arrival confirmed",
  "distance_meters": 12.5,
  "status": "farmer_arrived"
}
```

**Error if too far**:
```json
{
  "detail": "Too far from CCTV location. Distance: 65.3m"
}
```

---

### 8. Link Diagnosis
**For**: Linking phone diagnosis to CCTV alert

```http
POST /api/v1/cctv/handshake/{handshake_id}/diagnose
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "diagnosis_id": 789
}
```

**Response**:
```json
{
  "message": "Diagnosis completed",
  "status": "diagnosis_completed"
}
```

---

### 9. Update CCTV Config
**For**: Farmers adjusting device settings

```http
PATCH /api/v1/cctv/{cctv_id}/config
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "capture_interval_minutes": 60,
  "battery_save_mode": true,
  "pir_wake_enabled": true,
  "alert_threshold": 0.60
}
```

**Response**: Updated CCTV object

---

### 10. List Farm CCTVs
**For**: Farmers viewing all their CCTV devices

```http
GET /api/v1/cctv/farm/{farm_id}
Authorization: Bearer <jwt_token>
```

**Response**:
```json
[
  {
    "id": 1,
    "device_serial": "ESP32CAM-001",
    "latitude": -1.286389,
    "longitude": 36.817223,
    "is_calibrated": true,
    "last_calibration": "2024-01-15T10:00:00Z",
    "is_active": true,
    "battery_level": 85,
    "last_seen": "2024-01-15T10:30:00Z"
  }
]
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid token/API key) |
| 403 | Forbidden (access denied) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Error Responses

```json
{
  "detail": "Error message here"
}
```

---

## Handshake Status Flow

```
alert_sent → acknowledged → farmer_arrived → diagnosis_completed
```

| Status | Description |
|--------|-------------|
| `alert_sent` | CCTV alert sent to farmer |
| `acknowledged` | Farmer saw and acknowledged alert |
| `farmer_arrived` | Farmer reached location (GPS verified) |
| `diagnosis_completed` | Phone diagnosis linked |

---

## Health Status Values

| Status | Health Score | Description |
|--------|--------------|-------------|
| `healthy` | 0.75-1.00 | Crop is healthy |
| `mild_stress` | 0.60-0.75 | Slight stress detected |
| `moderate_stress` | 0.40-0.60 | Moderate stress, inspect soon |
| `severe_stress` | 0.00-0.40 | Severe stress, immediate action |
| `check_calibration` | >1.00 | Possible calibration error |

---

## Stress Types

| Type | Likely Cause |
|------|--------------|
| `early_stress` | Early detection, cause unknown |
| `water_or_nutrient` | Water stress or nutrient deficiency |
| `severe_stress` | Disease or severe water stress |

---

## ESP32 Integration Example

```cpp
// ESP32-CAM code snippet
void sendCapture() {
  HTTPClient http;
  String url = API_URL + "/" + String(CCTV_ID) + "/capture";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  
  String payload = "{";
  payload += "\"image_url\":\"" + image_url + "\",";
  payload += "\"nir_led_active\":true,";
  payload += "\"red_led_active\":true,";
  payload += "\"target_brightness_nir\":" + String(nir_brightness) + ",";
  payload += "\"target_brightness_red\":" + String(red_brightness) + ",";
  payload += "\"ambient_temperature\":" + String(temperature) + ",";
  payload += "\"ambient_humidity\":" + String(humidity) + ",";
  payload += "\"triage_result\":\"" + triage + "\",";
  payload += "\"triage_confidence\":" + String(confidence);
  payload += "}";
  
  int response_code = http.POST(payload);
  
  if (response_code == 200 || response_code == 201) {
    Serial.println("✅ Capture sent successfully");
    String response = http.getString();
    Serial.println(response);
  } else {
    Serial.printf("❌ Error: %d\n", response_code);
  }
  
  http.end();
}
```

---

## Mobile App Integration Example

```javascript
// React Native example
async function acknowledgeAlert(handshakeId) {
  const response = await fetch(
    `${API_URL}/api/v1/cctv/handshake/${handshakeId}/acknowledge`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
      }
    }
  );
  
  const data = await response.json();
  
  if (response.ok) {
    console.log('Alert acknowledged:', data.status);
  }
}

async function markArrival(handshakeId, latitude, longitude) {
  const response = await fetch(
    `${API_URL}/api/v1/cctv/handshake/${handshakeId}/arrived`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ latitude, longitude })
    }
  );
  
  const data = await response.json();
  
  if (response.ok) {
    console.log(`Arrival confirmed. Distance: ${data.distance_meters}m`);
  } else {
    console.error('Too far from CCTV:', data.detail);
  }
}
```

---

## Testing with cURL

### Register Device
```bash
curl -X POST http://localhost:8000/api/v1/cctv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": 1,
    "device_serial": "ESP32CAM-TEST-001",
    "latitude": -1.286389,
    "longitude": 36.817223,
    "has_nir_led": true,
    "has_red_led": true
  }'
```

### Submit Capture
```bash
curl -X POST http://localhost:8000/api/v1/cctv/1/capture \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "nir_led_active": true,
    "red_led_active": true,
    "target_brightness_nir": 128.5,
    "target_brightness_red": 95.3,
    "triage_result": "mild_stress",
    "triage_confidence": 0.75
  }'
```

### Get Health Readings
```bash
curl -X GET http://localhost:8000/api/v1/cctv/1/health?limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Capture submission | 1 per 5 minutes per device |
| Calibration | 1 per hour per device |
| Health readings | 100 per hour per user |
| Configuration updates | 10 per hour per device |

---

## Support

- **API Docs**: http://localhost:8000/docs
- **Documentation**: See `CCTV_INTEGRATION.md`
- **Issues**: Contact support@agropulse.com

---

*Last updated: January 2024*
