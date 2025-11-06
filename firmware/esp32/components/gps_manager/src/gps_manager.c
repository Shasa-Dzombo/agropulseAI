#include "gps_manager.h"
#include "minmea.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "app_config.h"
#include <string.h>
#include <stdlib.h>

#define GPS_UART_NUM            UART_NUM_2
#define GPS_RX_BUF_SIZE         (1024)
#define GPS_TASK_STACK_SIZE     (4096)
#define GPS_TASK_PRIORITY       (5)

static const char *TAG = "gps_manager";

static gps_location_t s_current_location = { .is_valid = false };
static SemaphoreHandle_t s_location_mutex;

static void gps_task(void *arg) {
    uart_config_t uart_config = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };

    int uart_tx_pin = -1;
    int uart_rx_pin = -1;
    app_config_get_int("gps_tx_pin", &uart_tx_pin);
    app_config_get_int("gps_rx_pin", &uart_rx_pin);

    if (uart_rx_pin == -1) {
        ESP_LOGE(TAG, "GPS RX pin not configured. Aborting task.");
        vTaskDelete(NULL);
        return;
    }

    uart_driver_install(GPS_UART_NUM, GPS_RX_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(GPS_UART_NUM, &uart_config);
    uart_set_pin(GPS_UART_NUM, uart_tx_pin, uart_rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    uint8_t* data = (uint8_t*) malloc(GPS_RX_BUF_SIZE);
    char line[MINMEA_MAX_SENTENCE_LENGTH];
    int line_pos = 0;

    while (1) {
        int len = uart_read_bytes(GPS_UART_NUM, data, GPS_RX_BUF_SIZE, 20 / portTICK_PERIOD_MS);
        if (len > 0) {
            for (int i = 0; i < len; i++) {
                if (data[i] == '$') {
                    line_pos = 0;
                    line[line_pos++] = data[i];
                } else if (line_pos > 0) {
                    if (line_pos < MINMEA_MAX_SENTENCE_LENGTH - 1) {
                        line[line_pos++] = data[i];
                    }
                    if (data[i] == '\n') {
                        line[line_pos] = '\0';
                        
                        enum minmea_sentence_id id = minmea_sentence_id(line, false);
                        if (id == MINMEA_SENTENCE_RMC) {
                            struct minmea_sentence_rmc frame;
                            if (minmea_parse_rmc(&frame, line)) {
                                if (xSemaphoreTake(s_location_mutex, portMAX_DELAY) == pdTRUE) {
                                    s_current_location.is_valid = frame.valid;
                                    if(frame.valid) {
                                        s_current_location.latitude = minmea_tocoord(&frame.latitude);
                                        s_current_location.longitude = minmea_tocoord(&frame.longitude);
                                    }
                                    xSemaphoreGive(s_location_mutex);
                                }
                            }
                        } else if (id == MINMEA_SENTENCE_GGA) {
                            struct minmea_sentence_gga frame;
                            if (minmea_parse_gga(&frame, line)) {
                                if (xSemaphoreTake(s_location_mutex, portMAX_DELAY) == pdTRUE) {
                                    s_current_location.satellites_tracked = frame.satellites_tracked;
                                    if (!s_current_location.is_valid && frame.fix_quality > 0) {
                                        s_current_location.is_valid = true;
                                        s_current_location.latitude = minmea_tocoord(&frame.latitude);
                                        s_current_location.longitude = minmea_tocoord(&frame.longitude);
                                    }
                                    xSemaphoreGive(s_location_mutex);
                                }
                            }
                        }
                        line_pos = 0;
                    }
                }
            }
        }
    }
    free(data);
}

esp_err_t gps_manager_init(void) {
    s_location_mutex = xSemaphoreCreateMutex();
    if (s_location_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create location mutex");
        return ESP_FAIL;
    }

    xTaskCreate(gps_task, "gps_task", GPS_TASK_STACK_SIZE, NULL, GPS_TASK_PRIORITY, NULL);
    ESP_LOGI(TAG, "GPS manager initialized.");
    return ESP_OK;
}

gps_location_t gps_manager_get_location(void) {
    gps_location_t location;
    if (xSemaphoreTake(s_location_mutex, portMAX_DELAY) == pdTRUE) {
        location = s_current_location;
        xSemaphoreGive(s_location_mutex);
    } else {
        location.is_valid = false;
    }
    return location;
}
