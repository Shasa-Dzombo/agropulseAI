#ifndef DATA_AGGREGATOR_H
#define DATA_AGGREGATOR_H

#include "esp_err.h"

typedef struct {
    double min;
    double max;
    double mean;
    double std_dev;
    int count;
} sensor_stats_t;

esp_err_t data_aggregator_init(void);
esp_err_t data_aggregator_add_reading(const char* sensor_id, double value);
esp_err_t data_aggregator_get_stats(const char* sensor_id, sensor_stats_t* stats);

#endif // DATA_AGGREGATOR_H
