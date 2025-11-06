# 🌿 AgroPulse Horticulture Quick Reference

**One-Page Guide to the Horticulture Reconfiguration**

---

## What Changed?

AgroPulse transformed from **general agriculture** → **specialized horticulture** (greenhouses, hydroponics, controlled environment agriculture)

---

## Key Terminology Changes

| Old (Agriculture) | New (Horticulture) | Context |
|-------------------|-------------------|---------|
| Farmer | Grower / Horticulturist | User roles |
| Farm | Greenhouse / Growing Facility | Infrastructure |
| Field | Growing Zone / Greenhouse | Production area |
| Soil sensors | Substrate / Hydroponic sensors | Measurement |
| Open-field crops | Greenhouse crops | Crop types |
| Weather monitoring | Climate control | Environmental |
| Irrigation | Fertigation | Water + nutrients |

---

## New Database Models

### 1. **Greenhouse** (`greenhouses` table)
```python
{
  "id": 1,
  "name": "Tomato Greenhouse #1",
  "area_sqm": 500,
  "volume_m3": 1500,
  "system_type": "hydroponics",  # or aeroponics, aquaponics, soil_based
  "structure_type": "Gothic Arch",
  "covering_material": "Twin-wall polycarbonate"
}
```

### 2. **GreenhouseEnvironment** (`greenhouse_environment` table)
```python
{
  "greenhouse_id": 1,
  "reading_timestamp": "2025-11-15T10:30:00Z",
  "temperature_celsius": 24.5,
  "humidity_percentage": 65.0,
  "co2_ppm": 800,
  "par_umol_m2_s": 450,      # PAR light intensity
  "water_ph": 6.2,
  "water_ec": 2.1,            # Electrical Conductivity
  "water_temperature_celsius": 20.0
}
```

---

## New API Endpoints

### Greenhouse Management

**Create Greenhouse**
```http
POST /api/v1/greenhouses?farm_id=123
Content-Type: application/json

{
  "name": "Tomato Greenhouse #1",
  "area_sqm": 500,
  "system_type": "hydroponics"
}
```

**List Greenhouses**
```http
GET /api/v1/greenhouses?farm_id=123
```

**Get Greenhouse**
```http
GET /api/v1/greenhouses/456
```

### Environmental Monitoring

**Record Data (from IoT sensors)**
```http
POST /api/v1/greenhouses/456/environment

{
  "reading_timestamp": "2025-11-15T10:30:00Z",
  "temperature_celsius": 24.5,
  "humidity_percentage": 65.0,
  "co2_ppm": 800,
  "par_umol_m2_s": 450,
  "water_ph": 6.2,
  "water_ec": 2.1
}
```

**Get History**
```http
GET /api/v1/greenhouses/456/environment?days=7
```

**Get Summary (Analytics)**
```http
GET /api/v1/greenhouses/456/environment/summary?days=7
```

---

## New Horticulture Sensors

| Sensor | Measures | Range | Use Case |
|--------|----------|-------|----------|
| **PAR Sensor** | Light intensity | 0-3000 μmol/m²/s | Photosynthesis monitoring |
| **CO2 Sensor** | CO2 concentration | 0-5000 ppm | CO2 supplementation |
| **pH Sensor** | Water acidity | 0-14 pH | Nutrient uptake |
| **EC Sensor** | Nutrient concentration | 0-10 mS/cm | Fertilizer strength |
| **Water Temp** | Solution temperature | 0-40°C | Root health |

---

## Optimal Growing Conditions

### Tomato (Hydroponic)
- **Temp**: Day 21-27°C, Night 16-18°C
- **Humidity**: 60-80% RH
- **CO2**: 800-1000 ppm
- **PAR**: 500-600 μmol/m²/s
- **pH**: 5.5-6.5
- **EC**: 2.0-3.5 mS/cm
- **Photoperiod**: 16-18 hours

### Lettuce (NFT)
- **Temp**: Day 18-24°C, Night 12-16°C
- **Humidity**: 50-70% RH
- **CO2**: 600-800 ppm
- **PAR**: 250-350 μmol/m²/s
- **pH**: 5.5-6.5
- **EC**: 1.2-2.0 mS/cm
- **Photoperiod**: 12-14 hours

### Basil (Hydroponic)
- **Temp**: 22-28°C
- **Humidity**: 60-75% RH
- **CO2**: 700-900 ppm
- **PAR**: 300-400 μmol/m²/s
- **pH**: 5.5-6.5
- **EC**: 1.0-1.6 mS/cm
- **Photoperiod**: 14 hours

---

## Automated Alerts

System generates alerts for:

- 🔴 **Critical**: Temp >35°C or <10°C → Immediate action!
- 🟠 **High**: Humidity >85% → Fungal disease risk
- 🟠 **High**: pH <5.0 or >7.0 → Nutrient lockout
- 🟠 **High**: EC >3.0 mS/cm → Salt burn risk
- 🟡 **Medium**: CO2 <400 ppm → Limited photosynthesis
- 🟡 **Medium**: Humidity <40% → Plant stress

---

## Crop Types (New)

