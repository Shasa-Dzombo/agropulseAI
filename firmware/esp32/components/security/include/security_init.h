/**
 * @file security_init.h
 * @brief Header for the security services initialization.
 */
#ifndef SECURITY_INIT_H
#define SECURITY_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all security services.
 *
 * This function orchestrates the initialization of security-related services,
 * such as the secure element driver.
 *
 * @return
 *     - ESP_OK: If all security services were initialized successfully.
 *     - ESP_FAIL: If any of the services failed to initialize.
 */
esp_err_t security_services_initialize(void);

#endif // SECURITY_INIT_H
