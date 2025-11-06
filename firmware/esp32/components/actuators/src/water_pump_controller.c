/**
 * @file water_pump_controller.c
 * @brief Implementation of the water pump controller.
 */

#include "water_pump_controller.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "WATER_PUMP";
static int pump_gpio_num = -1;
static bool is_on = false;

esp_err_t water_pump_init(int gpio_num) {
    pump_gpio_num = gpio_num;
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << pump_gpio_num),
        .mode = GPIO_MODE_OUTPUT,
        .intr_type = GPIO_INTR_DISABLE,
        .pull_down_en = 0,
        .pull_up_en = 0,
    };
    esp_err_t ret = gpio_config(&io_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure GPIO %d", pump_gpio_num);
        return ret;
    }
    // Ensure pump is off initially
    gpio_set_level(pump_gpio_num, 0);
    is_on = false;
    ESP_LOGI(TAG, "Water pump initialized on GPIO %d", pump_gpio_num);
    return ESP_OK;
}

esp_err_t water_pump_on(void) {
    if (pump_gpio_num == -1) return ESP_FAIL;
    gpio_set_level(pump_gpio_num, 1);
    is_on = true;
    ESP_LOGI(TAG, "Water pump turned ON");
    return ESP_OK;
}

esp_err_t water_pump_off(void) {
    if (pump_gpio_num == -1) return ESP_FAIL;
    gpio_set_level(pump_gpio_num, 0);
    is_on = false;
    ESP_LOGI(TAG, "Water pump turned OFF");
    return ESP_OK;
}

bool water_pump_is_on(void) {
    return is_on;
}
