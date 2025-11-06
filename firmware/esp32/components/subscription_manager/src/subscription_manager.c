#include "subscription_manager.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "platform.h" // For platform-specific checks

static const char *TAG = "SUBSCRIPTION_MGR";
static const char *NVS_NAMESPACE = "sub_mgr";
static const char *NVS_KEY_TIER = "tier";

static subscription_tier_t current_tier = SUBSCRIPTION_TIER_FREE;

esp_err_t subscription_manager_init(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS partition was truncated, erasing and re-initializing.");
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    nvs_handle_t nvs_handle;
    err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        return err;
    }

    // Try to read the stored tier. If it's not there, default to FREE.
    int32_t tier_val = (int32_t)SUBSCRIPTION_TIER_FREE;
    err = nvs_get_i32(nvs_handle, NVS_KEY_TIER, &tier_val);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "Subscription tier not found in NVS. Defaulting to FREE.");
        current_tier = SUBSCRIPTION_TIER_FREE;
        // Save the default value for next time
        esp_err_t save_err = nvs_set_i32(nvs_handle, NVS_KEY_TIER, (int32_t)current_tier);
        if (save_err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to save default tier to NVS: %s", esp_err_to_name(save_err));
        } else {
            save_err = nvs_commit(nvs_handle);
            if (save_err != ESP_OK) {
                ESP_LOGE(TAG, "Failed to commit default tier to NVS: %s", esp_err_to_name(save_err));
            }
        }
    } else if (err == ESP_OK) {
        current_tier = (subscription_tier_t)tier_val;
        ESP_LOGI(TAG, "Loaded subscription tier: %s", subscription_manager_get_tier_string(current_tier));
    } else {
        ESP_LOGE(TAG, "Error reading tier from NVS: %s", esp_err_to_name(err));
    }

    nvs_close(nvs_handle);
    return ESP_OK;
}

esp_err_t subscription_manager_set_tier(subscription_tier_t new_tier) {
    if (new_tier > SUBSCRIPTION_TIER_ENTERPRISE) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        return err;
    }

    err = nvs_set_i32(nvs_handle, NVS_KEY_TIER, (int32_t)new_tier);
    if (err == ESP_OK) {
        err = nvs_commit(nvs_handle);
        if (err == ESP_OK) {
            current_tier = new_tier;
            ESP_LOGI(TAG, "Subscription tier updated to: %s", subscription_manager_get_tier_string(current_tier));
        } else {
            ESP_LOGE(TAG, "NVS commit failed: %s", esp_err_to_name(err));
        }
    } else {
        ESP_LOGE(TAG, "NVS set failed: %s", esp_err_to_name(err));
    }

    nvs_close(nvs_handle);
    return err;
}

subscription_tier_t subscription_manager_get_tier(void) {
    return current_tier;
}

bool subscription_manager_is_feature_enabled(feature_flag_t feature) {
    platform_chip_info_t platform_info;
    platform_get_chip_info(&platform_info);

    // Example of platform-specific feature gating
    if (platform_info.type == PLATFORM_TYPE_RASPBERRY_PI && feature == FEATURE_FLAG_VISION_ANALYSIS) {
        // On a Pi, vision analysis might be available even on a lower tier
        if (current_tier >= SUBSCRIPTION_TIER_BASIC) return true;
    }

    switch (current_tier) {
        case SUBSCRIPTION_TIER_ENTERPRISE:
            if (feature == FEATURE_FLAG_SECURE_LOGGING ||
                feature == FEATURE_FLAG_HYBRID_ENCRYPTION ||
                feature == FEATURE_FLAG_ENTERPRISE_API) return true;
            // Fall-through
        case SUBSCRIPTION_TIER_PREMIUM:
            if (feature == FEATURE_FLAG_VISION_ANALYSIS ||
                feature == FEATURE_FLAG_GPS_TRACKING ||
                feature == FEATURE_FLAG_HIGH_FREQ_DATA ||
                feature == FEATURE_FLAG_CELLULAR_CONNECTIVITY ||
                feature == FEATURE_FLAG_DATA_HISTORIAN) return true;
            // Fall-through
        case SUBSCRIPTION_TIER_BASIC:
            if (feature == FEATURE_FLAG_ADVANCED_SENSORS ||
                feature == FEATURE_FLAG_AI_PLANT_HEALTH ||
                feature == FEATURE_FLAG_DATA_AGGREGATION) return true;
            // Fall-through
        case SUBSCRIPTION_TIER_FREE:
            if (feature == FEATURE_FLAG_BASIC_SENSORS) return true;
            break;
    }
    return false;
}

const char* subscription_manager_get_tier_string(subscription_tier_t tier) {
    switch (tier) {
        case SUBSCRIPTION_TIER_FREE: return "Free";
        case SUBSCRIPTION_TIER_BASIC: return "Basic";
        case SUBSCRIPTION_TIER_PREMIUM: return "Premium";
        case SUBSCRIPTION_TIER_ENTERPRISE: return "Enterprise";
        default: return "Unknown";
    }
}
