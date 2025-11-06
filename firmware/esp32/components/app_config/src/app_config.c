#include "app_config.h"
#include "config_manager_v2.h"
#include "esp_log.h"
#include "esp_system.h"

static const char *TAG = "APP_CONFIG";

static config_manager_v2_handle_t g_config_handle = NULL;

// Define the application configuration schema
static const config_schema_item_t g_app_schema[] = {
    // Device Info
    {"device_id", cJSON_String, true, "\"\""}, // Default will be populated with MAC address
    {"device_group", cJSON_String, false, "\"default_group\""},
    {"firmware_version", cJSON_String, false, "\"1.0.0\""},

    // Wi-Fi STA Configuration
    {"wifi_sta_ssid", cJSON_String, true, "\"\""},
    {"wifi_sta_password", cJSON_String, true, "\"\""},

    // Wi-Fi AP Configuration (for provisioning)
    {"wifi_ap_ssid", cJSON_String, false, "\"AgroPulse-Provision\""},
    {"wifi_ap_password", cJSON_String, false, "\"password\""},

    // MQTT Configuration
    {"mqtt_broker_uri", cJSON_String, true, "\"mqtts://your_mqtt_broker.com:8883\""},
    {"gcp_project_id", cJSON_String, false, "\"your-gcp-project-id\""}, // For JWT audience
    {"mqtt_username", cJSON_String, false, "\"\""}, // Using JWT, so username might not be needed
    {"mqtt_password", cJSON_String, false, "\"\""}, // Using JWT, so password might not be needed
    {"mqtt_qos", cJSON_Number, false, "1"},
    {"mqtt_keepalive_s", cJSON_Number, false, "120"},

    // Application Behavior
    {"sensor_read_interval_s", cJSON_Number, false, "60"},
    {"status_publish_interval_s", cJSON_Number, false, "300"},
    {"watering_threshold", cJSON_Number, false, "30"},
    {"pump_control_enabled", cJSON_True, false, "true"},
    {"auto_reboot_on_error_count", cJSON_Number, false, "10"},
    
    // Power Management
    {"power_management_enabled", cJSON_True, false, "false"},
    {"light_sleep_threshold_s", cJSON_Number, false, "600"},

    // OTA
    {"ota_auto_update_enabled", cJSON_True, false, "true"},

    // Hardware Pins
    {"i2c0_sda_pin", cJSON_Number, false, "21"},
    {"i2c0_scl_pin", cJSON_Number, false, "22"},
    {"spi_mosi_pin", cJSON_Number, false, "23"},
    {"spi_miso_pin", cJSON_Number, false, "19"},
    {"spi_sclk_pin", cJSON_Number, false, "18"},

    // GPS Pins (UART2)
    {"gps_tx_pin", cJSON_Number, false, "17"},
    {"gps_rx_pin", cJSON_Number, false, "16"},
};

static esp_err_t set_default_device_id() {
    const cJSON* current_config = config_manager_v2_get_config(g_config_handle);
    const cJSON* device_id_item = cJSON_GetObjectItem(current_config, "device_id");

    if (cJSON_IsString(device_id_item) && strlen(device_id_item->valuestring) > 0) {
        ESP_LOGI(TAG, "Device ID already set: %s", device_id_item->valuestring);
        return ESP_OK;
    }

    uint8_t mac[6];
    char mac_str[18];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    snprintf(mac_str, sizeof(mac_str), "%02x%02x%02x%02x%02x%02x", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    cJSON *update = cJSON_CreateObject();
    cJSON_AddStringToObject(update, "device_id", mac_str);
    
    ESP_LOGI(TAG, "Setting default device ID to MAC address: %s", mac_str);
    esp_err_t err = config_manager_v2_update_config(g_config_handle, update);

    cJSON_Delete(update);
    return err;
}


esp_err_t app_config_init(void) {
    if (g_config_handle) {
        ESP_LOGW(TAG, "Application config already initialized.");
        return ESP_OK;
    }

    size_t schema_size = sizeof(g_app_schema) / sizeof(g_app_schema[0]);
    esp_err_t err = config_manager_v2_init(g_app_schema, schema_size, &g_config_handle);

    if (err == ESP_OK) {
        // After init, check if we need to set a default device ID
        err = set_default_device_id();
    }

    return err;
}

esp_err_t app_config_deinit(void) {
    if (!g_config_handle) {
        return ESP_ERR_INVALID_STATE;
    }
    return config_manager_v2_deinit(g_config_handle);
}

const cJSON* app_config_get(void) {
    return config_manager_v2_get_config(g_config_handle);
}

esp_err_t app_config_update(const cJSON* new_config) {
    return config_manager_v2_update_config(g_config_handle, new_config);
}

esp_err_t app_config_reset(void) {
    esp_err_t err = config_manager_v2_reset_to_defaults(g_config_handle);
    if (err == ESP_OK) {
        // After reset, re-apply the default device ID
        err = set_default_device_id();
    }
    return err;
}

esp_err_t app_config_get_string(const char* key, char* buffer, size_t buffer_size) {
    return config_manager_v2_get_string(g_config_handle, key, buffer, buffer_size);
}

esp_err_t app_config_get_int(const char* key, int* value) {
    return config_manager_v2_get_int(g_config_handle, key, value);
}

esp_err_t app_config_get_bool(const char* key, bool* value) {
    return config_manager_v2_get_bool(g_config_handle, key, value);
}
