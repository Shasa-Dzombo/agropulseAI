/**
 * @file system_init.h
 * @brief Header for the system services initialization.
 */
#ifndef SYSTEM_INIT_H
#define SYSTEM_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all system services.
 *
 * This function orchestrates the initialization of system-level services,
 * such as the time manager for NTP sync.
 *
 * @return
 *     - ESP_OK: If all system services were initialized successfully.
 *     - ESP_FAIL: If any of the system services failed to initialize.
 */
esp_err_t system_services_initialize(void);

#endif // SYSTEM_INIT_H
