#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the display manager.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t display_manager_init(void);

/**
 * @brief Clears the display.
 */
void display_manager_clear(void);

/**
 * @brief Sets the text to be displayed on a specific line.
 *
 * @param line The line number (0-indexed).
 * @param text The text to display.
 */
void display_manager_set_line(int line, const char* text);

/**
 * @brief Refreshes the display to show the updated content.
 */
void display_manager_refresh(void);

#endif // DISPLAY_MANAGER_H
