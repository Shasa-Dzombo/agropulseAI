/**
 * @file sensor_sampler.h
 * @brief A component for sampling data from various sensors.
 *
 * This module creates a periodic task that reads data from attached sensors
 * (e.g., soil moisture, temperature, humidity) at a configurable interval.
 *
 * Features:
 * - A main task that orchestrates sensor readings.
 * - Placeholder functions for reading specific sensor types.
 * - Uses the configuration from `config_manager` to determine the sample rate.
 * - (Future) Could post raw sensor data to an internal event queue for processing.
 */
#ifndef SENSOR_SAMPLER_H
#define SENSOR_SAMPLER_H

#include "esp_err.h"

/**
 * @brief Initializes the sensor sampler component.
 *
 * This function starts the main sensor sampling task.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t sensor_sampler_init(void);

/**
 * @brief A structure to hold a complete sensor reading.
 */
typedef struct {
    float temperature;
    float humidity;
    float soil_moisture;
    float light_lux; // New field for light sensor
} sensor_data_t;


#endif // SENSOR_SAMPLER_H
