#include "platform.h"
#include "esp_system.h"
#include "esp_chip_info.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h" // Added for NVS init
#include "secure_element_manager.h" // For unique ID

static const char *TAG = "PLATFORM_ESP32";

esp_err_t platform_init(void) {
    // Initialize NVS as a core platform service
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_LOGW(TAG, "NVS partition was corrupt, erasing and re-initializing.");
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    ESP_LOGI(TAG, "ESP32 Platform Initialized.");
    return ESP_OK;
}

void platform_get_chip_info(platform_chip_info_t *info) {
    if (!info) return;

    esp_chip_info_t esp_info;
    esp_chip_info(&esp_info);

    info->type = PLATFORM_TYPE_ESP32;
    info->cores = esp_info.cores;
    info->revision = esp_info.revision;

    switch(esp_info.model) {
        case CHIP_ESP32:
            info->model = "ESP32";
            break;
        case CHIP_ESP32S2:
            info->model = "ESP32-S2";
            break;
        case CHIP_ESP32S3:
            info->model = "ESP32-S3";
            break;
        case CHIP_ESP32C3:
            info->model = "ESP32-C3";
            break;
        default:
            info->model = "Unknown ESP32";
            break;
    }
}

esp_err_t platform_get_unique_id(uint8_t *id_buf, size_t *len) {
    if (!id_buf || !len) {
        return ESP_ERR_INVALID_ARG;
    }

    // First, try to get the serial from the secure element, as it's the most secure and reliable ID.
    esp_err_t ret = secure_element_manager_get_serial_number(id_buf, len);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Using secure element serial number as unique ID.");
        return ESP_OK;
    }

    ESP_LOGW(TAG, "Could not get serial from secure element (err: %s). Falling back to MAC address.", esp_err_to_name(ret));
    
    // If the secure element fails or isn't present, fall back to the base MAC address.
    if (*len < 6) {
        return ESP_ERR_NO_MEM;
    }
    
    ret = esp_efuse_mac_get_default(id_buf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get base MAC address from EFUSE: %s", esp_err_to_name(ret));
        return ret;
    }
    *len = 6;
    return ESP_OK;
}

void platform_reboot(void) {
    ESP_LOGW(TAG, "Rebooting system via platform call.");
    esp_restart();
}

size_t platform_get_free_heap_size(void) {
    return esp_get_free_heap_size();
}

int64_t platform_get_uptime_ms(void) {
    return esp_timer_get_time() / 1000;
}
