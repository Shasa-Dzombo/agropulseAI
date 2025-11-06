/**
 * @file actuator_control.h
 * @brief Main logic for controlling actuators based on sensor data and AI models.
 *
 * This component subscribes to sensor data events and uses a set of rules
 * and the output from the Edge AI model to make decisions about when to

 * turn actuators (like a water pump) on or off.
 */
#ifndef ACTUATOR_CONTROL_H
#define ACTUATOR_CONTROL_H

#include "esp_err.h"

/**
 * @brief Initializes the actuator control module.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t actuator_control_init(void);

#endif // ACTUATOR_CONTROL_H
