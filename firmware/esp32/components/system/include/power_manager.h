#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include "esp_err.h"

typedef enum {
    POWER_MODE_NORMAL,
    POWER_MODE_POWER_SAVE,
} power_mode_t;

/**
 * @brief Initializes the power manager.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t power_manager_init(void);

/**
 * @brief Attempts to enter light sleep for a specified duration.
 * 
 * This function will only enter sleep if the current power mode is set to
 * POWER_MODE_POWER_SAVE. It configures a timer to wake the device up.
 * 
 * @param sleep_duration_ms The duration to sleep in milliseconds.
 * 
 * @return ESP_OK if sleep was entered, ESP_FAIL if not, or an error code.
 */
esp_err_t power_manager_enter_light_sleep(uint32_t sleep_duration_ms);

/**
 * @brief Sets the current power mode.
 * 
 * @param mode The power mode to set.
 */
void power_manager_set_mode(power_mode_t mode);

/**
 * @brief Gets the current power mode.
 * 
 * @return The current power_mode_t.
 */
power_mode_t power_manager_get_mode(void);

#endif // POWER_MANAGER_H
