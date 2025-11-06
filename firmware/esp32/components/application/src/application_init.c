/**
 * @file application_init.c
 * @brief Initializes the main application logic.
 */

#include "application_init.h"
#include "esp_log.h"
#include "i2c_manager.h" // Initialize the bus for sensors
#include "sensor_sampler.h"
#include "data_publisher.h"
#include "command_processor.h"
#include "status_publisher.h"
#include "device_shadow.h"

static const char *TAG = "APP_INIT";

esp_err_t application_initialize(void) {
    esp_err_t ret;

    // 1. Initialize I2C bus for sensors
    ret = i2c_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize I2C manager (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "I2C Manager initialized for application.");

    // 2. Initialize the Command Processor
    // This module is responsible for processing commands.
    ret = command_processor_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Command Processor (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Command Processor initialized.");

    ret = device_shadow_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Device Shadow (0x%x)", ret);
        return ret;
    }

    // 3. Initialize the Sensor Sampler
    // This module is responsible for reading data from the sensors.
    ret = sensor_sampler_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Sensor Sampler (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Sensor Sampler initialized.");

    // 4. Initialize the Data Publisher
    // This module is responsible for publishing the sensor data.
    ret = data_publisher_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Data Publisher (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Data Publisher initialized.");

    // 5. Initialize the Status Publisher
    // This module is responsible for publishing the application status.
    ret = status_publisher_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Status Publisher (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Status Publisher initialized.");

    ESP_LOGI(TAG, "Application logic initialized.");
    return ESP_OK;
}

esp_err_t application_services_initialize(void) {
    esp_err_t ret;

    ret = application_initialize();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize application (0x%x)", ret);
        return ret;
    }

    ESP_LOGI(TAG, "Application services initialized.");
    return ESP_OK;
}
