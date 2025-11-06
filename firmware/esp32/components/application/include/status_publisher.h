/**
 * @file status_publisher.h
 * @brief Periodically publishes the device's status to an MQTT topic.
 */
#ifndef STATUS_PUBLISHER_H
#define STATUS_PUBLISHER_H

#include "esp_err.h"

/**
 * @brief Initializes the status publisher module.
 *
 * This creates a task that periodically gathers and publishes device status.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t status_publisher_init(void);

/**
 * @brief Triggers an immediate publication of the device status.
 *
 * @return
 *     - ESP_OK: If the request was sent successfully.
 */
esp_err_t status_publisher_trigger(void);

#endif // STATUS_PUBLISHER_H
