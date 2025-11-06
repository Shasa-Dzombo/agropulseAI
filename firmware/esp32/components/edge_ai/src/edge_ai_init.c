/**
 * @file edge_ai_init.c
 * @brief Initializes all Edge AI services.
 */

#include "edge_ai_init.h"
#include "esp_log.h"
#include "preprocessor.h"
#include "inference_engine.h"
#include "model_manager.h"

static const char *TAG = "EDGE_AI_INIT";

esp_err_t edge_ai_services_initialize(void) {
    esp_err_t ret;

    ret = model_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Model Manager (0x%x)", ret);
        return ret;
    }

    ret = preprocessor_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Preprocessor (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Preprocessor initialized.");

    ret = inference_engine_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize Inference Engine (0x%x)", ret);
        return ret;
    }
    ESP_LOGI(TAG, "Inference Engine initialized.");

    ESP_LOGI(TAG, "Edge AI services initialized.");
    return ESP_OK;
}
