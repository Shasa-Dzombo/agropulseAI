/**
 * @file ota_manager.c
 * @brief Implementation of the OTA manager.
 */

#include "ota_manager.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "http_client.h"
#include "event_bus.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "OTA_MANAGER";
#define OTA_BUFF_SIZE 2048

typedef enum {
    OTA_TYPE_FIRMWARE,
    OTA_TYPE_MODEL,
} ota_type_t;

typedef struct {
    const char* url;
    ota_type_t type;
    const char* model_path; // Only used for model OTA
} ota_update_args_t;

static void ota_task(void *pvParameter);
static esp_err_t do_firmware_update(const char* url);
static esp_err_t do_model_update(const char* url, const char* path);

esp_err_t ota_manager_init(void) {
    ESP_LOGI(TAG, "OTA manager initialized.");
    return ESP_OK;
}

esp_err_t ota_manager_start_update(const char* url) {
    // For backward compatibility, default to firmware update
    return ota_manager_start_update_ex(url, OTA_TYPE_FIRMWARE, NULL);
}

esp_err_t ota_manager_start_update_ex(const char* url, ota_type_t type, const char* model_path) {
    ota_update_args_t* args = malloc(sizeof(ota_update_args_t));
    if (!args) {
        ESP_LOGE(TAG, "Failed to allocate memory for OTA args");
        return ESP_ERR_NO_MEM;
    }

    args->url = strdup(url);
    if (!args->url) {
        ESP_LOGE(TAG, "Failed to allocate memory for URL");
        free(args);
        return ESP_ERR_NO_MEM;
    }

    args->type = type;
    
    if (model_path) {
        args->model_path = strdup(model_path);
        if (!args->model_path) {
            ESP_LOGE(TAG, "Failed to allocate memory for model path");
            free((void*)args->url);
            free(args);
            return ESP_ERR_NO_MEM;
        }
    } else {
        args->model_path = NULL;
    }

    ESP_LOGI(TAG, "Starting OTA task for URL: %s", url);
    if (xTaskCreate(&ota_task, "ota_task", 8192, args, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "Failed to create OTA task");
        free((void*)args->url);
        if (args->model_path) {
            free((void*)args->model_path);
        }
        free(args);
        return ESP_FAIL;
    }
    
    return ESP_OK;
}

static void ota_task(void *pvParameter) {
    ota_update_args_t* args = (ota_update_args_t*)pvParameter;
    esp_err_t err = ESP_FAIL;

    event_bus_post(SYSTEM_EVENT_OTA_START, NULL, 0);

    switch (args->type) {
        case OTA_TYPE_FIRMWARE:
            ESP_LOGI(TAG, "Performing FIRMWARE update.");
            err = do_firmware_update(args->url);
            break;
        case OTA_TYPE_MODEL:
            ESP_LOGI(TAG, "Performing MODEL update.");
            err = do_model_update(args->url, args->model_path);
            break;
        default:
            ESP_LOGE(TAG, "Unknown OTA type!");
            break;
    }

    if (err == ESP_OK) {
        event_bus_post(SYSTEM_EVENT_OTA_SUCCESS, NULL, 0);
        ESP_LOGI(TAG, "OTA Update successful. Rebooting...");
        vTaskDelay(pdMS_TO_TICKS(2000));
        esp_restart();
    } else {
        event_bus_post(SYSTEM_EVENT_OTA_FAIL, NULL, 0);
        ESP_LOGE(TAG, "OTA Update failed.");
    }

    // Cleanup
    free((void*)args->url);
    if (args->model_path) {
        free((void*)args->model_path);
    }
    free(args);

    vTaskDelete(NULL);
}
    free((void*)args->url);
    if (args->model_path) {
        free((void*)args->model_path);
    }
    free(args);

    vTaskDelete(NULL);
}

