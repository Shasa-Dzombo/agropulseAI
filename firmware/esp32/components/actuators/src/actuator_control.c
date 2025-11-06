/**
 * @file actuator_control.c
 * @brief Implementation of the main actuator control logic.
 */

#include "actuator_control.h"
#include "esp_log.h"
#include "event_bus.h"
#include "sensor_sampler.h"
#include "water_pump_controller.h"
#include "app_config.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"
#include "device_shadow.h" // For reporting state

static const char *TAG = "ACTUATOR_CONTROL";
#define WATER_PUMP_GPIO 26 // Example GPIO for the pump
#define WATERING_DURATION_MS (10 * 1000) // Water for 10 seconds

static TimerHandle_t watering_timer;

static void sensor_data_event_handler(void* handler_args, esp_event_base_t base, int32_t id, void* event_data);
static void watering_timer_callback(TimerHandle_t xTimer);
static void report_pump_state(bool is_on);

esp_err_t actuator_control_init(void) {
    // Initialize actuators
    water_pump_init(WATER_PUMP_GPIO);

    // Create a one-shot timer to turn the pump off after a duration
    watering_timer = xTimerCreate("watering_timer", pdMS_TO_TICKS(WATERING_DURATION_MS), pdFALSE, (void*)0, watering_timer_callback);

    // Subscribe to sensor data events
    event_bus_subscribe(SYSTEM_EVENT_SENSOR_DATA_READY, sensor_data_event_handler);

    ESP_LOGI(TAG, "Actuator control initialized.");
    return ESP_OK;
}

static void sensor_data_event_handler(void* handler_args, esp_event_base_t base, int32_t id, void* event_data) {
    sensor_data_t* data = (sensor_data_t*)event_data;
    
    int watering_threshold = 30; // Default value
    app_config_get_int("watering_threshold", &watering_threshold);

    ESP_LOGI(TAG, "Received sensor data: Soil Moisture=%.2f%%", data->soil_moisture);

    // Simple rule-based control: if soil moisture is below the threshold, turn on the pump.
    if (data->soil_moisture < watering_threshold) {
        if (!water_pump_is_on()) {
            ESP_LOGI(TAG, "Soil moisture is below threshold (%.2f < %d). Turning on water pump.", data->soil_moisture, watering_threshold);
            water_pump_on();
            report_pump_state(true); // Report state change to shadow
            // Start the timer to turn the pump off automatically
            xTimerStart(watering_timer, 0);
        } else {
            ESP_LOGI(TAG, "Pump is already on. Ignoring trigger.");
        }
    }
}

static void watering_timer_callback(TimerHandle_t xTimer) {
    ESP_LOGI(TAG, "Watering duration elapsed. Turning off pump.");
    water_pump_off();
    report_pump_state(false); // Report state change to shadow
}

static void report_pump_state(bool is_on) {
    cJSON* root = cJSON_CreateObject();
    cJSON* state = cJSON_CreateObject();
    cJSON_AddItemToObject(root, "state", state);
    cJSON_AddBoolToObject(state, "waterPumpOn", is_on);
    device_shadow_update_reported_state(root);
}
