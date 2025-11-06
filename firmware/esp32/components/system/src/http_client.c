/**
 * @file http_client.c
 * @brief Implementation of the simple HTTP client wrapper.
 */

#include "http_client.h"
#include "esp_log.h"
#include "esp_ota_ops.h"

static const char *TAG = "HTTP_CLIENT";

esp_err_t http_client_download_ota(const char *url, esp_ota_handle_t ota_handle) {
    esp_http_client_config_t config = {
        .url = url,
        .cert_pem = NULL, // In production, you should embed the server's root CA
        .timeout_ms = 15000,
        .keep_alive_enable = true,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        ESP_LOGE(TAG, "Failed to initialize HTTP client");
        return ESP_FAIL;
    }

    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open HTTP connection: %s", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        return err;
    }

    int content_length = esp_http_client_fetch_headers(client);
    if (content_length <= 0) {
        ESP_LOGE(TAG, "HTTP client fetch headers failed, content_length = %d", content_length);
        esp_http_client_close(client);
        esp_http_client_cleanup(client);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "HTTP GET request sent, server response: %d, content_length: %d",
             esp_http_client_get_status_code(client), content_length);

    char buffer[1024];
    int total_read_len = 0;
    int read_len;
    while (total_read_len < content_length) {
        read_len = esp_http_client_read(client, buffer, sizeof(buffer));
        if (read_len < 0) {
            ESP_LOGE(TAG, "Error reading data from HTTP stream");
            err = ESP_FAIL;
            break;
        }
        if (read_len > 0) {
            err = esp_ota_write(ota_handle, (const void *)buffer, read_len);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Error writing to OTA partition: %s", esp_err_to_name(err));
                break;
            }
            total_read_len += read_len;
        }
    }

    ESP_LOGI(TAG, "Total bytes read: %d", total_read_len);

    esp_http_client_close(client);
    esp_http_client_cleanup(client);

    return err;
}
