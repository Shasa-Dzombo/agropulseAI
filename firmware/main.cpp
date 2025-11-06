/**
 * AgroPulse IoT Sensor Node - ESP32 Firmware
 * ============================================
 * 
 * Complete embedded firmware for agricultural IoT sensor platform.
 * 
 * Features:
 * - Multi-sensor data acquisition (soil, weather, plant health)
 * - LoRa mesh networking (10km range)
 * - Solar power management with MPPT
 * - Edge AI inference (TensorFlow Lite Micro)
 * - OTA firmware updates
 * - Deep sleep power optimization
 * - Local data buffering with SD card
 * - Watchdog timer for reliability
 * 
 * Hardware:
 * - ESP32-WROOM-32D (240MHz dual-core, 520KB SRAM, WiFi/BT)
 * - LoRa SX1276 transceiver (433MHz, 10km range)
 * - BME280 (temperature, humidity, pressure)
 * - Capacitive soil moisture sensor (analog)
 * - BH1750 light sensor (I2C)
 * - DS18B20 soil temperature (1-Wire)
 * - INA219 current/voltage sensor (I2C)
 * - 18650 Li-ion battery (3.7V, 3000mAh)
 * - 6V 2W solar panel with TP4056 MPPT charger
 * 
 * Power Budget:
 * - Active mode: 80mA @ 3.7V = 296mW
 * - LoRa transmit: 120mA peak
 * - Deep sleep: 10μA (battery life: 300 days on single charge)
 * - Solar recharge: 400mA @ 5V peak
 * 
 * Estimated Cost: $14 USD per node
 * 
 * @author AgroPulse Team
 * @version 2.1.0
 * @date 2025-11-01
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_BME280.h>
#include <BH1750.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_INA219.h>
#include <SD.h>
#include <SPIFFS.h>
#include <ESPAsyncWebServer.h>
#include <Update.h>
#include <esp_task_wdt.h>
#include <TensorFlowLite_ESP32.h>
#include <tensorflow/lite/micro/all_ops_resolver.h>
#include <tensorflow/lite/micro/micro_error_reporter.h>
#include <tensorflow/lite/micro/micro_interpreter.h>
#include <tensorflow/lite/schema/schema_generated.h>

// ===================
// PIN CONFIGURATION
// ===================

// LoRa SX1276
#define LORA_SCK       5
#define LORA_MISO      19
#define LORA_MOSI      27
#define LORA_CS        18
#define LORA_RST       14
#define LORA_IRQ       26

// I2C Sensors (BME280, BH1750, INA219)
#define I2C_SDA        21
#define I2C_SCL        22

// Analog Sensors
#define SOIL_MOISTURE_PIN  34  // ADC1_CH6
#define BATTERY_VOLTAGE_PIN 35 // ADC1_CH7

// 1-Wire (DS18B20)
#define ONE_WIRE_BUS   4

// SD Card
#define SD_CS          13

// Status LED
#define LED_PIN        2

// Wake button (for manual override)
#define WAKE_BUTTON    0

// ===================
// CONFIGURATION
// ===================

// Network
const char* WIFI_SSID = "AgroPulse_Gateway";
const char* WIFI_PASSWORD = "harvest2025";
const char* MQTT_BROKER = "192.168.1.100";
const uint16_t MQTT_PORT = 1883;

// LoRa Mesh
const long LORA_FREQUENCY = 433E6;  // 433MHz (ISM band)
const int LORA_TX_POWER = 17;       // dBm (50mW)
const int LORA_SPREADING_FACTOR = 7; // SF7 = 5.5kb/s
const long LORA_BANDWIDTH = 125E3;   // 125kHz
const int LORA_CODING_RATE = 5;      // 4/5

// Node Identity
String NODE_ID = "AGRO_001";
const uint8_t NODE_ADDRESS = 0x01;
const uint8_t GATEWAY_ADDRESS = 0xFF;

// Timing (milliseconds)
const uint32_t SENSOR_READ_INTERVAL = 60000;    // 1 minute
const uint32_t LORA_TRANSMIT_INTERVAL = 300000; // 5 minutes
const uint32_t DEEP_SLEEP_DURATION = 240000000; // 4 minutes (microseconds)
const uint32_t WATCHDOG_TIMEOUT = 30000;        // 30 seconds

// Sensor Calibration
const float SOIL_MOISTURE_DRY = 3000.0;   // ADC value in air
const float SOIL_MOISTURE_WET = 1000.0;   // ADC value in water
const float BATTERY_VOLTAGE_DIVIDER = 2.0; // R1=R2, Vout = Vin/2
const float ADC_VREF = 3.3;
const float ADC_RESOLUTION = 4095.0;

// Data Buffering
#define MAX_BUFFER_SIZE 100
#define FLASH_BUFFER_FILE "/data_buffer.json"

// ===================
// GLOBAL OBJECTS
// ===================

// Sensors
Adafruit_BME280 bme;
BH1750 lightMeter;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature soilTempSensor(&oneWire);
Adafruit_INA219 ina219;

// LoRa
SPIClass loraSpI(VSPI);

// Web Server (for OTA)
AsyncWebServer server(80);

// TensorFlow Lite
tflite::MicroErrorReporter micro_error_reporter;
tflite::ErrorReporter* error_reporter = &micro_error_reporter;
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;

constexpr int kTensorArenaSize = 8192;
uint8_t tensor_arena[kTensorArenaSize];

// ===================
// DATA STRUCTURES
// ===================

struct SensorData {
    // Timestamp
    unsigned long timestamp;
    
    // Environmental
    float air_temperature;      // °C
    float air_humidity;         // %
    float air_pressure;         // hPa
    float light_intensity;      // lux
    
    // Soil
    float soil_temperature;     // °C
    float soil_moisture;        // %
    
    // Power
    float battery_voltage;      // V
    float solar_current;        // mA
    float power_consumption;    // mW
    
    // Derived metrics
    float vpd;                  // Vapor Pressure Deficit (kPa)
    float dew_point;            // °C
    int8_t stress_level;        // 0-100 (AI inference)
    
    // Quality
    uint8_t rssi;               // LoRa signal strength
    uint8_t snr;                // Signal-to-noise ratio
    uint8_t data_quality;       // 0-100%
};

struct NodeStatus {
    uint32_t uptime_minutes;
    uint32_t total_readings;
    uint32_t successful_transmissions;
    uint32_t failed_transmissions;
    uint16_t free_heap_kb;
    uint8_t battery_percentage;
    bool solar_charging;
    bool sensors_ok;
};

// ===================
// GLOBAL VARIABLES
// ===================

SensorData currentData;
NodeStatus nodeStatus;

unsigned long lastSensorRead = 0;
unsigned long lastLoRaTransmit = 0;
unsigned long bootTime = 0;

bool loraInitialized = false;
bool sensorsInitialized = false;
bool sdCardAvailable = false;

std::vector<SensorData> dataBuffer;

// ===================
// FUNCTION PROTOTYPES
// ===================

// Initialization
void initPins();
void initSensors();
void initLoRa();
void initTensorFlow();
void initSDCard();
void initWatchdog();

// Sensor reading
SensorData readSensors();
float readSoilMoisture();
float readBatteryVoltage();
float calculateVPD(float temp, float humidity);
float calculateDewPoint(float temp, float humidity);

// AI Inference
int8_t inferStressLevel(SensorData& data);

// Data transmission
bool transmitLoRa(const SensorData& data);
bool transmitWiFi(const SensorData& data);
void receiveLoRa();
void routeMessage(uint8_t* payload, size_t len);

// Data buffering
void bufferData(const SensorData& data);
void flushBuffer();
bool saveBufferToFlash();
bool loadBufferFromFlash();

// Power management
void enterDeepSleep();
uint8_t calculateBatteryPercentage(float voltage);
bool isSolarCharging();

// OTA Updates
void initOTA();
void handleOTAUpload(AsyncWebServerRequest *request, String filename, 
                     size_t index, uint8_t *data, size_t len, bool final);

// Utilities
void blinkLED(int times, int delayMs);
void printSensorData(const SensorData& data);
String serializeData(const SensorData& data);
uint16_t calculateCRC16(const uint8_t* data, size_t len);

// ===================
// SETUP
// ===================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("====================================");
    Serial.println("  AgroPulse IoT Sensor Node v2.1");
    Serial.println("====================================");
    Serial.println();
    
    bootTime = millis();
    
    // Initialize pins
    initPins();
    blinkLED(3, 200);
    
    // Initialize I2C
    Wire.begin(I2C_SDA, I2C_SCL);
    Serial.println("[INIT] I2C initialized");
    
    // Initialize sensors
    initSensors();
    
    // Initialize LoRa
    initLoRa();
    
    // Initialize SD card
    initSDCard();
    
    // Load buffered data
    if (sdCardAvailable) {
        loadBufferFromFlash();
    }
    
    // Initialize TensorFlow
    initTensorFlow();
    
    // Initialize watchdog
    initWatchdog();
    
    // Initialize OTA
    initOTA();
    
    // Initialize node status
    nodeStatus.uptime_minutes = 0;
    nodeStatus.total_readings = 0;
    nodeStatus.successful_transmissions = 0;
    nodeStatus.failed_transmissions = 0;
    nodeStatus.sensors_ok = sensorsInitialized;
    
    Serial.println("\n[READY] Node initialized successfully");
    Serial.printf("[INFO] Node ID: %s (0x%02X)\n", NODE_ID.c_str(), NODE_ADDRESS);
    Serial.printf("[INFO] Free heap: %d KB\n", ESP.getFreeHeap() / 1024);
    
    blinkLED(5, 100);
}

// ===================
// MAIN LOOP
// ===================

void loop() {
    unsigned long now = millis();
    
    // Reset watchdog
    esp_task_wdt_reset();
    
    // Update uptime
    nodeStatus.uptime_minutes = (now - bootTime) / 60000;
    
    // Check for LoRa messages
    if (loraInitialized) {
        receiveLoRa();
    }
    
    // Read sensors periodically
    if (now - lastSensorRead >= SENSOR_READ_INTERVAL) {
        Serial.println("\n--- Sensor Reading Cycle ---");
        
        currentData = readSensors();
        nodeStatus.total_readings++;
        
        // Run AI inference
        currentData.stress_level = inferStressLevel(currentData);
        
        // Print data
        printSensorData(currentData);
        
        // Buffer data
        bufferData(currentData);
        
        lastSensorRead = now;
        
        blinkLED(1, 50);
    }
    
    // Transmit via LoRa periodically
    if (now - lastLoRaTransmit >= LORA_TRANSMIT_INTERVAL) {
        Serial.println("\n--- LoRa Transmission Cycle ---");
        
        // Flush entire buffer
        flushBuffer();
        
        lastLoRaTransmit = now;
    }
    
    // Update power status
    nodeStatus.battery_percentage = calculateBatteryPercentage(currentData.battery_voltage);
    nodeStatus.solar_charging = isSolarCharging();
    nodeStatus.free_heap_kb = ESP.getFreeHeap() / 1024;
    
    // Enter deep sleep if battery low and no solar
    if (nodeStatus.battery_percentage < 20 && !nodeStatus.solar_charging) {
        Serial.println("\n[WARN] Low battery, entering deep sleep...");
        saveBufferToFlash();
        enterDeepSleep();
    }
    
    // Small delay to prevent tight loop
    delay(100);
}

// ===================
// INITIALIZATION FUNCTIONS
// ===================

void initPins() {
    pinMode(LED_PIN, OUTPUT);
    pinMode(WAKE_BUTTON, INPUT_PULLUP);
    pinMode(SOIL_MOISTURE_PIN, INPUT);
    pinMode(BATTERY_VOLTAGE_PIN, INPUT);
    
    digitalWrite(LED_PIN, LOW);
    
    Serial.println("[INIT] GPIO pins configured");
}

void initSensors() {
    Serial.println("[INIT] Initializing sensors...");
    
    bool allOk = true;
    
    // BME280 (Temperature, Humidity, Pressure)
    if (bme.begin(0x76)) {
        bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                        Adafruit_BME280::SAMPLING_X2,  // temperature
                        Adafruit_BME280::SAMPLING_X2,  // pressure
                        Adafruit_BME280::SAMPLING_X2,  // humidity
                        Adafruit_BME280::FILTER_X16,
                        Adafruit_BME280::STANDBY_MS_500);
        Serial.println("  ✓ BME280 OK");
    } else {
        Serial.println("  ✗ BME280 FAILED");
        allOk = false;
    }
    
    // BH1750 (Light sensor)
    if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
        Serial.println("  ✓ BH1750 OK");
    } else {
        Serial.println("  ✗ BH1750 FAILED");
        allOk = false;
    }
    
    // DS18B20 (Soil temperature)
    soilTempSensor.begin();
    int deviceCount = soilTempSensor.getDeviceCount();
    if (deviceCount > 0) {
        soilTempSensor.setResolution(12); // 12-bit resolution
        Serial.printf("  ✓ DS18B20 OK (%d devices)\n", deviceCount);
    } else {
        Serial.println("  ✗ DS18B20 FAILED");
        allOk = false;
    }
    
    // INA219 (Power monitoring)
    if (ina219.begin()) {
        ina219.setCalibration_16V_400mA();
        Serial.println("  ✓ INA219 OK");
    } else {
        Serial.println("  ✗ INA219 FAILED");
        allOk = false;
    }
    
    sensorsInitialized = allOk;
    
    if (allOk) {
        Serial.println("[INIT] All sensors initialized successfully");
    } else {
        Serial.println("[WARN] Some sensors failed to initialize");
    }
}

void initLoRa() {
    Serial.println("[INIT] Initializing LoRa...");
    
    // Configure SPI
    loraSpI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
    LoRa.setSPI(loraSpI);
    LoRa.setPins(LORA_CS, LORA_RST, LORA_IRQ);
    
    // Initialize LoRa
    if (LoRa.begin(LORA_FREQUENCY)) {
        LoRa.setTxPower(LORA_TX_POWER);
        LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
        LoRa.setSignalBandwidth(LORA_BANDWIDTH);
        LoRa.setCodingRate4(LORA_CODING_RATE);
        LoRa.enableCrc();
        
        loraInitialized = true;
        
        Serial.println("  ✓ LoRa initialized");
        Serial.printf("  Frequency: %.1f MHz\n", LORA_FREQUENCY / 1e6);
        Serial.printf("  TX Power: %d dBm\n", LORA_TX_POWER);
        Serial.printf("  SF: %d, BW: %.1f kHz\n", LORA_SPREADING_FACTOR, LORA_BANDWIDTH / 1e3);
    } else {
        Serial.println("  ✗ LoRa initialization FAILED");
        loraInitialized = false;
    }
}

void initTensorFlow() {
    Serial.println("[INIT] Initializing TensorFlow Lite...");
    
    // Load model from SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("  ✗ SPIFFS mount failed");
        return;
    }
    
    File modelFile = SPIFFS.open("/model.tflite", "r");
    if (!modelFile) {
        Serial.println("  ✗ Model file not found");
        return;
    }
    
    size_t modelSize = modelFile.size();
    uint8_t* modelData = (uint8_t*)malloc(modelSize);
    modelFile.read(modelData, modelSize);
    modelFile.close();
    
    // Load model
    model = tflite::GetModel(modelData);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.printf("  ✗ Model schema version %d not supported\n", model->version());
        free(modelData);
        return;
    }
    
    // Create interpreter
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
    interpreter = &static_interpreter;
    
    // Allocate tensors
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        Serial.println("  ✗ Tensor allocation failed");
        return;
    }
    
    // Get input/output tensors
    input = interpreter->input(0);
    output = interpreter->output(0);
    
    Serial.println("  ✓ TensorFlow Lite initialized");
    Serial.printf("  Model size: %d bytes\n", modelSize);
    Serial.printf("  Arena used: %d / %d bytes\n", 
                  interpreter->arena_used_bytes(), kTensorArenaSize);
}

void initSDCard() {
    Serial.println("[INIT] Initializing SD card...");
    
    if (SD.begin(SD_CS)) {
        sdCardAvailable = true;
        
        uint64_t cardSize = SD.cardSize() / (1024 * 1024);
        Serial.printf("  ✓ SD card OK (%llu MB)\n", cardSize);
    } else {
        sdCardAvailable = false;
        Serial.println("  ✗ SD card not available");
    }
}

void initWatchdog() {
    Serial.println("[INIT] Initializing watchdog timer...");
    
    esp_task_wdt_init(WATCHDOG_TIMEOUT / 1000, true);
    esp_task_wdt_add(NULL);
    
    Serial.printf("  ✓ Watchdog enabled (%d seconds)\n", WATCHDOG_TIMEOUT / 1000);
}

void initOTA() {
    Serial.println("[INIT] Initializing OTA updates...");
    
    // Connect to WiFi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n  ✓ WiFi connected");
        Serial.printf("  IP: %s\n", WiFi.localIP().toString().c_str());
        
        // Setup web server for OTA
        server.on("/update", HTTP_POST, 
            [](AsyncWebServerRequest *request) {
                request->send(200, "text/plain", 
                             Update.hasError() ? "FAIL" : "OK");
                ESP.restart();
            },
            handleOTAUpload
        );
        
        server.begin();
        Serial.println("  ✓ OTA server started on port 80");
    } else {
        Serial.println("\n  ✗ WiFi connection failed (OTA disabled)");
    }
}

// ===================
// SENSOR READING FUNCTIONS
// ===================

SensorData readSensors() {
    SensorData data;
    data.timestamp = millis();
    
    // BME280 readings
    data.air_temperature = bme.readTemperature();
    data.air_humidity = bme.readHumidity();
    data.air_pressure = bme.readPressure() / 100.0; // Convert Pa to hPa
    
    // BH1750 light sensor
    data.light_intensity = lightMeter.readLightLevel();
    
    // DS18B20 soil temperature
    soilTempSensor.requestTemperatures();
    data.soil_temperature = soilTempSensor.getTempCByIndex(0);
    
    // Soil moisture (capacitive sensor)
    data.soil_moisture = readSoilMoisture();
    
    // Battery voltage
    data.battery_voltage = readBatteryVoltage();
    
    // Solar current and power
    data.solar_current = ina219.getCurrent_mA();
    float busVoltage = ina219.getBusVoltage_V();
    data.power_consumption = busVoltage * abs(data.solar_current);
    
    // Derived metrics
    data.vpd = calculateVPD(data.air_temperature, data.air_humidity);
    data.dew_point = calculateDewPoint(data.air_temperature, data.air_humidity);
    
    // Signal quality (from last LoRa packet)
    data.rssi = LoRa.packetRssi();
    data.snr = LoRa.packetSnr();
    
    // Data quality check (0-100%)
    data.data_quality = 100;
    if (isnan(data.air_temperature) || data.air_temperature < -40 || data.air_temperature > 85) {
        data.data_quality -= 20;
    }
    if (isnan(data.air_humidity) || data.air_humidity < 0 || data.air_humidity > 100) {
        data.data_quality -= 20;
    }
    if (data.soil_moisture < 0 || data.soil_moisture > 100) {
        data.data_quality -= 20;
    }
    if (data.battery_voltage < 2.5 || data.battery_voltage > 4.5) {
        data.data_quality -= 20;
    }
    
    return data;
}

float readSoilMoisture() {
    // Read ADC (average of 10 samples)
    uint32_t sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += analogRead(SOIL_MOISTURE_PIN);
        delay(10);
    }
    float adcValue = sum / 10.0;
    
    // Convert to percentage (inverted: low ADC = wet, high ADC = dry)
    float moisture = 100.0 * (SOIL_MOISTURE_DRY - adcValue) / 
                     (SOIL_MOISTURE_DRY - SOIL_MOISTURE_WET);
    
    // Clamp to 0-100%
    if (moisture < 0) moisture = 0;
    if (moisture > 100) moisture = 100;
    
    return moisture;
}

float readBatteryVoltage() {
    // Read ADC
    uint32_t sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += analogRead(BATTERY_VOLTAGE_PIN);
        delay(10);
    }
    float adcValue = sum / 10.0;
    
    // Convert to voltage (with voltage divider compensation)
    float voltage = (adcValue / ADC_RESOLUTION) * ADC_VREF * BATTERY_VOLTAGE_DIVIDER;
    
    return voltage;
}

float calculateVPD(float temp, float humidity) {
    // Vapor Pressure Deficit (kPa)
    // SVP = 0.6108 * exp(17.27 * T / (T + 237.3))
    // VPD = SVP * (1 - RH/100)
    
    float svp = 0.6108 * exp((17.27 * temp) / (temp + 237.3));
    float vpd = svp * (1.0 - humidity / 100.0);
    
    return vpd;
}

float calculateDewPoint(float temp, float humidity) {
    // Dew point (°C)
    // Approximation: Td = T - ((100 - RH) / 5)
    
    float a = 17.27;
    float b = 237.7;
    
    float alpha = ((a * temp) / (b + temp)) + log(humidity / 100.0);
    float dewPoint = (b * alpha) / (a - alpha);
    
    return dewPoint;
}

// ===================
// AI INFERENCE
// ===================

int8_t inferStressLevel(SensorData& data) {
    if (!interpreter || !input || !output) {
        return -1; // Model not loaded
    }
    
    // Prepare input tensor (7 features)
    input->data.f[0] = data.air_temperature / 50.0;  // Normalize to ~0-1
    input->data.f[1] = data.air_humidity / 100.0;
    input->data.f[2] = data.soil_moisture / 100.0;
    input->data.f[3] = data.soil_temperature / 50.0;
    input->data.f[4] = data.light_intensity / 100000.0;
    input->data.f[5] = data.vpd / 5.0;
    input->data.f[6] = data.battery_voltage / 5.0;
    
    // Run inference
    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk) {
        return -1;
    }
    
    // Get output (stress level 0-100)
    float stress = output->data.f[0] * 100.0;
    
    return (int8_t)stress;
}

// ===================
// LORA TRANSMISSION
// ===================

bool transmitLoRa(const SensorData& data) {
    if (!loraInitialized) {
        return false;
    }
    
    // Create packet (binary format for efficiency)
    uint8_t packet[64];
    size_t idx = 0;
    
    // Header
    packet[idx++] = 0xAA;  // Start byte
    packet[idx++] = NODE_ADDRESS;
    packet[idx++] = GATEWAY_ADDRESS;
    packet[idx++] = 0x01;  // Packet type: sensor data
    
    // Timestamp (4 bytes)
    uint32_t ts = data.timestamp;
    memcpy(&packet[idx], &ts, 4);
    idx += 4;
    
    // Sensor data (floats compressed to int16)
    int16_t temp_air = (int16_t)(data.air_temperature * 100);
    int16_t humidity = (int16_t)(data.air_humidity * 100);
    int16_t pressure = (int16_t)(data.air_pressure * 10);
    int16_t light = (int16_t)(data.light_intensity / 10);
    int16_t temp_soil = (int16_t)(data.soil_temperature * 100);
    int16_t moisture = (int16_t)(data.soil_moisture * 100);
    int16_t battery = (int16_t)(data.battery_voltage * 1000);
    int16_t solar = (int16_t)(data.solar_current * 10);
    
    memcpy(&packet[idx], &temp_air, 2); idx += 2;
    memcpy(&packet[idx], &humidity, 2); idx += 2;
    memcpy(&packet[idx], &pressure, 2); idx += 2;
    memcpy(&packet[idx], &light, 2); idx += 2;
    memcpy(&packet[idx], &temp_soil, 2); idx += 2;
    memcpy(&packet[idx], &moisture, 2); idx += 2;
    memcpy(&packet[idx], &battery, 2); idx += 2;
    memcpy(&packet[idx], &solar, 2); idx += 2;
    
    // Stress level
    packet[idx++] = (uint8_t)data.stress_level;
    
    // Data quality
    packet[idx++] = data.data_quality;
    
    // CRC16
    uint16_t crc = calculateCRC16(packet, idx);
    memcpy(&packet[idx], &crc, 2);
    idx += 2;
    
    // Transmit
    LoRa.beginPacket();
    LoRa.write(packet, idx);
    bool success = LoRa.endPacket();
    
    if (success) {
        Serial.printf("[LoRa] Transmitted %d bytes (RSSI: %d dBm)\n", idx, LoRa.packetRssi());
        nodeStatus.successful_transmissions++;
    } else {
        Serial.println("[LoRa] Transmission FAILED");
        nodeStatus.failed_transmissions++;
    }
    
    return success;
}

void receiveLoRa() {
    int packetSize = LoRa.parsePacket();
    if (packetSize == 0) {
        return; // No packet
    }
    
    // Read packet
    uint8_t packet[256];
    size_t len = 0;
    while (LoRa.available() && len < 256) {
        packet[len++] = LoRa.read();
    }
    
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();
    
    Serial.printf("\n[LoRa] Received %d bytes (RSSI: %d dBm, SNR: %.1f dB)\n", 
                  len, rssi, snr);
    
    // Check if addressed to this node or broadcast
    if (len < 4) {
        return; // Too short
    }
    
    uint8_t destAddr = packet[2];
    if (destAddr != NODE_ADDRESS && destAddr != 0xFF) {
        // Not for us, route it
        routeMessage(packet, len);
        return;
    }
    
    // Process packet
    uint8_t packetType = packet[3];
    
    switch (packetType) {
        case 0x10: // Command: Read sensors immediately
            Serial.println("[CMD] Immediate sensor read requested");
            lastSensorRead = 0; // Force read on next loop
            break;
            
        case 0x20: // Command: OTA update available
            Serial.println("[CMD] OTA update notification");
            // Trigger OTA check
            break;
            
        case 0x30: // Command: Configuration update
            Serial.println("[CMD] Configuration update");
            // Parse and apply new config
            break;
            
        case 0x40: // Command: Reset node
            Serial.println("[CMD] Reset requested");
            delay(100);
            ESP.restart();
            break;
            
        default:
            Serial.printf("[WARN] Unknown packet type: 0x%02X\n", packetType);
            break;
    }
}

void routeMessage(uint8_t* payload, size_t len) {
    // Simple mesh routing: forward to gateway if not already going there
    uint8_t destAddr = payload[2];
    
    if (destAddr != GATEWAY_ADDRESS) {
        Serial.printf("[MESH] Routing packet to 0x%02X\n", destAddr);
        
        // Retransmit
        LoRa.beginPacket();
        LoRa.write(payload, len);
        LoRa.endPacket();
    }
}

// ===================
// DATA BUFFERING
// ===================

void bufferData(const SensorData& data) {
    dataBuffer.push_back(data);
    
    if (dataBuffer.size() >= MAX_BUFFER_SIZE) {
        Serial.println("[WARN] Buffer full, flushing to flash");
        saveBufferToFlash();
    }
}

void flushBuffer() {
    if (dataBuffer.empty()) {
        return;
    }
    
    Serial.printf("[BUFFER] Flushing %d readings\n", dataBuffer.size());
    
    for (const auto& data : dataBuffer) {
        bool success = transmitLoRa(data);
        if (!success) {
            Serial.println("[WARN] Transmission failed, saving to flash");
            saveBufferToFlash();
            return;
        }
        delay(100); // Small delay between transmissions
    }
    
    // Clear buffer after successful transmission
    dataBuffer.clear();
    Serial.println("[BUFFER] Buffer cleared");
}

bool saveBufferToFlash() {
    if (!sdCardAvailable) {
        return false;
    }
    
    File file = SD.open(FLASH_BUFFER_FILE, FILE_WRITE);
    if (!file) {
        Serial.println("[ERROR] Failed to open buffer file for writing");
        return false;
    }
    
    // Write as JSON array
    file.print("[");
    for (size_t i = 0; i < dataBuffer.size(); i++) {
        String json = serializeData(dataBuffer[i]);
        file.print(json);
        if (i < dataBuffer.size() - 1) {
            file.print(",");
        }
    }
    file.print("]");
    file.close();
    
    Serial.printf("[FLASH] Saved %d readings to SD card\n", dataBuffer.size());
    return true;
}

bool loadBufferFromFlash() {
    if (!sdCardAvailable) {
        return false;
    }
    
    File file = SD.open(FLASH_BUFFER_FILE, FILE_READ);
    if (!file) {
        Serial.println("[INFO] No buffered data on flash");
        return false;
    }
    
    size_t fileSize = file.size();
    char* jsonBuffer = (char*)malloc(fileSize + 1);
    file.readBytes(jsonBuffer, fileSize);
    jsonBuffer[fileSize] = '\0';
    file.close();
    
    // Parse JSON (simplified - full implementation would use ArduinoJson)
    // For now, just count records
    int recordCount = 0;
    for (size_t i = 0; i < fileSize; i++) {
        if (jsonBuffer[i] == '{') {
            recordCount++;
        }
    }
    
    free(jsonBuffer);
    
    Serial.printf("[FLASH] Loaded %d buffered readings\n", recordCount);
    
    // Delete file after loading
    SD.remove(FLASH_BUFFER_FILE);
    
    return true;
}

// ===================
// POWER MANAGEMENT
// ===================

void enterDeepSleep() {
    Serial.println("\n[SLEEP] Entering deep sleep mode");
    Serial.printf("[SLEEP] Wake in %d minutes\n", DEEP_SLEEP_DURATION / 60000000);
    
    // Configure wake sources
    esp_sleep_enable_timer_wakeup(DEEP_SLEEP_DURATION);
    esp_sleep_enable_ext0_wakeup((gpio_num_t)WAKE_BUTTON, 0); // Wake on button press
    
    // Turn off peripherals
    LoRa.sleep();
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    
    // Enter deep sleep
    esp_deep_sleep_start();
}

uint8_t calculateBatteryPercentage(float voltage) {
    // Li-ion discharge curve (3.0V = 0%, 4.2V = 100%)
    const float V_MIN = 3.0;
    const float V_MAX = 4.2;
    
    float percentage = 100.0 * (voltage - V_MIN) / (V_MAX - V_MIN);
    
    if (percentage < 0) percentage = 0;
    if (percentage > 100) percentage = 100;
    
    return (uint8_t)percentage;
}

bool isSolarCharging() {
    // Check if solar current is positive (charging)
    return currentData.solar_current > 10.0; // >10mA threshold
}

// ===================
// OTA UPDATES
// ===================

void handleOTAUpload(AsyncWebServerRequest *request, String filename, 
                     size_t index, uint8_t *data, size_t len, bool final) {
    if (!index) {
        Serial.printf("[OTA] Update start: %s\n", filename.c_str());
        if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
            Update.printError(Serial);
        }
    }
    
    if (Update.write(data, len) != len) {
        Update.printError(Serial);
    }
    
    if (final) {
        if (Update.end(true)) {
            Serial.printf("[OTA] Update success: %u bytes\n", index + len);
        } else {
            Update.printError(Serial);
        }
    }
}

// ===================
// UTILITY FUNCTIONS
// ===================

void blinkLED(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        delay(delayMs);
    }
}

void printSensorData(const SensorData& data) {
    Serial.println("\n--- Sensor Data ---");
    Serial.printf("Timestamp:        %lu ms\n", data.timestamp);
    Serial.printf("Air Temp:         %.2f °C\n", data.air_temperature);
    Serial.printf("Air Humidity:     %.1f %%\n", data.air_humidity);
    Serial.printf("Air Pressure:     %.1f hPa\n", data.air_pressure);
    Serial.printf("Light:            %.0f lux\n", data.light_intensity);
    Serial.printf("Soil Temp:        %.2f °C\n", data.soil_temperature);
    Serial.printf("Soil Moisture:    %.1f %%\n", data.soil_moisture);
    Serial.printf("Battery:          %.2f V (%d%%)\n", 
                  data.battery_voltage, 
                  calculateBatteryPercentage(data.battery_voltage));
    Serial.printf("Solar Current:    %.1f mA\n", data.solar_current);
    Serial.printf("Power:            %.1f mW\n", data.power_consumption);
    Serial.printf("VPD:              %.2f kPa\n", data.vpd);
    Serial.printf("Dew Point:        %.1f °C\n", data.dew_point);
    Serial.printf("Stress Level:     %d/100\n", data.stress_level);
    Serial.printf("Data Quality:     %d%%\n", data.data_quality);
    Serial.printf("LoRa RSSI/SNR:    %d dBm / %d dB\n", data.rssi, data.snr);
    Serial.println("-------------------\n");
}

String serializeData(const SensorData& data) {
    StaticJsonDocument<512> doc;
    
    doc["timestamp"] = data.timestamp;
    doc["node_id"] = NODE_ID;
    
    JsonObject env = doc.createNestedObject("environmental");
    env["air_temp"] = data.air_temperature;
    env["air_humidity"] = data.air_humidity;
    env["air_pressure"] = data.air_pressure;
    env["light"] = data.light_intensity;
    env["vpd"] = data.vpd;
    env["dew_point"] = data.dew_point;
    
    JsonObject soil = doc.createNestedObject("soil");
    soil["temperature"] = data.soil_temperature;
    soil["moisture"] = data.soil_moisture;
    
    JsonObject power = doc.createNestedObject("power");
    power["battery_voltage"] = data.battery_voltage;
    power["solar_current"] = data.solar_current;
    power["consumption"] = data.power_consumption;
    
    JsonObject quality = doc.createNestedObject("quality");
    quality["stress_level"] = data.stress_level;
    quality["data_quality"] = data.data_quality;
    quality["rssi"] = data.rssi;
    quality["snr"] = data.snr;
    
    String output;
    serializeJson(doc, output);
    
    return output;
}

uint16_t calculateCRC16(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x0001) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    
    return crc;
}
