#ifndef GPS_MANAGER_H
#define GPS_MANAGER_H

#include "esp_err.h"
#include <stdbool.h>

/**
 * @brief Structure to hold GPS location data.
 */
typedef struct {
    float latitude;
    float longitude;
    bool is_valid;
    int satellites_tracked;
} gps_location_t;

/**
 * @brief Initializes the GPS manager.
 *
 * This function sets up the UART communication with the GPS module and starts a
 * background task to read and parse NMEA data.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t gps_manager_init(void);

/**
 * @brief Retrieves the last known GPS location.
 *
 * This function is thread-safe and returns the most recently parsed location
 * data.
 *
 * @return A gps_location_t structure with the latest data.
 *         The is_valid flag will be false if no valid fix has been obtained.
 */
gps_location_t gps_manager_get_location(void);

#endif // GPS_MANAGER_H
