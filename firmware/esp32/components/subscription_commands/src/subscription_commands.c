#include "subscription_commands.h"
#include "command_registry.h"
#include "subscription_manager.h"
#include "cJSON.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "SUB_COMMANDS";

/**
 * @brief Handles the 'set_subscription_tier' command.
 *
 * Expected payload:
 * {
 *   "tier": "free" | "basic" | "premium" | "enterprise"
 * }
 *
 * @param payload The cJSON payload from the command.
 * @return ESP_OK on success, ESP_ERR_INVALID_ARG if payload is invalid,
 *         or another error code from the subscription manager.
 */
static esp_err_t handle_set_subscription_tier(cJSON *payload) {
    if (!payload) {
        ESP_LOGE(TAG, "Payload is NULL for set_subscription_tier");
        return ESP_ERR_INVALID_ARG;
    }

    const cJSON *tier_json = cJSON_GetObjectItemCaseSensitive(payload, "tier");
    if (!cJSON_IsString(tier_json) || (tier_json->valuestring == NULL)) {
        ESP_LOGE(TAG, "Invalid or missing 'tier' in payload");
        return ESP_ERR_INVALID_ARG;
    }

    const char *tier_str = tier_json->valuestring;
    subscription_tier_t new_tier;

    if (strcasecmp(tier_str, "free") == 0) {
        new_tier = SUBSCRIPTION_TIER_FREE;
    } else if (strcasecmp(tier_str, "basic") == 0) {
        new_tier = SUBSCRIPTION_TIER_BASIC;
    } else if (strcasecmp(tier_str, "premium") == 0) {
        new_tier = SUBSCRIPTION_TIER_PREMIUM;
    } else if (strcasecmp(tier_str, "enterprise") == 0) {
        new_tier = SUBSCRIPTION_TIER_ENTERPRISE;
    } else {
        ESP_LOGE(TAG, "Unknown subscription tier: %s", tier_str);
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Received command to set subscription tier to %s", tier_str);
    return subscription_manager_set_tier(new_tier);
}

esp_err_t subscription_commands_init(void) {
    esp_err_t err = command_registry_register("set_subscription_tier", handle_set_subscription_tier);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register 'set_subscription_tier' command: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "Subscription commands initialized.");
    return ESP_OK;
}
