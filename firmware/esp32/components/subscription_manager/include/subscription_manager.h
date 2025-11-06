#ifndef SUBSCRIPTION_MANAGER_H
#define SUBSCRIPTION_MANAGER_H

#include "esp_err.h"
#include <stdbool.h>

// Define the different subscription tiers
typedef enum {
    SUBSCRIPTION_TIER_FREE,
    SUBSCRIPTION_TIER_BASIC,
    SUBSCRIPTION_TIER_PREMIUM,
    SUBSCRIPTION_TIER_ENTERPRISE,
    SUBSCRIPTION_TIER_MAX,
} subscription_tier_t;

// Define feature flags that are controlled by subscriptions
typedef enum {
    FEATURE_FLAG_BASIC_SENSORS,      // Always available
    FEATURE_FLAG_ADVANCED_SENSORS,   // Basic+
    FEATURE_FLAG_AI_PLANT_HEALTH,    // Basic+
    FEATURE_FLAG_VISION_ANALYSIS,    // Premium+
    FEATURE_FLAG_GPS_TRACKING,       // Premium+
    FEATURE_FLAG_HIGH_FREQ_DATA,     // Premium+
    FEATURE_FLAG_ENTERPRISE_API,     // Enterprise only
    
    // New Features
    FEATURE_FLAG_CELLULAR_CONNECTIVITY, // Premium+
    FEATURE_FLAG_DATA_AGGREGATION,      // Basic+
    FEATURE_FLAG_DATA_HISTORIAN,        // Premium+
    FEATURE_FLAG_SECURE_LOGGING,        // Enterprise only
    FEATURE_FLAG_HYBRID_ENCRYPTION,     // Enterprise only

    FEATURE_FLAG_MAX,
} feature_flag_t;

/**
 * @brief Initializes the subscription manager.
 *
 * This function loads the current subscription tier from NVS and sets up
 * the feature flags accordingly.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t subscription_manager_init(void);

/**
 * @brief Updates the device's subscription tier.
 *
 * This would typically be called after receiving a command from the cloud
 * (e.g., via MQTT) upon a successful payment or plan change. It saves the
 * new tier to NVS and re-evaluates feature flags.
 *
 * @param new_tier The new subscription tier to apply.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t subscription_manager_set_tier(subscription_tier_t new_tier);

/**
 * @brief Gets the current subscription tier.
 *
 * @return The current subscription_tier_t.
 */
subscription_tier_t subscription_manager_get_tier(void);

/**
 * @brief Checks if a specific feature is enabled for the current subscription tier.
 *
 * This is the main function that other components will use to gate their
 * functionality.
 *
 * @param feature The feature to check.
 * @return true if the feature is enabled, false otherwise.
 */
bool subscription_manager_is_feature_enabled(feature_flag_t feature);

/**
 * @brief Checks if a specific feature is enabled for the current subscription tier
 *        and the current hardware platform.
 *
 * This is the main function that other components will use to gate their
 * functionality.
 *
 * @param feature The feature to check.
 * @return true if the feature is enabled, false otherwise.
 */
bool subscription_manager_is_feature_enabled(feature_flag_t feature);

/**
 * @brief Converts a subscription tier enum to its string representation.
 *
 * @param tier The subscription tier.
 * @return A const char* representing the tier.
 */
const char* subscription_manager_get_tier_string(subscription_tier_t tier);

#endif // SUBSCRIPTION_MANAGER_H
