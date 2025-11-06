/**
 * @file time_manager.h
 * @brief Manages system time, including NTP synchronization.
 *
 * This component is responsible for ensuring the device has an accurate
 * real-time clock (RTC). It handles synchronization with an NTP server
 * when a network connection is available.
 *
 * Features:
 * - Initializes the SNTP service.
 * - Starts time synchronization upon Wi-Fi connection.
 * - Posts an event (`SYSTEM_EVENT_TIME_SYNCED`) upon successful sync.
 * - Provides a function to get the current time as a formatted string.
 */
#ifndef TIME_MANAGER_H
#define TIME_MANAGER_H

#include "esp_err.h"
#include <time.h>

/**
 * @brief Initializes the time manager.
 *
 * This function sets up the SNTP service and registers event handlers
 * to start the synchronization process when Wi-Fi connects.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t time_manager_init(void);

/**
 * @brief Checks if the system time is currently synchronized.
 *
 * @return true if the time has been successfully synchronized with an NTP server, false otherwise.
 */
bool time_manager_is_synced(void);

/**
 * @brief Gets the current system time.
 *
 * @param[out] timeinfo Pointer to a `struct tm` to be filled with the current time.
 * @return
 *     - ESP_OK: If the time was successfully retrieved.
 *     - ESP_FAIL: If the time is not yet synchronized.
 */
esp_err_t time_manager_get_time(struct tm *timeinfo);

/**
 * @brief Gets the current system time as a formatted string.
 *
 * The format is ISO 8601: "YYYY-MM-DDTHH:MM:SSZ".
 *
 * @param[out] buf The buffer to write the formatted string into.
 * @param[in] buf_size The size of the buffer.
 * @return
 *     - ESP_OK: If the string was successfully created.
 *     - ESP_FAIL: If the time is not yet synchronized or the buffer is too small.
 */
esp_err_t time_manager_get_time_str(char *buf, size_t buf_size);

#endif // TIME_MANAGER_H
