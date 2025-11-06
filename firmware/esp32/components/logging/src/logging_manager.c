#include "logging_manager.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <string.h>
#include <stdio.h>
#include "cJSON.h"
#include "esp_spiffs.h"
#include "mqtt_client.h"
#include "app_config.h"

#define MAX_LOG_TAGS 50
#define LOG_FILE_1 "/spiffs/log1.txt"
#define LOG_FILE_2 "/spiffs/log2.txt"
#define MAX_LOG_FILE_SIZE (10 * 1024) // 10 KB

static const char *TAG = "LOGGING_MANAGER";

typedef struct {
    char tag[20];
    esp_log_level_t level;
} log_level_entry_t;

static log_level_entry_t log_levels[MAX_LOG_TAGS];
static int log_level_count = 0;
static esp_log_level_t default_log_level = ESP_LOG_INFO;

static vprintf_like_t original_vprintf = NULL;
static SemaphoreHandle_t log_mutex;
static FILE* current_log_file = NULL;
static const char* current_log_filename = LOG_FILE_1;

static void switch_log_file(void);

static int custom_vprintf(const char *fmt, va_list args) {
    int ret = original_vprintf(fmt, args);

    if (xSemaphoreTake(log_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
        if (current_log_file) {
            char buffer[256];
            vsnprintf(buffer, sizeof(buffer), fmt, args);
            fprintf(current_log_file, "%s", buffer);
        }
        xSemaphoreGive(log_mutex);
    }
    return ret;
}

esp_err_t logging_manager_init(void) {
    log_mutex = xSemaphoreCreateMutex();
    if (!log_mutex) {
        ESP_LOGE(TAG, "Failed to create log mutex");
        return ESP_FAIL;
    }

    current_log_file = fopen(current_log_filename, "a");
    if (!current_log_file) {
        ESP_LOGE(TAG, "Failed to open log file: %s", current_log_filename);
    }

    original_vprintf = esp_log_set_vprintf(custom_vprintf);
    ESP_LOGI(TAG, "Logging manager initialized and vprintf hooked.");
    return ESP_OK;
}

esp_err_t logging_manager_set_level(const char* tag, esp_log_level_t level) {
    if (!tag) return ESP_ERR_INVALID_ARG;

    if (strcmp(tag, "*") == 0) {
        ESP_LOGI(TAG, "Setting default log level to %d", level);
        default_log_level = level;
        esp_log_level_set("*", level);
        return ESP_OK;
    }

    for (int i = 0; i < log_level_count; i++) {
        if (strcmp(log_levels[i].tag, tag) == 0) {
            log_levels[i].level = level;
            esp_log_level_set(tag, level);
            return ESP_OK;
        }
    }

    if (log_level_count < MAX_LOG_TAGS) {
        strncpy(log_levels[log_level_count].tag, tag, sizeof(log_levels[0].tag) - 1);
        log_levels[log_level_count].level = level;
        log_level_count++;
        esp_log_level_set(tag, level);
        return ESP_OK;
    }

    return ESP_ERR_NO_MEM;
}

esp_log_level_t logging_manager_get_level(const char* tag) {
    for (int i = 0; i < log_level_count; i++) {
        if (strcmp(log_levels[i].tag, tag) == 0) {
            return log_levels[i].level;
        }
    }
    return default_log_level;
}

char* logging_manager_get_levels_json(void) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "*", default_log_level);
    for (int i = 0; i < log_level_count; i++) {
        cJSON_AddNumberToObject(root, log_levels[i].tag, log_levels[i].level);
    }
    char* json_str = cJSON_Print(root);
    cJSON_Delete(root);
    return json_str;
}

static void switch_log_file(void) {
    if (xSemaphoreTake(log_mutex, portMAX_DELAY) == pdTRUE) {
        if (current_log_file) {
            fclose(current_log_file);
        }

        current_log_filename = (strcmp(current_log_filename, LOG_FILE_1) == 0) ? LOG_FILE_2 : LOG_FILE_1;
        
        // Open the new file in write mode to truncate it
        current_log_file = fopen(current_log_filename, "w");
        if (current_log_file) {
            ESP_LOGI(TAG, "Switched to log file: %s", current_log_filename);
        } else {
            ESP_LOGE(TAG, "Failed to open new log file: %s", current_log_filename);
        }
        xSemaphoreGive(log_mutex);
    }
}

esp_err_t logging_manager_upload_logs(void) {
    if (!mqtt_client_is_connected()) {
        ESP_LOGE(TAG, "Cannot upload logs, MQTT not connected.");
        return ESP_FAIL;
    }

    const char* upload_filename = (strcmp(current_log_filename, LOG_FILE_1) == 0) ? LOG_FILE_2 : LOG_FILE_1;
    FILE* f = fopen(upload_filename, "r");
    if (!f) {
        ESP_LOGE(TAG, "No previous log file to upload: %s", upload_filename);
        return ESP_FAIL;
    }

    char* buffer = malloc(1024);
    if (!buffer) {
        fclose(f);
        return ESP_ERR_NO_MEM;
    }

    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    char topic[128];
    snprintf(topic, sizeof(topic), "device/logs/%s", device_id);

    size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, 1023, f)) > 0) {
        buffer[bytes_read] = '\0';
        mqtt_client_publish(topic, buffer, bytes_read, 0, 0);
        vTaskDelay(pdMS_TO_TICKS(50)); // Avoid overwhelming MQTT
    }

    free(buffer);
    fclose(f);

    // Clear the uploaded log file
    f = fopen(upload_filename, "w");
    if (f) {
        fclose(f);
    }

    ESP_LOGI(TAG, "Log upload complete for %s", upload_filename);
    return ESP_OK;
}

// This task should run periodically to check log file size
void logging_maintenance_task(void* pvParameters) {
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(60000)); // Check every minute

        if (xSemaphoreTake(log_mutex, portMAX_DELAY) == pdTRUE) {
            if (current_log_file) {
                long size = ftell(current_log_file);
                if (size > MAX_LOG_FILE_SIZE) {
                    ESP_LOGI(TAG, "Log file size (%ld) exceeds limit. Switching files.", size);
                    switch_log_file();
                }
            }
            xSemaphoreGive(log_mutex);
        }
    }
}
