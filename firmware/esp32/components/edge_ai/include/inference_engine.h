/**
 * @file inference_engine.h
 * @brief An interface for running ML model inferences.
 *
 * This component provides an abstraction layer for a machine learning
 * inference framework, such as TensorFlow Lite for Microcontrollers.
 *
 * Features:
 * - Loading a model from flash.
 * - Running an inference on pre-processed data.
 * - Retrieving the model's output.
 *
 * NOTE: This is a simulated driver.
 */
#ifndef INFERENCE_ENGINE_H
#define INFERENCE_ENGINE_H

#include "esp_err.h"
#include "preprocessor.h" // For model_input_t

// Define the structure for the model's output
#define OUTPUT_CLASS_COUNT 3
typedef struct {
    float predictions[OUTPUT_CLASS_COUNT]; // e.g., probabilities for [healthy, mild_stress, high_stress]
} model_output_t;

/**
 * @brief Initializes the inference engine.
 *
 * This function would typically load the ML model from flash memory into RAM
 * and prepare the interpreter (e.g., TFLite Micro).
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: If the model cannot be loaded or the engine fails to start.
 */
esp_err_t inference_engine_init(void);

/**
 * @brief Runs an inference using the loaded model.
 *
 * @param[in] input The pre-processed input data for the model.
 * @param[out] output The structure to be filled with the model's output.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t inference_engine_run(const model_input_t* input, model_output_t* output);

#endif // INFERENCE_ENGINE_H
