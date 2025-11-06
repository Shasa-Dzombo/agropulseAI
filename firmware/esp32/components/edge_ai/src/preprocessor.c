/**
 * @file preprocessor.c
 * @brief Simulated implementation of the data preprocessor.
 */

#include "preprocessor.h"
#include "esp_log.h"

static const char *TAG = "PREPROCESSOR_SIM";

// These would be learned from a training dataset
#define TEMP_MEAN 25.0f
#define TEMP_STD  5.0f
#define HUMID_MEAN 60.0f
#define HUMID_STD 10.0f
#define MOIST_MEAN 50.0f
#define MOIST_STD 15.0f

esp_err_t preprocessor_init(void) {
    ESP_LOGI(TAG, "Preprocessor initialized (simulated).");
    return ESP_OK;
}

esp_err_t preprocessor_run(const sensor_data_t* raw_data, model_input_t* model_input) {
    if (raw_data == NULL || model_input == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Running z-score normalization on sensor data.");

    // Perform z-score normalization (value - mean) / std_dev
    model_input->features[0] = (raw_data->temperature - TEMP_MEAN) / TEMP_STD;
    model_input->features[1] = (raw_data->humidity - HUMID_MEAN) / HUMID_STD;
    model_input->features[2] = (raw_data->soil_moisture - MOIST_MEAN) / MOIST_STD;

    ESP_LOGD(TAG, "Normalized features: [%.2f, %.2f, %.2f]",
             model_input->features[0],
             model_input->features[1],
             model_input->features[2]);

    return ESP_OK;
}
