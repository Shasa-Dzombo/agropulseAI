/**
 * @file command_processor.c
 * @brief Implementation of the command processor.
 */

#include "command_processor.h"
#include "esp_log.h"
#include "cJSON.h"
#include "esp_system.h"
#include "water_pump_controller.h"
#include "ota_manager.h"
#include "status_publisher.h"
#include "model_manager.h"
#include "diagnostics_manager.h"
#include "command_registry.h"
#include "logging_manager.h"
#include "job_scheduler.h"
#include "app_config.h"
#include "subscription_commands.h"
#include "platform.h"

static const char *TAG = "CMD_PROCESSOR";

// Forward declarations for command handlers
static esp_err_t handle_set_pump(cJSON* payload);
static esp_err_t handle_reboot(cJSON* payload);
static esp_err_t handle_request_status(cJSON* payload);
static esp_err_t handle_ota_update(cJSON* payload);
static esp_err_t handle_reload_model(cJSON* payload);
static esp_err_t handle_get_diagnostics(cJSON* payload);
static esp_err_t handle_set_log_level(cJSON* payload);
static esp_err_t handle_get_log_levels(cJSON* payload);
static esp_err_t handle_upload_logs(cJSON* payload);
static esp_err_t handle_add_job(cJSON* payload);
static esp_err_t handle_remove_job(cJSON* payload);
static esp_err_t handle_get_jobs(cJSON* payload);
static esp_err_t handle_update_config(cJSON* payload);
static esp_err_t handle_get_config(cJSON* payload);
static esp_err_t handle_provision_certificate(cJSON* payload);

esp_err_t command_processor_init(void) {
    ESP_LOGI(TAG, "Command processor initialized.");
    
    // Initialize the central command registry
    command_registry_init();

    // Initialize subscription commands
    subscription_commands_init();

    // Register all known commands
    command_registry_register("set_pump", handle_set_pump);
    command_registry_register("reboot", handle_reboot);
    command_registry_register("request_status", handle_request_status);
    command_registry_register("ota_update", handle_ota_update);
    command_registry_register("reload_model", handle_reload_model);
    command_registry_register("get_diagnostics", handle_get_diagnostics);
    command_registry_register("set_log_level", handle_set_log_level);
    command_registry_register("get_log_levels", handle_get_log_levels);
    command_registry_register("upload_logs", handle_upload_logs);
    command_registry_register("add_job", handle_add_job);
    command_registry_register("remove_job", handle_remove_job);
    command_registry_register("get_jobs", handle_get_jobs);
    command_registry_register("update_config", handle_update_config);
    command_registry_register("get_config", handle_get_config);
    command_registry_register("provision_certificate", handle_provision_certificate);

    return ESP_OK;
}

// Command handlers
static esp_err_t handle_set_pump(cJSON* payload) {
    // This is now deprecated in favor of device shadow delta.
    // A user could still use it for direct, immediate control.
    ESP_LOGW(TAG, "'set_pump' command is deprecated. Use device shadow 'desired' state.");
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;

    const cJSON* state = cJSON_GetObjectItem(payload, "state");
    if (!cJSON_IsString(state)) return ESP_ERR_INVALID_ARG;

    if (strcmp(state->valuestring, "on") == 0) {
        return water_pump_on();
    } else if (strcmp(state->valuestring, "off") == 0) {
        return water_pump_off();
    }
    return ESP_ERR_INVALID_ARG;
}

static esp_err_t handle_reboot(cJSON* payload) {
    ESP_LOGW(TAG, "Reboot command received. Restarting in 3 seconds.");
    vTaskDelay(pdMS_TO_TICKS(3000));
    platform_reboot();
    return ESP_OK; // This line will not be reached
}

static esp_err_t handle_request_status(cJSON* payload) {
    ESP_LOGI(TAG, "Status request command received.");
    return status_publisher_trigger();
}

static esp_err_t handle_ota_update(cJSON* payload) {
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;
    const cJSON* url = cJSON_GetObjectItem(payload, "url");
    if (!cJSON_IsString(url)) return ESP_ERR_INVALID_ARG;

    const cJSON* type_json = cJSON_GetObjectItem(payload, "type");
    const char* type_str = cJSON_IsString(type_json) ? type_json->valuestring : "firmware";

    ESP_LOGI(TAG, "OTA update command received with URL: %s, type: %s", url->valuestring, type_str);

    if (strcmp(type_str, "model") == 0) {
        // For model updates, we download to the 'incoming' path.
        // The model manager will then be responsible for activating it.
        return ota_manager_start_update_ex(url->valuestring, OTA_TYPE_MODEL, INCOMING_MODEL_PATH);
    } else {
        return ota_manager_start_update_ex(url->valuestring, OTA_TYPE_FIRMWARE, NULL);
    }
}

static esp_err_t handle_reload_model(cJSON* payload) {
    ESP_LOGI(TAG, "Reload model command received.");
    // This command now activates the model that was previously downloaded.
    return model_manager_activate_incoming_model();
}

static esp_err_t handle_get_diagnostics(cJSON* payload) {
    ESP_LOGI(TAG, "Get diagnostics command received.");
    return diagnostics_manager_publish();
}

