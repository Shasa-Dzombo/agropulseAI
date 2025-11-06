#include "config_manager_v2.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "CONFIG_MGR_V2";
#define CONFIG_NVS_NAMESPACE "config_v2"
#define CONFIG_NVS_KEY "app_config"
#define CONFIG_VERSION_KEY "config_version"

struct config_manager_v2_t {
    cJSON* config_json;
    const config_schema_item_t* schema;
    size_t schema_size;
    SemaphoreHandle_t mutex;
};

// Forward declarations
static esp_err_t load_config_from_nvs(config_manager_v2_handle_t handle);
static esp_err_t save_config_to_nvs(config_manager_v2_handle_t handle);
static esp_err_t create_default_config(config_manager_v2_handle_t handle);
static bool validate_config(const cJSON* config, const config_schema_item_t* schema, size_t schema_size);

esp_err_t config_manager_v2_init(const config_schema_item_t* schema, size_t schema_size, config_manager_v2_handle_t* handle_out) {
    if (!schema || schema_size == 0 || !handle_out) {
        return ESP_ERR_INVALID_ARG;
    }

    config_manager_v2_handle_t handle = calloc(1, sizeof(struct config_manager_v2_t));
    if (!handle) {
        return ESP_ERR_NO_MEM;
    }

    handle->schema = schema;
    handle->schema_size = schema_size;
    handle->mutex = xSemaphoreCreateMutex();
    if (!handle->mutex) {
        free(handle);
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = load_config_from_nvs(handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to load config from NVS (%s). Creating default config.", esp_err_to_name(err));
        err = create_default_config(handle);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to create default config.");
            vSemaphoreDelete(handle->mutex);
            free(handle);
            return err;
        }
    }

    *handle_out = handle;
    ESP_LOGI(TAG, "Config Manager V2 initialized successfully.");
    return ESP_OK;
}

esp_err_t config_manager_v2_deinit(config_manager_v2_handle_t handle) {
    if (!handle) {
        return ESP_ERR_INVALID_ARG;
    }
    if (handle->config_json) {
        cJSON_Delete(handle->config_json);
    }
    vSemaphoreDelete(handle->mutex);
    free(handle);
    return ESP_OK;
}

const cJSON* config_manager_v2_get_config(config_manager_v2_handle_t handle) {
    if (!handle) {
        return NULL;
    }
    // No mutex needed for read-only access to the pointer itself.
    // The caller is trusted not to modify the content.
    return handle->config_json;
}

esp_err_t config_manager_v2_update_config(config_manager_v2_handle_t handle, const cJSON* new_config) {
    if (!handle || !new_config) {
        return ESP_ERR_INVALID_ARG;
    }

    xSemaphoreTake(handle->mutex, portMAX_DELAY);

    cJSON *merged_config = cJSON_Duplicate(handle->config_json, true);
    if (!merged_config) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_NO_MEM;
    }

    cJSON *child = new_config->child;
    while (child) {
        if (cJSON_HasObjectItem(merged_config, child->string)) {
            cJSON_ReplaceItemInObject(merged_config, child->string, cJSON_Duplicate(child, true));
        } else {
            cJSON_AddItemToObject(merged_config, child->string, cJSON_Duplicate(child, true));
        }
        child = child->next;
    }

    if (!validate_config(merged_config, handle->schema, handle->schema_size)) {
        ESP_LOGE(TAG, "Update failed: new configuration is invalid.");
        cJSON_Delete(merged_config);
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_INVALID_ARG;
    }

    cJSON_Delete(handle->config_json);
    handle->config_json = merged_config;

    esp_err_t err = save_config_to_nvs(handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to save updated config to NVS.");
        // Attempt to rollback? For now, we just log the error.
    }

    xSemaphoreGive(handle->mutex);
    return err;
}

esp_err_t config_manager_v2_reset_to_defaults(config_manager_v2_handle_t handle) {
    if (!handle) {
        return ESP_ERR_INVALID_ARG;
    }

    xSemaphoreTake(handle->mutex, portMAX_DELAY);
    
    esp_err_t err = create_default_config(handle);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Configuration reset to defaults.");
    }

    xSemaphoreGive(handle->mutex);
    return err;
}

// Helper functions
static esp_err_t load_config_from_nvs(config_manager_v2_handle_t handle) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(CONFIG_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) return err;

    // Check version
    char nvs_version[16] = {0};
    size_t version_size = sizeof(nvs_version);
    err = nvs_get_str(nvs_handle, CONFIG_VERSION_KEY, nvs_version, &version_size);
    if (err != ESP_OK || strcmp(nvs_version, CONFIG_VERSION) != 0) {
        ESP_LOGW(TAG, "NVS config version mismatch (found '%s', expected '%s'). Forcing default.", nvs_version, CONFIG_VERSION);
        nvs_close(nvs_handle);
        return ESP_ERR_NVS_INVALID_VERSION;
    }

    // Get config string size
    size_t required_size = 0;
    err = nvs_get_str(nvs_handle, CONFIG_NVS_KEY, NULL, &required_size);
    if (err != ESP_OK || required_size == 0) {
        nvs_close(nvs_handle);
        return err == ESP_OK ? ESP_ERR_NVS_NOT_FOUND : err;
    }

    char* config_str = malloc(required_size);
    if (!config_str) {
        nvs_close(nvs_handle);
        return ESP_ERR_NO_MEM;
    }

    err = nvs_get_str(nvs_handle, CONFIG_NVS_KEY, config_str, &required_size);
    nvs_close(nvs_handle);

    if (err != ESP_OK) {
        free(config_str);
        return err;
    }

    cJSON* loaded_json = cJSON_Parse(config_str);
    free(config_str);

    if (!loaded_json) {
        return ESP_FAIL;
    }

    if (!validate_config(loaded_json, handle->schema, handle->schema_size)) {
        ESP_LOGE(TAG, "Loaded configuration is invalid according to schema.");
        cJSON_Delete(loaded_json);
        return ESP_ERR_INVALID_STATE;
    }

    if (handle->config_json) {
        cJSON_Delete(handle->config_json);
    }
    handle->config_json = loaded_json;

    ESP_LOGI(TAG, "Successfully loaded config from NVS.");
    return ESP_OK;
}

