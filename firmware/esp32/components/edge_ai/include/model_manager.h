/**
 * @file model_manager.h
 * @brief Manages machine learning models on the device.
 *
 * This module is responsible for finding, loading, and verifying
 * machine learning models stored on the device's filesystem (SPIFFS).
 * It provides a central point of access to the currently active model.
 */
#ifndef MODEL_MANAGER_H
#define MODEL_MANAGER_H

#include "esp_err.h"

#define MAX_MODEL_PATH_LEN 64

typedef struct {
    char path[MAX_MODEL_PATH_LEN];
    uint8_t* data;
    size_t size;
    // In a real scenario, you'd have version info, metadata, etc.
} ml_model_t;

/**
 * @brief Initializes the model manager.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t model_manager_init(void);

/**
 * @brief Loads the active machine learning model from SPIFFS.
 *
 * This function will look for a model file at a predefined path and
 * load it into memory.
 *
 * @return
 *     - ESP_OK: If the model was loaded successfully.
 *     - ESP_FAIL: If the model could not be found or loaded.
 */
esp_err_t model_manager_load_model(const char* model_path);

/**
 * @brief Gets a pointer to the currently active model.
 *
 * @return A pointer to the ml_model_t struct, or NULL if no model is loaded.
 */
const ml_model_t* model_manager_get_active_model(void);

/**
 * @brief Unloads the current model and frees associated memory.
 */
void model_manager_unload_current_model(void);

#endif // MODEL_MANAGER_H
