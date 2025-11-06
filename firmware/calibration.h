/**
 * Sensor Calibration Utilities
 * ============================
 * 
 * Tools for calibrating sensors in the field.
 * 
 * Calibration procedures:
 * 1. Soil Moisture: Dry air vs. water immersion
 * 2. Battery: Known voltmeter reading
 * 3. Light: Reference luxmeter
 * 4. LoRa: Signal strength mapping
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <Arduino.h>
#include <Preferences.h>

class SensorCalibration {
private:
    Preferences prefs;
    
public:
    SensorCalibration() {}
    
    // Initialize calibration storage
    bool begin() {
        return prefs.begin("calibration", false);
    }
    
    void end() {
        prefs.end();
    }
    
    // ===== Soil Moisture Calibration =====
    
    struct SoilMoistureCalib {
        float dry_value;   // ADC in dry air
        float wet_value;   // ADC in water
        bool valid;
    };
    
    void calibrateSoilMoistureDry(float adcValue) {
        prefs.putFloat("soil_dry", adcValue);
        Serial.printf("[CALIB] Soil moisture DRY: %.0f\n", adcValue);
    }
    
    void calibrateSoilMoistureWet(float adcValue) {
        prefs.putFloat("soil_wet", adcValue);
        Serial.printf("[CALIB] Soil moisture WET: %.0f\n", adcValue);
    }
    
    SoilMoistureCalib getSoilMoistureCalib() {
        SoilMoistureCalib calib;
        calib.dry_value = prefs.getFloat("soil_dry", 3000.0);
        calib.wet_value = prefs.getFloat("soil_wet", 1000.0);
        calib.valid = prefs.isKey("soil_dry") && prefs.isKey("soil_wet");
        return calib;
    }
    
    // ===== Battery Voltage Calibration =====
    
    void calibrateBatteryVoltage(float measuredADC, float actualVoltage) {
        // Calculate correction factor
        float expectedADC = (actualVoltage / 2.0) / 3.3 * 4095.0;
        float correction = actualVoltage / (measuredADC / 4095.0 * 3.3 * 2.0);
        
        prefs.putFloat("batt_corr", correction);
        Serial.printf("[CALIB] Battery correction factor: %.3f\n", correction);
        Serial.printf("[CALIB] Measured: %.0f ADC, Actual: %.2fV\n", 
                     measuredADC, actualVoltage);
    }
    
    float getBatteryCorrection() {
        return prefs.getFloat("batt_corr", 1.0);
    }
    
    // ===== Light Sensor Calibration =====
    
    void calibrateLightSensor(float measuredLux, float referenceLux) {
        float correction = referenceLux / measuredLux;
        prefs.putFloat("light_corr", correction);
        Serial.printf("[CALIB] Light correction factor: %.3f\n", correction);
    }
    
    float getLightCorrection() {
        return prefs.getFloat("light_corr", 1.0);
    }
    
    // ===== Temperature Offset =====
    
    void calibrateTemperatureOffset(float offset) {
        prefs.putFloat("temp_offset", offset);
        Serial.printf("[CALIB] Temperature offset: %.2f°C\n", offset);
    }
    
    float getTemperatureOffset() {
        return prefs.getFloat("temp_offset", 0.0);
    }
    
    // ===== Humidity Offset =====
    
    void calibrateHumidityOffset(float offset) {
        prefs.putFloat("hum_offset", offset);
        Serial.printf("[CALIB] Humidity offset: %.1f%%\n", offset);
    }
    
    float getHumidityOffset() {
        return prefs.getFloat("hum_offset", 0.0);
    }
    
    // ===== LoRa RSSI Mapping =====
    
    struct LoRaDistanceMapping {
        float distance_m;
        int rssi_dbm;
    };
    
    void addLoRaDistancePoint(float distance, int rssi) {
        char key[32];
        snprintf(key, sizeof(key), "lora_d%.0f", distance);
        prefs.putInt(key, rssi);
        Serial.printf("[CALIB] LoRa @ %.0fm: %d dBm\n", distance, rssi);
    }
    
    int estimateDistance(int rssi) {
        // Path loss model: RSSI = -10*n*log10(d) + A
        // n = path loss exponent (2-4 for rural)
        // A = RSSI at 1m
        
        int rssi_1m = prefs.getInt("lora_d1", -40); // Default: -40dBm @ 1m
        float n = 2.5; // Rural environment
        
        float distance = pow(10, (rssi_1m - rssi) / (10.0 * n));
        return (int)distance;
    }
    
    // ===== Factory Reset =====
    
    void factoryReset() {
        prefs.clear();
        Serial.println("[CALIB] Factory reset complete");
    }
    
    // ===== Print All Calibrations =====
    
    void printCalibrations() {
        Serial.println("\n===== CALIBRATION STATUS =====");
        
        SoilMoistureCalib soil = getSoilMoistureCalib();
        Serial.printf("Soil Moisture: %s\n", soil.valid ? "CALIBRATED" : "DEFAULT");
        Serial.printf("  Dry: %.0f, Wet: %.0f\n", soil.dry_value, soil.wet_value);
        
        float battCorr = getBatteryCorrection();
        Serial.printf("Battery: %.3f\n", battCorr);
        
        float lightCorr = getLightCorrection();
        Serial.printf("Light: %.3f\n", lightCorr);
        
        float tempOffset = getTemperatureOffset();
        Serial.printf("Temperature offset: %.2f°C\n", tempOffset);
        
        float humOffset = getHumidityOffset();
        Serial.printf("Humidity offset: %.1f%%\n", humOffset);
        
        Serial.println("==============================\n");
    }
};

// ===== Interactive Calibration Menu =====

class CalibrationMenu {
private:
    SensorCalibration& calib;
    
public:
    CalibrationMenu(SensorCalibration& c) : calib(c) {}
    
    void run() {
        Serial.println("\n");
        Serial.println("╔════════════════════════════════════╗");
        Serial.println("║   SENSOR CALIBRATION MENU          ║");
        Serial.println("╠════════════════════════════════════╣");
        Serial.println("║  1. Calibrate Soil Moisture (DRY)  ║");
        Serial.println("║  2. Calibrate Soil Moisture (WET)  ║");
        Serial.println("║  3. Calibrate Battery Voltage      ║");
        Serial.println("║  4. Calibrate Light Sensor         ║");
        Serial.println("║  5. Calibrate Temperature          ║");
        Serial.println("║  6. Calibrate Humidity             ║");
        Serial.println("║  7. LoRa Distance Mapping          ║");
        Serial.println("║  8. View Calibrations              ║");
        Serial.println("║  9. Factory Reset                  ║");
        Serial.println("║  0. Exit                           ║");
        Serial.println("╚════════════════════════════════════╝");
        Serial.print("\nSelect option: ");
        
        // Wait for input
        while (!Serial.available()) {
            delay(100);
        }
        
        int choice = Serial.parseInt();
        Serial.println(choice);
        
        handleChoice(choice);
    }
    
private:
    void handleChoice(int choice) {
        switch (choice) {
            case 1:
                calibrateSoilDry();
                break;
            case 2:
                calibrateSoilWet();
                break;
            case 3:
                calibrateBattery();
                break;
            case 4:
                calibrateLight();
                break;
            case 5:
                calibrateTemperature();
                break;
            case 6:
                calibrateHumidity();
                break;
            case 7:
                calibrateLoRa();
                break;
            case 8:
                calib.printCalibrations();
                break;
            case 9:
                confirmFactoryReset();
                break;
            case 0:
                Serial.println("Exiting calibration menu...\n");
                return;
            default:
                Serial.println("Invalid option\n");
                break;
        }
        
        delay(2000);
        run(); // Show menu again
    }
    
    void calibrateSoilDry() {
        Serial.println("\n[CALIB] Soil Moisture - DRY");
        Serial.println("Remove sensor from soil (in air)");
        Serial.println("Reading in 5 seconds...");
        
        for (int i = 5; i > 0; i--) {
            Serial.printf("%d...\n", i);
            delay(1000);
        }
        
        // Read ADC
        uint32_t sum = 0;
        for (int i = 0; i < 50; i++) {
            sum += analogRead(SOIL_MOISTURE_PIN);
            delay(20);
        }
        float adcValue = sum / 50.0;
        
        calib.calibrateSoilMoistureDry(adcValue);
        Serial.println("✓ Dry calibration complete\n");
    }
    
    void calibrateSoilWet() {
        Serial.println("\n[CALIB] Soil Moisture - WET");
        Serial.println("Immerse sensor in water");
        Serial.println("Reading in 5 seconds...");
        
        for (int i = 5; i > 0; i--) {
            Serial.printf("%d...\n", i);
            delay(1000);
        }
        
        // Read ADC
        uint32_t sum = 0;
        for (int i = 0; i < 50; i++) {
            sum += analogRead(SOIL_MOISTURE_PIN);
            delay(20);
        }
        float adcValue = sum / 50.0;
        
        calib.calibrateSoilMoistureWet(adcValue);
        Serial.println("✓ Wet calibration complete\n");
    }
    
    void calibrateBattery() {
        Serial.println("\n[CALIB] Battery Voltage");
        Serial.println("Enter actual voltage from voltmeter (e.g., 3.85): ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        float actualVoltage = Serial.parseFloat();
        
        // Read ADC
        uint32_t sum = 0;
        for (int i = 0; i < 50; i++) {
            sum += analogRead(BATTERY_VOLTAGE_PIN);
            delay(20);
        }
        float adcValue = sum / 50.0;
        
        calib.calibrateBatteryVoltage(adcValue, actualVoltage);
        Serial.println("✓ Battery calibration complete\n");
    }
    
    void calibrateLight() {
        Serial.println("\n[CALIB] Light Sensor");
        Serial.println("Enter reference lux value from luxmeter: ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        float referenceLux = Serial.parseFloat();
        
        // Read from BH1750
        float measuredLux = lightMeter.readLightLevel();
        
        calib.calibrateLightSensor(measuredLux, referenceLux);
        Serial.println("✓ Light calibration complete\n");
    }
    
    void calibrateTemperature() {
        Serial.println("\n[CALIB] Temperature");
        Serial.println("Enter offset in °C (e.g., +0.5 or -1.2): ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        float offset = Serial.parseFloat();
        calib.calibrateTemperatureOffset(offset);
        Serial.println("✓ Temperature offset set\n");
    }
    
    void calibrateHumidity() {
        Serial.println("\n[CALIB] Humidity");
        Serial.println("Enter offset in % (e.g., +2.0 or -3.5): ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        float offset = Serial.parseFloat();
        calib.calibrateHumidityOffset(offset);
        Serial.println("✓ Humidity offset set\n");
    }
    
    void calibrateLoRa() {
        Serial.println("\n[CALIB] LoRa Distance Mapping");
        Serial.println("Enter distance in meters: ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        float distance = Serial.parseFloat();
        
        Serial.println("Send LoRa packet from gateway...");
        Serial.println("Waiting for packet (30 seconds)...");
        
        unsigned long startTime = millis();
        int rssi = 0;
        bool received = false;
        
        while (millis() - startTime < 30000) {
            int packetSize = LoRa.parsePacket();
            if (packetSize > 0) {
                rssi = LoRa.packetRssi();
                received = true;
                break;
            }
            delay(100);
        }
        
        if (received) {
            calib.addLoRaDistancePoint(distance, rssi);
            Serial.println("✓ LoRa calibration point added\n");
        } else {
            Serial.println("✗ No packet received\n");
        }
    }
    
    void confirmFactoryReset() {
        Serial.println("\n[WARN] Factory Reset");
        Serial.println("This will erase ALL calibrations!");
        Serial.println("Type 'YES' to confirm: ");
        
        while (!Serial.available()) {
            delay(100);
        }
        
        String confirm = Serial.readStringUntil('\n');
        confirm.trim();
        
        if (confirm == "YES") {
            calib.factoryReset();
            Serial.println("✓ Factory reset complete\n");
        } else {
            Serial.println("✗ Cancelled\n");
        }
    }
};

#endif // CALIBRATION_H
