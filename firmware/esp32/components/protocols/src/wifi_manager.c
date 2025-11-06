/**
 * @file wifi_manager.c
 * @brief Implementation of the Wi-Fi manager.
 */

#include "wifi_manager.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "app_config.h"
#include "event_bus.h"
#include "http_server.h"
#include "dns_server.h"

static const char *TAG = "WIFI_MANAGER";

#define WIFI_MAX_RETRY 10
#define WIFI_AP_SSID "AgroPulse-Setup"
#define WIFI_AP_PASS "agropulse"
#define WIFI_AP_CHANNEL 1
#define WIFI_AP_MAX_CONN 4

// Event group to signal Wi-Fi connection status
static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static int s_retry_num = 0;
static bool is_connected = false;
static bool is_ap_mode = false;

static void wifi_event_handler_internal(void* arg, esp_event_base_t event_base,
                                        int32_t event_id, void* event_data);
static void start_ap_mode(void);
static void stop_ap_mode(void);

esp_err_t wifi_manager_init(void) {
    s_wifi_event_group = xEventGroupCreate();
    if (s_wifi_event_group == NULL) {
        ESP_LOGE(TAG, "Failed to create event group");
        return ESP_FAIL;
    }

    // Initialize TCP/IP adapter
    ESP_ERROR_CHECK(esp_netif_init());

    // Create default event loop
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Create default Wi-Fi station
    esp_netif_create_default_wifi_sta();

    // Initialize Wi-Fi stack
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Register event handlers
    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler_internal,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler_internal,
                                                        NULL,
                                                        &instance_got_ip));
    
    // Handler for AP mode events
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        WIFI_EVENT_AP_STACONNECTED,
                                                        &wifi_event_handler_internal,
                                                        NULL,
                                                        NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        WIFI_EVENT_AP_STADISCONNECTED,
                                                        &wifi_event_handler_internal,
                                                        NULL,
                                                        NULL));


    ESP_LOGI(TAG, "Wi-Fi manager initialization finished.");
    return ESP_OK;
}

esp_err_t wifi_manager_connect(void) {
    char ssid[33] = {0};
    char password[65] = {0};

    app_config_get_string("wifi_sta_ssid", ssid, sizeof(ssid));
    app_config_get_string("wifi_sta_password", password, sizeof(password));

    // If SSID is not set, go into AP mode for configuration
    if (strlen(ssid) == 0 || strcmp(ssid, "YourSSID") == 0) {
        ESP_LOGW(TAG, "Wi-Fi credentials not set. Starting AP mode for configuration.");
        start_ap_mode();
        return ESP_OK;
    }

    // If we were in AP mode, stop it first
    if (is_ap_mode) {
        stop_ap_mode();
        // A small delay to allow services to stop cleanly
        vTaskDelay(pdMS_TO_TICKS(500));
        // Re-initialize station mode infrastructure
        ESP_ERROR_CHECK(esp_netif_init());
        ESP_ERROR_CHECK(esp_event_loop_create_default());
        esp_netif_create_default_wifi_sta();
        wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
        ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    }


    wifi_config_t wifi_config = {
        .sta = {
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
            .pmf_cfg = {
                .capable = true,
                .required = false
            },
        },
    };
    char ssid[33] = {0};
    app_config_get_string("wifi_sta_ssid", ssid, sizeof(ssid));
    strncpy((char*)wifi_config.sta.ssid, ssid, sizeof(wifi_config.sta.ssid));
    
    char password[65] = {0};
    app_config_get_string("wifi_sta_password", password, sizeof(password));
    strncpy((char*)wifi_config.sta.password, password, sizeof(wifi_config.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "Connecting to AP: %s", ssid);
    return ESP_OK;
}

esp_err_t wifi_manager_reconnect(void) {
    ESP_LOGI(TAG, "Reconnect requested. Stopping Wi-Fi and restarting connection logic.");
    s_retry_num = 0;
    ESP_ERROR_CHECK(esp_wifi_stop());
    return wifi_manager_connect();
}

esp_err_t wifi_manager_disconnect(void) {
    ESP_LOGI(TAG, "Disconnecting from Wi-Fi.");
    return esp_wifi_disconnect();
}

bool wifi_manager_is_connected(void) {
    return is_connected;
}

int8_t wifi_manager_get_rssi(void) {
    if (!is_connected) {
        return 0;
    }
    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        return ap_info.rssi;
    }
    return 0;
}

esp_err_t wifi_manager_get_ip_str(char* ip_str, size_t ip_str_size) {
    if (!is_connected || ip_str == NULL) {
        return ESP_FAIL;
    }

    esp_netif_ip_info_t ip_info;
    esp_netif_t* netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (netif == NULL) {
        return ESP_FAIL;
    }

    esp_netif_get_ip_info(netif, &ip_info);
    snprintf(ip_str, ip_str_size, IPSTR, IP2STR(&ip_info.ip));
    return ESP_OK;
}

static void wifi_event_handler_internal(void* arg, esp_event_base_t event_base,
                                        int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        is_connected = false;
        event_bus_post(SYSTEM_EVENT_WIFI_DISCONNECTED, NULL, 0);
        if (s_retry_num < WIFI_MAX_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retry to connect to the AP. Attempt #%d", s_retry_num);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "Failed to connect to the AP after %d attempts. Entering AP mode.", WIFI_MAX_RETRY);
            start_ap_mode(); // Fallback to AP mode
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP address: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        is_connected = true;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        event_bus_post(SYSTEM_EVENT_WIFI_CONNECTED, NULL, 0);
        event_bus_post(SYSTEM_EVENT_WIFI_GOT_IP, NULL, 0);
        event_bus_post(SYSTEM_EVENT_WIFI_STATUS_CHANGED, NULL, 0);
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t* event = (wifi_event_ap_staconnected_t*) event_data;
        ESP_LOGI(TAG, "Station "MACSTR" joined, AID=%d", MAC2STR(event->mac), event->aid);
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t* event = (wifi_event_ap_stadisconnected_t*) event_data;
        ESP_LOGI(TAG, "Station "MACSTR" left, AID=%d", MAC2STR(event->mac), event->aid);
    }
}

static void start_ap_mode(void) {
    if (is_ap_mode) return;
    ESP_LOGI(TAG, "Starting device in AP mode...");
    is_ap_mode = true;

    // Stop station mode if it's running
    esp_wifi_stop();
    
    esp_netif_create_default_wifi_ap();

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = WIFI_AP_SSID,
            .ssid_len = strlen(WIFI_AP_SSID),
            .channel = WIFI_AP_CHANNEL,
            .password = WIFI_AP_PASS,
            .max_connection = WIFI_AP_MAX_CONN,
            .authmode = WIFI_AUTH_WPA_WPA2_PSK
        },
    };
    if (strlen(WIFI_AP_PASS) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    // Start DNS and HTTP servers for the captive portal
    dns_server_start();
    http_server_start();

    ESP_LOGI(TAG, "AP Mode started. SSID: %s", WIFI_AP_SSID);
}

static void stop_ap_mode(void) {
    if (!is_ap_mode) return;
    ESP_LOGI(TAG, "Stopping AP mode...");
    is_ap_mode = false;

    // Stop servers
    dns_server_stop();
    http_server_stop();

    // Stop Wi-Fi and destroy AP netif
    esp_wifi_stop();
    esp_netif_t* ap_netif = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (ap_netif) {
        esp_netif_destroy(ap_netif);
    }
}
