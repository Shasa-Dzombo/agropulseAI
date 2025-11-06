/**
 * @file http_client.h
 * @brief A simple wrapper for the ESP-IDF HTTP client.
 *
 * This component provides a simplified interface for making HTTP requests,
 * specifically for downloading files for OTA updates.
 *
 * Features:
 * - Perform HTTP GET requests.
 * - Stream response body directly to a buffer or OTA handle.
 */
#ifndef HTTP_CLIENT_H
#define HTTP_CLIENT_H

#include "esp_err.h"
#include "esp_http_client.h"

/**
 * @brief Performs an HTTP GET request to download a file.
 *
 * This function streams the content of the response directly into the OTA update partition.
 *
 * @param[in] url The URL of the file to download.
 * @param[in] ota_handle The handle for the OTA update partition.
 * @return
 *     - ESP_OK: If the download was successful.
 *     - ESP_FAIL: On failure.
 */
esp_err_t http_client_download_ota(const char *url, esp_ota_handle_t ota_handle);

#endif // HTTP_CLIENT_H
