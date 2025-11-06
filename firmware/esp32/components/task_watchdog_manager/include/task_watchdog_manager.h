#ifndef TASK_WATCHDOG_MANAGER_H
#define TASK_WATCHDOG_MANAGER_H

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/**
 * @brief Initializes the task watchdog manager.
 *
 * This function initializes the ESP Task Watchdog Timer (TWDT) and subscribes
 * the main application task (the task that calls this function) to it.
 *
 * @param timeout_s The watchdog timeout period in seconds.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t task_watchdog_manager_init(uint32_t timeout_s);

/**
 * @brief Adds a task to be monitored by the watchdog.
 *
 * @param task_handle The handle of the task to add. If NULL, the current task is added.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t task_watchdog_manager_add_task(TaskHandle_t task_handle);

/**
 * @brief Removes a task from watchdog monitoring.
 *
 * @param task_handle The handle of the task to remove.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t task_watchdog_manager_remove_task(TaskHandle_t task_handle);

/**
 * @brief Resets the watchdog timer for the current task.
 *
 * Monitored tasks must call this function periodically to prevent a watchdog timeout.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t task_watchdog_manager_reset(void);

#endif // TASK_WATCHDOG_MANAGER_H
