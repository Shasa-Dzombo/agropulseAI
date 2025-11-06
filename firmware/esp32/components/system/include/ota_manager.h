/**
 * @file ota_manager.h
 * @brief Manages the Over-the-Air (OTA) update process.
 *
 * This component provides a high-level interface for handling firmware updates.
 * It can be triggered by an external event (like an MQTT message) and will
 * handle the process of downloading, verifying, and applying a new firmware image.
 *
 * Features:
 * - A task to handle the OTA process in the background.
 * - Downloads firmware from a specified URL.
 * - Verifies the signature of the new firmware using the `ota_verifier`.
 * - Sets the new firmware as the next boot partition.
 * - Triggers a device restart to apply the update.
 */
#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the OTA manager.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t ota_manager_init(void);

/**
 * @brief Starts the OTA update process.
 *
 * This function creates a new task that will handle the entire update flow.
 *
 * @param[in] url The URL of the firmware binary.
 * @return
 *     - ESP_OK: If the update task was started successfully.
 *     - ESP_FAIL: On failure.
 */
esp_err_t ota_manager_start_update(const char* url);

/**
 * @brief Starts an over-the-air update for a specific type.
 *
 * @param[in] url The URL of the binary.
 * @param[in] type The type of OTA update (firmware or model).
 * @param[in] model_path The destination path on the filesystem (for model OTA only).
 * @return
 *     - ESP_OK: If the update task was started successfully.
 */
esp_err_t ota_manager_start_update_ex(const char* url, int type, const char* model_path);


#endif // OTA_MANAGER_H
