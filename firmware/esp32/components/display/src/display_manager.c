#include "display_manager.h"
#include "esp_log.h"
#include <string.h>

#define MAX_LINES 4
#define MAX_LINE_LENGTH 20

static const char *TAG = "DISPLAY_MANAGER";
static char display_buffer[MAX_LINES][MAX_LINE_LENGTH + 1];
static bool is_initialized = false;

esp_err_t display_manager_init(void) {
    ESP_LOGI(TAG, "Display manager initialized (simulated).");
    is_initialized = true;
    display_manager_clear();
    return ESP_OK;
}

void display_manager_clear(void) {
    if (!is_initialized) return;
    for (int i = 0; i < MAX_LINES; i++) {
        memset(display_buffer[i], ' ', MAX_LINE_LENGTH);
        display_buffer[i][MAX_LINE_LENGTH] = '\0';
    }
    ESP_LOGI(TAG, "Display cleared (simulated).");
}

void display_manager_set_line(int line, const char* text) {
    if (!is_initialized || line < 0 || line >= MAX_LINES) {
        return;
    }
    strncpy(display_buffer[line], text, MAX_LINE_LENGTH);
    // Ensure null termination
    display_buffer[line][MAX_LINE_LENGTH] = '\0';
}

void display_manager_refresh(void) {
    if (!is_initialized) return;
    ESP_LOGI(TAG, "--- Display Refresh (Simulated) ---");
    for (int i = 0; i < MAX_LINES; i++) {
        ESP_LOGI(TAG, "| %s |", display_buffer[i]);
    }
    ESP_LOGI(TAG, "-----------------------------------");
}
