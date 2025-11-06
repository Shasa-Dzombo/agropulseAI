#include "offline_data_uploader.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "data_logger.h"
#include "device_shadow.h"
#include "wifi_manager.h"
#include "cJSON.h"
#include <stdio.h>
#include "task_watchdog.h"

static const char *TAG = "OFFLINE_UPLOADER";
#define UPLOAD_INTERVAL_MS (60 * 1000) // Try to upload every 60 seconds
#define MAX_LOG_LINE_LENGTH 128

static void offline_data_uploader_task(void *pvParameters);

void offline_data_uploader_init(void) {
    TaskHandle_t task_handle;
    xTaskCreate(offline_data_uploader_task, "offline_upload_task", 4096, NULL, 5, &task_handle);
    task_watchdog_register_task(task_handle, "OfflineUploader");
    ESP_LOGI(TAG, "Offline data uploader initialized.");
}

static void offline_data_uploader_task(void *pvParameters) {
    while (1) {
        // Pet the watchdog at the start of every cycle
        task_watchdog_pet();

        vTaskDelay(pdMS_TO_TICKS(UPLOAD_INTERVAL_MS));

        // Only run if Wi-Fi is connected
        if (!wifi_manager_is_connected()) {
            ESP_LOGD(TAG, "Wi-Fi not connected. Skipping upload cycle.");
            continue;
        }

        ESP_LOGI(TAG, "Checking for offline data to upload...");

        // Loop to upload all available data
        while (1) {
            char* line_buffer = NULL;
            size_t entry_size = 0;
            esp_err_t ret = data_logger_read_oldest_entry(&line_buffer, &entry_size);

            if (ret == ESP_ERR_NOT_FOUND) {
                ESP_LOGI(TAG, "No more offline data to upload.");
                break; // No more entries
            }
            if (ret != ESP_OK) {
                ESP_LOGE(TAG, "Failed to read oldest log entry.");
                break;
            }

            // Parse the CSV line
            long long timestamp_ll;
            float temp, humidity, soil, light;
            int items = sscanf(line_buffer, "%lld,%f,%f,%f,%f", &timestamp_ll, &temp, &humidity, &soil, &light);

            if (items != 5) {
                ESP_LOGE(TAG, "Failed to parse log line: %s. Deleting it.", line_buffer);
                free(line_buffer);
                data_logger_delete_oldest_entry(); // Delete corrupted line
                continue;
            }

            ESP_LOGI(TAG, "Found offline data from timestamp %lld. Uploading...", timestamp_ll);

            // Create a JSON object for the device shadow
            cJSON *reported_state = cJSON_CreateObject();
            if (!reported_state) {
                free(line_buffer);
                continue;
            }
            
            cJSON *historic_data = cJSON_CreateObject();
            if (!historic_data) {
                cJSON_Delete(reported_state);
                free(line_buffer);
                continue;
            }
            
            cJSON_AddItemToObject(reported_state, "historic_data", historic_data);
            cJSON_AddNumberToObject(historic_data, "timestamp", (double)timestamp_ll);
            cJSON_AddNumberToObject(historic_data, "temperature", temp);
            cJSON_AddNumberToObject(historic_data, "humidity", humidity);
            cJSON_AddNumberToObject(historic_data, "soil_moisture", soil);
            cJSON_AddNumberToObject(historic_data, "light_lux", light);

            // Update the device shadow
            if (device_shadow_update_reported_state(reported_state) == ESP_OK) {
                ESP_LOGI(TAG, "Successfully uploaded offline data. Deleting entry.");
                data_logger_delete_oldest_entry();
                // Give the system a moment to process the MQTT message
                vTaskDelay(pdMS_TO_TICKS(500)); 
            } else {
                ESP_LOGE(TAG, "Failed to upload offline data to shadow. Will retry later.");
                cJSON_Delete(reported_state);
                free(line_buffer);
                break; // Stop trying if shadow update fails
            }
            
            cJSON_Delete(reported_state);
            free(line_buffer);
        }
    }
}
