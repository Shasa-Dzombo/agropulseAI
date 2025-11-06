# 🌿 AgroPulse Horticulture Implementation Guide

**Complete Guide to Greenhouse & Controlled Environment Horticulture**

---

## Table of Contents

1. [Overview](#overview)
2. [Horticulture vs. Traditional Agriculture](#horticulture-vs-traditional-agriculture)
3. [Greenhouse Management](#greenhouse-management)
4. [Environmental Control Systems](#environmental-control-systems)
5. [Hydroponic & Soilless Systems](#hydroponic--soilless-systems)
6. [Crop-Specific Protocols](#crop-specific-protocols)
7. [Sensor Integration](#sensor-integration)
8. [Climate Automation](#climate-automation)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)

---

## Overview

AgroPulse has been **completely reconfigured from general agriculture to specialized horticulture**, focusing on:

### 🎯 **Target Applications**
- **Commercial Greenhouses**: Glass & polycarbonate structures for year-round production
- **Hydroponic Farms**: NFT, DWC, drip systems for soil-less cultivation
- **Vertical Farms**: Multi-tier indoor growing with LED lighting
- **Nurseries**: Propagation & ornamental plant production
- **Specialty Crops**: Herbs, microgreens, edible flowers, medicinal plants

### 🌱 **Primary Crops Supported**
1. **Vegetables**: Tomatoes, peppers, cucumbers, lettuce, spinach, kale
2. **Herbs**: Basil, cilantro, parsley, mint, oregano, thyme
3. **Ornamentals**: Orchids, roses, gerbera, chrysanthemum
4. **Berries**: Strawberries, blueberries (substrate culture)
5. **Microgreens**: Arugula, radish, pea shoots, sunflower

### 💡 **Key Innovations for Horticulture**
- **Precision Climate Control**: ±0.5°C temperature, ±5% humidity accuracy
- **Real-Time Nutrient Monitoring**: pH ±0.1, EC ±0.05 mS/cm
- **PAR Light Optimization**: Measure & control photosynthetically active radiation
- **CO2 Supplementation**: Automated dosing for enhanced photosynthesis
- **Fertigation Automation**: Scheduled nutrient delivery with EC/pH correction
- **Disease Prevention**: Environmental alerts prevent powdery mildew, Botrytis

---

## Horticulture vs. Traditional Agriculture

### Key Differences

| Aspect | Traditional Agriculture | Commercial Horticulture |
|--------|------------------------|-------------------------|
| **Environment** | Open fields, rain-fed | Greenhouses, controlled climate |
| **Crop Types** | Grains, legumes, staples | Vegetables, fruits, flowers, herbs |
| **Growing Media** | Soil | Soil-less (hydroponics, coco coir, perlite) |
| **Water Use** | Flood/furrow irrigation | Precision drip, NFT, aeroponics |
| **Labor Intensity** | Seasonal, mechanized | Year-round, specialized |
| **Value per Acre** | $500-$2,000 | $50,000-$500,000 |
| **Crop Cycles** | 1-2 per year | 3-6 per year (continuous) |
| **Technology** | Tractors, basic sensors | Climate computers, automated fertigation |
| **Market** | Commodity bulk crops | Fresh produce, premium ornamentals |
| **Inputs** | Fertilizers, pesticides | Nutrients, biological controls, CO2 |

### Why Horticulture?

**Economic Advantages:**
- **10-100x higher revenue per acre** than field crops
- **Year-round production** (no seasonal limitations)
- **Premium pricing** for fresh, locally-grown produce
- **Reduced water use** (90% savings with hydroponics)
- **Higher quality** (controlled environment = consistent crops)

**Technological Requirements:**
- **Environmental sensors**: Temperature, humidity, CO2, PAR light
- **Nutrient monitoring**: pH, EC, dissolved oxygen
- **Automated controls**: HVAC, irrigation, lighting, ventilation
- **Data analytics**: Real-time monitoring, predictive models
- **Supply chain**: Cold storage, rapid distribution

---

## Greenhouse Management

### Greenhouse Model

AgroPulse tracks comprehensive greenhouse data:

```python
class Greenhouse(Base):
    """Model for managing greenhouses."""
    id: int
    uuid: UUID
    farm_id: int
    name: str
    description: str
    
    # Physical Characteristics
    area_sqm: float  # Area in square meters
    volume_m3: float  # Volume for climate calculations
    structure_type: str  # Dome, A-Frame, Gothic Arch, Quonset
    covering_material: str  # Glass, polycarbonate, polyethylene
    
    # System Type
    system_type: GreenhouseSystemType  # Hydroponics, aeroponics, etc.
    
    # Location
    latitude: float
    longitude: float
    altitude: float
```

### System Types

#### 1. **Hydroponics** (Water-Based)
- **NFT (Nutrient Film Technique)**: Thin film of nutrient solution flowing over roots
- **DWC (Deep Water Culture)**: Roots suspended in oxygenated nutrient solution
- **Drip Systems**: Controlled nutrient delivery to substrate (coco coir, rockwool)

**Advantages:**
- 90% less water than soil
- Faster growth (30-50%)
- Higher yields (3-10x per m²)
- No soil-borne diseases

**Challenges:**
- Requires precise pH & EC control
- Power dependency (pumps, aeration)
- Initial setup cost ($50-$200/m²)

#### 2. **Aeroponics** (Mist-Based)
- Roots suspended in air, misted with nutrients every 3-5 minutes
- **Highest efficiency**: 95% less water, 60% faster growth
- Used for: Leafy greens, herbs, strawberries

#### 3. **Aquaponics** (Fish + Plants)
- Combines fish farming with plant cultivation
- Fish waste provides nutrients for plants
- Plants filter water for fish

#### 4. **Soil-Based** (Traditional)
- Greenhouse with soil beds or pots
- Easier management, lower tech requirements
- Used for: Ornamentals, specialty crops

#### 5. **Vertical Farms** (Multi-Tier)
- Stacked growing layers with LED lighting
- 10-20x more productive per m² floor space
- Ideal for: Leafy greens, microgreens, herbs

---

## Environmental Control Systems

### Critical Parameters

AgroPulse monitors and controls:

#### 1. **Temperature** 🌡️
- **Day**: 18-28°C (varies by crop)
- **Night**: 16-22°C (10-15°C cooler than day)
- **Control Methods**: Ventilation, evaporative cooling, heating

**Alerts:**
- 🔴 **Critical**: >35°C or <10°C (crop damage)
- 🟠 **High**: >30°C or <15°C (stress)
- 🟢 **Normal**: 18-28°C

#### 2. **Humidity** 💧
- **Optimal**: 50-80% RH (crop-dependent)
- **High Humidity** (>85%): Fungal diseases (powdery mildew, Botrytis)
- **Low Humidity** (<40%): Transpiration stress, tip burn

**Control Methods:**
- Ventilation (reduce humidity)
- Fog/misting systems (increase humidity)
- Dehumidifiers (high-tech greenhouses)

#### 3. **CO2 Enrichment** 🌬️
- **Ambient**: ~400 ppm
- **Optimal**: 800-1200 ppm (photosynthesis enhancement)
- **Yield Increase**: 20-40% with CO2 supplementation

**Sources:**
- CO2 burners (propane/natural gas)
- Bottled CO2 (more precise)
- Composting (organic method)

#### 4. **Light (PAR)** ☀️
- **PAR**: Photosynthetically Active Radiation (400-700nm wavelength)
- **Units**: μmol/m²/s (micromoles per square meter per second)

**Crop Requirements:**
- **High Light**: Tomatoes, peppers, roses (500-800 μmol/m²/s)
- **Medium Light**: Cucumbers, herbs (300-500 μmol/m²/s)
- **Low Light**: Lettuce, leafy greens, orchids (200-300 μmol/m²/s)

**Supplemental Lighting:**
- LED grow lights (energy-efficient, full spectrum)
- HPS (High-Pressure Sodium) - traditional, high heat
- Metal halide - vegetative growth

#### 5. **Photoperiod** 🕐
- **Day Length**: Critical for flowering/fruiting
- **Long Day Plants**: >14 hours (lettuce, spinach)
- **Short Day Plants**: <12 hours (strawberries, chrysanthemum)
- **Day-Neutral**: Tomatoes, peppers (12-18 hours)

---

## Hydroponic & Soilless Systems

### Nutrient Solution Management

#### pH Control
- **Optimal Range**: 5.5-6.5 (crop-specific)
- **Too Low** (<5.0): Manganese/iron toxicity
- **Too High** (>7.0): Iron/phosphorus deficiency

**pH Adjustment:**
- **Lower pH**: Phosphoric acid, nitric acid
- **Raise pH**: Potassium hydroxide, potassium carbonate

#### EC (Electrical Conductivity)
- **Measures**: Total dissolved salts (nutrient concentration)
- **Units**: mS/cm (millisiemens/centimeter) or dS/m
- **Optimal Range**: 1.0-3.5 mS/cm (crop & growth stage dependent)

**EC by Crop:**
- **Lettuce/Herbs**: 1.2-2.0 mS/cm (low feeders)
- **Tomatoes/Peppers**: 2.0-3.5 mS/cm (heavy feeders)
- **Strawberries**: 1.0-1.8 mS/cm (sensitive)

**EC Management:**
- **Too Low**: Add concentrated nutrient solution
- **Too High**: Dilute with fresh water
- **Daily Monitoring**: Prevents nutrient imbalances

#### Water Temperature
- **Optimal**: 18-22°C
- **Too Warm** (>28°C): Low dissolved oxygen, root diseases
- **Too Cold** (<15°C): Slow nutrient uptake

### Environmental Data Model

```python
class GreenhouseEnvironment(Base):
    """Stores environmental data from within a greenhouse."""
    id: int
    greenhouse_id: int
    reading_timestamp: datetime
    
    # Climate Parameters
    temperature_celsius: float
    humidity_percentage: float
    co2_ppm: float
    par_umol_m2_s: float  # PAR light intensity
    light_duration_hours: float
    
    # Hydroponic Parameters
    water_ph: float
    water_ec: float  # Electrical Conductivity
    water_temperature_celsius: float
```

---

## Crop-Specific Protocols

### Tomato (Solanum lycopersicum)

**System**: Hydroponics (drip to rockwool/coco), Dutch bucket
**Cycle**: 8-10 months (indeterminate varieties)
**Yield**: 50-80 kg/m²/year

| Parameter | Range |
|-----------|-------|
| Temperature (day) | 21-27°C |
| Temperature (night) | 16-18°C |
| Humidity | 60-80% RH |
| CO2 | 800-1000 ppm |
| PAR | 500-600 μmol/m²/s |
| Photoperiod | 16-18 hours |
| pH | 5.5-6.5 |
| EC | 2.0-3.5 mS/cm |

**Critical Stages:**
- **Vegetative**: EC 2.0-2.5, high nitrogen
- **Flowering**: EC 2.5-3.0, reduce nitrogen, increase potassium
- **Fruiting**: EC 3.0-3.5, high potassium for fruit quality

### Lettuce (Lactuca sativa)

**System**: NFT, DWC, raft systems
**Cycle**: 4-6 weeks (harvest to harvest)
**Yield**: 20-25 kg/m²/cycle (80-100 kg/m²/year)

| Parameter | Range |
|-----------|-------|
| Temperature (day) | 18-24°C |
| Temperature (night) | 12-16°C |
| Humidity | 50-70% RH |
| CO2 | 600-800 ppm |
| PAR | 250-350 μmol/m²/s |
| Photoperiod | 12-14 hours |
| pH | 5.5-6.5 |
| EC | 1.2-2.0 mS/cm |

**Varieties:**
- **Butterhead**: Most popular for hydroponics
- **Romaine**: Higher light requirements
- **Oakleaf**: Heat-tolerant

### Basil (Ocimum basilicum)

**System**: NFT, DWC, drip
**Cycle**: 4-6 weeks (multiple harvests)
**Yield**: 2-3 kg/m²/month

| Parameter | Range |
|-----------|-------|
| Temperature | 22-28°C |
| Humidity | 60-75% RH |
| CO2 | 700-900 ppm |
| PAR | 300-400 μmol/m²/s |
| pH | 5.5-6.5 |
| EC | 1.0-1.6 mS/cm |

**Tips:**
- Prevent flowering (pinch tips) for leaf production
- High humidity reduces essential oil concentration
- Harvest in morning for best flavor

---

## Sensor Integration

### IoT Devices for Horticulture

AgroPulse supports specialized greenhouse sensors:

```python
class DeviceType(enum.Enum):
    """Types of IoT devices."""
    # Standard Sensors
    WEATHER_STATION = "weather_station"
    SOIL_SENSOR = "soil_sensor"
    CAMERA = "camera"
    
    # Horticulture-Specific Sensors
    PAR_SENSOR = "par_sensor"  # Photosynthetically Active Radiation
    CO2_SENSOR = "co2_sensor"
    WATER_PH_SENSOR = "water_ph_sensor"
    WATER_EC_SENSOR = "water_ec_sensor"
    
    # Actuators/Controllers
    LIGHT_CONTROLLER = "light_controller"
    PUMP_CONTROLLER = "pump_controller"
    VENT_CONTROLLER = "vent_controller"
```

### Sensor Specifications

#### PAR Sensor (Quantum Sensor)
- **Measures**: 400-700nm wavelength light
- **Range**: 0-3000 μmol/m²/s
- **Accuracy**: ±5%
- **Cost**: $150-$400 (professional) or $30-$80 (DIY with photodiode)
- **Placement**: Canopy level, multiple points per greenhouse

**DIY Option**: TSL2591 light sensor + calibration ($12)

#### CO2 Sensor
- **Technology**: NDIR (Non-Dispersive Infrared)
- **Range**: 0-5000 ppm
- **Accuracy**: ±50 ppm
- **Cost**: $80-$300 (Senseair S8, MH-Z19B)
- **Lifespan**: 5-10 years

#### pH Sensor
- **Type**: Glass electrode or ISFET (solid-state)
- **Range**: 0-14 pH
- **Accuracy**: ±0.1 pH
- **Cost**: $30-$150 (requires regular calibration)
- **Maintenance**: Clean weekly, calibrate bi-weekly

#### EC Sensor
- **Type**: Conductivity probe
- **Range**: 0-10 mS/cm
- **Accuracy**: ±2%
- **Cost**: $40-$200
- **Temperature Compensation**: Essential (EC changes with temperature)

---

## Climate Automation

### Automated Control Strategies

#### 1. **Ventilation Control**
```python
def control_ventilation(temp, humidity, co2):
    if temp > 28 or humidity > 85:
        open_vents(100%)  # Full cooling
    elif temp > 25 or humidity > 75:
        open_vents(60%)   # Moderate cooling
    elif co2 < 400:
        open_vents(30%)   # Fresh air intake
    else:
        close_vents()     # Conserve CO2 & heat
```

#### 2. **CO2 Dosing**
```python
def control_co2(co2_ppm, light_intensity):
    if light_intensity > 300 and co2_ppm < 800:
        # Only dose CO2 during photosynthesis (light)
        target_co2 = 1000  # ppm
        dose_rate = (target_co2 - co2_ppm) * greenhouse_volume * 0.001
        activate_co2_generator(dose_rate)
```

#### 3. **Fertigation Automation**
```python
def control_fertigation(ec, ph, time_since_last):
    if time_since_last > irrigation_interval:
        if ec < target_ec - 0.2:
            # EC too low, add nutrients
            inject_nutrients(volume=calculate_dose(ec, target_ec))
        elif ec > target_ec + 0.2:
            # EC too high, dilute
            flush_with_fresh_water()
        
        if ph < target_ph - 0.2:
            inject_ph_up()
        elif ph > target_ph + 0.2:
            inject_ph_down()
        
        run_irrigation_cycle()
```

---

## API Reference

### Greenhouse Endpoints

#### Create Greenhouse
```http
POST /api/v1/greenhouses?farm_id=123
Content-Type: application/json

{
  "name": "Tomato Greenhouse #1",
  "area_sqm": 500,
  "system_type": "hydroponics",
  "structure_type": "Gothic Arch",
  "covering_material": "Twin-wall polycarbonate"
}
```

#### Record Environmental Data
```http
POST /api/v1/greenhouses/456/environment
Content-Type: application/json

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

#### Get Environmental Summary
```http
GET /api/v1/greenhouses/456/environment/summary?days=7
```

**Response:**
```json
{
  "statistics": {
    "temperature": {
      "average": 24.3,
      "min": 18.5,
      "max": 29.1,
      "in_range": true
    },
    "humidity": {"average": 68.5, "in_range": true},
    "co2": {"average": 850, "in_range": true},
    "water_ph": {"average": 6.1, "in_range": true},
    "water_ec": {"average": 2.3, "in_range": true}
  },
  "recommendations": [
    "Temperature occasionally exceeds 28°C. Consider increasing ventilation."
  ],
  "overall_health": "good"
}
```

---

## Best Practices

### 1. **Environmental Monitoring**
- Record data every 5-15 minutes
- Store historical data for trend analysis
- Set up real-time alerts for critical parameters
- Use multiple sensors per greenhouse (avoid single points of failure)

### 2. **Nutrient Management**
- Check pH & EC daily (2x per day for critical crops)
- Replace nutrient solution every 2-4 weeks
- Monitor individual nutrient levels monthly (lab testing)
- Adjust recipes based on crop growth stage

### 3. **Disease Prevention**
- Maintain optimal humidity (<80% RH at night)
- Ensure good air circulation (fans, ventilation)
- Scout for pests/diseases weekly
- Use biological controls (predatory insects)
- Quarantine new plants

### 4. **Data-Driven Decisions**
- Track yields per greenhouse/crop
- Correlate environmental data with quality/yield
- A/B test different climate setpoints
- Use AI models for predictive optimization

### 5. **Energy Efficiency**
- Use thermal screens at night (reduce heating costs 30-50%)
- LED lighting (50% less energy than HPS)
- Heat recovery from CO2 generators
- Insulated north wall (cold climates)

---

## Conclusion

AgroPulse's horticulture platform provides **enterprise-grade tools for greenhouse growers**, from small operations to large commercial farms. By precisely monitoring and controlling environmental parameters, growers can:

- **Increase yields** by 30-50% vs. traditional methods
- **Reduce water use** by 90% with hydroponics
- **Grow year-round** independent of weather
- **Produce premium quality** with consistent climate
- **Minimize crop losses** with early disease detection
- **Optimize inputs** (energy, nutrients, CO2) with data analytics

**Start growing smarter with AgroPulse! 🌿**

---

## Related Documentation

- [Database Schema](DATABASE_GUIDE.md) - Complete model reference
- [API Endpoints](API_ENDPOINTS_REFERENCE.md) - Full REST API docs
- [Sensor Integration](MOBILE_PHONE_SENSOR.md) - IoT device setup
- [AI Models](HYBRID_BRAIN_MODEL.md) - ML for optimization

---

**Questions?** Contact: [support@agropulse.io](mailto:support@agropulse.io)  
**Documentation**: https://docs.agropulse.io  
**GitHub**: https://github.com/agropulse/platform
