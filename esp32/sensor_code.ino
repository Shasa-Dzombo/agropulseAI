"""
ESP32-CAM Arduino Code for AgroPulse Sensor
Detects changes in crop appearance and sends FREE alerts to backend
"""

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// AgroPulse API
const char* apiEndpoint = "https://api.agropulse.com/api/v1/sensors/alerts";
const char* apiKey = "agro_your_sensor_api_key_here";
const int farmId = 1;  // Your farm ID

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

// Variables
unsigned long lastCheckTime = 0;
const unsigned long checkInterval = 3600000; // 1 hour
float previousGreenRatio = 0.0;

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  
  // Initialize camera
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
  
  if(psramFound()){
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  Serial.println("Camera initialized");
  Serial.println("AgroPulse Sentry active!");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check every hour
  if (currentTime - lastCheckTime >= checkInterval) {
    lastCheckTime = currentTime;
    
    // Capture image
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      return;
    }
    
    // Simple AI: Calculate green ratio
    float greenRatio = calculateGreenRatio(fb);
    
    // Detect significant change (e.g., 15% reduction in green)
    if (previousGreenRatio > 0 && (previousGreenRatio - greenRatio) > 0.15) {
      Serial.println("🚨 Change detected! Sending alert...");
      sendAlert("yellow_spot_detected", "medium", 0.75);
    }
    
    previousGreenRatio = greenRatio;
    
    // Release frame buffer
    esp_camera_fb_return(fb);
    
    // Send heartbeat ping
    sendPing();
  }
  
  delay(1000);
}

float calculateGreenRatio(camera_fb_t * fb) {
  // Simple green pixel detection
  // This is a basic algorithm - real implementation would be more sophisticated
  int greenPixels = 0;
  int totalPixels = fb->width * fb->height;
  
  // Sample every 10th pixel for efficiency
  for (int i = 0; i < fb->len; i += 30) {
    uint8_t r = fb->buf[i];
    uint8_t g = fb->buf[i+1];
    uint8_t b = fb->buf[i+2];
    
    // Check if pixel is greenish
    if (g > r && g > b && g > 100) {
      greenPixels++;
    }
  }
  
  return (float)greenPixels / (totalPixels / 10.0);
}

void sendAlert(String alertType, String severity, float confidence) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    http.begin(apiEndpoint);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", apiKey);
    
    // Create JSON payload
    StaticJsonDocument<512> doc;
    doc["farm_id"] = farmId;
    doc["alert_type"] = alertType;
    doc["severity"] = severity;
    doc["confidence_score"] = confidence;
    doc["description"] = "Change detected by ESP32-CAM sensor";
    
    String jsonPayload;
    serializeJson(doc, jsonPayload);
    
    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Alert sent successfully!");
      Serial.println(response);
    } else {
      Serial.print("Error sending alert: ");
      Serial.println(httpResponseCode);
    }
    
    http.end();
  }
}

void sendPing() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    String pingUrl = "https://api.agropulse.com/api/v1/sensors/ping";
    http.begin(pingUrl);
    http.addHeader("X-API-Key", apiKey);
    
    int httpResponseCode = http.POST("");
    
    if (httpResponseCode > 0) {
      Serial.println("Ping successful");
    }
    
    http.end();
  }
}
