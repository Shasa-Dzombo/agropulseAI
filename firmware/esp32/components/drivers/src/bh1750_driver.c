/**
 * @file bh1750_driver.c
 * @brief Implementation of the BH1750 light sensor driver.
 */

#include "bh1750_driver.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c.h"

static const char *TAG = "BH1750";

// BH1750 Opcodes
#define BH1750_POWER_DOWN 0x00
#define BH1750_POWER_ON 0x01
#define BH1750_RESET 0x07
#define BH1750_CONTINUOUS_HIGH_RES_MODE 0x10 // 1 lux resolution, 120ms
#define BH1750_CONTINUOUS_HIGH_RES_MODE_2 0x11 // 0.5 lux resolution, 120ms
#define BH1750_ONE_TIME_HIGH_RES_MODE 0x20

static i2c_port_t bh1750_i2c_port;
static uint8_t bh1750_i2c_addr;

esp_err_t bh1750_init(i2c_port_t i2c_port, uint8_t i2c_addr) {
    bh1750_i2c_port = i2c_port;
    bh1750_i2c_addr = i2c_addr;

    // Power on the sensor
    uint8_t power_on_cmd = BH1750_POWER_ON;
    esp_err_t ret = i2c_master_write_to_device(bh1750_i2c_port, bh1750_i2c_addr, &power_on_cmd, 1, pdMS_TO_TICKS(1000));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to power on BH1750");
        return ret;
    }
    vTaskDelay(pdMS_TO_TICKS(10)); // Small delay after power on

    // Set to continuous high resolution mode
    uint8_t mode_cmd = BH1750_CONTINUOUS_HIGH_RES_MODE;
    ret = i2c_master_write_to_device(bh1750_i2c_port, bh1750_i2c_addr, &mode_cmd, 1, pdMS_TO_TICKS(1000));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set measurement mode");
        return ret;
    }
    vTaskDelay(pdMS_TO_TICKS(120)); // Wait for first measurement

    ESP_LOGI(TAG, "BH1750 initialized at address 0x%x", bh1750_i2c_addr);
    return ESP_OK;
}

esp_err_t bh1750_read_lux(float* lux) {
    if (lux == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    uint8_t data[2];
    esp_err_t ret = i2c_master_read_from_device(bh1750_i2c_port, bh1750_i2c_addr, data, 2, pdMS_TO_TICKS(1000));
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read data from BH1750");
        return ret;
    }

    // Combine the two bytes and convert to lux
    uint16_t raw_value = (data[0] << 8) | data[1];
    *lux = (float)raw_value / 1.2;

    return ESP_OK;
}
