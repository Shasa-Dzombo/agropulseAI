/**
 * @file spiffs_manager.h
 * @brief Manages the SPIFFS filesystem.
 *
 * This component handles the initialization and mounting of the SPI
 * Flash File System (SPIFFS). It provides a simple abstraction for other
 * components that need to perform file I/O.
 *
 * Features:
 * - Initializes and mounts the SPIFFS partition.
 * - Provides filesystem info (total/used space).
 * - Handles unmounting the filesystem.
 */
#ifndef SPIFFS_MANAGER_H
#define SPIFFS_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes and mounts the SPIFFS filesystem.
 *
 * @param[in] partition_label The label of the SPIFFS partition in the partition table.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t spiffs_manager_init(const char* partition_label);

/**
 * @brief Deinitializes the SPIFFS filesystem.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t spiffs_manager_deinit(void);

/**
 * @brief Gets information about the SPIFFS filesystem.
 *
 * @param[out] total_bytes Pointer to store the total size of the filesystem.
 * @param[out] used_bytes Pointer to store the used size of the filesystem.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t spiffs_manager_get_info(size_t* total_bytes, size_t* used_bytes);

#endif // SPIFFS_MANAGER_H
