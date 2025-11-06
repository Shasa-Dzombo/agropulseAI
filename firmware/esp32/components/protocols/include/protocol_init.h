/**
 * @file protocol_init.h
 * @brief Header for the protocol services initialization.
 */
#ifndef PROTOCOL_INIT_H
#define PROTOCOL_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all protocol services.
 *
 * This function orchestrates the initialization of protocol-level services,
 * such as the Wi-Fi manager and MQTT client.
 *
 * @return
 *     - ESP_OK: If all protocol services were initialized successfully.
 *     - ESP_FAIL: If any of the protocol services failed to initialize.
 */
esp_err_t protocol_services_initialize(void);

#endif // PROTOCOL_INIT_H
