#ifndef IMAGE_UTILS_H
#define IMAGE_UTILS_H

#include "esp_camera.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Decodes a JPEG image into a raw RGB888 buffer.
 *
 * @param fb Pointer to the camera frame buffer containing the JPEG image.
 * @param[out] rgb_buffer Pointer to a buffer where the decoded RGB data will be stored.
 *                        This buffer must be allocated by the caller.
 * @param[out] width Pointer to store the width of the decoded image.
 * @param[out] height Pointer to store the height of the decoded image.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t image_utils_decode_jpg(camera_fb_t *fb, uint8_t *rgb_buffer, int *width, int *height);

/**
 * @brief Resizes an RGB888 image to a target size.
 *
 * This function performs a simple box-sampling resize.
 *
 * @param src_image Pointer to the source image buffer (RGB888).
 * @param src_width Width of the source image.
 * @param src_height Height of the source image.
 * @param dest_image Pointer to the destination image buffer (RGB888).
 * @param dest_width Target width.
 * @param dest_height Target height.
 * @return esp_err_t ESP_OK on success.
 */
esp_err_t image_utils_resize_image(const uint8_t *src_image, int src_width, int src_height,
                                   uint8_t *dest_image, int dest_width, int dest_height);

#ifdef __cplusplus
}
#endif

#endif // IMAGE_UTILS_H
