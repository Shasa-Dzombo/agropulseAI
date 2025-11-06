/**
 * @file http_server.h
 * @brief Provides a local web server for device configuration and status.
 *
 * This component runs a small HTTP server that can be accessed when the device
 * is in AP mode. It serves a web page allowing the user to scan for Wi-Fi
 * networks and configure the credentials to connect to one.
 *
 * Features:
 * - Starts and stops the HTTP server.
 * - Includes a simple DNS server to capture all requests and redirect to the portal.
 * - Serves a single-page application for configuration.
 */
#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include "esp_err.h"

/**
 * @brief Starts the web server.
 *
 * This function initializes the HTTPD server and registers the necessary URI handlers.
 * It should be called when the device enters a state where local configuration
 * is needed (e.g., AP mode).
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t http_server_start(void);

/**
 * @brief Stops the web server.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t http_server_stop(void);

#endif // HTTP_SERVER_H
