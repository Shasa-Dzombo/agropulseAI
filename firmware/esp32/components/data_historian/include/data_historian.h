#ifndef DATA_HISTORIAN_H
#define DATA_HISTORIAN_H

#include "esp_err.h"
#include "data_aggregator.h"

esp_err_t data_historian_init(void);
esp_err_t data_historian_write_record(const char* sensor_id, const sensor_stats_t* stats);
// Read functions would be more complex, involving callbacks or iterators
// esp_err_t data_historian_read_records(...);

#endif // DATA_HISTORIAN_H
