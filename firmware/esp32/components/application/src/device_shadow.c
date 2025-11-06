/**
 * @file device_shadow.c
 * @brief Implementation of the device shadow module.
 */

#include "device_shadow.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "cJSON.h"
#include "mqtt_client.h"
#include "app_config.h"
#include "event_bus.h"
#include "water_pump_controller.h"
#include "power_manager.h"

static const char *TAG = "DEVICE_SHADOW";

// Shadow topics
#define SHADOW_TOPIC_PREFIX "$aws/things/%s/shadow"
#define SHADOW_UPDATE_TOPIC SHADOW_TOPIC_PREFIX "/update"
#define SHADOW_GET_TOPIC SHADOW_TOPIC_PREFIX "/get"
#define SHADOW_GET_ACCEPTED_TOPIC SHADOW_GET_TOPIC "/accepted"
#define SHADOW_UPDATE_DELTA_TOPIC SHADOW_UPDATE_TOPIC "/delta"

// Local copy of the shadow state
static cJSON *shadow_state = NULL;
static SemaphoreHandle_t shadow_mutex = NULL;

// Forward declarations
static void process_delta(cJSON* delta);
static void publish_shadow_update(cJSON* update_payload);

esp_err_t device_shadow_init(void) {
    shadow_mutex = xSemaphoreCreateMutex();
    if (shadow_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create shadow mutex");
        return ESP_FAIL;
    }

    // Initialize with an empty object
    shadow_state = cJSON_CreateObject();

    ESP_LOGI(TAG, "Device shadow initialized.");
    return ESP_OK;
}

void device_shadow_handle_mqtt_connect(void) {
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    char topic_buf[256];

    // Subscribe to delta topic
    snprintf(topic_buf, sizeof(topic_buf), SHADOW_UPDATE_DELTA_TOPIC, device_id);
    mqtt_client_subscribe(topic_buf, 1);

    // Subscribe to get accepted topic
    snprintf(topic_buf, sizeof(topic_buf), SHADOW_GET_ACCEPTED_TOPIC, device_id);
    mqtt_client_subscribe(topic_buf, 1);

    // Request the full shadow state
    snprintf(topic_buf, sizeof(topic_buf), SHADOW_GET_TOPIC, device_id);
    mqtt_client_publish(topic_buf, "", 0, 1, 0);
    ESP_LOGI(TAG, "Requested full shadow state.");
}

void device_shadow_handle_mqtt_message(const char* topic, const char* payload) {
    cJSON *root = cJSON_Parse(payload);
    if (root == NULL) {
        ESP_LOGE(TAG, "Failed to parse shadow JSON");
        return;
    }

    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    char expected_topic[256];

    // Check for delta update
    snprintf(expected_topic, sizeof(expected_topic), SHADOW_UPDATE_DELTA_TOPIC, device_id);
    if (strcmp(topic, expected_topic) == 0) {
        ESP_LOGI(TAG, "Received shadow delta");
        cJSON* state_delta = cJSON_GetObjectItem(root, "state");
        if (state_delta) {
            process_delta(state_delta);
        }
    }

    // Check for full shadow response
    snprintf(expected_topic, sizeof(expected_topic), SHADOW_GET_ACCEPTED_TOPIC, device_id);
    if (strcmp(topic, expected_topic) == 0) {
        ESP_LOGI(TAG, "Received full shadow document");
        if (xSemaphoreTake(shadow_mutex, portMAX_DELAY) == pdTRUE) {
            cJSON_Delete(shadow_state);
            shadow_state = cJSON_Duplicate(root, true); // Duplicate the whole response
            xSemaphoreGive(shadow_mutex);
        }
        // Process delta from the full shadow
        cJSON* state_node = cJSON_GetObjectItem(root, "state");
        if(state_node) {
            cJSON* delta = cJSON_GetObjectItem(state_node, "delta");
            if (delta) {
                process_delta(delta);
            }
        }
    }

    cJSON_Delete(root);
}

esp_err_t device_shadow_update_reported_state(cJSON* reported_update) {
    if (xSemaphoreTake(shadow_mutex, pdMS_TO_TICKS(1000)) != pdTRUE) {
        ESP_LOGE(TAG, "Failed to take shadow mutex");
        cJSON_Delete(reported_update);
        return ESP_FAIL;
    }

    // Prepare the payload for publishing
    cJSON *publish_payload = cJSON_CreateObject();
    cJSON* state_payload = cJSON_CreateObject();
    cJSON_AddItemToObject(publish_payload, "state", state_payload);
    cJSON_AddItemToObject(state_payload, "reported", reported_update);

    publish_shadow_update(publish_payload);
    
    // No need to merge locally, we'll get the update back if accepted.
    // Cleanup
    cJSON_Delete(publish_payload);
    xSemaphoreGive(shadow_mutex);

    return ESP_OK;
}

static void publish_shadow_update(cJSON* update_payload) {
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    char topic_buf[256];
    snprintf(topic_buf, sizeof(topic_buf), SHADOW_UPDATE_TOPIC, device_id);

    char* json_str = cJSON_PrintUnformatted(update_payload);
    if (json_str) {
        mqtt_client_publish(topic_buf, json_str, strlen(json_str), 1, 0);
        free(json_str);
    }
}

static void process_delta(cJSON* delta) {
    ESP_LOGI(TAG, "Processing delta...");

    // Example: Handle desired water pump state
    cJSON* pump_state = cJSON_GetObjectItem(delta, "waterPumpOn");
    if (cJSON_IsBool(pump_state)) {
        if (cJSON_IsTrue(pump_state)) {
            ESP_LOGI(TAG, "Delta wants to turn pump ON");
            water_pump_on();
        } else {
            ESP_LOGI(TAG, "Delta wants to turn pump OFF");
            water_pump_off();
        }
    }

    // Handle desired power mode
    cJSON* power_mode_json = cJSON_GetObjectItem(delta, "powerMode");
    if (cJSON_IsString(power_mode_json)) {
        if (strcmp(power_mode_json->valuestring, "POWER_SAVE") == 0) {
            ESP_LOGI(TAG, "Delta wants to set power mode to POWER_SAVE");
            power_manager_set_mode(POWER_MODE_POWER_SAVE);
        } else if (strcmp(power_mode_json->valuestring, "NORMAL") == 0) {
            ESP_LOGI(TAG, "Delta wants to set power mode to NORMAL");
            power_manager_set_mode(POWER_MODE_NORMAL);
        }
    }

    // After processing, we should report back that we have achieved the desired state.
    // The individual components (like actuator_control) already report their state,
    // so the shadow will eventually converge. We can clear the desired state by reporting null.
    cJSON *reported_payload = cJSON_CreateObject();
    cJSON *reported_state = cJSON_CreateObject();
    cJSON_AddItemToObject(reported_payload, "state", reported_state);
    cJSON_AddNullToObject(reported_state, "desired");

    publish_shadow_update(reported_payload);
    cJSON_Delete(reported_payload);
}
