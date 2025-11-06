/**
 * @file system_init.c
 * @brief Initializes all system services.
 */

#include "system_init.h"
#include "esp_log.h"
#include "time_manager.h"
#include "ota_manager.h"
#include "task_watchdog.h"
#include "power_manager.h"

static const char *TAG = "SYSTEM_INIT";

esp_err_t system_services_initialize(void) {
    esp_err_t ret;

    // 1. Initialize the Task Watchdog first
    ret = task_watchdog_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Task Watchdog (0x%x)", ret);
        // This is critical, we might want to halt
    } else {
        ESP_LOGI(TAG, "Task Watchdog initialized.");
    }

    // 2. Initialize the Power Manager
    ret = power_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Power Manager (0x%x)", ret);
    } else {
        ESP_LOGI(TAG, "Power Manager initialized.");
    }

    // 3. Initialize the Time Manager
    ret = time_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Time Manager (0x%x)", ret);
    } else {
        ESP_LOGI(TAG, "Time Manager initialized.");
    }

    // 4. Initialize the OTA Manager
    ret = ota_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize OTA Manager (0x%x)", ret);
    } else {
        ESP_LOGI(TAG, "OTA Manager initialized.");
    }

    ESP_LOGI(TAG, "System services initialized.");
    return ESP_OK;
}
