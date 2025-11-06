#ifndef PERIPHERAL_INIT_H
#define PERIPHERAL_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all peripheral managers.
 *
 * This function initializes I2C, SPI, and other hardware buses required by the drivers.
 * It should be called before initializing any device drivers.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_initialize(void);

#endif // PERIPHERAL_INIT_H
