/**
 * @file storage_init.h
 * @brief Header for the storage services initialization.
 */
#ifndef STORAGE_INIT_H
#define STORAGE_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all storage services.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t storage_services_initialize(void);

#endif // STORAGE_INIT_H
