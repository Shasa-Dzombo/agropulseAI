/**
 * @file sensor_sampler.c
 * @brief Implementation of the sensor sampler.
 */

#include "sensor_sampler.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "config_manager.h"
#include "data_publisher.h" // To send data to the publisher
#include "bme280_driver.h"  // The new sensor driver
#include "bh1750_driver.h"  // The light sensor driver
#include "power_manager.h"

#include "task_watchdog.h"

static const char *TAG = "SENSOR_SAMPLER";
#define SAMPLING_PERIOD_MS (60 * 1000) // 60 seconds
#define ADC_CHANNEL ADC1_CHANNEL_6 // GPIO34 for soil moisture

static void sensor_sampler_task(void *pvParameters);

esp_err_t sensor_sampler_init(void) {
    // Initialize BME280 sensor
    if (bme280_init(I2C_NUM_0, BME280_I2C_ADDR_PRIM) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize BME280 sensor");
        // Continue anyway, maybe other sensors work
    }

    // Initialize BH1750 sensor
    if (bh1750_init(I2C_NUM_0, 0x23) != ESP_OK) { // Common address for BH1750
        ESP_LOGE(TAG, "Failed to initialize BH1750 sensor");
    }

    // Configure ADC for soil moisture sensor
    adc1_config_width(ADC_WIDTH_BIT_12);

    // Create the main sampling task
    TaskHandle_t task_handle;
    xTaskCreate(sensor_sampler_task, "sensor_sampler_task", 4096, NULL, 5, &task_handle);
    task_watchdog_register_task(task_handle, "SensorSampler");
    return ESP_OK;
}

static void sensor_sampler_task(void *pvParameters) {
    ESP_LOGI(TAG, "Sensor sampler task started.");
    sensor_data_t data;

    while (1) {
        // Pet the watchdog at the beginning of the loop
        task_watchdog_pet();

        // Reset data structure
        memset(&data, 0, sizeof(sensor_data_t));

        // Read from BME280
        if (bme280_read_data(&data.temperature, &data.humidity) != ESP_OK) {
            ESP_LOGW(TAG, "Failed to read from BME280, using dummy data.");
            data.temperature = 25.0f + (float)(esp_random() % 100) / 100.0f;
            data.humidity = 60.0f + (float)(esp_random() % 100) / 100.0f;
        }

        // Read from BH1750
        if (bh1750_read_lux(&data.light_lux) != ESP_OK) {
            ESP_LOGW(TAG, "Failed to read from BH1750, using dummy data.");
            data.light_lux = 1500.0f + (float)(esp_random() % 500);
        }

        // Read from Soil Moisture Sensor (ADC)
        int adc_reading = adc1_get_raw(ADC_CHANNEL);
        // For this example, we'll just use a dummy value.
        data.soil_moisture = 45.0f + (float)(esp_random() % 100) / 100.0f;

        ESP_LOGI(TAG, "Sampled Data: Temp=%.2fC, Hum=%.2f%%, Soil=%.2f%%, Lux=%.2f",
                 data.temperature, data.humidity, data.soil_moisture, data.light_lux);

        // Post an event with the sensor data for other modules to use
        event_bus_post(SYSTEM_EVENT_SENSOR_DATA_READY, &data, sizeof(sensor_data_t));

        // Queue the data for the publisher
        data_publisher_queue_data(&data);

        // Wait for the next sampling period, potentially entering light sleep
        ESP_LOGI(TAG, "Next sensor reading in %d seconds.", SAMPLING_PERIOD_MS / 1000);
        if (power_manager_get_mode() == POWER_MODE_POWER_SAVE) {
            power_manager_enter_light_sleep(SAMPLING_PERIOD_MS);
        } else {
            vTaskDelay(pdMS_TO_TICKS(SAMPLING_PERIOD_MS));
        }
    }
}
