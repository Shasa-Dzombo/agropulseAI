/**
 * @file wifi_manager.h
 * @brief Manages the device's Wi-Fi connection.
 *
 * This component is responsible for all aspects of the Wi-Fi connection,
 * including initialization, connecting to an access point, monitoring the
 * connection status, and handling automatic reconnection.
 *
 * Features:
 * - Initializes the ESP-IDF Wi-Fi stack.
 * - Connects to the AP specified in the device configuration.
 * - Automatically attempts to reconnect if the connection is lost.
 * - Posts `SYSTEM_EVENT_WIFI_CONNECTED` and `SYSTEM_EVENT_WIFI_DISCONNECTED`
 *   to the system event bus.
 * - Provides functions to get the current connection status and IP address.
 */
#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the Wi-Fi manager.
 *
 * This function sets up the Wi-Fi driver, the TCP/IP adapter, and registers
 * event handlers to manage the connection lifecycle. It reads the target
 * SSID and password from the configuration manager.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t wifi_manager_init(void);

/**
 * @brief Starts the Wi-Fi connection process.
 *
 * This function initiates the connection to the configured access point.
 * The process runs in the background, and events will be posted to indicate
 * the outcome.
 *
 * @return
 *     - ESP_OK: If the connection process was started successfully.
 *     - ESP_FAIL: If an error occurred.
 */
esp_err_t wifi_manager_connect(void);

/**
 * @brief Stops current Wi-Fi mode and starts the connection process again.
 *
 * This is used after configuration changes to apply new settings.
 *
 * @return
 *     - ESP_OK: If the reconnection process was started successfully.
 */
esp_err_t wifi_manager_reconnect(void);

/**
 * @brief Disconnects from the Wi-Fi access point.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t wifi_manager_disconnect(void);

/**
 * @brief Checks if the device is currently connected to a Wi-Fi network.
 *
 * @return true if connected, false otherwise.
 */
bool wifi_manager_is_connected(void);

/**
 * @brief Gets the RSSI of the current Wi-Fi connection.
 *
 * @return The RSSI in dBm, or 0 if not connected.
 */
int8_t wifi_manager_get_rssi(void);

/**
 * @brief Gets the IP address of the device.
 *
 * @param[out] ip_str A buffer to store the IP address string.
 * @param[in] ip_str_size The size of the buffer.
 * @return
 *     - ESP_OK: If the IP address was retrieved and copied successfully.
 *     - ESP_FAIL: If not connected or an error occurred.
 */
esp_err_t wifi_manager_get_ip_str(char* ip_str, size_t ip_str_size);

#endif // WIFI_MANAGER_H
