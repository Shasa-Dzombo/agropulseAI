/**
 * @file main.c
 * @brief Main entry point for the AgroPulse ESP32 Firmware.
 *
 * This file contains the `app_main` function, which is the starting point of the application.
 * It is responsible for initializing all the core components and starting the main application logic.
 *
 * The initialization sequence is as follows:
 * 1. Initialize core services: NVS (Non-Volatile Storage), system configuration,
 *    and the main event loop. This sets up the foundational services required by all
 *    other components.
 * 2. Initialize system services: Wi-Fi, networking stack, and time synchronization (SNTP).
 *    This establishes the device's connectivity to the outside world.
 * 3. Initialize protocol services: MQTT client, HTTP server, and BLE services. These
 *    are the communication channels for interacting with the cloud and mobile apps.
 * 4. Initialize the main application logic: This starts the primary state machine,
 *    sensor reading tasks, and control loops that define the device's behavior.
 *
 * This modular approach ensures a clean separation of concerns and allows for robust
 * and scalable firmware development.
 */

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "core_init.h"
#include "protocols_init.h"
#include "drivers_init.h"
#include "system_init.h"
#include "application_init.h"
#include "vision_system.h"
#include "storage_init.h"
#include "peripheral_init.h"
#include "security_init.h"
#include "ui_manager.h"
#include "logging_manager.h"
#include "job_scheduler.h"
#include "app_config.h"
#include "health_monitor.h"
#include "persistent_logger.h"
#include "task_watchdog_manager.h"
#include "event_bus.h"
#include "subscription_manager.h"
#include "secure_element_manager.h"
#include "security_manager.h"
#include "platform.h"
#include "trigger_manager.h"
#include "network_manager.h"
#include "data_aggregator.h"
#include "data_historian.h"
#include "secure_logger.h"

static const char *TAG = "MAIN";

void app_main(void)
{
    ESP_LOGI(TAG, "Initializing system...");

    // Initialize platform-specific features (like NVS) and get chip info
    platform_init();

    platform_chip_info_t chip_info;
    platform_get_chip_info(&chip_info);
    ESP_LOGI(TAG, "Running on %s with %d cores, revision %d.", chip_info.model, chip_info.cores, chip_info.revision);

    // Initialize Task Watchdog as one of the first things.
    // This ensures the main task is monitored from the beginning.
    task_watchdog_manager_init(30); // 30-second timeout

    // Initialize the main application event bus
    event_bus_init();

    // Initialize Core Services (Config)
    app_config_init();

    // Initialize Data Processing & Storage
    data_aggregator_init();
    data_historian_init();
    secure_logger_init();

    // Initialize Subscription Manager (must be after NVS and config)
    subscription_manager_init();

    // Initialize Storage (SPIFFS must be after NVS)
    storage_initialize();

    // Initialize Persistent Logger (must be after storage)
    persistent_logger_init("/spiffs/app.log", 10 * 1024, 5); // 10KB per file, 5 files max

    // Initialize Logging Manager (redirects logs, so initialize after persistent logger if both are used)
    logging_manager_init();

    // Initialize Peripheral Buses (I2C, SPI)
    peripheral_initialize();

    // Initialize Secure Element (must be after I2C is initialized)
    secure_element_manager_init();

    // Initialize Security Manager (must be after secure element)
    security_manager_init();

    // Initialize Network Manager (replaces direct Wi-Fi init)
    network_manager_init(NETWORK_PREF_WIFI_PREFERRED);
    network_manager_connect();

    // Initialize System Services (OTA, etc.)
    system_services_initialize();

    // Initialize Protocols (Wi-Fi, MQTT)
    // protocols_initialize(); // This is now handled by network_manager and mqtt_client

    // Initialize Drivers (Sensors, Actuators)
    drivers_initialize();

    // Initialize the "Tripwire" trigger manager
    trigger_manager_init();

    // Initialize Edge AI and Vision Services (must be after storage)
    // edge_ai_services_initialize(); // This is now part of vision_system_init
    vision_system_init();

    // Initialize Job Scheduler
    job_scheduler_init();

    // Initialize Application Logic (must be last)
    application_initialize();

    // Initialize UI Manager (can be after application)
    ui_manager_init();

    // Initialize Health Monitor (can be initialized towards the end)
    health_monitor_init();

    ESP_LOGI(TAG, "System initialization complete. Starting main loop.");

    while (1) {
        // The main task loop.
        // Since this task is monitored by the watchdog, it must reset it periodically.
        task_watchdog_manager_reset();
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
