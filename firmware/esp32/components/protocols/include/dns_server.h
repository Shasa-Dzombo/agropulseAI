/**
 * @file dns_server.h
 * @brief A simple DNS server to implement a captive portal.
 *
 * When the device is in AP mode, this DNS server will respond to all
 * DNS queries with the device's own IP address. This forces clients
 * that connect to the AP to be redirected to the device's configuration
 * web page, creating a "captive portal".
 */
#ifndef DNS_SERVER_H
#define DNS_SERVER_H

#include "esp_err.h"

/**
 * @brief Starts the DNS server.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t dns_server_start(void);

/**
 * @brief Stops the DNS server.
 */
void dns_server_stop(void);

#endif // DNS_SERVER_H
