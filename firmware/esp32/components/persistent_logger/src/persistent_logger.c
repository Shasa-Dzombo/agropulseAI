#include "persistent_logger.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "storage_manager.h"
#include "mqtt_client.h"
#include "app_config.h"

static const char *TAG = "PERSISTENT_LOGGER";

static char g_log_file_base_path[64];
static size_t g_max_log_file_size;
static int g_max_log_files;
static int g_current_log_file_index = 0;
static size_t g_current_log_file_size = 0;
static esp_log_level_t g_log_level = ESP_LOG_INFO;

static SemaphoreHandle_t g_log_mutex;

static int persistent_log_vprintf(const char *fmt, va_list args);
static void rotate_log_files_if_needed();

esp_err_t persistent_logger_init(const char *log_file_path, size_t max_file_size, int max_files) {
    strncpy(g_log_file_base_path, log_file_path, sizeof(g_log_file_base_path) - 1);
    g_max_log_file_size = max_file_size;
    g_max_log_files = max_files;

    g_log_mutex = xSemaphoreCreateMutex();
    if (!g_log_mutex) {
        ESP_LOGE(TAG, "Failed to create log mutex");
        return ESP_ERR_NO_MEM;
    }

    // Find the last written log file to continue appending
    for (int i = 0; i < g_max_log_files; i++) {
        char current_path[128];
        snprintf(current_path, sizeof(current_path), "%s.%d", g_log_file_base_path, i);
        if (storage_manager_file_exists(current_path)) {
            g_current_log_file_index = i;
            g_current_log_file_size = storage_manager_get_file_size(current_path);
        } else {
            break; // Found the first non-existent file, start here
        }
    }

    esp_log_set_vprintf(persistent_log_vprintf);
    ESP_LOGI(TAG, "Persistent logger initialized. Logging to %s", g_log_file_base_path);
    return ESP_OK;
}

void persistent_logger_set_level(esp_log_level_t level) {
    g_log_level = level;
}

static int persistent_log_vprintf(const char *fmt, va_list args) {
    if (xSemaphoreTake(g_log_mutex, pdMS_TO_TICKS(100)) != pdTRUE) {
        // Could not get mutex, just print to UART and drop from file
        return vprintf(fmt, args);
    }

    // First, print to default UART output
    int ret = vprintf(fmt, args);

    // Now, write to the persistent log file if level is sufficient
    // Note: We can't easily get the log level of the incoming message here.
    // A more advanced implementation would wrap ESP_LOGx macros.
    // For now, we write what we receive. A filter is applied at a higher level.
    
    char log_buffer[256];
    int len = vsnprintf(log_buffer, sizeof(log_buffer), fmt, args);

    if (len > 0) {
        rotate_log_files_if_needed();
        char current_path[128];
        snprintf(current_path, sizeof(current_path), "%s.%d", g_log_file_base_path, g_current_log_file_index);
        
        if (storage_manager_write_file(current_path, log_buffer, len, g_current_log_file_size) == ESP_OK) {
            g_current_log_file_size += len;
        } else {
            ESP_LOGE(TAG, "Failed to write to log file %s", current_path);
        }
    }

    xSemaphoreGive(g_log_mutex);
    return ret;
}

static void rotate_log_files_if_needed() {
    if (g_current_log_file_size < g_max_log_file_size) {
        return;
    }

    g_current_log_file_index = (g_current_log_file_index + 1) % g_max_log_files;
    g_current_log_file_size = 0;

    char path_to_delete[128];
    snprintf(path_to_delete, sizeof(path_to_delete), "%s.%d", g_log_file_base_path, g_current_log_file_index);
    
    if (storage_manager_file_exists(path_to_delete)) {
        ESP_LOGI(TAG, "Rotating log file. Deleting oldest log: %s", path_to_delete);
        storage_manager_delete_file(path_to_delete);
    }
}

esp_err_t persistent_logger_upload_logs(void) {
    ESP_LOGI(TAG, "Starting log upload process.");
    if (!mqtt_client_is_connected()) {
        ESP_LOGE(TAG, "Cannot upload logs, MQTT client is not connected.");
        return ESP_FAIL;
    }

    char topic[128];
    char device_id[64];
    app_config_get_string("device_id", device_id, sizeof(device_id));
    snprintf(topic, sizeof(topic), "/devices/%s/events/logs", device_id);

    if (xSemaphoreTake(g_log_mutex, portMAX_DELAY) != pdTRUE) {
        return ESP_FAIL;
    }

    for (int i = 0; i < g_max_log_files; i++) {
        char file_path[128];
        snprintf(file_path, sizeof(file_path), "%s.%d", g_log_file_base_path, i);

        if (storage_manager_file_exists(file_path)) {
            size_t file_size = storage_manager_get_file_size(file_path);
            char *file_content = malloc(file_size + 1);
            if (file_content) {
                if (storage_manager_read_file(file_path, file_content, file_size) == ESP_OK) {
                    file_content[file_size] = '\0';
                    // Publish the log file content. Might need to be chunked for large files.
                    mqtt_client_publish(topic, file_content, 0, 0);
                    ESP_LOGI(TAG, "Uploaded log file: %s (%d bytes)", file_path, file_size);
                }
                free(file_content);
            }
        }
    }

    xSemaphoreGive(g_log_mutex);
    ESP_LOGI(TAG, "Log upload process finished.");
    return ESP_OK;
}
