#ifndef HEALTH_MONITOR_H
#define HEALTH_MONITOR_H

#include "esp_err.h"

/**
 * @brief Initializes the system health monitor.
 *
 * This function starts a background task that periodically checks various
 * system health metrics like memory usage, task states, and network connectivity.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t health_monitor_init(void);

/**
 * @brief Publishes a system health report.
 *
 * This function can be called to manually trigger a health report publication.
 * It gathers the latest metrics and publishes them to a dedicated MQTT topic.
 *
 * @return ESP_OK if the report was published successfully, or an error code otherwise.
 */
esp_err_t health_monitor_publish_report(void);

#endif // HEALTH_MONITOR_H
