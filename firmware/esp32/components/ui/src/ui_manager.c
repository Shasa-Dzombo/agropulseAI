#include "ui_manager.h"
#include "display_manager.h"
#include "event_bus.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "wifi_manager.h"
#include "mqtt_client.h"
#include "device_shadow.h"
#include <stdio.h>

static const char *TAG = "UI_MANAGER";

static void ui_task(void *pvParameters);
static void system_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);

esp_err_t ui_manager_init(void) {
    // Initialize the underlying display driver
    esp_err_t ret = display_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize display manager.");
        return ret;
    }

    // Register for system events
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_WIFI_STATUS_CHANGED, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_MQTT_STATUS_CHANGED, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_SHADOW_UPDATED, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_OTA_START, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_OTA_PROGRESS, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_OTA_SUCCESS, system_event_handler, NULL));
    ESP_ERROR_CHECK(event_bus_register_handler(SYSTEM_EVENT_OTA_FAIL, system_event_handler, NULL));


    // Create the UI task
    xTaskCreate(ui_task, "ui_task", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "UI Manager initialized.");
    return ESP_OK;
}

static void update_status_line(void) {
    char status_line[21];
    const char* wifi_status = wifi_manager_is_connected() ? "C" : "D";
    const char* mqtt_status = mqtt_client_is_connected() ? "C" : "D";
    snprintf(status_line, sizeof(status_line), "W:%s M:%s", wifi_status, mqtt_status);
    display_manager_set_line(0, status_line);
}

static void update_sensor_display(void) {
    const device_shadow_t* shadow = device_shadow_get();
    char line[21];

    snprintf(line, sizeof(line), "T:%.1fC H:%.1f%%", shadow->state.reported.temperature, shadow->state.reported.humidity);
    display_manager_set_line(1, line);

    snprintf(line, sizeof(line), "P:%.1fhPa L:%.0flx", shadow->state.reported.pressure, shadow->state.reported.lux);
    display_manager_set_line(2, line);
}


static void ui_task(void *pvParameters) {
    ESP_LOGI(TAG, "UI task started.");

    // Initial display update
    update_status_line();
    display_manager_set_line(1, "Initializing...");
    display_manager_refresh();

    while (1) {
        // The UI is updated based on events, but we do a periodic refresh here
        // to catch any state changes that might not trigger an event.
        update_status_line();
        update_sensor_display();
        display_manager_refresh();
        vTaskDelay(pdMS_TO_TICKS(5000)); // Refresh every 5 seconds
    }
}

static void system_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    char line[21];
    switch (event_id) {
        case SYSTEM_EVENT_WIFI_STATUS_CHANGED:
        case SYSTEM_EVENT_MQTT_STATUS_CHANGED:
            ESP_LOGI(TAG, "Connectivity status changed, updating UI.");
            update_status_line();
            break;
        case SYSTEM_EVENT_SHADOW_UPDATED:
            ESP_LOGI(TAG, "Device shadow updated, updating sensor display.");
            update_sensor_display();
            break;
        case SYSTEM_EVENT_OTA_START:
            ESP_LOGI(TAG, "OTA update started, updating UI.");
            display_manager_clear();
            display_manager_set_line(0, "OTA Update...");
            display_manager_set_line(1, "Downloading...");
            display_manager_refresh();
            break;
        case SYSTEM_EVENT_OTA_PROGRESS:
            if (event_data) {
                int progress = *(int*)event_data;
                snprintf(line, sizeof(line), "Progress: %d%%", progress);
                display_manager_set_line(2, line);
            }
            break;
        case SYSTEM_EVENT_OTA_SUCCESS:
            ESP_LOGI(TAG, "OTA success, updating UI.");
            display_manager_set_line(1, "Success!");
            display_manager_set_line(2, "Rebooting...");
            display_manager_refresh();
            break;
        case SYSTEM_EVENT_OTA_FAIL:
            ESP_LOGI(TAG, "OTA fail, updating UI.");
            display_manager_set_line(1, "Update Failed!");
            display_manager_refresh();
            break;
        default:
            break;
    }
    // No need to refresh immediately, the main loop will handle it.
}
