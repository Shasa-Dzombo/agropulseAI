/**
 * @file bh1750_driver.h
 * @brief Driver for the BH1750 light sensor.
 *
 * This driver provides an interface to read ambient light levels in lux
 * from a BH1750 sensor connected via I2C.
 */
#ifndef BH1750_DRIVER_H
#define BH1750_DRIVER_H

#include "esp_err.h"
#include "i2c_manager.h"

/**
 * @brief Initializes the BH1750 sensor.
 *
 * @param[in] i2c_port The I2C port the sensor is on.
 * @param[in] i2c_addr The I2C address of the sensor.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t bh1750_init(i2c_port_t i2c_port, uint8_t i2c_addr);

/**
 * @brief Reads the ambient light level from the sensor.
 *
 * @param[out] lux Pointer to store the light level in lux.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t bh1750_read_lux(float* lux);

#endif // BH1750_DRIVER_H
