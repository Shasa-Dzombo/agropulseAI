/**
 * @file application_init.h
 * @brief Header for the main application logic initialization.
 */
#ifndef APPLICATION_INIT_H
#define APPLICATION_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes the main application logic.
 *
 * This function starts the tasks responsible for the device's primary
 * functions, such as reading sensors and publishing data.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t application_initialize(void);

#endif // APPLICATION_INIT_H
