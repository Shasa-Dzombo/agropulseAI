#ifndef PERSISTENT_LOGGER_H
#define PERSISTENT_LOGGER_H

#include "esp_err.h"
#include "esp_log.h"

/**
 * @brief Initializes the persistent logger.
 *
 * This function sets up a custom ESP-IDF log output that writes logs to a
 * file on the SPIFFS filesystem. It handles log rotation to prevent the
 * filesystem from filling up.
 *
 * @param log_file_path The base path for the log file (e.g., "/spiffs/app.log").
 * @param max_file_size The maximum size of a single log file in bytes.
 * @param max_files The maximum number of log files to keep.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t persistent_logger_init(const char *log_file_path, size_t max_file_size, int max_files);

/**
 * @brief Uploads the stored log files to the cloud.
 *
 * This function can be triggered (e.g., by an MQTT command) to read the log
 * files from SPIFFS and publish them to a specific MQTT topic for remote
 * debugging.
 *
 * @return ESP_OK if the upload process was started successfully.
 */
esp_err_t persistent_logger_upload_logs(void);

/**
 * @brief Sets the minimum log level for persistent storage.
 * 
 * @param level The minimum log level to store.
 */
void persistent_logger_set_level(esp_log_level_t level);

#endif // PERSISTENT_LOGGER_H
