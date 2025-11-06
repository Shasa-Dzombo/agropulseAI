/**
 * @file device_shadow.h
 * @brief Manages the device shadow, synchronizing state with the cloud.
 *
 * This module implements the device shadow pattern. It maintains a JSON document
 * representing the device's state, which is synchronized with a cloud service (like AWS IoT).
 *
 * The shadow has two main parts:
 * - "reported": The last known state reported by the device (e.g., current sensor values, pump status).
 * - "desired": The state the cloud wants the device to be in (e.g., turn the pump on).
 *
 * This module handles:
 * - Subscribing to shadow topics on MQTT connect.
 * - Requesting the full shadow on startup.
 * - Processing "delta" updates (differences between desired and reported).
 * - Publishing updates to the "reported" state.
 * - Providing an interface for other components to interact with the shadow.
 */
#ifndef DEVICE_SHADOW_H
#define DEVICE_SHADOW_H

#include "esp_err.h"
#include "cJSON.h"

/**
 * @brief Initializes the device shadow module.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t device_shadow_init(void);

/**
 * @brief To be called by the MQTT client when it connects.
 *
 * This function subscribes to the necessary shadow topics and requests the
 * current shadow state from the cloud.
 */
void device_shadow_handle_mqtt_connect(void);

/**
 * @brief Processes an incoming MQTT message intended for the device shadow.
 *
 * @param[in] topic The MQTT topic the message was received on.
 * @param[in] payload The message payload.
 */
void device_shadow_handle_mqtt_message(const char* topic, const char* payload);

/**
 * @brief Updates a portion of the 'reported' section of the device shadow.
 *
 * This function takes a cJSON object and merges it into the 'reported' state,
 * then publishes the update to the cloud. The provided cJSON object will be
 * deleted by this function.
 *
 * Example:
 *   cJSON* report = cJSON_CreateObject();
 *   cJSON* sensors = cJSON_CreateObject();
 *   cJSON_AddItemToObject(report, "sensors", sensors);
 *   cJSON_AddNumberToObject(sensors, "temperature", 25.5);
 *   device_shadow_update_reported_state(report);
 *
 * @param[in] reported_update A cJSON object containing the state to update.
 * @return
 *     - ESP_OK: If the update was successfully queued for publishing.
 *     - ESP_FAIL: On failure.
 */
esp_err_t device_shadow_update_reported_state(cJSON* reported_update);

#endif // DEVICE_SHADOW_H
