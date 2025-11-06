#include "power_manager.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "driver/rtc_io.h"

static const char *TAG = "POWER_MANAGER";
static power_mode_t s_current_mode = POWER_MODE_NORMAL;

esp_err_t power_manager_init(void) {
    ESP_LOGI(TAG, "Power manager initialized.");
    // In a real scenario, you might configure wakeup sources here,
    // like a GPIO pin for an external interrupt.
    // For example:
    // rtc_gpio_pullup_en(GPIO_NUM_33);
    // rtc_gpio_pulldown_dis(GPIO_NUM_33);
    // esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, 1); // Wake on high
    return ESP_OK;
}

esp_err_t power_manager_enter_light_sleep(uint32_t sleep_duration_ms) {
    if (s_current_mode != POWER_MODE_POWER_SAVE) {
        ESP_LOGD(TAG, "Light sleep is disabled in normal power mode.");
        return ESP_FAIL;
    }

    if (sleep_duration_ms == 0) {
        return ESP_OK; // Nothing to do
    }

    ESP_LOGI(TAG, "Entering light sleep for %lu ms.", sleep_duration_ms);

    // Configure the timer wakeup source
    esp_sleep_enable_timer_wakeup(sleep_duration_ms * 1000);

    // Enter light sleep
    esp_err_t err = esp_light_sleep_start();

    // Code resumes here after wakeup
    if (err == ESP_ERR_SLEEP_REJECT) {
        ESP_LOGW(TAG, "Light sleep request was rejected.");
    } else {
        ESP_LOGI(TAG, "Woke up from light sleep.");
    }

    return err;
}

void power_manager_set_mode(power_mode_t mode) {
    if (s_current_mode != mode) {
        s_current_mode = mode;
        ESP_LOGI(TAG, "Power mode set to %s", (mode == POWER_MODE_POWER_SAVE) ? "POWER_SAVE" : "NORMAL");
    }
}

power_mode_t power_manager_get_mode(void) {
    return s_current_mode;
}
