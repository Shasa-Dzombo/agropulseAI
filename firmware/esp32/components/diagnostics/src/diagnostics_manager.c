#include "diagnostics_manager.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "cJSON.h"
#include "mqtt_client.h"
#include "app_config.h"
#include "wifi_manager.h"
#include "esp_wifi.h"

static const char *TAG = "DIAGNOSTICS";

#define MAX_TASK_INFO_ENTRIES 20

esp_err_t diagnostics_manager_init(void) {
    ESP_LOGI(TAG, "Diagnostics manager initialized.");
    return ESP_OK;
}

static void add_heap_info(cJSON *parent) {
    cJSON *heap_info = cJSON_CreateObject();
    cJSON_AddNumberToObject(heap_info, "total_free_bytes", heap_caps_get_free_size(MALLOC_CAP_DEFAULT));
    cJSON_AddNumberToObject(heap_info, "largest_free_block", heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT));
    cJSON_AddNumberToObject(heap_info, "min_free_bytes", heap_caps_get_minimum_free_size(MALLOC_CAP_DEFAULT));
    cJSON_AddItemToObject(parent, "heap", heap_info);
}

static void add_wifi_info(cJSON *parent) {
    cJSON *wifi_info = cJSON_CreateObject();
    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        cJSON_AddStringToObject(wifi_info, "ssid", (char *)ap_info.ssid);
        cJSON_AddNumberToObject(wifi_info, "rssi", ap_info.rssi);
    }
    cJSON_AddItemToObject(parent, "wifi", wifi_info);
}

static void add_task_info(cJSON *parent) {
    TaskStatus_t *pxTaskStatusArray;
    volatile UBaseType_t uxArraySize;
    uint32_t ulTotalRunTime;

    uxArraySize = uxTaskGetNumberOfTasks();
    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));

    if (pxTaskStatusArray != NULL) {
        uxArraySize = uxTaskGetSystemState(pxTaskStatusArray, uxArraySize, &ulTotalRunTime);
        cJSON *tasks = cJSON_CreateArray();

        for (UBaseType_t i = 0; i < uxArraySize; i++) {
            cJSON *task = cJSON_CreateObject();
            cJSON_AddStringToObject(task, "name", pxTaskStatusArray[i].pcTaskName);
            cJSON_AddNumberToObject(task, "state", pxTaskStatusArray[i].eCurrentState);
            cJSON_AddNumberToObject(task, "priority", pxTaskStatusArray[i].uxCurrentPriority);
            cJSON_AddNumberToObject(task, "stack_high_water_mark", pxTaskStatusArray[i].usStackHighWaterMark);
            cJSON_AddItemToArray(tasks, task);
        }
        cJSON_AddItemToObject(parent, "tasks", tasks);
        vPortFree(pxTaskStatusArray);
    }
}

esp_err_t diagnostics_manager_publish(void) {
    if (!mqtt_client_is_connected()) {
        ESP_LOGW(TAG, "Cannot publish diagnostics, MQTT not connected.");
        return ESP_FAIL;
    }

    char device_id[64];
    char firmware_version[32];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    app_config_get_string("firmware_version", firmware_version, sizeof(firmware_version));

    cJSON *root = cJSON_CreateObject();
    
    cJSON_AddNumberToObject(root, "timestamp", time(NULL));
    cJSON_AddStringToObject(root, "firmware_version", firmware_version);
    cJSON_AddNumberToObject(root, "uptime_ms", esp_log_timestamp());

    add_heap_info(root);
    add_wifi_info(root);
    add_task_info(root);

    char *json_string = cJSON_PrintUnformatted(root);
    if (json_string) {
        char topic[128];
        snprintf(topic, sizeof(topic), "device/diagnostics/%s", device_id);
        mqtt_client_publish(topic, json_string, strlen(json_string), 1, 0);
        free(json_string);
    }

    cJSON_Delete(root);
    return ESP_OK;
}
