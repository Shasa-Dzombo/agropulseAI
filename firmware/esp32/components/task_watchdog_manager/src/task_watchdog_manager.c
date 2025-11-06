#include "task_watchdog_manager.h"
#include "esp_task_wdt.h"
#include "esp_log.h"

static const char *TAG = "TASK_WATCHDOG";

esp_err_t task_watchdog_manager_init(uint32_t timeout_s) {
    ESP_LOGI(TAG, "Initializing task watchdog with a %lu second timeout.", (unsigned long)timeout_s);
    
    esp_task_wdt_config_t twdt_config = {
        .timeout_ms = timeout_s * 1000,
        .idle_core_mask = (1 << portNUM_PROCESSORS) - 1,    // Watch the idle task of all cores.
        .trigger_panic = true,                             // Trigger a panic on timeout
    };
    
    //Initialize or reconfigure TWDT
    esp_err_t ret = esp_task_wdt_init(&twdt_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize task watchdog: 0x%x", ret);
        return ret;
    }

    // The task that initializes the watchdog is automatically added.
    // We can log this for clarity.
    ESP_LOGI(TAG, "Task watchdog initialized. The current task is now being monitored.");
    return ESP_OK;
}

esp_err_t task_watchdog_manager_add_task(TaskHandle_t task_handle) {
    if (task_handle == NULL) {
        task_handle = xTaskGetCurrentTaskHandle();
    }
    
    esp_err_t ret = esp_task_wdt_add(task_handle);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Task '%s' added to watchdog.", pcTaskGetName(task_handle));
    } else {
        ESP_LOGE(TAG, "Failed to add task '%s' to watchdog: 0x%x", pcTaskGetName(task_handle), ret);
    }
    return ret;
}

esp_err_t task_watchdog_manager_remove_task(TaskHandle_t task_handle) {
    esp_err_t ret = esp_task_wdt_delete(task_handle);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Task '%s' removed from watchdog.", pcTaskGetName(task_handle));
    } else {
        ESP_LOGE(TAG, "Failed to remove task '%s' from watchdog: 0x%x", pcTaskGetName(task_handle), ret);
    }
    return ret;
}

esp_err_t task_watchdog_manager_reset(void) {
    return esp_task_wdt_reset();
}
