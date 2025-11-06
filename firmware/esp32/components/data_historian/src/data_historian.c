#include "data_historian.h"
#include "esp_log.h"
#include "esp_spiffs.h"
#include <stdio.h>

static const char *TAG = "DATA_HISTORIAN";
#define HISTORIAN_FILE "/spiffs/historian.dat"

esp_err_t data_historian_init(void) {
    // The SPIFFS filesystem is assumed to be initialized elsewhere
    ESP_LOGI(TAG, "Data historian initialized.");
    return ESP_OK;
}

esp_err_t data_historian_write_record(const char* sensor_id, const sensor_stats_t* stats) {
    FILE* f = fopen(HISTORIAN_FILE, "a"); // Append mode
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open historian file for writing.");
        return ESP_FAIL;
    }

    // In a real implementation, a more robust binary format would be used.
    fprintf(f, "ts=%lld,sensor=%s,min=%.2f,max=%.2f,mean=%.2f,std=%.2f,count=%d\n",
            (long long)time(NULL),
            sensor_id,
            stats->min,
            stats->max,
            stats->mean,
            stats->std_dev,
            stats->count);
    
    fclose(f);
    return ESP_OK;
}
