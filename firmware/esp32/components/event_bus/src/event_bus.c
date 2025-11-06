#include "event_bus.h"
#include "esp_log.h"

// Define the custom event base
ESP_EVENT_DEFINE_BASE(APP_EVENT);

static const char *TAG = "EVENT_BUS";
static esp_event_loop_handle_t app_event_loop_handle;

esp_err_t event_bus_init(void) {
    esp_event_loop_args_t event_loop_args = {
        .queue_size = 10,
        .task_name = "app_event_task",
        .task_priority = uxTaskPriorityGet(NULL),
        .task_stack_size = 3072,
        .task_core_id = tskNO_AFFINITY
    };

    esp_err_t ret = esp_event_loop_create(&event_loop_args, &app_event_loop_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create application event loop: 0x%x", ret);
    } else {
        ESP_LOGI(TAG, "Application event bus initialized.");
    }
    return ret;
}

esp_event_loop_handle_t event_bus_get_handle(void) {
    return app_event_loop_handle;
}

esp_err_t event_bus_post(app_event_id_t event_id, const void* event_data, size_t event_data_size, TickType_t ticks_to_wait) {
    if (!app_event_loop_handle) {
        return ESP_ERR_INVALID_STATE;
    }
    return esp_event_post_to(app_event_loop_handle, APP_EVENT, event_id, event_data, event_data_size, ticks_to_wait);
}
