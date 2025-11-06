#ifndef CAMERA_MANAGER_H
#define CAMERA_MANAGER_H

#include "esp_err.h"
#include "esp_camera.h"

/**
 * @brief Initializes the camera module.
 *
 * This function configures and initializes the camera pins and the camera driver.
 * It will probe the camera sensor to ensure it's connected and working.
 * The camera configuration (pins, resolution, etc.) is hardcoded for a specific
 * board layout (like the ESP32-CAM AI-Thinker model) but can be adapted.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t camera_manager_init(void);

/**
 * @brief Deinitializes the camera module.
 *
 * Releases resources used by the camera driver.
 *
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t camera_manager_deinit(void);

/**
 * @brief Captures a single image from the camera.
 *
 * This function triggers the camera to capture a frame. The returned frame buffer
 * must be returned to the driver using `camera_manager_return_fb` once it's no
 * longer needed.
 *
 * @return camera_fb_t* A pointer to the frame buffer structure, or NULL on failure.
 */
camera_fb_t* camera_manager_capture(void);

/**
 * @brief Returns a frame buffer to the camera driver.
 *
 * After processing an image, the frame buffer must be returned to the driver
 * so the memory can be reused for subsequent captures.
 *
 * @param fb A pointer to the frame buffer to be returned.
 */
void camera_manager_return_fb(camera_fb_t *fb);

/**
 * @brief Gets the current status of the camera sensor.
 *
 * @return sensor_t* A pointer to the camera's sensor status structure, or NULL if not initialized.
 */
sensor_t* camera_manager_get_status(void);

#endif // CAMERA_MANAGER_H
