/*
 * 🌿 AgroPulse Greenhouse Horticultural Sensor System
 * 
 * ESP32-CAM + Multi-Sensor Platform for 25 Major Horticultural Crops
 * 
 * Supported Crop Categories:
 * - Vegetables & Roots: Potatoes, Tomatoes, Onions, Cucumbers, Garlic, Watermelons, 
 *                       Peppers, Sweet Potatoes, Eggplants, Cabbages, Spinach, Lettuce, 
 *                       Peas, Cassava
 * - Fruits & Nuts: Grapes, Apples, Bananas, Mangoes, Oranges, Olives, Tangerines, 
 *                  Strawberries, Peaches
 * - Spices & Herbs: Coffee, Tea
 * 
 * Sensor Capabilities:
 * - Visual crop monitoring (ESP32-CAM with LED grow light compensation)
 * - PAR light measurement (photosynthetically active radiation)
 * - CO2 concentration monitoring
 * - pH and EC measurement for hydroponic systems
 * - Temperature and humidity sensing
 * - Water temperature monitoring
 * - Soil/substrate moisture detection
 * 
 * Author: AgroPulse Horticulture Firmware Team
 * Date: November 3, 2025
 * Version: 2.0 - Greenhouse Edition
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include <Wire.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ==================== CONFIGURATION ====================

// WiFi credentials
const char* ssid = "GREENHOUSE_WIFI";
const char* password = "YOUR_WIFI_PASSWORD";

// AgroPulse Greenhouse API
const char* apiEndpoint = "https://api.agropulse.com/api/v1/greenhouse/sensors";
const char* apiKey = "greenhouse_sensor_api_key_here";
const int greenhouseId = 1;
const int zoneId = 1;

// Camera pins for AI Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Sensor pins
#define DHT_PIN           14  // DHT22 temperature/humidity sensor
#define DHT_TYPE          DHT22
#define CO2_PIN           33  // MH-Z19B CO2 sensor analog output
#define PAR_SENSOR_PIN    34  // PAR light sensor (LI-190R or equivalent)
#define PH_SENSOR_PIN     35  // pH sensor analog output
#define EC_SENSOR_PIN     36  // EC sensor analog output
#define WATER_TEMP_PIN    13  // DS18B20 water temperature sensor
#define MOISTURE_PIN      39  // Soil/substrate moisture sensor

// Timing intervals
const unsigned long SENSOR_INTERVAL = 60000;    // 1 minute for environmental sensors
const unsigned long CAMERA_INTERVAL = 300000;   // 5 minutes for visual inspection
const unsigned long UPLOAD_INTERVAL = 600000;   // 10 minutes for data upload

// ==================== CROP DATABASE ====================

enum CropType {
  // Vegetables & Roots (14 crops)
  CROP_POTATO,
  CROP_TOMATO,
  CROP_ONION,
  CROP_CUCUMBER,
  CROP_GARLIC,
  CROP_WATERMELON,
  CROP_PEPPER,
  CROP_SWEET_POTATO,
  CROP_EGGPLANT,
  CROP_CABBAGE,
  CROP_SPINACH,
  CROP_LETTUCE,
  CROP_PEA,
  CROP_CASSAVA,
  
  // Fruits & Nuts (9 crops)
  CROP_GRAPE,
  CROP_APPLE,
  CROP_BANANA,
  CROP_MANGO,
  CROP_ORANGE,
  CROP_OLIVE,
  CROP_TANGERINE,
  CROP_STRAWBERRY,
  CROP_PEACH,
  
  // Spices & Herbs (2 crops)
  CROP_COFFEE,
  CROP_TEA,
  
  CROP_UNKNOWN
};

struct CropParameters {
  const char* name;
  float optimal_ph_min;
  float optimal_ph_max;
  float optimal_ec_min;      // mS/cm
  float optimal_ec_max;
  float optimal_temp_min;    // Celsius
  float optimal_temp_max;
  float optimal_humidity_min; // %
  float optimal_humidity_max;
  float optimal_co2_min;     // ppm
  float optimal_co2_max;
  float optimal_par_min;     // μmol/m²/s
  float optimal_par_max;
  float water_stress_threshold; // 0-1, lower = more sensitive
};

// Crop parameter database for all 25 major horticultural crops
const CropParameters CROP_DB[] = {
  // Vegetables & Roots
  {"Potato", 5.0, 6.5, 1.8, 2.5, 15, 22, 70, 85, 800, 1200, 300, 500, 0.3},
  {"Tomato", 5.5, 6.5, 2.0, 3.5, 18, 26, 60, 75, 800, 1200, 400, 600, 0.25},
  {"Onion", 6.0, 7.0, 1.2, 1.8, 15, 25, 50, 70, 600, 1000, 250, 400, 0.4},
  {"Cucumber", 5.5, 6.0, 1.7, 2.5, 22, 28, 65, 80, 900, 1400, 400, 600, 0.2},
  {"Garlic", 6.0, 7.0, 1.0, 1.5, 12, 22, 50, 70, 600, 1000, 250, 400, 0.5},
  {"Watermelon", 5.5, 6.5, 1.5, 2.5, 24, 32, 60, 75, 700, 1200, 400, 600, 0.3},
  {"Pepper", 5.8, 6.5, 2.0, 3.0, 20, 28, 60, 75, 900, 1300, 400, 600, 0.3},
  {"Sweet Potato", 5.5, 6.5, 1.5, 2.2, 22, 30, 60, 80, 700, 1100, 350, 550, 0.35},
  {"Eggplant", 5.5, 6.5, 2.0, 2.8, 22, 30, 60, 75, 800, 1200, 400, 600, 0.3},
  {"Cabbage", 6.0, 7.0, 1.5, 2.5, 15, 22, 60, 80, 800, 1200, 300, 500, 0.35},
  {"Spinach", 6.0, 7.0, 1.5, 2.2, 12, 20, 50, 70, 800, 1200, 250, 400, 0.3},
  {"Lettuce", 5.8, 6.2, 1.2, 1.8, 16, 22, 50, 70, 800, 1200, 200, 300, 0.25},
  {"Pea", 6.0, 7.0, 1.2, 1.8, 15, 24, 60, 75, 700, 1100, 250, 400, 0.35},
  {"Cassava", 5.5, 6.5, 1.5, 2.2, 25, 35, 60, 80, 600, 1000, 400, 600, 0.4},
  
  // Fruits & Nuts
  {"Grape", 5.5, 7.0, 1.0, 1.5, 18, 28, 50, 70, 700, 1100, 400, 600, 0.35},
  {"Apple", 5.5, 6.5, 1.0, 1.8, 15, 25, 60, 75, 700, 1100, 350, 550, 0.3},
  {"Banana", 5.5, 6.5, 1.5, 2.5, 25, 32, 70, 85, 700, 1100, 400, 600, 0.25},
  {"Mango", 5.5, 7.0, 1.5, 2.2, 24, 32, 60, 75, 600, 1000, 400, 600, 0.35},
  {"Orange", 5.5, 6.5, 1.2, 2.0, 18, 28, 60, 75, 700, 1100, 400, 600, 0.3},
  {"Olive", 6.0, 8.0, 1.0, 1.5, 18, 28, 50, 65, 600, 1000, 350, 550, 0.5},
  {"Tangerine", 5.5, 6.5, 1.2, 2.0, 18, 28, 60, 75, 700, 1100, 400, 600, 0.3},
  {"Strawberry", 5.5, 6.5, 1.0, 1.5, 18, 24, 55, 75, 700, 1000, 300, 500, 0.25},
  {"Peach", 6.0, 7.0, 1.2, 2.0, 18, 28, 55, 70, 700, 1100, 400, 600, 0.3},
  
  // Spices & Herbs
  {"Coffee", 5.5, 6.5, 1.5, 2.5, 18, 28, 60, 80, 600, 1000, 300, 500, 0.35},
  {"Tea", 4.5, 5.5, 1.5, 2.2, 18, 28, 60, 80, 600, 1000, 300, 500, 0.3},
  
  {"Unknown", 5.5, 6.5, 1.5, 2.5, 20, 25, 60, 70, 800, 1200, 300, 500, 0.3}
};

// ==================== GLOBAL VARIABLES ====================

DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(WATER_TEMP_PIN);
DallasTemperature waterTempSensor(&oneWire);

CropType currentCrop = CROP_TOMATO;  // Default crop (configurable via API)

// Sensor readings
struct SensorData {
  float temperature;
  float humidity;
  float co2;
  float par_light;
  float ph;
  float ec;
  float water_temp;
  float moisture;
  float vpd;  // Vapor Pressure Deficit
  unsigned long timestamp;
} latestReadings;

// Camera analysis
struct VisionData {
  float health_index;      // 0-1
  float leaf_area_index;   // Estimated leaf coverage
  float stress_indicator;  // 0-1, higher = more stress
  bool disease_detected;
  bool pest_detected;
  unsigned long timestamp;
} latestVision;

unsigned long lastSensorRead = 0;
unsigned long lastCameraCapture = 0;
unsigned long lastDataUpload = 0;

// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);
  Serial.println("\n🌿 AgroPulse Greenhouse Sensor System v2.0");
  Serial.println("Supporting 25 Major Horticultural Crops");
  
  // Initialize sensors
  pinMode(CO2_PIN, INPUT);
  pinMode(PAR_SENSOR_PIN, INPUT);
  pinMode(PH_SENSOR_PIN, INPUT);
  pinMode(EC_SENSOR_PIN, INPUT);
  pinMode(MOISTURE_PIN, INPUT);
  
  dht.begin();
  waterTempSensor.begin();
  
  // Connect to WiFi
  connectWiFi();
  
  // Initialize camera
  initializeCamera();
  
  // Get configuration from API
  fetchGreenhouseConfig();
  
  Serial.println("✅ System initialized successfully!");
  printCropInfo();
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠️ WiFi connection failed - running in offline mode");
  }
}

void initializeCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  
  if(psramFound()){
    config.frame_size = FRAMESIZE_SVGA;  // 800x600 for better analysis
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA;   // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Camera init failed: 0x%x\n", err);
    return;
  }
  
  // Configure camera for greenhouse LED lighting
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     // -2 to 2
  s->set_contrast(s, 0);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_whitebal(s, 1);       // Enable white balance
  s->set_awb_gain(s, 1);       // Enable Auto White Balance gain
  s->set_wb_mode(s, 0);        // Auto white balance mode
  s->set_exposure_ctrl(s, 1);  // Enable exposure control
  s->set_aec2(s, 1);           // Enable automatic exposure correction
  s->set_gain_ctrl(s, 1);      // Enable gain control
  s->set_agc_gain(s, 0);       // Auto gain
  s->set_gainceiling(s, (gainceiling_t)2);  // Gain ceiling 4x
  
  Serial.println("✅ Camera initialized with LED compensation");
}

// ==================== MAIN LOOP ====================

void loop() {
  unsigned long currentTime = millis();
  
  // Read environmental sensors every minute
  if (currentTime - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = currentTime;
    readAllSensors();
    analyzeEnvironment();
    displayReadings();
  }
  
  // Capture and analyze image every 5 minutes
  if (currentTime - lastCameraCapture >= CAMERA_INTERVAL) {
    lastCameraCapture = currentTime;
    captureAndAnalyze();
  }
  
  // Upload data every 10 minutes
  if (currentTime - lastDataUpload >= UPLOAD_INTERVAL) {
    lastDataUpload = currentTime;
    uploadData();
  }
  
  delay(1000);
}

// ==================== SENSOR READING FUNCTIONS ====================

void readAllSensors() {
  Serial.println("\n📊 Reading sensors...");
  
  // Temperature & Humidity (DHT22)
  latestReadings.temperature = dht.readTemperature();
  latestReadings.humidity = dht.readHumidity();
  
  // CO2 concentration (MH-Z19B analog output: 0-5V = 0-5000ppm)
  int co2Raw = analogRead(CO2_PIN);
  latestReadings.co2 = map(co2Raw, 0, 4095, 0, 5000);
  
  // PAR light sensor (0-3.3V = 0-2000 μmol/m²/s)
  int parRaw = analogRead(PAR_SENSOR_PIN);
  latestReadings.par_light = map(parRaw, 0, 4095, 0, 2000);
  
  // pH sensor (0-3.3V = 0-14 pH)
  int phRaw = analogRead(PH_SENSOR_PIN);
  latestReadings.ph = map(phRaw, 0, 4095, 0, 1400) / 100.0;
  
  // EC sensor (0-3.3V = 0-10 mS/cm)
  int ecRaw = analogRead(EC_SENSOR_PIN);
  latestReadings.ec = map(ecRaw, 0, 4095, 0, 1000) / 100.0;
  
  // Water temperature (DS18B20)
  waterTempSensor.requestTemperatures();
  latestReadings.water_temp = waterTempSensor.getTempCByIndex(0);
  
  // Substrate moisture (0-3.3V = 0-100%)
  int moistureRaw = analogRead(MOISTURE_PIN);
  latestReadings.moisture = map(moistureRaw, 0, 4095, 0, 100);
  
  // Calculate VPD (Vapor Pressure Deficit)
  latestReadings.vpd = calculateVPD(latestReadings.temperature, latestReadings.humidity);
  
  latestReadings.timestamp = millis();
}

float calculateVPD(float temp, float humidity) {
  // Calculate saturation vapor pressure (SVP) using Tetens equation
  float svp = 0.6108 * exp((17.27 * temp) / (temp + 237.3));
  
  // Calculate actual vapor pressure (AVP)
  float avp = svp * (humidity / 100.0);
  
  // VPD = SVP - AVP (in kPa)
  return svp - avp;
}

void analyzeEnvironment() {
  const CropParameters& crop = CROP_DB[currentCrop];
  
  Serial.println("\n🔍 Analyzing environment for: " + String(crop.name));
  
  // Check each parameter against optimal ranges
  checkParameter("Temperature", latestReadings.temperature, crop.optimal_temp_min, crop.optimal_temp_max, "°C");
  checkParameter("Humidity", latestReadings.humidity, crop.optimal_humidity_min, crop.optimal_humidity_max, "%");
  checkParameter("CO2", latestReadings.co2, crop.optimal_co2_min, crop.optimal_co2_max, "ppm");
  checkParameter("PAR Light", latestReadings.par_light, crop.optimal_par_min, crop.optimal_par_max, "μmol/m²/s");
  checkParameter("pH", latestReadings.ph, crop.optimal_ph_min, crop.optimal_ph_max, "");
  checkParameter("EC", latestReadings.ec, crop.optimal_ec_min, crop.optimal_ec_max, "mS/cm");
  
  // VPD analysis
  if (latestReadings.vpd < 0.4) {
    Serial.println("⚠️ VPD too low (" + String(latestReadings.vpd, 2) + " kPa) - Risk of mold/mildew");
  } else if (latestReadings.vpd > 1.6) {
    Serial.println("⚠️ VPD too high (" + String(latestReadings.vpd, 2) + " kPa) - Water stress risk");
  } else {
    Serial.println("✅ VPD optimal (" + String(latestReadings.vpd, 2) + " kPa)");
  }
}

void checkParameter(const char* name, float value, float min, float max, const char* unit) {
  if (value < min) {
    Serial.println("⚠️ " + String(name) + " LOW: " + String(value, 1) + unit + " (optimal: " + String(min, 1) + "-" + String(max, 1) + ")");
  } else if (value > max) {
    Serial.println("⚠️ " + String(name) + " HIGH: " + String(value, 1) + unit + " (optimal: " + String(min, 1) + "-" + String(max, 1) + ")");
  } else {
    Serial.println("✅ " + String(name) + " OK: " + String(value, 1) + unit);
  }
}

void displayReadings() {
  Serial.println("\n📈 Current Readings:");
  Serial.println("Temperature: " + String(latestReadings.temperature, 1) + "°C");
  Serial.println("Humidity: " + String(latestReadings.humidity, 1) + "%");
  Serial.println("CO2: " + String(latestReadings.co2, 0) + " ppm");
  Serial.println("PAR Light: " + String(latestReadings.par_light, 0) + " μmol/m²/s");
  Serial.println("pH: " + String(latestReadings.ph, 2));
  Serial.println("EC: " + String(latestReadings.ec, 2) + " mS/cm");
  Serial.println("Water Temp: " + String(latestReadings.water_temp, 1) + "°C");
  Serial.println("Moisture: " + String(latestReadings.moisture, 0) + "%");
  Serial.println("VPD: " + String(latestReadings.vpd, 2) + " kPa");
}

// ==================== VISION ANALYSIS ====================

void captureAndAnalyze() {
  Serial.println("\n📷 Capturing image for analysis...");
  
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Camera capture failed");
    return;
  }
  
  // Perform on-chip vision analysis
  analyzeImage(fb);
  
  // Release frame buffer
  esp_camera_fb_return(fb);
  
  latestVision.timestamp = millis();
  
  displayVisionResults();
}

void analyzeImage(camera_fb_t * fb) {
  // Simple computer vision analysis on ESP32
  // Real implementation would use TensorFlow Lite or similar
  
  int greenPixels = 0;
  int brownPixels = 0;
  int yellowPixels = 0;
  int whitePixels = 0;
  int totalPixels = 0;
  
  // Sample pixels for efficiency (every 50th pixel)
  for (size_t i = 0; i < fb->len - 2; i += 150) {
    uint8_t r = fb->buf[i];
    uint8_t g = fb->buf[i + 1];
    uint8_t b = fb->buf[i + 2];
    
    totalPixels++;
    
    // Classify pixel color
    if (g > r && g > b && g > 100) {
      greenPixels++;  // Healthy vegetation
    } else if (r > 150 && g > 100 && b < 80) {
      brownPixels++;  // Dead/stressed tissue
    } else if (r > 180 && g > 180 && b < 100) {
      yellowPixels++;  // Chlorosis/nutrient deficiency
    } else if (r > 200 && g > 200 && b > 200) {
      whitePixels++;  // Powdery mildew or light reflection
    }
  }
  
  // Calculate health metrics
  latestVision.health_index = (float)greenPixels / totalPixels;
  latestVision.stress_indicator = (float)(brownPixels + yellowPixels) / totalPixels;
  latestVision.leaf_area_index = latestVision.health_index * 1.2;  // Simplified LAI
  
  // Disease/pest detection (simplified)
  latestVision.disease_detected = (whitePixels > totalPixels * 0.15) || (brownPixels > totalPixels * 0.2);
  latestVision.pest_detected = latestVision.stress_indicator > 0.25;
}

void displayVisionResults() {
  Serial.println("\n🔬 Vision Analysis Results:");
  Serial.println("Health Index: " + String(latestVision.health_index * 100, 1) + "%");
  Serial.println("Leaf Area Index: " + String(latestVision.leaf_area_index, 2));
  Serial.println("Stress Indicator: " + String(latestVision.stress_indicator * 100, 1) + "%");
  
  if (latestVision.disease_detected) {
    Serial.println("⚠️ Potential disease detected!");
  }
  if (latestVision.pest_detected) {
    Serial.println("⚠️ Potential pest damage detected!");
  }
}

// ==================== DATA UPLOAD ====================

void uploadData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi not connected - skipping upload");
    return;
  }
  
  Serial.println("\n📤 Uploading data to AgroPulse...");
  
  HTTPClient http;
  http.begin(apiEndpoint);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + apiKey);
  
  // Create JSON payload
  StaticJsonDocument<1024> doc;
  doc["greenhouse_id"] = greenhouseId;
  doc["zone_id"] = zoneId;
  doc["crop_type"] = CROP_DB[currentCrop].name;
  doc["timestamp"] = millis();
  
  // Environmental data
  JsonObject env = doc.createNestedObject("environmental");
  env["temperature"] = latestReadings.temperature;
  env["humidity"] = latestReadings.humidity;
  env["co2"] = latestReadings.co2;
  env["par_light"] = latestReadings.par_light;
  env["ph"] = latestReadings.ph;
  env["ec"] = latestReadings.ec;
  env["water_temp"] = latestReadings.water_temp;
  env["moisture"] = latestReadings.moisture;
  env["vpd"] = latestReadings.vpd;
  
  // Vision data
  JsonObject vision = doc.createNestedObject("vision");
  vision["health_index"] = latestVision.health_index;
  vision["leaf_area_index"] = latestVision.leaf_area_index;
  vision["stress_indicator"] = latestVision.stress_indicator;
  vision["disease_detected"] = latestVision.disease_detected;
  vision["pest_detected"] = latestVision.pest_detected;
  
  String payload;
  serializeJson(doc, payload);
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200 || httpCode == 201) {
    Serial.println("✅ Data uploaded successfully");
  } else {
    Serial.println("❌ Upload failed. HTTP code: " + String(httpCode));
  }
  
  http.end();
}

// ==================== CONFIGURATION ====================

void fetchGreenhouseConfig() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ Using default configuration (offline mode)");
    return;
  }
  
  Serial.println("📥 Fetching greenhouse configuration...");
  
  HTTPClient http;
  String configUrl = String("https://api.agropulse.com/api/v1/greenhouse/") + 
                     greenhouseId + "/zones/" + zoneId + "/config";
  http.begin(configUrl);
  http.addHeader("Authorization", String("Bearer ") + apiKey);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String response = http.getString();
    StaticJsonDocument<512> doc;
    deserializeJson(doc, response);
    
    // Parse crop type
    const char* cropName = doc["crop_type"];
    currentCrop = getCropTypeByName(cropName);
    
    Serial.println("✅ Configuration loaded: " + String(cropName));
  } else {
    Serial.println("⚠️ Config fetch failed - using defaults");
  }
  
  http.end();
}

CropType getCropTypeByName(const char* name) {
  for (int i = 0; i < 26; i++) {
    if (strcasecmp(CROP_DB[i].name, name) == 0) {
      return (CropType)i;
    }
  }
  return CROP_UNKNOWN;
}

void printCropInfo() {
  const CropParameters& crop = CROP_DB[currentCrop];
  Serial.println("\n🌱 Current Crop Configuration:");
  Serial.println("Crop: " + String(crop.name));
  Serial.println("Optimal pH: " + String(crop.optimal_ph_min, 1) + " - " + String(crop.optimal_ph_max, 1));
  Serial.println("Optimal EC: " + String(crop.optimal_ec_min, 1) + " - " + String(crop.optimal_ec_max, 1) + " mS/cm");
  Serial.println("Optimal Temp: " + String(crop.optimal_temp_min, 0) + " - " + String(crop.optimal_temp_max, 0) + "°C");
  Serial.println("Optimal Humidity: " + String(crop.optimal_humidity_min, 0) + " - " + String(crop.optimal_humidity_max, 0) + "%");
  Serial.println("Optimal CO2: " + String(crop.optimal_co2_min, 0) + " - " + String(crop.optimal_co2_max, 0) + " ppm");
  Serial.println("Optimal PAR: " + String(crop.optimal_par_min, 0) + " - " + String(crop.optimal_par_max, 0) + " μmol/m²/s");
}
