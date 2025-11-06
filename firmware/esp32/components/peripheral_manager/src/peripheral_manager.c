#include "peripheral_manager.h"
#include "esp_log.h"

static const char *TAG = "PERIPHERAL_MANAGER";

esp_err_t peripheral_manager_i2c_init(i2c_port_t i2c_port, int sda_io_num, int scl_io_num, uint32_t clk_speed) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = sda_io_num,
        .scl_io_num = scl_io_num,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = clk_speed,
    };
    
    esp_err_t ret = i2c_param_config(i2c_port, &conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C param config failed. port=%d, error=0x%x", i2c_port, ret);
        return ret;
    }

    ret = i2c_driver_install(i2c_port, conf.mode, 0, 0, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C driver install failed. port=%d, error=0x%x", i2c_port, ret);
    } else {
        ESP_LOGI(TAG, "I2C port %d initialized (SDA: %d, SCL: %d, Speed: %lu Hz)", i2c_port, sda_io_num, scl_io_num, (unsigned long)clk_speed);
    }
    return ret;
}

esp_err_t peripheral_manager_i2c_deinit(i2c_port_t i2c_port) {
    ESP_LOGI(TAG, "Deinitializing I2C port %d", i2c_port);
    return i2c_driver_delete(i2c_port);
}

esp_err_t peripheral_manager_spi_init(spi_host_device_t host, int mosi_io_num, int miso_io_num, int sclk_io_num) {
    spi_bus_config_t buscfg = {
        .mosi_io_num = mosi_io_num,
        .miso_io_num = miso_io_num,
        .sclk_io_num = sclk_io_num,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096
    };

    esp_err_t ret = spi_bus_initialize(host, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI bus initialize failed. host=%d, error=0x%x", host, ret);
    } else {
        ESP_LOGI(TAG, "SPI host %d initialized (MOSI: %d, MISO: %d, SCLK: %d)", host, mosi_io_num, miso_io_num, sclk_io_num);
    }
    return ret;
}

esp_err_t peripheral_manager_spi_deinit(spi_host_device_t host) {
    ESP_LOGI(TAG, "Deinitializing SPI host %d", host);
    return spi_bus_free(host);
}

esp_err_t peripheral_manager_gpio_init(gpio_num_t gpio_num, gpio_mode_t mode, bool pull_up_en, bool pull_down_en, gpio_int_type_t intr_type) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << gpio_num),
        .mode = mode,
        .pull_up_en = pull_up_en ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = pull_down_en ? GPIO_PULLDOWN_ENABLE : GPIO_PULLDOWN_DISABLE,
        .intr_type = intr_type,
    };

    esp_err_t ret = gpio_config(&io_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GPIO config failed. gpio=%d, error=0x%x", gpio_num, ret);
    } else {
        ESP_LOGI(TAG, "GPIO %d initialized (mode: %d)", gpio_num, mode);
    }
    return ret;
}
