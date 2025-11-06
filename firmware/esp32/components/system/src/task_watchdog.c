#include "task_watchdog.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "freertos/semphr.h"
#include "cJSON.h"
#include <string.h>
#include <time.h>

static const char *TAG = "TASK_WATCHDOG";

#define MAX_MONITORED_TASKS 10

typedef struct {
    TaskHandle_t handle;
    char name[configMAX_TASK_NAME_LEN];
    time_t last_pet_time;
    bool is_active;
} monitored_task_t;

static monitored_task_t s_monitored_tasks[MAX_MONITORED_TASKS];
static SemaphoreHandle_t s_task_list_mutex;

static void watchdog_monitor_task(void *pvParameters);

esp_err_t task_watchdog_init(void) {
    ESP_LOGI(TAG, "Initializing Task Watchdog with %d second timeout.", TASK_WATCHDOG_TIMEOUT_S);

    // Configure the ESP Task Watchdog Timer
    esp_task_wdt_config_t twdt_config = {
        .timeout_ms = TASK_WATCHDOG_TIMEOUT_S * 1000,
        .idle_core_mask = (1 << 0) | (1 << 1), // Watch idle tasks on both cores
        .trigger_panic = true,
    };
    ESP_ERROR_CHECK(esp_task_wdt_init(&twdt_config));

    // Subscribe the main task (the one running this init) to the watchdog
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    ESP_LOGI(TAG, "Main task subscribed to TWDT.");

    s_task_list_mutex = xSemaphoreCreateMutex();
    if (s_task_list_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create task list mutex.");
        return ESP_FAIL;
    }

    memset(s_monitored_tasks, 0, sizeof(s_monitored_tasks));

    xTaskCreate(watchdog_monitor_task, "wd_monitor", 3072, NULL, 10, NULL);

    return ESP_OK;
}

esp_err_t task_watchdog_register_task(TaskHandle_t task_handle, const char* task_name) {
    if (task_handle == NULL) {
        task_handle = xTaskGetCurrentTaskHandle();
    }

    if (xSemaphoreTake(s_task_list_mutex, portMAX_DELAY) == pdTRUE) {
        for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
            if (!s_monitored_tasks[i].is_active) {
                s_monitored_tasks[i].handle = task_handle;
                strncpy(s_monitored_tasks[i].name, task_name, configMAX_TASK_NAME_LEN - 1);
                s_monitored_tasks[i].last_pet_time = time(NULL);
                s_monitored_tasks[i].is_active = true;
                ESP_LOGI(TAG, "Registered task '%s' for monitoring.", task_name);
                xSemaphoreGive(s_task_list_mutex);
                return ESP_OK;
            }
        }
        xSemaphoreGive(s_task_list_mutex);
        ESP_LOGE(TAG, "Failed to register task '%s', no free slots.", task_name);
        return ESP_ERR_NO_MEM;
    }
    return ESP_FAIL;
}

esp_err_t task_watchdog_unregister_task(TaskHandle_t task_handle) {
     if (xSemaphoreTake(s_task_list_mutex, portMAX_DELAY) == pdTRUE) {
        for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
            if (s_monitored_tasks[i].is_active && s_monitored_tasks[i].handle == task_handle) {
                s_monitored_tasks[i].is_active = false;
                ESP_LOGI(TAG, "Unregistered task '%s'.", s_monitored_tasks[i].name);
                break;
            }
        }
        xSemaphoreGive(s_task_list_mutex);
        return ESP_OK;
    }
    return ESP_FAIL;
}

esp_err_t task_watchdog_pet(void) {
    TaskHandle_t current_task = xTaskGetCurrentTaskHandle();
    if (xSemaphoreTake(s_task_list_mutex, portMAX_DELAY) == pdTRUE) {
        for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
            if (s_monitored_tasks[i].is_active && s_monitored_tasks[i].handle == current_task) {
                s_monitored_tasks[i].last_pet_time = time(NULL);
                break;
            }
        }
        xSemaphoreGive(s_task_list_mutex);
    }
    return ESP_OK;
}

uint32_t task_watchdog_get_stack_hwm(TaskHandle_t task_handle) {
    if (task_handle == NULL) return 0;
    return uxTaskGetStackHighWaterMark(task_handle);
}

esp_err_t task_watchdog_get_status_json(char* buffer, size_t buffer_size) {
    cJSON *root = cJSON_CreateObject();
    if (!root) return ESP_ERR_NO_MEM;

    cJSON *tasks_array = cJSON_CreateArray();
    if (!tasks_array) {
        cJSON_Delete(root);
        return ESP_ERR_NO_MEM;
    }
    cJSON_AddItemToObject(root, "monitored_tasks", tasks_array);

    time_t now = time(NULL);

    if (xSemaphoreTake(s_task_list_mutex, portMAX_DELAY) == pdTRUE) {
        for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
            if (s_monitored_tasks[i].is_active) {
                cJSON *task_obj = cJSON_CreateObject();
                cJSON_AddStringToObject(task_obj, "name", s_monitored_tasks[i].name);
                cJSON_AddNumberToObject(task_obj, "stack_hwm_bytes", uxTaskGetStackHighWaterMark(s_monitored_tasks[i].handle));
                cJSON_AddNumberToObject(task_obj, "last_pet_sec_ago", now - s_monitored_tasks[i].last_pet_time);
                cJSON_AddItemToArray(tasks_array, task_obj);
            }
        }
        xSemaphoreGive(s_task_list_mutex);
    }

    if (!cJSON_PrintPreallocated(root, buffer, buffer_size, false)) {
        ESP_LOGE(TAG, "Failed to print task status JSON, buffer too small?");
        cJSON_Delete(root);
        return ESP_ERR_NO_MEM;
    }

    cJSON_Delete(root);
    return ESP_OK;
}

static void watchdog_monitor_task(void *pvParameters) {
    while (1) {
        // Let the main TWDT pet this monitoring task
        esp_task_wdt_reset();

        time_t now = time(NULL);

        if (xSemaphoreTake(s_task_list_mutex, portMAX_DELAY) == pdTRUE) {
            for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
                if (s_monitored_tasks[i].is_active) {
                    time_t elapsed = now - s_monitored_tasks[i].last_pet_time;
                    if (elapsed > TASK_WATCHDOG_TIMEOUT_S) {
                        ESP_LOGE(TAG, "!!! TASK HANG DETECTED: '%s' has not pet the watchdog in %ld seconds. Triggering panic.", 
                                 s_monitored_tasks[i].name, elapsed);
                        // The main TWDT will now expire because we stop petting it,
                        // which will cause a panic and reset as configured.
                        while(1);
                    }
                }
            }
            xSemaphoreGive(s_task_list_mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(5000)); // Check every 5 seconds
    }
}
