/**
 * @file spiffs_manager.c
 * @brief Implementation of the SPIFFS manager.
 */

#include "spiffs_manager.h"
#include "esp_spiffs.h"
#include "esp_log.h"

static const char *TAG = "SPIFFS_MANAGER";
static char spiffs_partition_label[32] = {0};

esp_err_t spiffs_manager_init(const char* partition_label) {
    ESP_LOGI(TAG, "Initializing SPIFFS");

    esp_vfs_spiffs_conf_t conf = {
      .base_path = "/spiffs",
      .partition_label = partition_label,
      .max_files = 5,
      .format_if_mount_failed = true
    };

    esp_err_t ret = esp_vfs_spiffs_register(&conf);

    if (ret != ESP_OK) {
        if (ret == ESP_FAIL) {
            ESP_LOGE(TAG, "Failed to mount or format filesystem");
        } else if (ret == ESP_ERR_NOT_FOUND) {
            ESP_LOGE(TAG, "Failed to find SPIFFS partition '%s'", partition_label);
        } else {
            ESP_LOGE(TAG, "Failed to initialize SPIFFS (%s)", esp_err_to_name(ret));
        }
        return ESP_FAIL;
    }
    
    strncpy(spiffs_partition_label, partition_label, sizeof(spiffs_partition_label) - 1);

    size_t total = 0, used = 0;
    ret = esp_spiffs_info(conf.partition_label, &total, &used);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get SPIFFS partition information (%s)", esp_err_to_name(ret));
    } else {
        ESP_LOGI(TAG, "Partition size: total: %d, used: %d", total, used);
    }

    return ESP_OK;
}

esp_err_t spiffs_manager_deinit(void) {
    if (strlen(spiffs_partition_label) > 0) {
        return esp_vfs_spiffs_unregister(spiffs_partition_label);
    }
    return ESP_OK;
}

esp_err_t spiffs_manager_get_info(size_t* total_bytes, size_t* used_bytes) {
    if (strlen(spiffs_partition_label) > 0) {
        return esp_spiffs_info(spiffs_partition_label, total_bytes, used_bytes);
    }
    return ESP_FAIL;
}