static esp_err_t do_firmware_update(const char* url) {
    esp_http_client_config_t config = {
        .url = url,
        .cert_pem = NULL, // In production, you'd use a cert
    };

    esp_http_client_handle_t client = http_client_init(&config);
    if (client == NULL) {
        return ESP_FAIL;
    }

    char *ota_write_buf = malloc(OTA_BUFF_SIZE);
    if (!ota_write_buf) {
        http_client_cleanup(client);
        return ESP_ERR_NO_MEM;
    }

    esp_ota_handle_t update_handle = 0;
    const esp_partition_t *update_partition = NULL;

    update_partition = esp_ota_get_next_update_partition(NULL);
    if (update_partition == NULL) {
        ESP_LOGE(TAG, "Failed to get next update partition.");
        goto cleanup;
    }
    ESP_LOGI(TAG, "Writing to partition subtype %d at offset 0x%x",
             update_partition->subtype, update_partition->address);

    esp_err_t err = esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &update_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin failed (%s)", esp_err_to_name(err));
        goto cleanup;
    }

    ESP_LOGI(TAG, "Starting firmware update...");
    
    int binary_file_length = 0;
    int data_read;
    while ((data_read = http_client_read(client, ota_write_buf, OTA_BUFF_SIZE)) > 0) {
        esp_err_t ret = esp_ota_write(update_handle, (const void *)ota_write_buf, data_read);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "esp_ota_write failed (%s)", esp_err_to_name(ret));
            goto cleanup;
        }
        binary_file_length += data_read;
        int progress = (binary_file_length * 100) / total_len;
        event_bus_post(SYSTEM_EVENT_OTA_PROGRESS, &progress, sizeof(progress));
    }

    if (data_read < 0) {
        ESP_LOGE(TAG, "HTTP read error during firmware download.");
        err = ESP_FAIL;
        goto cleanup;
    }

    err = esp_ota_end(update_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_end failed (%s)!", esp_err_to_name(err));
        goto cleanup;
    }
    
    // For now, we skip signature verification as it's complex to simulate fully
    // In a real scenario, you would download the signature and call the verifier.
    ESP_LOGW(TAG, "Skipping signature verification in this example.");
    
    // Set the new partition to boot
    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_set_boot_partition failed (%s)!", esp_err_to_name(err));
        goto cleanup;
    }

    ESP_LOGI(TAG, "OTA update successful. Restarting device...");
    vTaskDelay(pdMS_TO_TICKS(2000));
    esp_restart();

cleanup:
    http_client_close(client);
    http_client_cleanup(client);
    free(ota_write_buf);
    return err;
}

static esp_err_t do_model_update(const char* url, const char* path) {
    if (path == NULL) {
        ESP_LOGE(TAG, "Model path cannot be null for model OTA.");
        return ESP_ERR_INVALID_ARG;
    }

    esp_http_client_config_t config = {
        .url = url,
        .cert_pem = NULL, // In production, you'd use a cert
    };

    esp_http_client_handle_t client = http_client_init(&config);
    if (client == NULL) {
        return ESP_FAIL;
    }

    char* buffer = malloc(OTA_BUFF_SIZE);
    if (!buffer) {
        http_client_cleanup(client);
        return ESP_ERR_NO_MEM;
    }

    // Open file on SPIFFS for writing
    ESP_LOGI(TAG, "Downloading model to %s", path);
    FILE* f = fopen(path, "wb");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open file for writing: %s", path);
        free(buffer);
        http_client_cleanup(client);
        return ESP_FAIL;
    }

    int total_written = 0;
    int data_read;
    esp_err_t err = ESP_OK;

    while ((data_read = http_client_read(client, buffer, OTA_BUFF_SIZE)) > 0) {
        if (fwrite(buffer, 1, data_read, f) != data_read) {
            ESP_LOGE(TAG, "Failed to write to model file.");
            err = ESP_FAIL;
            break;
        }
        total_written += data_read;
    }

    if (data_read < 0) {
        ESP_LOGE(TAG, "HTTP read error during model download.");
        err = ESP_FAIL;
    }

    fclose(f);
    free(buffer);
    http_client_close(client);
    http_client_cleanup(client);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Model downloaded successfully (%d bytes).", total_written);
        // Here you would typically trigger the model manager to reload the new model
    } else {
        // Delete the partial file on failure
        remove(path);
    }

    return err;
}
