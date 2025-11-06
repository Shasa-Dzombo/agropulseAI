/**
 * @file model_manager.c
 * @brief Implementation of the model manager.
 */

#include "model_manager.h"
#include "esp_log.h"
#include <stdio.h>
#include <stdlib.h>

static const char *TAG = "MODEL_MANAGER";
static ml_model_t* active_model = NULL;

esp_err_t model_manager_init(void) {
    ESP_LOGI(TAG, "Model manager initialized.");
    // Attempt to load the default model on startup
    model_manager_load_model("/spiffs/default_model.tflite");
    return ESP_OK;
}

void model_manager_unload_current_model(void) {
    if (active_model) {
        ESP_LOGI(TAG, "Unloading model from %s", active_model->path);
        free(active_model->data);
        free(active_model);
        active_model = NULL;
    }
}

esp_err_t model_manager_load_model(const char* model_path) {
    // Unload any previously loaded model
    model_manager_unload_current_model();

    ESP_LOGI(TAG, "Attempting to load model from: %s", model_path);
    FILE* f = fopen(model_path, "rb");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open model file.");
        return ESP_FAIL;
    }

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size <= 0) {
        ESP_LOGE(TAG, "Model file is empty or invalid.");
        fclose(f);
        return ESP_FAIL;
    }

    uint8_t* model_data = (uint8_t*)malloc(size);
    if (model_data == NULL) {
        ESP_LOGE(TAG, "Failed to allocate memory for model data (%ld bytes)", size);
        fclose(f);
        return ESP_ERR_NO_MEM;
    }

    if (fread(model_data, 1, size, f) != size) {
        ESP_LOGE(TAG, "Failed to read model data from file.");
        fclose(f);
        free(model_data);
        return ESP_FAIL;
    }
    fclose(f);

    // In a real implementation, you would perform signature verification
    // or checksum validation on the model data here.
    ESP_LOGI(TAG, "Simulating model verification... OK");

    active_model = (ml_model_t*)malloc(sizeof(ml_model_t));
    if (!active_model) {
        free(model_data);
        return ESP_ERR_NO_MEM;
    }

    active_model->data = model_data;
    active_model->size = size;
    strncpy(active_model->path, model_path, MAX_MODEL_PATH_LEN - 1);

    ESP_LOGI(TAG, "Successfully loaded model '%s' (%d bytes)", active_model->path, active_model->size);

    return ESP_OK;
}

const ml_model_t* model_manager_get_active_model(void) {
    return active_model;
}
