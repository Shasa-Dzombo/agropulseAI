/**
 * @file storage_init.c
 * @brief Initializes all storage services.
 */

#include "storage_init.h"
#include "esp_log.h"
#include "data_logger.h"

static const char *TAG = "STORAGE_INIT";

esp_err_t storage_services_initialize(void) {
    esp_err_t ret;

    // Initialize the data logger, which in turn initializes SPIFFS
    ret = data_logger_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Data Logger (0x%x)", ret);
        return ret;
    }

    ESP_LOGI(TAG, "Storage services initialized.");
    return ESP_OK;
}
