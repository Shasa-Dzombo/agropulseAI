#ifndef LOGGING_MANAGER_H
#define LOGGING_MANAGER_H

#include "esp_err.h"
#include "esp_log.h"

/**
 * @brief Initializes the logging manager.
 *
 * This function sets up the custom vprintf hook to intercept log messages
 * and initializes the log level management system.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t logging_manager_init(void);

/**
 * @brief Sets the log level for a specific component tag.
 *
 * @param tag The log tag (e.g., "WIFI_MANAGER").
 * @param level The desired log level.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NO_MEM if no space for new tag,
 *         or ESP_ERR_INVALID_ARG for invalid arguments.
 */
esp_err_t logging_manager_set_level(const char* tag, esp_log_level_t level);

/**
 * @brief Gets the currently configured log level for a specific tag.
 *
 * If the tag has no specific level set, it returns the default level.
 *
 * @param tag The log tag to query.
 * @return esp_log_level_t The current log level for the tag.
 */
esp_log_level_t logging_manager_get_level(const char* tag);

/**
 * @brief Gets a JSON string representing all configured log levels.
 *
 * The caller is responsible for freeing the returned string.
 *
 * @return char* A dynamically allocated JSON string, or NULL on failure.
 */
char* logging_manager_get_levels_json(void);

/**
 * @brief Triggers the upload of persisted log files.
 *
 * This function will read the log files from SPIFFS and publish them
 * to a dedicated MQTT topic.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t logging_manager_upload_logs(void);

#endif // LOGGING_MANAGER_H
