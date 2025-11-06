#ifndef COMMAND_REGISTRY_H
#define COMMAND_REGISTRY_H

#include "esp_err.h"
#include "cJSON.h"

/**
 * @brief Function signature for a command handler.
 * @param payload The cJSON payload associated with the command.
 * @return ESP_OK on success, or an error code on failure.
 */
typedef esp_err_t (*command_handler_t)(cJSON* payload);

/**
 * @brief Initializes the command registry.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t command_registry_init(void);

/**
 * @brief Registers a command with its handler.
 *
 * @param command The name of the command (e.g., "reboot").
 * @param handler The function to be called when the command is received.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NO_MEM if the registry is full,
 *         or ESP_ERR_INVALID_ARG if arguments are invalid.
 */
esp_err_t command_registry_register(const char* command, command_handler_t handler);

/**
 * @brief Dispatches a command to its registered handler.
 *
 * @param command The name of the command to dispatch.
 * @param payload The cJSON payload for the command.
 * @return esp_err_t ESP_OK if the handler was found and executed successfully,
 *         ESP_ERR_NOT_FOUND if the command is not registered, or the error
 *         code returned by the handler.
 */
esp_err_t command_registry_dispatch(const char* command, cJSON* payload);

#endif // COMMAND_REGISTRY_H