static esp_err_t handle_set_log_level(cJSON* payload) {
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;
    const cJSON* tag = cJSON_GetObjectItem(payload, "tag");
    const cJSON* level = cJSON_GetObjectItem(payload, "level");

    if (!cJSON_IsString(tag) || !cJSON_IsNumber(level)) {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Setting log level for tag '%s' to %d", tag->valuestring, level->valueint);
    return logging_manager_set_level(tag->valuestring, (esp_log_level_t)level->valueint);
}

static esp_err_t handle_get_log_levels(cJSON* payload) {
    ESP_LOGI(TAG, "Get log levels command received.");
    char* levels_json = logging_manager_get_levels_json();
    if (levels_json) {
        char device_id[64];
        app_config_get_string("device_id", device_id, sizeof(device_id));
        char topic[128];
        snprintf(topic, sizeof(topic), "device/log_levels/%s", device_id);
        mqtt_client_publish(topic, levels_json, strlen(levels_json), 1, 0);
        free(levels_json);
        return ESP_OK;
    }
    return ESP_FAIL;
}

static esp_err_t handle_upload_logs(cJSON* payload) {
    ESP_LOGI(TAG, "Upload logs command received.");
    return logging_manager_upload_logs();
}

static esp_err_t handle_add_job(cJSON* payload) {
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;

    const cJSON* id = cJSON_GetObjectItem(payload, "id");
    const cJSON* cron = cJSON_GetObjectItem(payload, "cron");
    const cJSON* command_payload = cJSON_GetObjectItem(payload, "command");
    const cJSON* is_active = cJSON_GetObjectItem(payload, "is_active");

    if (!cJSON_IsString(id) || !cJSON_IsString(cron) || !cJSON_IsObject(command_payload)) {
        return ESP_ERR_INVALID_ARG;
    }

    char* command_str = cJSON_PrintUnformatted(command_payload);
    if (!command_str) {
        return ESP_ERR_NO_MEM;
    }

    bool active = true; // Default to active if not specified
    if (cJSON_IsBool(is_active)) {
        active = cJSON_IsTrue(is_active);
    }

    ESP_LOGI(TAG, "Adding/updating job ID: %s", id->valuestring);
    esp_err_t ret = job_scheduler_add_job(id->valuestring, cron->valuestring, command_str, active);

    free(command_str);
    return ret;
}

static esp_err_t handle_remove_job(cJSON* payload) {
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;
    const cJSON* id = cJSON_GetObjectItem(payload, "id");
    if (!cJSON_IsString(id)) return ESP_ERR_INVALID_ARG;

    ESP_LOGI(TAG, "Removing job ID: %s", id->valuestring);
    return job_scheduler_remove_job(id->valuestring);
}

static esp_err_t handle_get_jobs(cJSON* payload) {
    ESP_LOGI(TAG, "Get jobs command received.");
    char* jobs_json = job_scheduler_get_jobs_json();
    if (jobs_json) {
        char device_id[64];
        app_config_get_string("device_id", device_id, sizeof(device_id));
        char topic[128];
        snprintf(topic, sizeof(topic), "device/jobs/%s", device_id);
        mqtt_client_publish(topic, jobs_json, strlen(jobs_json), 1, 0);
        free(jobs_json);
        return ESP_OK;
    }
    return ESP_FAIL;
}

static esp_err_t handle_provision_certificate(cJSON* payload) {
    if (!cJSON_IsObject(payload)) return ESP_ERR_INVALID_ARG;
    const cJSON* cert_pem = cJSON_GetObjectItem(payload, "certificate");
    if (!cJSON_IsString(cert_pem)) return ESP_ERR_INVALID_ARG;

    ESP_LOGI(TAG, "Received provision_certificate command.");
    esp_err_t ret = security_manager_store_certificate(cert_pem->valuestring);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Certificate stored successfully. Rebooting in 5 seconds to apply.");
        vTaskDelay(pdMS_TO_TICKS(5000));
        platform_reboot();
    } else {
        ESP_LOGE(TAG, "Failed to store certificate: %s", esp_err_to_name(ret));
    }
    return ret;
}

static esp_err_t handle_update_config(cJSON* payload) {
    ESP_LOGI(TAG, "Update config command received.");
    if (!cJSON_IsObject(payload)) {
        return ESP_ERR_INVALID_ARG;
    }
    
    // The payload itself is the new config partial
    return app_config_update(payload);
}

static esp_err_t handle_get_config(cJSON* payload) {
    ESP_LOGI(TAG, "Get config command received.");
    const cJSON* config_json = app_config_get();
    if (config_json) {
        char* config_str = cJSON_Print(config_json);
        if (config_str) {
            char device_id[64];
            app_config_get_string("device_id", device_id, sizeof(device_id));
            char topic[128];
            snprintf(topic, sizeof(topic), "device/config/%s", device_id);
            mqtt_client_publish(topic, config_str, strlen(config_str), 1, 0);
            free(config_str);
        }
        return ESP_OK;
    }
    return ESP_FAIL;
}

esp_err_t command_processor_process(const char* topic, const char* payload_str) {
    ESP_LOGI(TAG, "Processing command on topic: %s", topic);
    
    cJSON *root = cJSON_Parse(payload_str);
    if (root == NULL) {
        ESP_LOGE(TAG, "Failed to parse JSON payload.");
        return ESP_ERR_INVALID_ARG;
    }

    const cJSON *command_json = cJSON_GetObjectItem(root, "command");
    if (!cJSON_IsString(command_json)) {
        ESP_LOGE(TAG, "Command field is missing or not a string.");
        cJSON_Delete(root);
        return ESP_ERR_INVALID_ARG;
    }

    const cJSON *payload_json = cJSON_GetObjectItem(root, "payload");
    char* command = command_json->valuestring;

    // Dispatch the command using the registry
    esp_err_t ret = command_registry_dispatch(command, payload_json);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to execute command '%s': %s", command, esp_err_to_name(ret));
    } else {
        ESP_LOGI(TAG, "Command '%s' executed successfully.", command);
    }

    cJSON_Delete(root);
    return ret;
}