### HorticulturalCropType Enum
- `FRUIT` - Tomatoes, peppers, cucumbers, strawberries
- `VEGETABLE` - Lettuce, spinach, kale, chard
- `FLOWER` - Roses, gerbera, carnations
- `ORNAMENTAL` - Orchids, ferns, tropical plants
- `HERB` - Basil, mint, cilantro, parsley
- `MUSHROOM` - Oyster, shiitake (controlled environment)

---

## Growing Systems

### GreenhouseSystemType Enum
- `HYDROPONICS` - Water-based nutrient delivery (NFT, DWC, drip)
- `AEROPONICS` - Mist-based nutrient delivery
- `AQUAPONICS` - Fish + plants symbiotic system
- `SOIL_BASED` - Traditional soil in greenhouse
- `VERTICAL_FARM` - Multi-tier stacked growing

---

## Files Created/Modified

### New Files (This Session)
1. ✨ `app/api/greenhouses.py` - 710 lines (Greenhouse API)
2. ✨ `app/schemas/greenhouse.py` - 300 lines (Pydantic schemas)
3. ✨ `HORTICULTURE_GUIDE.md` - 500+ lines (Complete guide)
4. ✨ `HORTICULTURE_RECONFIGURATION_PROGRESS.md` - 400+ lines (Progress report)

### Modified Files
1. ✅ `app/models/database.py` - Added Greenhouse & GreenhouseEnvironment models
2. ✅ `README.md` - Updated title & intro (horticulture focus)
3. ✅ `PROJECT_SUMMARY.md` - Updated project overview

---

## What's Next?

### Immediate (Phase 3)
- [ ] Update existing 50+ API endpoints for horticulture terminology
- [ ] Create hydroponic nutrient management endpoints
- [ ] Build climate automation API

### Short-Term (Phase 4-5)
- [ ] Develop greenhouse-specific services
- [ ] Retrain AI models for greenhouse crops & diseases
- [ ] Create environmental optimization ML model

### Medium-Term (Phase 6-7)
- [ ] Update ESP32 firmware for new sensors (PAR, CO2, pH, EC)
- [ ] Implement climate control automation
- [ ] Deploy time-series database (InfluxDB/TimescaleDB)

### Long-Term (Phase 8)
- [ ] Build greenhouse monitoring dashboard (real-time charts)
- [ ] Create mobile app for remote monitoring
- [ ] Pilot with commercial greenhouse growers

---

## Resources

### Documentation
- 📘 [Horticulture Guide](HORTICULTURE_GUIDE.md) - Complete 500+ line guide
- 📊 [Progress Report](HORTICULTURE_RECONFIGURATION_PROGRESS.md) - Detailed status
- 🗄️ [Database Schema](DATABASE_GUIDE.md) - All models
- 🔌 [API Reference](API_ENDPOINTS_REFERENCE.md) - All endpoints

### Code Locations
- **Models**: `app/models/database.py` (lines 907-976 for greenhouse)
- **API**: `app/api/greenhouses.py` (all greenhouse endpoints)
- **Schemas**: `app/schemas/greenhouse.py` (validation)
- **Tests**: `tests/api/test_greenhouses.py` (to be created)

---

## Key Metrics

### Technical
- ✅ 2 new database models
- ✅ 8 new API endpoints
- ✅ 10 Pydantic schemas
- ✅ 8 predefined crop profiles
- ✅ ~1,510 lines of new production code

### Business Impact (Expected)
- **10-100x** higher revenue per acre vs. field crops
- **30-50%** yield increase with climate optimization
- **90%** water savings with hydroponics
- **Year-round** production (3-6 crop cycles/year)
- **Premium pricing** for fresh, locally-grown produce

---

## Quick Start (For Developers)

### 1. Database Migration
```bash
alembic revision --autogenerate -m "Add greenhouse models"
alembic upgrade head
```

### 2. Test Greenhouse API
```bash
# Create greenhouse
curl -X POST "http://localhost:8000/api/v1/greenhouses?farm_id=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Greenhouse",
    "area_sqm": 100,
    "system_type": "hydroponics"
  }'

# Record environmental data
curl -X POST "http://localhost:8000/api/v1/greenhouses/1/environment" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reading_timestamp": "2025-11-15T10:00:00Z",
    "temperature_celsius": 24.0,
    "humidity_percentage": 65.0,
    "co2_ppm": 800,
    "par_umol_m2_s": 450,
    "water_ph": 6.2,
    "water_ec": 2.1
  }'

# Get summary
curl "http://localhost:8000/api/v1/greenhouses/1/environment/summary?days=7" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Register IoT Device
```python
# ESP32 greenhouse sensor node
device = {
    "device_name": "Greenhouse-1 Climate Sensor",
    "device_type": "par_sensor",  # or co2_sensor, water_ph_sensor, water_ec_sensor
    "manufacturer": "Custom ESP32",
    "farm_id": 1
}
```

---

## Support

**Questions?** 
- 📧 Email: support@agropulse.io
- 📚 Docs: https://docs.agropulse.io
- 💬 Slack: #horticulture-dev

---

**Status**: 🟢 **ACTIVE DEVELOPMENT** (15% complete)  
**Last Updated**: November 2025  
**Version**: 2.0.0-horticulture
