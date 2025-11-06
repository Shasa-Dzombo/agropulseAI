/**
 * @file mqtt_client.c
 * @brief Implementation of the MQTT client manager.
 */

#include "mqtt_client.h"
#include "esp_log.h"
#include "mqtt_client.h"
#include "app_config.h"
#include "event_bus.h"
#include "command_processor.h"
#include "device_shadow.h"
#include "security_manager.h"
#include "wifi_manager.h"
#include "platform.h"
#include "network_manager.h" // For event handler

static const char *TAG = "MQTT_CLIENT";

static esp_mqtt_client_handle_t client = NULL;
static bool is_connected = false;

static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event);
static void network_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);

esp_err_t mqtt_client_init(void) {
    // Register a handler to listen for generic network events
    ESP_ERROR_CHECK(esp_event_handler_register(NETWORK_EVENT, NETWORK_EVENT_CONNECTED, &network_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(NETWORK_EVENT, NETWORK_EVENT_DISCONNECTED, &network_event_handler, NULL));

    ESP_LOGI(TAG, "MQTT client initialized.");
    return ESP_OK;
}

esp_err_t mqtt_client_start(void) {
    if (!wifi_manager_is_connected()) {
        ESP_LOGW(TAG, "Cannot start MQTT client, Wi-Fi is not connected.");
        return ESP_FAIL;
    }

    // If client exists, destroy it to create a new one with a fresh JWT
    if (client) {
        ESP_LOGI(TAG, "MQTT client exists. Destroying and recreating for new JWT.");
        esp_mqtt_client_stop(client);
        esp_mqtt_client_destroy(client);
        client = NULL;
    }

    const cJSON* config = app_config_get();
    char project_id[64];
    app_config_get_string("gcp_project_id", project_id, sizeof(project_id));

    char jwt_buffer[512];
    
    // Generate a new JWT for this connection attempt
    // Note: For Google IoT Core, the project_id is used as the audience (aud) claim.
    esp_err_t jwt_err = security_manager_generate_jwt(project_id, jwt_buffer, sizeof(jwt_buffer));
    if (jwt_err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to generate JWT for MQTT authentication (0x%x).", jwt_err);
        return jwt_err;
    }

    ESP_LOGI(TAG, "Generated new JWT for MQTT authentication.");

    char broker_uri[128];
    char client_id[64];
    app_config_get_string("mqtt_broker_uri", broker_uri, sizeof(broker_uri));
    app_config_get_string("device_id", client_id, sizeof(client_id)); // Using device_id as client_id

    // For JWT-based authentication (e.g., Google Cloud IoT Core), the username is typically ignored.
    // The password field is used to send the JWT.
    esp_mqtt_client_config_t mqtt_cfg = {
        .uri = broker_uri,
        .client_id = client_id,
        .username = "unused", 
        .password = jwt_buffer,
        .event_handle = mqtt_event_handler,
        // .cert_pem = (const char *)gcp_root_ca_pem_start, // Uncomment for TLS with Google Cloud
    };

    client = esp_mqtt_client_init(&mqtt_cfg);
    if (client == NULL) {
        ESP_LOGE(TAG, "Failed to initialize MQTT client.");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Starting MQTT client...");
    return esp_mqtt_client_start(client);
}

esp_err_t mqtt_client_stop(void) {
    if (client == NULL) {
        return ESP_OK;
    }
    esp_err_t err = esp_mqtt_client_stop(client);
    if (err == ESP_OK) {
        is_connected = false;
    }
    return err;
}

int mqtt_client_publish(const char *topic, const char *data, int len, int qos, int retain) {
    if (!is_connected || client == NULL) {
        ESP_LOGE(TAG, "MQTT client not connected. Cannot publish.");
        return -1;
    }
    return esp_mqtt_client_publish(client, topic, data, len, qos, retain);
}

int mqtt_client_subscribe(const char *topic, int qos) {
    if (!is_connected || client == NULL) {
        ESP_LOGE(TAG, "MQTT client not connected. Cannot subscribe.");
        return -1;
    }
    return esp_mqtt_client_subscribe(client, topic, qos);
}

bool mqtt_client_is_connected(void) {
    return is_connected;
}

static void subscribe_to_command_topic(void) {
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    char command_topic[128];
    snprintf(command_topic, sizeof(command_topic), "device/command/%s", device_id);
    
    ESP_LOGI(TAG, "Subscribing to command topic: %s", command_topic);
    int msg_id = esp_mqtt_client_subscribe(client, command_topic, 1);
    if (msg_id > 0) {
        ESP_LOGI(TAG, "Successfully subscribed to command topic, msg_id=%d", msg_id);
    } else {
        ESP_LOGE(TAG, "Failed to subscribe to command topic");
    }
}

static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event) {
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
            is_connected = true;
            event_bus_post(SYSTEM_EVENT_MQTT_CONNECTED, NULL, 0);
            subscribe_to_command_topic();
            device_shadow_handle_mqtt_connect(); // Notify shadow module
            break;
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
            is_connected = false;
            event_bus_post(SYSTEM_EVENT_MQTT_DISCONNECTED, NULL, 0);
            break;
        case MQTT_EVENT_SUBSCRIBED:
            ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED, msg_id=%d", event->msg_id);
            break;
        case MQTT_EVENT_UNSUBSCRIBED:
            ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d", event->msg_id);
            break;
        case MQTT_EVENT_PUBLISHED:
            ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED, msg_id=%d", event->msg_id);
            break;
        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "MQTT_EVENT_DATA");
            printf("TOPIC=%.*s\r\n", event->topic_len, event->topic);
            printf("DATA=%.*s\r\n", event->data_len, event->data);
            
            // Route message to appropriate handler
            if (strstr(event->topic, "/shadow/")) {
                device_shadow_handle_mqtt_message(event->topic, event->data);
            } else {
                // Null-terminate the payload to be safe
                char* payload_str = malloc(event->data_len + 1);
                if (payload_str) {
                    memcpy(payload_str, event->data, event->data_len);
                    payload_str[event->data_len] = '\0';
                    command_processor_process(event->topic, payload_str);
                    free(payload_str);
                }
            }
            break;
        case MQTT_EVENT_ERROR:
            ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
            break;
        default:
            ESP_LOGI(TAG, "Other event id:%d", event->event_id);
            break;
    }
    return ESP_OK;
}

static void network_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_id == NETWORK_EVENT_CONNECTED) {
        ESP_LOGI(TAG, "Network connected, starting MQTT client.");
        mqtt_client_start();
    } else if (event_id == NETWORK_EVENT_DISCONNECTED) {
        ESP_LOGI(TAG, "Network disconnected, stopping MQTT client.");
        mqtt_client_stop();
    }
}
