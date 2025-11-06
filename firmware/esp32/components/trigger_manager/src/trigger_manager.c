#include "trigger_manager.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "event_bus.h"

// Define the GPIO pin connected to the external trigger (e.g., a PIR sensor)
#define TRIGGER_GPIO_PIN GPIO_NUM_27

static const char *TAG = "TRIGGER_MGR";

// This is the Interrupt Service Routine (ISR) that gets called when the GPIO pin changes state.
static void IRAM_ATTR gpio_isr_handler(void* arg) {
    // In an ISR, we cannot block or perform complex operations.
    // The best practice is to notify a high-priority task or, in our case,
    // post an event to our application's event loop.
    // The event loop will then handle the logic in a normal task context.
    esp_event_post(APP_EVENT, APP_EVENT_TRIGGER_ACTIVATED, NULL, 0, 0);
}

esp_err_t trigger_manager_init(void) {
    gpio_config_t io_conf;
    // Interrupt on falling edge (HIGH to LOW)
    io_conf.intr_type = GPIO_INTR_NEGEDGE;
    // Bit mask of the pin
    io_conf.pin_bit_mask = (1ULL << TRIGGER_GPIO_PIN);
    // Set as input mode
    io_conf.mode = GPIO_MODE_INPUT;
    // Enable pull-up mode
    io_conf.pull_up_en = 1;
    io_conf.pull_down_en = 0;
    esp_err_t err = gpio_config(&io_conf);

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure GPIO for trigger: %s", esp_err_to_name(err));
        return err;
    }

    // Install the GPIO ISR service
    err = gpio_install_isr_service(0); // 0 = default priority
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        // ESP_ERR_INVALID_STATE means it's already installed, which is fine.
        ESP_LOGE(TAG, "Failed to install GPIO ISR service: %s", esp_err_to_name(err));
        return err;
    }

    // Hook our specific ISR handler to the GPIO pin
    err = gpio_isr_handler_add(TRIGGER_GPIO_PIN, gpio_isr_handler, NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add ISR handler for GPIO pin: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "Trigger manager initialized on GPIO %d.", TRIGGER_GPIO_PIN);
    return ESP_OK;
}
