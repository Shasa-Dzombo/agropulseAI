/**
 * @file status_publisher.c
 * @brief Implementation of the status publisher.
 */

#include "status_publisher.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "cJSON.h"
#include "mqtt_client.h"
#include "config_manager.h"
#include "wifi_manager.h"
#include "water_pump_controller.h"
#include "device_shadow.h"
#include "task_watchdog.h"

static const char *TAG = "STATUS_PUBLISHER";
#define STATUS_PUBLISH_INTERVAL_MS (5 * 60 * 1000) // 5 minutes
#define TASK_STATUS_BUFFER_SIZE 512

static TaskHandle_t status_task_handle = NULL;
static SemaphoreHandle_t trigger_semaphore = NULL;

static void publish_status(void) {
    if (!mqtt_client_is_connected()) {
        ESP_LOGW(TAG, "Cannot publish status, MQTT not connected.");
        return;
    }

    cJSON *root = cJSON_CreateObject();
    if (root == NULL) {
        ESP_LOGE(TAG, "Failed to create JSON object for status.");
        return;
    }

    // Build the status payload
    cJSON *system = cJSON_CreateObject();
    cJSON_AddNumberToObject(system, "freeHeap", esp_get_free_heap_size());
    cJSON_AddNumberToObject(system, "uptimeSeconds", esp_timer_get_time() / 1000000);
    
    // Add task watchdog status
    char task_status_buf[TASK_STATUS_BUFFER_SIZE];
    if (task_watchdog_get_status_json(task_status_buf, sizeof(task_status_buf)) == ESP_OK) {
        cJSON* task_status_json = cJSON_Parse(task_status_buf);
        if (task_status_json) {
            cJSON_AddItemToObject(system, "tasks", task_status_json);
        }
    }
    
    cJSON *network = cJSON_CreateObject();
    cJSON_AddNumberToObject(network, "rssi", wifi_manager_get_rssi());

    cJSON *actuators = cJSON_CreateObject();
    cJSON_AddBoolToObject(actuators, "waterPumpOn", water_pump_is_on());

    // Create the final reported state object
    cJSON *reported_payload = cJSON_CreateObject();
    cJSON_AddItemToObject(reported_payload, "system", system);
    cJSON_AddItemToObject(reported_payload, "network", network);
    cJSON_AddItemToObject(reported_payload, "actuators", actuators);

    ESP_LOGI(TAG, "Publishing status to device shadow.");
    device_shadow_update_reported_state(reported_payload);

    // This module no longer needs to print or publish directly.
    cJSON_Delete(root); // root is not used, but good practice
}

static void status_publisher_task(void *pvParameters) {
    ESP_LOGI(TAG, "Status publisher task started.");
    while (1) {
        // Pet the watchdog
        task_watchdog_pet();

        // Wait for the interval or a manual trigger
        if (xSemaphoreTake(trigger_semaphore, pdMS_TO_TICKS(STATUS_PUBLISH_INTERVAL_MS)) == pdTRUE) {
            ESP_LOGI(TAG, "Manual status publish triggered.");
        }
        publish_status();
    }
}

esp_err_t status_publisher_init(void) {
    trigger_semaphore = xSemaphoreCreateBinary();
    if (trigger_semaphore == NULL) {
        ESP_LOGE(TAG, "Failed to create trigger semaphore.");
        return ESP_FAIL;
    }

    xTaskCreate(status_publisher_task, "status_publisher_task", 4096, NULL, 3, &status_task_handle);
    task_watchdog_register_task(status_task_handle, "StatusPublisher");
    return ESP_OK;
}

esp_err_t status_publisher_trigger(void) {
    if (trigger_semaphore != NULL) {
        xSemaphoreGive(trigger_semaphore);
        return ESP_OK;
    }
    return ESP_FAIL;
}
