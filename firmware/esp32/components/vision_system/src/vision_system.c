#include "vision_system.h"
#include "camera_manager.h"
#include "visual_intelligence.h"
#include "gps_manager.h"
#include "data_publisher.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

#define VISION_TASK_STACK_SIZE (8192)
#define VISION_TASK_PRIORITY   (5)
#define VISION_TASK_DELAY_MS   (15000) // 15 seconds

static const char *TAG = "VISION_SYSTEM";

static void vision_task(void *arg) {
    ESP_LOGI(TAG, "Vision task started.");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(VISION_TASK_DELAY_MS));

        ESP_LOGI(TAG, "Performing vision analysis cycle.");

        // 1. Capture an image
        camera_fb_t *fb = camera_manager_capture();
        if (!fb) {
            ESP_LOGE(TAG, "Failed to capture image.");
            continue;
        }

        // 2. Analyze the image
        visual_analysis_result_t *results = NULL;
        int result_count = 0;
        esp_err_t analysis_err = visual_intelligence_analyze_frame(fb, &results, &result_count);

        // After analysis, return the frame buffer
        esp_camera_fb_return(fb);

        if (analysis_err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to analyze image.");
            continue;
        }

        // 3. Get GPS location
        gps_location_t location = gps_manager_get_location();

        // 4. Publish the results
        if (result_count > 0) {
            ESP_LOGI(TAG, "Found %d objects. Publishing results.", result_count);
            data_publisher_publish_vision_results(results, result_count, &location);
            // Free the results allocated by the visual_intelligence component
            free(results);
        } else {
            ESP_LOGI(TAG, "No objects detected in this cycle.");
        }
    }
}

esp_err_t vision_system_init(void) {
    esp_err_t ret;

    // Initialize Camera
    ret = camera_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize camera manager: 0x%x", ret);
        return ret;
    }

    // Initialize Visual Intelligence
    ret = visual_intelligence_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize visual intelligence: 0x%x", ret);
        return ret;
    }

    // Initialize GPS Manager
    ret = gps_manager_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize GPS manager: 0x%x", ret);
        return ret;
    }

    // Create the vision task
    xTaskCreate(vision_task, "vision_task", VISION_TASK_STACK_SIZE, NULL, VISION_TASK_PRIORITY, NULL);

    ESP_LOGI(TAG, "Vision system initialized successfully.");
    return ESP_OK;
}
