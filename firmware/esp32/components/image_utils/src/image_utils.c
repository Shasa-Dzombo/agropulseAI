#include "image_utils.h"
#include "esp_log.h"
#include "tjpgd.h"
#include <string.h>

static const char *TAG = "image_utils";

typedef struct {
    uint8_t *rgb_buffer;
    int width;
    int height;
    int current_x;
    int current_y;
} JpegDecodeData;

static UINT jpeg_decode_output_function(JDEC *jdec, void *bitmap, JRECT *rect) {
    JpegDecodeData *decode_data = (JpegDecodeData *)jdec->device;
    uint8_t *src = (uint8_t *)bitmap;

    for (int y = rect->top; y <= rect->bottom; y++) {
        for (int x = rect->left; x <= rect->right; x++) {
            int index = (y * decode_data->width + x) * 3;
            decode_data->rgb_buffer[index] = src[0];
            decode_data->rgb_buffer[index + 1] = src[1];
            decode_data->rgb_buffer[index + 2] = src[2];
            src += 3;
        }
    }
    return 1;
}

esp_err_t image_utils_decode_jpg(camera_fb_t *fb, uint8_t *rgb_buffer, int *width, int *height) {
    JDEC jdec;
    char *work = (char *)malloc(TJPGD_WORKSPACE_SIZE);
    if (!work) {
        ESP_LOGE(TAG, "Failed to allocate JPEG workspace");
        return ESP_ERR_NO_MEM;
    }

    JpegDecodeData decode_data;
    decode_data.rgb_buffer = rgb_buffer;

    JRESULT res = jd_prepare(&jdec, (void *)fb->buf, fb->len, 0, 0, &decode_data);
    if (res != JDR_OK) {
        ESP_LOGE(TAG, "JPEG prepare failed: %d", res);
        free(work);
        return ESP_FAIL;
    }

    *width = jdec.width;
    *height = jdec.height;
    decode_data.width = jdec.width;
    decode_data.height = jdec.height;

    res = jd_decomp(&jdec, jpeg_decode_output_function, 0);
    if (res != JDR_OK) {
        ESP_LOGE(TAG, "JPEG decomp failed: %d", res);
        free(work);
        return ESP_FAIL;
    }

    free(work);
    return ESP_OK;
}

esp_err_t image_utils_resize_image(const uint8_t *src_image, int src_width, int src_height,
                                   uint8_t *dest_image, int dest_width, int dest_height) {
    float x_ratio = (float)src_width / dest_width;
    float y_ratio = (float)src_height / dest_height;

    for (int y = 0; y < dest_height; y++) {
        for (int x = 0; x < dest_width; x++) {
            int px = (int)(x * x_ratio);
            int py = (int)(y * y_ratio);

            const uint8_t *src_pixel = &src_image[(py * src_width + px) * 3];
            uint8_t *dest_pixel = &dest_image[(y * dest_width + x) * 3];

            dest_pixel[0] = src_pixel[0]; // R
            dest_pixel[1] = src_pixel[1]; // G
            dest_pixel[2] = src_pixel[2]; // B
        }
    }
    return ESP_OK;
}
