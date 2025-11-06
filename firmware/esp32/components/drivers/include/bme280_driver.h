/**
 * @file bme280_driver.h
 * @brief Driver for the BME280 temperature, humidity, and pressure sensor.
 *
 * This driver provides an interface to read data from a BME280 sensor
 * over the I2C bus. It depends on the `i2c_manager` to be initialized.
 *
 * Features:
 * - Initializes the BME280 sensor.
 * - Reads temperature, humidity, and pressure.
 * - Uses a 3rd-party BME280 library.
 */
#ifndef BME280_DRIVER_H
#define BME280_DRIVER_H

#include "esp_err.h"

/**
 * @brief A structure to hold a BME280 sensor reading.
 */
typedef struct {
    float temperature;
    float humidity;
    float pressure;
} bme280_data_t;

/**
 * @brief Initializes the BME280 sensor.
 *
 * This function configures the sensor and verifies communication over I2C.
 * It assumes `i2c_manager_init()` has already been called.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: If the sensor cannot be found or initialized.
 */
esp_err_t bme280_driver_init(void);

/**
 * @brief Reads the latest data from the BME280 sensor.
 *
 * @param[out] data Pointer to a `bme280_data_t` struct to be filled with sensor readings.
 * @return
 *     - ESP_OK: If the data was read successfully.
 *     - ESP_FAIL: If an error occurred during the reading.
 */
esp_err_t bme280_driver_read_data(bme280_data_t *data);

#endif // BME280_DRIVER_H
