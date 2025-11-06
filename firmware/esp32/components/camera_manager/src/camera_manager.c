#include "camera_manager.h"
#include "esp_log.h"
#include "esp_camera.h"
#include "app_config.h" // To get pin configurations

static const char *TAG = "CAMERA_MANAGER";

// AI-Thinker ESP32-CAM Pin Map
#define CAM_PIN_PWDN    32
#define CAM_PIN_RESET   -1 // NC
#define CAM_PIN_XCLK    0
#define CAM_PIN_SIOD    26
#define CAM_PIN_SIOC    27
#define CAM_PIN_D7      35
#define CAM_PIN_D6      34
#define CAM_PIN_D5      39
#define CAM_PIN_D4      36
#define CAM_PIN_D3      21
#define CAM_PIN_D2      19
#define CAM_PIN_D1      18
#define CAM_PIN_D0      5
#define CAM_PIN_VSYNC   25
#define CAM_PIN_HREF    23
#define CAM_PIN_PCLK    22

static camera_config_t camera_config = {
    .pin_pwdn  = CAM_PIN_PWDN,
    .pin_reset = CAM_PIN_RESET,
    .pin_xclk = CAM_PIN_XCLK,
    .pin_sscb_sda = CAM_PIN_SIOD,
    .pin_sscb_scl = CAM_PIN_SIOC,

    .pin_d7 = CAM_PIN_D7,
    .pin_d6 = CAM_PIN_D6,
    .pin_d5 = CAM_PIN_D5,
    .pin_d4 = CAM_PIN_D4,
    .pin_d3 = CAM_PIN_D3,
    .pin_d2 = CAM_PIN_D2,
    .pin_d1 = CAM_PIN_D1,
    .pin_d0 = CAM_PIN_D0,
    .pin_vsync = CAM_PIN_VSYNC,
    .pin_href = CAM_PIN_HREF,
    .pin_pclk = CAM_PIN_PCLK,

    // XCLK 20MHz or 10MHz for OV2640 double FPS (Experimental)
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,

    .pixel_format = PIXFORMAT_JPEG, // JPEG for streaming, YUV422 for processing
    .frame_size = FRAMESIZE_VGA,    // 640x480. Can be changed to SVGA (800x600), UXGA (1600x1200) for high-res captures
    .jpeg_quality = 12, // 0-63, lower number means higher quality
    .fb_count = 2,       // Use 2 frame buffers for smoother capture
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
};

esp_err_t camera_manager_init(void) {
    // Note: In a real application, you might want to get pin numbers from app_config
    // For simplicity here, we use the defines for a common board.
    
    // Power up the camera
    // gpio_set_direction(CAM_PIN_PWDN, GPIO_MODE_OUTPUT);
    // gpio_set_level(CAM_PIN_PWDN, 0);
    // vTaskDelay(pdMS_TO_TICKS(10));

    // Initialize the camera
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera initialization failed with error 0x%x", err);
        return err;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s->id.PID == OV3660_PID) {
        // Adjust settings for OV3660
        s->set_vflip(s, 1); // Flip vertically
        s->set_brightness(s, 1);
        s->set_saturation(s, -2);
    }

    ESP_LOGI(TAG, "Camera initialized successfully. Sensor: %d", s->id.PID);
    return ESP_OK;
}

esp_err_t camera_manager_deinit(void) {
    esp_err_t err = esp_camera_deinit();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera deinitialization failed with error 0x%x", err);
        return err;
    }
    ESP_LOGI(TAG, "Camera deinitialized successfully.");
    return ESP_OK;
}

camera_fb_t* camera_manager_capture(void) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGE(TAG, "Camera capture failed");
        return NULL;
    }
    ESP_LOGI(TAG, "Captured image: %zu bytes, %dx%d", fb->len, fb->width, fb->height);
    return fb;
}

void camera_manager_return_fb(camera_fb_t *fb) {
    if (fb) {
        esp_camera_fb_return(fb);
    }
}

sensor_t* camera_manager_get_status(void) {
    return esp_camera_sensor_get();
}
