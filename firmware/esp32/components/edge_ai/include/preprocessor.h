/**
 * @file preprocessor.h
 * @brief A component for pre-processing sensor data for ML models.
 *
 * This module provides functions to transform raw sensor data into a format
 * suitable for an inference engine (e.g., normalization, feature scaling).
 *
 * NOTE: This is a simulated implementation.
 */
#ifndef PREPROCESSOR_H
#define PREPROCESSOR_H

#include "esp_err.h"
#include "sensor_sampler.h" // For sensor_data_t

// Define the structure for the model's input tensor
#define FEATURE_COUNT 3
typedef struct {
    float features[FEATURE_COUNT]; // Normalized features
} model_input_t;

/**
 * @brief Initializes the preprocessor.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t preprocessor_init(void);

/**
 * @brief Processes raw sensor data into a model-ready input tensor.
 *
 * @param[in] raw_data Pointer to the raw sensor data.
 * @param[out] model_input Pointer to the structure to be filled with processed data.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t preprocessor_run(const sensor_data_t* raw_data, model_input_t* model_input);

#endif // PREPROCESSOR_H
