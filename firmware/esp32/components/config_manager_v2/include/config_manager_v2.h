#ifndef CONFIG_MANAGER_V2_H
#define CONFIG_MANAGER_V2_H

#include "esp_err.h"
#include "cJSON.h"

#define CONFIG_VERSION "2.0.0"

/**
 * @brief Opaque handle for the configuration manager.
 */
typedef struct config_manager_v2_t* config_manager_v2_handle_t;

/**
 * @brief Definition of a configuration schema item.
 */
typedef struct {
    const char* key;
    cJSON_Type type;
    bool required;
    const char* default_value; // JSON string representation of the default value
} config_schema_item_t;

/**
 * @brief Initializes the configuration manager with a given schema.
 *
 * This function initializes the V2 configuration manager. It takes a schema
 * to validate the configuration against. It will attempt to load the configuration
 * from NVS. If it doesn't exist, is invalid, or from an older version, it will
 * create a new one based on the default values in the schema.
 *
 * @param schema Pointer to an array of schema items.
 * @param schema_size The number of items in the schema array.
 * @param handle_out Pointer to store the handle of the initialized config manager.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t config_manager_v2_init(const config_schema_item_t* schema, size_t schema_size, config_manager_v2_handle_t* handle_out);

/**
 * @brief Deinitializes the configuration manager and frees resources.
 *
 * @param handle The handle to the configuration manager.
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t config_manager_v2_deinit(config_manager_v2_handle_t handle);

/**
 * @brief Gets a read-only pointer to the current configuration JSON object.
 *
 * The returned cJSON object should NOT be modified or deleted by the caller.
 * It is a pointer to the internal state of the configuration manager.
 *
 * @param handle The handle to the configuration manager.
 * @return const cJSON* A pointer to the configuration object, or NULL on error.
 */
const cJSON* config_manager_v2_get_config(config_manager_v2_handle_t handle);

/**
 * @brief Updates the configuration with a new JSON object.
 *
 * This function takes a cJSON object containing the desired configuration changes.
 * It validates the new settings against the schema, merges them with the existing
 * configuration, and saves the result to NVS atomically.
 *
 * @param handle The handle to the configuration manager.
 * @param new_config A cJSON object with the new configuration values.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t config_manager_v2_update_config(config_manager_v2_handle_t handle, const cJSON* new_config);

/**
 * @brief Resets the configuration to the default values defined in the schema.
 *
 * @param handle The handle to the configuration manager.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t config_manager_v2_reset_to_defaults(config_manager_v2_handle_t handle);

/**
 * @brief Gets a string value from the configuration.
 *
 * @param handle The handle to the configuration manager.
 * @param key The key of the value to retrieve.
 * @param buffer Buffer to store the value.
 * @param buffer_size Size of the buffer.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NOT_FOUND if key doesn't exist,
 *         or ESP_ERR_INVALID_ARG if the value is not a string.
 */
esp_err_t config_manager_v2_get_string(config_manager_v2_handle_t handle, const char* key, char* buffer, size_t buffer_size);

/**
 * @brief Gets an integer value from the configuration.
 *
 * @param handle The handle to the configuration manager.
 * @param key The key of the value to retrieve.
 * @param value Pointer to store the integer value.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NOT_FOUND if key doesn't exist,
 *         or ESP_ERR_INVALID_ARG if the value is not a number.
 */
esp_err_t config_manager_v2_get_int(config_manager_v2_handle_t handle, const char* key, int* value);

/**
 * @brief Gets a boolean value from the configuration.
 *
 * @param handle The handle to the configuration manager.
 * @param key The key of the value to retrieve.
 * @param value Pointer to store the boolean value.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NOT_FOUND if key doesn't exist,
 *         or ESP_ERR_INVALID_ARG if the value is not a boolean.
 */
esp_err_t config_manager_v2_get_bool(config_manager_v2_handle_t handle, const char* key, bool* value);


#endif // CONFIG_MANAGER_V2_H
