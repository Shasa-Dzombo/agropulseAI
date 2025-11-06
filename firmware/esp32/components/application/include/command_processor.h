/**
 * @file command_processor.h
 * @brief Processes commands received from an external source, like MQTT.
 *
 * This module is responsible for parsing and executing commands sent to the device.
 * It acts as a central dispatcher, invoking functions in other components based
 * on the command received.
 */
#ifndef COMMAND_PROCESSOR_H
#define COMMAND_PROCESSOR_H

#include "esp_err.h"

/**
 * @brief Initializes the command processor.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t command_processor_init(void);

/**
 * @brief Processes a command payload.
 *
 * @param[in] topic The topic the command was received on.
 * @param[in] payload The command payload, expected to be a JSON string.
 * @return
 *     - ESP_OK: If the command was processed successfully.
 *     - ESP_ERR_INVALID_ARG: If the payload is invalid.
 *     - ESP_FAIL: If the command is unknown or fails to execute.
 */
esp_err_t command_processor_process(const char* topic, const char* payload);

#endif // COMMAND_PROCESSOR_H
