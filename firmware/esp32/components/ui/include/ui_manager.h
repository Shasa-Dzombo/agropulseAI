#ifndef UI_MANAGER_H
#define UI_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the UI manager.
 *
 * This function starts the UI task which is responsible for updating the display.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t ui_manager_init(void);

#endif // UI_MANAGER_H
