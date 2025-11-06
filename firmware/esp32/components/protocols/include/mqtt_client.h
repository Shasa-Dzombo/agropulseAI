/**
 * @file mqtt_client.h
 * @brief Manages the MQTT client connection and communication.
 *
 * This component handles the connection to an MQTT broker, subscribing to topics,
 * and publishing messages. It is designed to be resilient, with automatic
 * reconnection logic.
 *
 * Features:
 * - Connects to the MQTT broker specified in the device configuration.
 * - Automatically reconnects on disconnection.
 * - Posts `SYSTEM_EVENT_MQTT_CONNECTED` and `SYSTEM_EVENT_MQTT_DISCONNECTED`.
 * - Provides a simple API for publishing and subscribing.
 * - Handles incoming message routing (can be extended with a callback system).
 */
#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include "esp_err.h"

/**
 * @brief Initializes the MQTT client.
 *
 * This function configures the MQTT client based on settings from the
 * configuration manager and registers event handlers to start the connection
 * process once Wi-Fi is available.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t mqtt_client_init(void);

/**
 * @brief Starts the MQTT client and connects to the broker.
 *
 * This should typically be called after a Wi-Fi connection is established.
 *
 * @return
 *     - ESP_OK: If the client was started successfully.
 *     - ESP_FAIL: On failure.
 */
esp_err_t mqtt_client_start(void);

/**
 * @brief Stops the MQTT client and disconnects from the broker.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t mqtt_client_stop(void);

/**
 * @brief Publishes a message to a specific MQTT topic.
 *
 * @param topic The topic to publish to.
 * @param data The message payload.
 * @param len The length of the payload.
 * @param qos The Quality of Service level for the message.
 * @param retain The retain flag.
 * @return The message ID of the published message on success, or -1 on failure.
 */
int mqtt_client_publish(const char *topic, const char *data, int len, int qos, int retain);

/**
 * @brief Subscribes to an MQTT topic.
 *
 * @param topic The topic to subscribe to.
 * @param qos The desired Quality of Service level.
 * @return The message ID of the subscribe request on success, or -1 on failure.
 */
int mqtt_client_subscribe(const char *topic, int qos);

/**
 * @brief Checks if the MQTT client is currently connected to the broker.
 *
 * @return true if connected, false otherwise.
 */
bool mqtt_client_is_connected(void);

#endif // MQTT_CLIENT_H
