/**
 * @file security_init.c
 * @brief Initializes all security services.
 */

#include "security_init.h"
#include "esp_log.h"
#include "secure_element.h"
#include "ota_verifier.h"
#include "security_manager.h"

static const char *TAG = "SECURITY_INIT";

esp_err_t security_services_initialize(void) {
    esp_err_t ret;

    // 1. Initialize the Security Manager
    // This handles key generation/storage and cryptographic operations.
    ret = security_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Security Manager (0x%x)", ret);
        // This is a critical failure.
        return ret;
    } else {
        ESP_LOGI(TAG, "Security Manager initialized.");
    }

    // 2. Initialize the Secure Element (Simulated)
    // This provides hardware-backed key storage and crypto operations.
    ret = secure_element_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Secure Element (0x%x)", ret);
        // This could be a critical failure depending on the application's security requirements.
        return ret;
    } else {
        ESP_LOGI(TAG, "Secure Element initialized.");
    }

    // 3. Initialize the OTA Verifier
    // This module handles signature checks for firmware updates.
    ret = ota_verifier_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize OTA Verifier (0x%x)", ret);
        return ret;
    } else {
        ESP_LOGI(TAG, "OTA Verifier initialized.");
    }

    ESP_LOGI(TAG, "Security services initialized.");
    return ESP_OK;
}
