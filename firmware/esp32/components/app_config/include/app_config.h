#ifndef APP_CONFIG_H
#define APP_CONFIG_H

#include "esp_err.h"
#include "cJSON.h"

/**
 * @brief Initializes the application configuration manager.
 *
 * This function sets up the schema for the application's configuration
 * and initializes the config_manager_v2 with it.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_init(void);

/**
 * @brief Deinitializes the application configuration manager.
 *
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t app_config_deinit(void);

/**
 * @brief Gets a read-only pointer to the current application configuration.
 *
 * @return const cJSON* A pointer to the configuration object, or NULL on error.
 */
const cJSON* app_config_get(void);

/**
 * @brief Updates the application configuration.
 *
 * @param new_config A cJSON object with the new configuration values.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_update(const cJSON* new_config);

/**
 * @brief Resets the application configuration to defaults.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_reset(void);

/**
 * @brief Gets a specific string value from the application configuration.
 *
 * @param key The key of the value to retrieve.
 * @param buffer Buffer to store the value.
 * @param buffer_size Size of the buffer.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_get_string(const char* key, char* buffer, size_t buffer_size);

/**
 * @brief Gets a specific integer value from the application configuration.
 *
 * @param key The key of the value to retrieve.
 * @param value Pointer to store the integer value.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_get_int(const char* key, int* value);

/**
 * @brief Gets a specific boolean value from the application configuration.
 *
 * @param key The key of the value to retrieve.
 * @param value Pointer to store the boolean value.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t app_config_get_bool(const char* key, bool* value);


#endif // APP_CONFIG_H
