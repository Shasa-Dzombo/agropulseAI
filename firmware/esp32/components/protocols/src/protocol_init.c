/**
 * @file protocol_init.c
 * @brief Initializes all protocol services.
 */

#include "protocol_init.h"
#include "esp_log.h"
#include "wifi_manager.h"
#include "mqtt_client.h"
#include "http_server.h"
#include "dns_server.h"
#include "ble_manager.h"

static const char *TAG = "PROTOCOL_INIT";

esp_err_t protocol_services_initialize(void) {
    esp_err_t ret;

    // 1. Initialize the BLE Manager
    // This allows for local configuration and diagnostics.
    ret = ble_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize BLE Manager (0x%x)", ret);
        // Non-critical, we can continue without BLE.
    } else {
        ESP_LOGI(TAG, "BLE Manager initialized.");
    }

    // 2. Initialize the Wi-Fi Manager
    // This service handles Wi-Fi connection and reconnection.
    ret = wifi_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Wi-Fi Manager (0x%x)", ret);
        // This is often a critical failure for an IoT device.
        return ret;
    } else {
        ESP_LOGI(TAG, "Wi-Fi Manager initialized.");
    }

    // 3. Initialize the MQTT Client
    // This service handles the connection to the MQTT broker.
    ret = mqtt_client_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize MQTT Client (0x%x)", ret);
        return ret;
    } else {
        ESP_LOGI(TAG, "MQTT Client initialized.");
    }

    // The HTTP and DNS servers are started by the wifi_manager when it enters AP mode.

    // Start the Wi-Fi connection process.
    wifi_manager_connect();

    ESP_LOGI(TAG, "Protocol services initialized.");
    return ESP_OK;
}
