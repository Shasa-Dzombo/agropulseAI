/**
 * @file http_server.c
 * @brief Implementation of the local web server.
 */

#include "http_server.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "cJSON.h"
#include "web_content.h"
#include "config_manager.h"
#include "wifi_manager.h"

static const char *TAG = "HTTP_SERVER";
static httpd_handle_t server = NULL;

// Handler for serving the main HTML page
static esp_err_t root_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    const size_t index_html_size = (index_html_end - index_html_start);
    httpd_resp_send(req, index_html_start, index_html_size);
    return ESP_OK;
}

// Handler for the Wi-Fi scan API
static esp_err_t api_scan_get_handler(httpd_req_t *req) {
    wifi_scan_config_t scan_config = {
        .ssid = 0, .bssid = 0, .channel = 0, .show_hidden = false
    };
    ESP_ERROR_CHECK(esp_wifi_scan_start(&scan_config, true));

    uint16_t num_aps = 0;
    esp_wifi_scan_get_ap_num(&num_aps);
    if (num_aps == 0) {
        httpd_resp_send(req, "[]", HTTPD_RESP_USE_STRLEN);
        return ESP_OK;
    }

    wifi_ap_record_t *ap_list = (wifi_ap_record_t *)malloc(num_aps * sizeof(wifi_ap_record_t));
    if (!ap_list) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_records(&num_aps, ap_list));

    cJSON *root = cJSON_CreateArray();
    for (int i = 0; i < num_aps; i++) {
        cJSON *ap_json = cJSON_CreateObject();
        cJSON_AddStringToObject(ap_json, "ssid", (char *)ap_list[i].ssid);
        cJSON_AddNumberToObject(ap_json, "rssi", ap_list[i].rssi);
        cJSON_AddItemToArray(root, ap_json);
    }

    char *json_str = cJSON_Print(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json_str, HTTPD_RESP_USE_STRLEN);

    free(json_str);
    free(ap_list);
    cJSON_Delete(root);

    return ESP_OK;
}

// Handler for configuring Wi-Fi credentials
static esp_err_t api_configure_post_handler(httpd_req_t *req) {
    char buf[256];
    int ret, remaining = req->content_len;

    if (remaining > sizeof(buf) - 1) {
        httpd_resp_send_400(req, "Request too long");
        return ESP_FAIL;
    }
    ret = httpd_req_recv(req, buf, remaining);
    if (ret <= 0) {
        return ESP_FAIL;
    }
    buf[ret] = '\0';

    cJSON *root = cJSON_Parse(buf);
    if (!root) {
        httpd_resp_send_400(req, "Invalid JSON");
        return ESP_FAIL;
    }

    const char *ssid = cJSON_GetObjectItem(root, "ssid")->valuestring;
    const char *password = cJSON_GetObjectItem(root, "password")->valuestring;

    if (!ssid) {
        httpd_resp_send_400(req, "SSID is required");
        cJSON_Delete(root);
        return ESP_FAIL;
    }

    app_config_t current_config;
    config_manager_get_editable_copy(&current_config);
    strncpy(current_config.wifi.ssid, ssid, sizeof(current_config.wifi.ssid) - 1);
    strncpy(current_config.wifi.password, password, sizeof(current_config.wifi.password) - 1);

    if (config_manager_save(&current_config) != ESP_OK) {
        httpd_resp_send_500(req, "Failed to save configuration");
        cJSON_Delete(root);
        return ESP_FAIL;
    }

    cJSON_Delete(root);
    httpd_resp_send(req, "OK", HTTPD_RESP_USE_STRLEN);

    // Trigger reconnection logic
    ESP_LOGI(TAG, "Configuration updated via HTTP. Triggering reconnect.");
    wifi_manager_reconnect();

    return ESP_OK;
}

// Fallback handler to redirect all other requests to the root page
static esp_err_t fallback_get_handler(httpd_req_t *req) {
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

esp_err_t http_server_start(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.uri_match_fn = httpd_uri_match_wildcard;

    ESP_LOGI(TAG, "Starting httpd server");
    if (httpd_start(&server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start httpd server");
        return ESP_FAIL;
    }

    const httpd_uri_t root = { .uri = "/", .method = HTTP_GET, .handler = root_get_handler };
    httpd_register_uri_handler(server, &root);

    const httpd_uri_t scan_api = { .uri = "/api/scan", .method = HTTP_GET, .handler = api_scan_get_handler };
    httpd_register_uri_handler(server, &scan_api);

    const httpd_uri_t configure_api = { .uri = "/api/configure", .method = HTTP_POST, .handler = api_configure_post_handler };
    httpd_register_uri_handler(server, &configure_api);
    
    const httpd_uri_t fallback = { .uri = "/*", .method = HTTP_GET, .handler = fallback_get_handler };
    httpd_register_uri_handler(server, &fallback);

    return ESP_OK;
}

esp_err_t http_server_stop(void) {
    if (server) {
        httpd_stop(server);
        server = NULL;
        ESP_LOGI(TAG, "HTTP server stopped.");
    }
    return ESP_OK;
}
