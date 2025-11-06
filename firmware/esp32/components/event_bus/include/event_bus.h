#ifndef EVENT_BUS_H
#define EVENT_BUS_H

#include "esp_event.h"

// Declare a custom event base
ESP_EVENT_DECLARE_BASE(APP_EVENT);

// Define custom event IDs
typedef enum {
    // Wi-Fi Events
    APP_EVENT_WIFI_STA_CONNECTED,
    APP_EVENT_WIFI_STA_DISCONNECTED,
    APP_EVENT_WIFI_AP_START,
    APP_EVENT_WIFI_AP_STOP,

    // MQTT Events
    APP_EVENT_MQTT_CONNECTED,
    APP_EVENT_MQTT_DISCONNECTED,
    APP_EVENT_MQTT_DATA_RECEIVED,

    // Sensor Events
    APP_EVENT_SENSOR_DATA_READY,

    // System Events
    APP_EVENT_SYSTEM_SHUTDOWN_REQUEST,
    APP_EVENT_SYSTEM_REBOOT_REQUEST,

    // Vision Events
    APP_EVENT_VISION_ANALYSIS_COMPLETE,
    
    // Health Monitor Events
    APP_EVENT_HEALTH_REPORT_REQUEST,

    // External Trigger Events
    APP_EVENT_TRIGGER_ACTIVATED,

} app_event_id_t;

/**
 * @brief Initializes the application-wide event bus.
 *
 * This function creates a dedicated event loop for application-level events,
 * allowing different components to communicate in a decoupled manner.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t event_bus_init(void);

/**
 * @brief Gets the handle to the application event loop.
 *
 * @return The event loop handle.
 */
esp_event_loop_handle_t event_bus_get_handle(void);

/**
 * @brief Posts an event to the application event bus.
 *
 * A convenience wrapper around esp_event_post_to.
 *
 * @param event_id The ID of the event to post.
 * @param event_data Pointer to the data associated with the event.
 * @param event_data_size Size of the event data.
 * @param ticks_to_wait Ticks to wait if the event queue is full.
 * @return ESP_OK on success.
 */
esp_err_t event_bus_post(app_event_id_t event_id, const void* event_data, size_t event_data_size, TickType_t ticks_to_wait);

#endif // EVENT_BUS_H
