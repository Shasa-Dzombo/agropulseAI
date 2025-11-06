#include "health_monitor.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "mqtt_client.h"
#include "app_config.h"
#include "cJSON.h"
#include "time_manager.h"
#include "wifi_manager.h"
#include "platform.h"

#define HEALTH_MONITOR_TASK_STACK_SIZE 4096
#define HEALTH_MONITOR_TASK_PRIORITY   3
#define HEALTH_MONITOR_INTERVAL_S      300 // 5 minutes

static const char *TAG = "HEALTH_MONITOR";

static void health_monitor_task(void *pvParameters);

esp_err_t health_monitor_init(void) {
    xTaskCreate(health_monitor_task, "health_monitor_task", HEALTH_MONITOR_TASK_STACK_SIZE, NULL, HEALTH_MONITOR_TASK_PRIORITY, NULL);
    ESP_LOGI(TAG, "System health monitor initialized.");
    return ESP_OK;
}

esp_err_t health_monitor_publish_report(void) {
    if (!mqtt_client_is_connected()) {
        ESP_LOGW(TAG, "MQTT not connected. Cannot publish health report.");
        return ESP_FAIL;
    }

    char topic[128];
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    snprintf(topic, sizeof(topic), "/devices/%s/events/health", device_id);

    cJSON *root = cJSON_CreateObject();
    char timestamp[32];
    time_manager_get_iso8601_timestamp(timestamp, sizeof(timestamp));
    cJSON_AddStringToObject(root, "timestamp", timestamp);
    cJSON_AddNumberToObject(root, "uptime_s", platform_get_uptime_ms() / 1000);
    cJSON_AddNumberToObject(root, "free_heap_bytes", platform_get_free_heap_size());
    
    wifi_ap_record_t ap_info;
    if (wifi_manager_get_ap_info(&ap_info) == ESP_OK) {
        cJSON_AddNumberToObject(root, "wifi_rssi", ap_info.rssi);
    }

    // Task states (optional, can be verbose)
    // #if ( ( configUSE_TRACE_FACILITY == 1 ) && ( configUSE_STATS_FORMATTING_FUNCTIONS > 0 ) )
    //     char* task_stats_buffer = malloc(2048);
    //     if (task_stats_buffer) {
    //         vTaskList(task_stats_buffer);
    //         cJSON_AddStringToObject(root, "task_list", task_stats_buffer);
    //         free(task_stats_buffer);
    //     }
    // #endif

    char *json_string = cJSON_PrintUnformatted(root);
    if (json_string) {
        mqtt_client_publish(topic, json_string, 0, 0); // QoS 0 for health reports
        free(json_string);
    }

    cJSON_Delete(root);
    ESP_LOGI(TAG, "Published health report to topic: %s", topic);
    return ESP_OK;
}

static void health_monitor_task(void *pvParameters) {
    ESP_LOGI(TAG, "Health monitor task started.");
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(HEALTH_MONITOR_INTERVAL_S * 1000));
        ESP_LOGI(TAG, "Publishing periodic health report.");
        health_monitor_publish_report();
    }
}
