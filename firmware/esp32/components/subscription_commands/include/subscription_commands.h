#ifndef SUBSCRIPTION_COMMANDS_H
#define SUBSCRIPTION_COMMANDS_H

#include "esp_err.h"

/**
 * @brief Initializes the subscription command handlers.
 *
 * This function registers commands related to subscription management
 * with the central command registry.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t subscription_commands_init(void);

#endif // SUBSCRIPTION_COMMANDS_H
