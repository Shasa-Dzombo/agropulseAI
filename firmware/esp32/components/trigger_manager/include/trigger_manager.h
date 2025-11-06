#ifndef TRIGGER_MANAGER_H
#define TRIGGER_MANAGER_H

#include "esp_err.h"

/**
 * @brief Initializes the trigger manager.
 *
 * This function configures the specified GPIO pin as an input with a pull-up
 * and sets up an interrupt to fire on the falling edge. This is ideal for
 * connecting to a "tripwire" sensor like a PIR or radar module.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t trigger_manager_init(void);

#endif // TRIGGER_MANAGER_H