static esp_err_t save_config_to_nvs(config_manager_v2_handle_t handle) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(CONFIG_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) return err;

    char* config_str = cJSON_PrintUnformatted(handle->config_json);
    if (!config_str) {
        nvs_close(nvs_handle);
        return ESP_ERR_NO_MEM;
    }

    err = nvs_set_str(nvs_handle, CONFIG_NVS_KEY, config_str);
    free(config_str);
    if (err != ESP_OK) {
        nvs_close(nvs_handle);
        return err;
    }

    err = nvs_set_str(nvs_handle, CONFIG_VERSION_KEY, CONFIG_VERSION);
    if (err != ESP_OK) {
        nvs_close(nvs_handle);
        return err;
    }

    err = nvs_commit(nvs_handle);
    nvs_close(nvs_handle);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Configuration saved to NVS.");
    }
    return err;
}

static esp_err_t create_default_config(config_manager_v2_handle_t handle) {
    if (handle->config_json) {
        cJSON_Delete(handle->config_json);
    }
    handle->config_json = cJSON_CreateObject();
    if (!handle->config_json) {
        return ESP_ERR_NO_MEM;
    }

    for (size_t i = 0; i < handle->schema_size; i++) {
        const config_schema_item_t* item = &handle->schema[i];
        if (item->default_value) {
            cJSON* default_val_json = cJSON_Parse(item->default_value);
            if (default_val_json) {
                cJSON_AddItemToObject(handle->config_json, item->key, default_val_json);
            } else {
                ESP_LOGE(TAG, "Failed to parse default value for key '%s'", item->key);
            }
        } else if (item->required) {
            ESP_LOGE(TAG, "Required key '%s' has no default value!", item->key);
            // This indicates a schema design error.
        }
    }

    if (!validate_config(handle->config_json, handle->schema, handle->schema_size)) {
        ESP_LOGE(TAG, "FATAL: Default configuration does not validate against schema.");
        return ESP_ERR_INVALID_STATE;
    }

    return save_config_to_nvs(handle);
}

static bool validate_config(const cJSON* config, const config_schema_item_t* schema, size_t schema_size) {
    for (size_t i = 0; i < schema_size; i++) {
        const config_schema_item_t* item = &schema[i];
        const cJSON* json_item = cJSON_GetObjectItem(config, item->key);

        if (!json_item) {
            if (item->required) {
                ESP_LOGE(TAG, "Validation failed: Required key '%s' is missing.", item->key);
                return false;
            }
            continue; // Optional and not present, so it's fine.
        }

        if (json_item->type != item->type) {
            ESP_LOGE(TAG, "Validation failed: Key '%s' has incorrect type.", item->key);
            return false;
        }
    }
    return true;
}

// Type-safe getters
esp_err_t config_manager_v2_get_string(config_manager_v2_handle_t handle, const char* key, char* buffer, size_t buffer_size) {
    if (!handle || !key || !buffer || buffer_size == 0) return ESP_ERR_INVALID_ARG;
    
    xSemaphoreTake(handle->mutex, portMAX_DELAY);
    const cJSON* item = cJSON_GetObjectItem(handle->config_json, key);
    if (!item) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_NOT_FOUND;
    }
    if (!cJSON_IsString(item)) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_INVALID_ARG;
    }
    strncpy(buffer, item->valuestring, buffer_size - 1);
    buffer[buffer_size - 1] = '\0';
    xSemaphoreGive(handle->mutex);
    return ESP_OK;
}

esp_err_t config_manager_v2_get_int(config_manager_v2_handle_t handle, const char* key, int* value) {
    if (!handle || !key || !value) return ESP_ERR_INVALID_ARG;

    xSemaphoreTake(handle->mutex, portMAX_DELAY);
    const cJSON* item = cJSON_GetObjectItem(handle->config_json, key);
    if (!item) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_NOT_FOUND;
    }
    if (!cJSON_IsNumber(item)) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_INVALID_ARG;
    }
    *value = item->valueint;
    xSemaphoreGive(handle->mutex);
    return ESP_OK;
}

esp_err_t config_manager_v2_get_bool(config_manager_v2_handle_t handle, const char* key, bool* value) {
    if (!handle || !key || !value) return ESP_ERR_INVALID_ARG;

    xSemaphoreTake(handle->mutex, portMAX_DELAY);
    const cJSON* item = cJSON_GetObjectItem(handle->config_json, key);
    if (!item) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_NOT_FOUND;
    }
    if (!cJSON_IsBool(item)) {
        xSemaphoreGive(handle->mutex);
        return ESP_ERR_INVALID_ARG;
    }
    *value = cJSON_IsTrue(item);
    xSemaphoreGive(handle->mutex);
    return ESP_OK;
}
