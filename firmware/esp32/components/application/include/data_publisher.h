/**
 * @file data_publisher.h
 * @brief Handles the publishing of sensor data.
 *
 * This module receives sensor data from the `sensor_sampler` (via a queue)
 * and formats it into a payload (e.g., JSON) to be published over MQTT.
 *
 * Features:
 * - A FreeRTOS queue to decouple data collection from data publishing.
 * - A task that waits for data on the queue.
 * - Formats data into a JSON string.
 * - Publishes the formatted data to a specific MQTT topic.
 */
#ifndef DATA_PUBLISHER_H
#define DATA_PUBLISHER_H

#include "esp_err.h"
#include "sensor_sampler.h" // For sensor_data_t
#include "visual_intelligence.h" // For visual_analysis_result_t
#include "gps_manager.h"       // For gps_location_t

/**
 * @brief Initializes the data publisher component.
 *
 * This function creates the data queue and starts the publisher task.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t data_publisher_init(void);

/**
 * @brief Queues sensor data to be published.
 *
 * This function is called by the sensor sampler to send new data to the
 * publisher task. It is thread-safe.
 *
 * @param data Pointer to the `sensor_data_t` struct to be queued.
 * @return
 *     - ESP_OK: If the data was successfully sent to the queue.
 *     - ESP_FAIL: If the queue is full or an error occurred.
 */
esp_err_t data_publisher_queue_data(const sensor_data_t* data);

/**
 * @brief Publishes vision analysis results and location data.
 *
 * This function formats the detected objects and GPS location into a JSON
 * payload and publishes it to a dedicated MQTT topic.
 *
 * @param results Pointer to an array of visual analysis results.
 * @param result_count The number of results in the array.
 * @param location Pointer to the GPS location data.
 * @return
 *     - ESP_OK: If the data was successfully published.
 *     - ESP_FAIL: If an error occurred during formatting or publishing.
 */
esp_err_t data_publisher_publish_vision_results(const visual_analysis_result_t* results, int result_count, const gps_location_t* location);

#endif // DATA_PUBLISHER_H
