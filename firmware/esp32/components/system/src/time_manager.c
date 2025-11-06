/**
 * @file time_manager.c
 * @brief Implementation of the time manager.
 */

#include "time_manager.h"
#include "esp_log.h"
#include "esp_sntp.h"
#include "event_bus.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "TIME_MANAGER";

static SemaphoreHandle_t s_sync_sem = NULL;
static bool is_synced = false;

static void time_sync_notification_cb(struct timeval *tv);
static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);

esp_err_t time_manager_init(void) {
    s_sync_sem = xSemaphoreCreateBinary();
    if (s_sync_sem == NULL) {
        ESP_LOGE(TAG, "Failed to create sync semaphore");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Initializing SNTP");
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "pool.ntp.org");
    esp_sntp_set_time_sync_notification_cb(time_sync_notification_cb);
    esp_sntp_init();

    // Register a handler to listen for Wi-Fi connection events
    esp_err_t err = event_bus_register_handler(SYSTEM_EVENT_WIFI_GOT_IP, wifi_event_handler, NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register Wi-Fi connect handler for time manager");
        return err;
    }
    
    err = event_bus_register_handler(SYSTEM_EVENT_WIFI_DISCONNECTED, wifi_event_handler, NULL);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register Wi-Fi disconnect handler for time manager");
        return err;
    }

    return ESP_OK;
}

bool time_manager_is_synced(void) {
    return is_synced;
}

esp_err_t time_manager_get_time(struct tm *timeinfo) {
    if (!is_synced) {
        return ESP_FAIL;
    }
    time_t now;
    time(&now);
    localtime_r(&now, timeinfo);
    return ESP_OK;
}

esp_err_t time_manager_get_time_str(char *buf, size_t buf_size) {
    if (!is_synced) {
        return ESP_FAIL;
    }
    struct tm timeinfo;
    if (time_manager_get_time(&timeinfo) != ESP_OK) {
        return ESP_FAIL;
    }
    // ISO 8601 format
    size_t required_size = strftime(buf, buf_size, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    if (required_size == 0) {
        ESP_LOGE(TAG, "Buffer too small for time string");
        return ESP_FAIL;
    }
    return ESP_OK;
}

static void time_sync_notification_cb(struct timeval *tv) {
    ESP_LOGI(TAG, "Time synchronized successfully. New time: %s", ctime(&tv->tv_sec));
    is_synced = true;
    xSemaphoreGive(s_sync_sem);
    
    // Post an event to notify the rest of the system
    event_bus_post(SYSTEM_EVENT_TIME_SYNCED, NULL, 0);
}

static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_id == SYSTEM_EVENT_WIFI_GOT_IP) {
        ESP_LOGI(TAG, "Wi-Fi has IP, starting SNTP sync.");
        // Start SNTP service
        esp_sntp_init();
    } else if (event_id == SYSTEM_EVENT_WIFI_DISCONNECTED) {
        ESP_LOGI(TAG, "Wi-Fi disconnected, stopping SNTP.");
        is_synced = false;
        // Stop SNTP service
        esp_sntp_stop();
    }
}
