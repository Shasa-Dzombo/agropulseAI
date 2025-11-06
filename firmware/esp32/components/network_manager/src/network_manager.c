#include "network_manager.h"
#include "wifi_manager.h"
#include "cellular_manager.h"
#include "event_bus.h"
#include "esp_log.h"

static const char *TAG = "NETWORK_MGR";
static network_preference_t net_pref;

static void network_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    // This handler listens to low-level network events and attempts to connect
    // based on the user's preference.
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "Wi-Fi disconnected.");
        if (net_pref == NETWORK_PREF_WIFI_PREFERRED) {
            ESP_LOGI(TAG, "Wi-Fi preferred, attempting to start cellular as fallback.");
            cellular_manager_start();
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_PPP_LOST_IP) {
        ESP_LOGW(TAG, "Cellular disconnected.");
        if (net_pref == NETWORK_PREF_CELLULAR_PREFERRED) {
            ESP_LOGI(TAG, "Cellular preferred, attempting to start Wi-Fi as fallback.");
            wifi_manager_connect();
        }
    }
}

esp_err_t network_manager_init(network_preference_t preference) {
    net_pref = preference;
    wifi_manager_init();
    cellular_manager_init();

    // Register for low-level events to handle failover
    esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, &network_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_PPP_LOST_IP, &network_event_handler, NULL);

    ESP_LOGI(TAG, "Network manager initialized.");
    return ESP_OK;
}

esp_err_t network_manager_connect(void) {
    ESP_LOGI(TAG, "Network manager connecting with preference: %d", net_pref);
    switch (net_pref) {
        case NETWORK_PREF_WIFI_ONLY:
            return wifi_manager_connect();
        case NETWORK_PREF_CELLULAR_ONLY:
            return cellular_manager_start();
        case NETWORK_PREF_WIFI_PREFERRED:
            // Try Wi-Fi first. If it fails, the event handler will start cellular.
            return wifi_manager_connect();
        case NETWORK_PREF_CELLULAR_PREFERRED:
            // Try Cellular first. If it fails, the event handler will start Wi-Fi.
            return cellular_manager_start();
    }
    return ESP_FAIL;
}
