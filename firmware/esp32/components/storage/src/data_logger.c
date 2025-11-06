/**
 * @file data_logger.c
 * @brief Implementation of the data logger.
 */

#include "data_logger.h"
#include "spiffs_manager.h"
#include "esp_log.h"
#include <stdio.h>
#include <string.h>
#include <dirent.h>

static const char *TAG = "DATA_LOGGER";
#define LOG_FILE_PATH "/spiffs/datalog.csv"
#define MAX_LOG_SIZE (10 * 1024) // 10 KB max log file size before rotation

#define TEMP_LOG_FILE_PATH "/spiffs/datalog.tmp"

esp_err_t data_logger_init(void) {
    // Check if the main log file exists, if not, create it.
    FILE* f = fopen(LOG_FILE_PATH, "r");
    if (f == NULL) {
        ESP_LOGI(TAG, "Log file not found, creating a new one.");
        f = fopen(LOG_FILE_PATH, "w");
        if (f == NULL) {
            ESP_LOGE(TAG, "Failed to create log file.");
            return ESP_FAIL;
        }
        // You could add a header here if you want
        // fprintf(f, "timestamp,temperature,humidity,soil_moisture,light_lux\n");
    }
    fclose(f);

    ESP_LOGI(TAG, "Data logger initialized.");
    return ESP_OK;
}

esp_err_t data_logger_log(const sensor_data_t* data) {
    // First, check current file size and rotate if necessary
    FILE* f_check = fopen(LOG_FILE_PATH, "r");
    if (f_check) {
        fseek(f_check, 0, SEEK_END);
        long size = ftell(f_check);
        fclose(f_check);

        if (size > MAX_LOG_SIZE) {
            ESP_LOGI(TAG, "Log file size (%ld bytes) exceeds limit (%d bytes). Rotating.", size, MAX_LOG_SIZE);
            char new_path[64];
            snprintf(new_path, sizeof(new_path), "/spiffs/datalog_%lld.csv", (long long)time(NULL));
            if (rename(LOG_FILE_PATH, new_path) != 0) {
                ESP_LOGE(TAG, "Failed to rotate log file. Deleting to prevent disk full.");
                remove(LOG_FILE_PATH);
            }
        }
    }

    FILE* f = fopen(LOG_FILE_PATH, "a");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open log file for writing.");
        return ESP_FAIL;
    }

    fprintf(f, "%lld,%.2f,%.2f,%.2f,%.2f\n", (long long)time(NULL), data->temperature, data->humidity, data->soil_moisture, data->light_lux);
    fclose(f);
    ESP_LOGD(TAG, "Logged sensor data to SPIFFS.");
    return ESP_OK;
}

esp_err_t data_logger_read_oldest_entry(char** buffer, size_t* entry_size) {
    FILE* f = fopen(LOG_FILE_PATH, "r");
    if (f == NULL) {
        return ESP_ERR_NOT_FOUND; // No log file
    }

    char line[256]; // Assume max line length
    if (fgets(line, sizeof(line), f) == NULL) {
        fclose(f);
        return ESP_ERR_NOT_FOUND; // File is empty
    }
    fclose(f);

    // Remove newline character if present
    char* newline = strchr(line, '\n');
    if (newline) {
        *newline = '\0';
    }

    *entry_size = strlen(line);
    *buffer = (char*)malloc(*entry_size + 1);
    if (*buffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate memory for log entry");
        return ESP_ERR_NO_MEM;
    }

    strcpy(*buffer, line);
    return ESP_OK;
}

esp_err_t data_logger_delete_oldest_entry(void) {
    FILE* f_read = fopen(LOG_FILE_PATH, "r");
    if (f_read == NULL) {
        ESP_LOGW(TAG, "Cannot delete entry, log file not found.");
        return ESP_ERR_NOT_FOUND;
    }

    // Check if file is empty
    fseek(f_read, 0, SEEK_END);
    if (ftell(f_read) == 0) {
        fclose(f_read);
        ESP_LOGI(TAG, "Log file is empty, nothing to delete.");
        return ESP_OK;
    }
    fseek(f_read, 0, SEEK_SET);

    FILE* f_write = fopen(TEMP_LOG_FILE_PATH, "w");
    if (f_write == NULL) {
        ESP_LOGE(TAG, "Failed to open temp file for writing.");
        fclose(f_read);
        return ESP_FAIL;
    }

    char line[256];
    // Skip the first line (the one we want to delete)
    if (fgets(line, sizeof(line), f_read) != NULL) {
        // Copy the rest of the lines
        while (fgets(line, sizeof(line), f_read) != NULL) {
            fputs(line, f_write);
        }
    }

    fclose(f_read);
    fclose(f_write);

    // Replace the original file with the temp file
    if (remove(LOG_FILE_PATH) != 0) {
        ESP_LOGE(TAG, "Failed to remove original log file.");
        remove(TEMP_LOG_FILE_PATH); // Clean up temp file
        return ESP_FAIL;
    }

    if (rename(TEMP_LOG_FILE_PATH, LOG_FILE_PATH) != 0) {
        ESP_LOGE(TAG, "Failed to rename temp log file.");
        return ESP_FAIL;
    }

    ESP_LOGD(TAG, "Deleted oldest log entry.");
    return ESP_OK;
}

