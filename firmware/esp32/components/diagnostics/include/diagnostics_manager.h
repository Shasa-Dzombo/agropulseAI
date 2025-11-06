#ifndef DIAGNOSTICS_MANAGER_H
#define DIAGNOSTICS_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the diagnostics manager.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t diagnostics_manager_init(void);

/**
 * @brief Gathers system diagnostics and publishes them via MQTT.
 *
 * This function collects a wide range of system information, formats it into a
 * JSON payload, and publishes it to the device's diagnostics topic.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t diagnostics_manager_publish(void);

#endif // DIAGNOSTICS_MANAGER_H
