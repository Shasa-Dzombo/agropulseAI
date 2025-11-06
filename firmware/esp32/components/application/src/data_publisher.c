/**
 * @file data_publisher.c
 * @brief Implementation of the data publisher.
 */

#include "data_publisher.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "cJSON.h"
#include "mqtt_client.h"
#include "app_config.h"
#include "time_manager.h"
#include "preprocessor.h"
#include "inference_engine.h"
#include "data_logger.h" // For logging data when offline
#include "device_shadow.h"
#include "ble_manager.h"
#include "visual_intelligence.h"
#include "gps_manager.h"

static const char *TAG = "DATA_PUBLISHER";

#define DATA_QUEUE_LENGTH 10
static QueueHandle_t data_queue = NULL;

static void data_publisher_task(void *pvParameters);
static void offline_data_uploader_task(void *pvParameters);

esp_err_t data_publisher_publish_vision_results(const visual_analysis_result_t* results, int result_count, const gps_location_t* location) {
    if (!mqtt_client_is_connected()) {
        ESP_LOGW(TAG, "MQTT not connected. Cannot publish vision results.");
        // Optionally, log vision data to a separate file for later upload
        return ESP_FAIL;
    }

    char topic[128];
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    snprintf(topic, sizeof(topic), "/devices/%s/events/vision", device_id);

    cJSON *root = cJSON_CreateObject();
    char timestamp[32];
    time_manager_get_iso8601_timestamp(timestamp, sizeof(timestamp));
    cJSON_AddStringToObject(root, "timestamp", timestamp);

    if (location && location->is_valid) {
        cJSON *loc_json = cJSON_CreateObject();
        cJSON_AddNumberToObject(loc_json, "latitude", location->latitude);
        cJSON_AddNumberToObject(loc_json, "longitude", location->longitude);
        cJSON_AddNumberToObject(loc_json, "satellites", location->satellites_tracked);
        cJSON_AddItemToObject(root, "location", loc_json);
    }

    cJSON *detections = cJSON_CreateArray();
    for (int i = 0; i < result_count; i++) {
        cJSON *detection = cJSON_CreateObject();
        cJSON_AddStringToObject(detection, "label", results[i].label);
        cJSON_AddNumberToObject(detection, "confidence", results[i].confidence);
        
        cJSON *bbox = cJSON_CreateObject();
        cJSON_AddNumberToObject(bbox, "x", results[i].box.x);
        cJSON_AddNumberToObject(bbox, "y", results[i].box.y);
        cJSON_AddNumberToObject(bbox, "width", results[i].box.width);
        cJSON_AddNumberToObject(bbox, "height", results[i].box.height);
        cJSON_AddItemToObject(detection, "boundingBox", bbox);

        cJSON_AddItemToArray(detections, detection);
    }
    cJSON_AddItemToObject(root, "detections", detections);

    char *json_string = cJSON_PrintUnformatted(root);
    if (json_string) {
        mqtt_client_publish(topic, json_string, 1, 0);
        free(json_string);
    }

    cJSON_Delete(root);
    ESP_LOGI(TAG, "Published vision results to topic: %s", topic);
    return ESP_OK;
}

esp_err_t data_publisher_init(void) {
    data_queue = xQueueCreate(DATA_QUEUE_LENGTH, sizeof(sensor_data_t));
    if (data_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create data queue.");
        return ESP_FAIL;
    }

    xTaskCreate(data_publisher_task, "data_publisher_task", 4096, NULL, 5, NULL);
    xTaskCreate(offline_data_uploader_task, "offline_uploader_task", 4096, NULL, 4, NULL);
    return ESP_OK;
}

esp_err_t data_publisher_queue_data(const sensor_data_t* data) {
    if (data_queue == NULL) {
        return ESP_FAIL;
    }

    if (xQueueSend(data_queue, data, pdMS_TO_TICKS(100)) != pdTRUE) {
        ESP_LOGW(TAG, "Data queue is full. Dropping sensor data.");
        return ESP_FAIL;
    }
    return ESP_OK;
}

static void data_publisher_task(void *pvParameters) {
    ESP_LOGI(TAG, "Data publisher task started.");
    sensor_data_t received_data;

    while (1) {
        if (xQueueReceive(data_queue, &received_data, portMAX_DELAY) == pdTRUE) {
            ESP_LOGI(TAG, "Received sensor data from queue. Reporting to shadow.");

            // Always report to the shadow. The shadow will decide when to publish.
            cJSON *reported_payload = cJSON_CreateObject();
            cJSON *sensors = cJSON_CreateObject();
            cJSON_AddItemToObject(reported_payload, "sensors", sensors);
            cJSON_AddNumberToObject(sensors, "temperature", received_data.temperature);
            cJSON_AddNumberToObject(sensors, "humidity", received_data.humidity);
            cJSON_AddNumberToObject(sensors, "soilMoisture", received_data.soil_moisture);
            cJSON_AddNumberToObject(sensors, "lightLux", received_data.light_lux);
            
            // Also add AI model output to the shadow
            preprocessed_data_t model_input;
            if (preprocessor_run(&received_data, &model_input) == ESP_OK) {
                model_output_t model_output;
                if (inference_engine_run(&model_input, &model_output) == ESP_OK) {
                    cJSON *ai_output = cJSON_CreateObject();
                    cJSON_AddItemToObject(reported_payload, "ai_model", ai_output);
                    cJSON_AddNumberToObject(ai_output, "healthy_prob", model_output.predictions[0]);
                    cJSON_AddNumberToObject(ai_output, "mild_stress_prob", model_output.predictions[1]);
                    cJSON_AddNumberToObject(ai_output, "high_stress_prob", model_output.predictions[2]);
                }
            }

            device_shadow_update_reported_state(reported_payload);

            // Also notify via BLE
            ble_manager_notify_sensor_data(&received_data);

            // The old direct publishing logic is now replaced by the shadow update.
            // We still log to SPIFFS if MQTT is offline.
            if (!mqtt_client_is_connected()) {
                ESP_LOGW(TAG, "MQTT not connected. Logging data to SPIFFS.");
                data_logger_log(&received_data);
            }
        }
    }
}

// This task runs periodically to upload any data that was logged while offline.
static void offline_data_uploader_task(void *pvParameters) {
    char buffer[256];
    while(1) {
        // Run every 5 minutes
        vTaskDelay(pdMS_TO_TICKS(300 * 1000));

        if (!mqtt_client_is_connected()) {
            continue;
        }

        ESP_LOGI(TAG, "Checking for offline data to upload...");
        
        // A real implementation would loop until the file is empty
        if (data_logger_read_oldest_entry(buffer, sizeof(buffer)) == ESP_OK) {
            ESP_LOGI(TAG, "Found offline data: %s", buffer);
            
            // In a real app, you'd parse this CSV and publish it.
            // For simplicity, we'll just publish the raw CSV string.
            char device_id[64];
            app_config_get_string("device_id", device_id, sizeof(device_id));
            char topic[128];
            snprintf(topic, sizeof(topic), "device/data/offline/%s", device_id);
            mqtt_client_publish(topic, buffer, strlen(buffer), 1, 0);

            // After successful upload, you would delete the entry/file.
            // data_logger_delete_oldest_log();
            ESP_LOGW(TAG, "Offline data upload simulation complete. Deletion skipped.");
        } else {
            ESP_LOGI(TAG, "No offline data found.");
        }
    }
}
