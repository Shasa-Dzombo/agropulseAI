#ifndef CELLULAR_MANAGER_H
#define CELLULAR_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the cellular modem.
 *
 * Sets up UART communication and the PPP network interface for the modem.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t cellular_manager_init(void);

/**
 * @brief Starts the cellular data connection.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t cellular_manager_start(void);

/**
 * @brief Stops the cellular data connection.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t cellular_manager_stop(void);

/**
 * @brief Gets the signal quality (RSSI).
 *
 * @param rssi Pointer to store the signal quality value.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t cellular_manager_get_signal_quality(int *rssi);

#endif // CELLULAR_MANAGER_H
