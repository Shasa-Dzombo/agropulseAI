#ifndef VISION_SYSTEM_H
#define VISION_SYSTEM_H

#include "esp_err.h"

/**
 * @brief Initializes the vision system.
 *
 * This function initializes the camera, visual intelligence, and GPS components,
 * and starts the main vision task.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t vision_system_init(void);

#endif // VISION_SYSTEM_H
