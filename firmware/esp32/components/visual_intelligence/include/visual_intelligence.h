#ifndef VISUAL_INTELLIGENCE_H
#define VISUAL_INTELLIGENCE_H

#include "esp_err.h"
#include "esp_camera.h"

/**
 * @brief Defines the structure for a bounding box.
 */
typedef struct {
    int x;
    int y;
    int width;
    int height;
} bounding_box_t;

/**
 * @brief Defines the structure for a single visual analysis result.
 */
typedef struct {
    char label[32];
    float confidence;
    bounding_box_t box;
} visual_analysis_result_t;

/**
 * @brief Initializes the visual intelligence module.
 *
 * This function loads the TensorFlow Lite model, initializes the interpreter,
 * and allocates the necessary tensors. It must be called before any analysis
 * is performed.
 *
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t visual_intelligence_init(void);

/**
 * @brief Analyzes a camera frame for object detection.
 *
 * Takes a camera frame buffer, preprocesses the image, runs inference,
 * and post-processes the results to find objects.
 *
 * @param fb Pointer to the camera frame buffer (JPEG format).
 * @param[out] results Pointer to a pointer that will be updated to an array of results.
 *                     The caller is responsible for freeing this memory.
 * @param[out] result_count Pointer to an integer that will be updated with the number of results found.
 *
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no objects are detected,
 *         or another error code on failure.
 */
esp_err_t visual_intelligence_analyze_frame(camera_fb_t *fb, visual_analysis_result_t **results, int *result_count);

#endif // VISUAL_INTELLIGENCE_H
