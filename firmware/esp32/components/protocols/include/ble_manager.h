#ifndef BLE_MANAGER_H
#define BLE_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the BLE manager.
 * 
 * This function sets up the BLE stack, configures the GATT server,
 * defines services and characteristics, and starts advertising.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t ble_manager_init(void);

/**
 * @brief Sends a notification with the latest sensor data over BLE.
 * 
 * This function should be called when new sensor data is available. It will
 * update the value of the sensor data characteristic and notify any subscribed
 * clients.
 * 
 * @param data A pointer to the sensor_data_t struct containing the latest data.
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t ble_manager_notify_sensor_data(const sensor_data_t* data);


#endif // BLE_MANAGER_H
