#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include "esp_err.h"

typedef enum {
    NETWORK_PREF_WIFI_ONLY,
    NETWORK_PREF_CELLULAR_ONLY,
    NETWORK_PREF_WIFI_PREFERRED,
    NETWORK_PREF_CELLULAR_PREFERRED,
} network_preference_t;

/**
 * @brief Initializes the network manager.
 *
 * @param preference The desired network connection preference.
 * @return ESP_OK on success.
 */
esp_err_t network_manager_init(network_preference_t preference);

/**
 * @brief Starts the network connection process based on the preference.
 *
 * @return ESP_OK on success.
 */
esp_err_t network_manager_connect(void);

#endif // NETWORK_MANAGER_H
