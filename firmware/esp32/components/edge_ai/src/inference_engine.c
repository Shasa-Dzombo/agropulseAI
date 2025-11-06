/**
 * @file inference_engine.c
 * @brief Simulated implementation of the inference engine.
 */

#include "inference_engine.h"
#include "esp_log.h"
#include "model_manager.h"

static const char *TAG = "INFERENCE_ENGINE";

esp_err_t inference_engine_init(void) {
    ESP_LOGI(TAG, "Inference engine initialized.");
    // In a real scenario, this would initialize the TFLite Micro interpreter
    return ESP_OK;
}

esp_err_t inference_engine_run(const preprocessed_data_t* input, model_output_t* output) {
    const uint8_t* model_data = model_manager_get_model_data();
    size_t model_size = model_manager_get_model_size();

    if (model_data == NULL || model_size == 0) {
        ESP_LOGE(TAG, "No model loaded, cannot run inference.");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Running inference with model of size %d bytes", model_size);

    // This is where the TFLite Micro interpreter would be invoked with the
    // input data and the model_data buffer.
    // For simulation, we'll continue to use random data based on input.

    // Simulate some dependency on the input
    float input_factor = (input->temperature + input->humidity + input->light_intensity) / 300.0f;

    output->predictions[0] = (float)(esp_random() % 100) / 100.0f * (1.0 - input_factor); // healthy
    output->predictions[1] = (float)(esp_random() % 100) / 100.0f * input_factor; // mild_stress
    output->predictions[2] = (float)(esp_random() % 100) / 100.0f * (input_factor / 2.0); // high_stress

    // Normalize the outputs
    float sum = output->predictions[0] + output->predictions[1] + output->predictions[2];
    if (sum > 0) {
        output->predictions[0] /= sum;
        output->predictions[1] /= sum;
        output->predictions[2] /= sum;
    }

    ESP_LOGI(TAG, "Inference complete. Results: H=%.2f, M=%.2f, S=%.2f",
             output->predictions[0], output->predictions[1], output->predictions[2]);

    return ESP_OK;
}
