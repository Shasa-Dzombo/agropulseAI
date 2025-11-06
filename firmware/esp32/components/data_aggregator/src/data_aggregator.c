#include "data_aggregator.h"
#include "esp_log.h"
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#define MAX_SENSORS 10
#define MAX_READINGS 60 // Store up to 60 readings per sensor

static const char *TAG = "DATA_AGGREGATOR";

typedef struct {
    char sensor_id[32];
    double readings[MAX_READINGS];
    int head;
    int count;
} sensor_data_buffer_t;

static sensor_data_buffer_t sensor_buffers[MAX_SENSORS];
static int num_sensors = 0;
static SemaphoreHandle_t aggregator_mutex;

esp_err_t data_aggregator_init(void) {
    aggregator_mutex = xSemaphoreCreateMutex();
    memset(sensor_buffers, 0, sizeof(sensor_buffers));
    ESP_LOGI(TAG, "Data aggregator initialized.");
    return ESP_OK;
}

esp_err_t data_aggregator_add_reading(const char* sensor_id, double value) {
    xSemaphoreTake(aggregator_mutex, portMAX_DELAY);
    
    int sensor_idx = -1;
    for (int i = 0; i < num_sensors; i++) {
        if (strcmp(sensor_buffers[i].sensor_id, sensor_id) == 0) {
            sensor_idx = i;
            break;
        }
    }

    if (sensor_idx == -1 && num_sensors < MAX_SENSORS) {
        sensor_idx = num_sensors;
        strncpy(sensor_buffers[sensor_idx].sensor_id, sensor_id, sizeof(sensor_buffers[0].sensor_id) - 1);
        num_sensors++;
    }

    if (sensor_idx != -1) {
        sensor_buffers[sensor_idx].readings[sensor_buffers[sensor_idx].head] = value;
        sensor_buffers[sensor_idx].head = (sensor_buffers[sensor_idx].head + 1) % MAX_READINGS;
        if (sensor_buffers[sensor_idx].count < MAX_READINGS) {
            sensor_buffers[sensor_idx].count++;
        }
    }

    xSemaphoreGive(aggregator_mutex);
    return ESP_OK;
}

esp_err_t data_aggregator_get_stats(const char* sensor_id, sensor_stats_t* stats) {
    xSemaphoreTake(aggregator_mutex, portMAX_DELAY);

    int sensor_idx = -1;
    for (int i = 0; i < num_sensors; i++) {
        if (strcmp(sensor_buffers[i].sensor_id, sensor_id) == 0) {
            sensor_idx = i;
            break;
        }
    }

    if (sensor_idx == -1 || sensor_buffers[sensor_idx].count == 0) {
        xSemaphoreGive(aggregator_mutex);
        return ESP_ERR_NOT_FOUND;
    }

    sensor_data_buffer_t* buffer = &sensor_buffers[sensor_idx];
    double sum = 0;
    stats->min = buffer->readings[0];
    stats->max = buffer->readings[0];

    for (int i = 0; i < buffer->count; i++) {
        sum += buffer->readings[i];
        if (buffer->readings[i] < stats->min) stats->min = buffer->readings[i];
        if (buffer->readings[i] > stats->max) stats->max = buffer->readings[i];
    }
    stats->mean = sum / buffer->count;

    double sum_sq_diff = 0;
    for (int i = 0; i < buffer->count; i++) {
        sum_sq_diff += pow(buffer->readings[i] - stats->mean, 2);
    }
    stats->std_dev = sqrt(sum_sq_diff / buffer->count);
    stats->count = buffer->count;

    xSemaphoreGive(aggregator_mutex);
    return ESP_OK;
}
