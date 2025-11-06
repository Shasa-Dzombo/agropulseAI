/**
 * @file water_pump_controller.h
 * @brief Controls a water pump connected to a GPIO pin.
 */
#ifndef WATER_PUMP_CONTROLLER_H
#define WATER_PUMP_CONTROLLER_H

#include "esp_err.h"

/**
 * @brief Initializes the water pump controller.
 *
 * @param[in] gpio_num The GPIO pin connected to the pump's relay/driver.
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t water_pump_init(int gpio_num);

/**
 * @brief Turns the water pump on.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t water_pump_on(void);

/**
 * @brief Turns the water pump off.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t water_pump_off(void);

/**
 * @brief Gets the current state of the water pump.
 *
 * @return
 *     - true: If the pump is on.
 *     - false: If the pump is off.
 */
bool water_pump_is_on(void);

#endif // WATER_PUMP_CONTROLLER_H
