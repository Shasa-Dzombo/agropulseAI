#include "peripheral_init.h"
#include "peripheral_manager.h"
#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "PERIPHERAL_INIT";

esp_err_t peripheral_initialize(void) {
    int i2c0_sda_pin, i2c0_scl_pin, spi_mosi_pin, spi_miso_pin, spi_sclk_pin;

    app_config_get_int("i2c0_sda_pin", &i2c0_sda_pin);
    app_config_get_int("i2c0_scl_pin", &i2c0_scl_pin);
    app_config_get_int("spi_mosi_pin", &spi_mosi_pin);
    app_config_get_int("spi_miso_pin", &spi_miso_pin);
    app_config_get_int("spi_sclk_pin", &spi_sclk_pin);

    esp_err_t ret;

    ESP_LOGI(TAG, "Initializing peripheral buses...");

    // Initialize I2C0 for primary sensors
    ret = peripheral_manager_i2c_init(
        I2C_NUM_0,
        i2c0_sda_pin,
        i2c0_scl_pin,
        400000 // 400 kHz
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize I2C0 bus.");
        return ret;
    }

    // Initialize SPI for devices like SD cards or SPI-based sensors/displays
    ret = peripheral_manager_spi_init(
        SPI2_HOST,
        spi_mosi_pin,
        spi_miso_pin,
        spi_sclk_pin
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SPI bus.");
        // Continue even if SPI fails, as it might not be critical
    }

    ESP_LOGI(TAG, "Peripheral buses initialized successfully.");
    return ESP_OK;
}
