#include "command_registry.h"
#include "esp_log.h"
#include <string.h>

#define MAX_COMMANDS 20

static const char *TAG = "CMD_REGISTRY";

typedef struct {
    char name[32];
    command_handler_t handler;
} command_entry_t;

static command_entry_t command_table[MAX_COMMANDS];
static int command_count = 0;

esp_err_t command_registry_init(void) {
    memset(command_table, 0, sizeof(command_table));
    command_count = 0;
    ESP_LOGI(TAG, "Command registry initialized.");
    return ESP_OK;
}

esp_err_t command_registry_register(const char* command, command_handler_t handler) {
    if (!command || !handler || command_count >= MAX_COMMANDS) {
        ESP_LOGE(TAG, "Failed to register command '%s': Invalid arguments or registry full.", command);
        return ESP_ERR_INVALID_ARG;
    }

    for (int i = 0; i < command_count; i++) {
        if (strcmp(command_table[i].name, command) == 0) {
            ESP_LOGW(TAG, "Command '%s' is already registered. Overwriting.", command);
            command_table[i].handler = handler;
            return ESP_OK;
        }
    }

    strncpy(command_table[command_count].name, command, sizeof(command_table[0].name) - 1);
    command_table[command_count].handler = handler;
    command_count++;

    ESP_LOGI(TAG, "Registered command: %s", command);
    return ESP_OK;
}

esp_err_t command_registry_dispatch(const char* command, cJSON* payload) {
    if (!command) {
        return ESP_ERR_INVALID_ARG;
    }

    for (int i = 0; i < command_count; i++) {
        if (strcmp(command_table[i].name, command) == 0) {
            ESP_LOGI(TAG, "Dispatching command: %s", command);
            return command_table[i].handler(payload);
        }
    }

    ESP_LOGW(TAG, "Unknown command: %s", command);
    return ESP_ERR_NOT_FOUND;
}
