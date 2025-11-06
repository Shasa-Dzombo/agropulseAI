/**
 * @file data_logger.h
 * @brief Logs sensor data to the local filesystem.
 *
 * This component provides a mechanism to log sensor data to a file on the
 * SPIFFS filesystem. This is useful for storing data when the device is
 * offline. A separate process can then read this data and upload it when
 * connectivity is restored.
 *
 * Features:
 * - Appends data records to a log file.
 * - Handles log file rotation (e.g., creating a new file when one gets too large).
 * - Provides functions to read and clear the log.
 */
#ifndef DATA_LOGGER_H
#define DATA_LOGGER_H

#include "esp_err.h"
#include "sensor_sampler.h"

/**
 * @brief Initializes the data logger.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t data_logger_init(void);

/**
 * @brief Logs a sensor data record to the filesystem.
 *
 * @param[in] data The sensor data to log.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t data_logger_log(const sensor_data_t* data);

/**
 * @brief Reads the oldest log entry from the filesystem.
 *
 * The caller is responsible for freeing the returned buffer.
 *
 * @param[out] buffer Pointer to a char pointer that will be allocated and filled.
 * @param[out] entry_size The size of the read entry.
 * @return
 *     - ESP_OK: If a log entry was read successfully.
 *     - ESP_ERR_NOT_FOUND: If no log files exist.
 *     - ESP_FAIL: On other errors.
 */
esp_err_t data_logger_read_oldest_entry(char** buffer, size_t* entry_size);

/**
 * @brief Deletes the oldest log entry from the log file.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t data_logger_delete_oldest_entry(void);

#endif // DATA_LOGGER_H
