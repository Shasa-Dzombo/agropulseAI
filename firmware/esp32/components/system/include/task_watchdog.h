#ifndef TASK_WATCHDOG_H
#define TASK_WATCHDOG_H

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TASK_WATCHDOG_TIMEOUT_S 30 // 30 seconds timeout

/**
 * @brief Initializes the Task Watchdog Timer (TWDT).
 * 
 * This function subscribes the main task to the TWDT and creates a separate
 * task to monitor the health of other critical application tasks.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t task_watchdog_init(void);

/**
 * @brief Registers a task to be monitored by the watchdog.
 * 
 * @param task_handle The handle of the task to monitor. If NULL, it registers the calling task.
 * @param task_name A descriptive name for the task for logging purposes.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t task_watchdog_register_task(TaskHandle_t task_handle, const char* task_name);

/**
 * @brief Unregisters a task from watchdog monitoring.
 * 
 * @param task_handle The handle of the task to unregister.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t task_watchdog_unregister_task(TaskHandle_t task_handle);

/**
 * @brief "Pets" the watchdog for the calling task.
 * 
 * This function must be called periodically by each registered task to prevent
 * the watchdog from timing out and resetting the system.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t task_watchdog_pet(void);

/**
 * @brief Gets the stack high water mark for a monitored task.
 *
 * @param task_handle The handle of the task to query.
 * @return The stack high water mark in bytes, or 0 if the task is not found.
 */
uint32_t task_watchdog_get_stack_hwm(TaskHandle_t task_handle);

/**
 * @brief Fills a provided buffer with a JSON string containing the status of all monitored tasks.
 *
 * @param buffer The buffer to write the JSON string to.
 * @param buffer_size The size of the buffer.
 * @return ESP_OK on success, ESP_ERR_NO_MEM if the buffer is too small.
 */
esp_err_t task_watchdog_get_status_json(char* buffer, size_t buffer_size);


#endif // TASK_WATCHDOG_H
