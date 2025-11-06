#ifndef PERIPHERAL_MANAGER_H
#define PERIPHERAL_MANAGER_H

#include "esp_err.h"
#include "driver/i2c.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"

/**
 * @brief Initializes the I2C bus.
 * 
 * @param i2c_port The I2C port number.
 * @param sda_io_num The GPIO number for SDA.
 * @param scl_io_num The GPIO number for SCL.
 * @param clk_speed The I2C clock speed.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_manager_i2c_init(i2c_port_t i2c_port, int sda_io_num, int scl_io_num, uint32_t clk_speed);

/**
 * @brief Deinitializes the I2C bus.
 * 
 * @param i2c_port The I2C port number.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_manager_i2c_deinit(i2c_port_t i2c_port);

/**
 * @brief Initializes the SPI bus.
 * 
 * @param host The SPI host device.
 * @param mosi_io_num The GPIO number for MOSI.
 * @param miso_io_num The GPIO number for MISO.
 * @param sclk_io_num The GPIO number for SCLK.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_manager_spi_init(spi_host_device_t host, int mosi_io_num, int miso_io_num, int sclk_io_num);

/**
 * @brief Deinitializes the SPI bus.
 * 
 * @param host The SPI host device.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_manager_spi_deinit(spi_host_device_t host);

/**
 * @brief Configures a GPIO pin.
 * 
 * @param gpio_num The GPIO number.
 * @param mode The GPIO mode (input, output, etc.).
 * @param pull_up_en Enable pull-up resistor.
 * @param pull_down_en Enable pull-down resistor.
 * @param intr_type The interrupt type.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t peripheral_manager_gpio_init(gpio_num_t gpio_num, gpio_mode_t mode, bool pull_up_en, bool pull_down_en, gpio_int_type_t intr_type);

#endif // PERIPHERAL_MANAGER_H
