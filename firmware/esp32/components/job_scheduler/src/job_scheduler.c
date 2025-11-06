#include "job_scheduler.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "ccronexpr.h"
#include "cJSON.h"
#include "string.h"
#include "command_processor.h"

#define JOB_SCHEDULER_TASK_STACK_SIZE 4096
#define MAX_JOBS 20
#define JOB_NVS_NAMESPACE "job_scheduler"
#define JOB_NVS_KEY "jobs"

static const char *TAG = "JOB_SCHEDULER";

typedef struct {
    char id[37]; // UUID
    char cron_string[100];
    char command[256];
    time_t next_run;
    cron_expr expr;
    bool is_active;
} job_t;

static job_t scheduled_jobs[MAX_JOBS];
static int job_count = 0;
static TaskHandle_t job_scheduler_task_handle = NULL;
static SemaphoreHandle_t jobs_mutex;

static void save_jobs_to_nvs() {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(JOB_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        return;
    }

    cJSON *jobs_json_array = cJSON_CreateArray();
    if (jobs_json_array == NULL) {
        ESP_LOGE(TAG, "Failed to create JSON array for jobs");
        nvs_close(nvs_handle);
        return;
    }

    xSemaphoreTake(jobs_mutex, portMAX_DELAY);
    for (int i = 0; i < job_count; i++) {
        cJSON *job_json = cJSON_CreateObject();
        cJSON_AddStringToObject(job_json, "id", scheduled_jobs[i].id);
        cJSON_AddStringToObject(job_json, "cron", scheduled_jobs[i].cron_string);
        cJSON_AddStringToObject(job_json, "command", scheduled_jobs[i].command);
        cJSON_AddBoolToObject(job_json, "is_active", scheduled_jobs[i].is_active);
        cJSON_AddItemToArray(jobs_json_array, job_json);
    }
    xSemaphoreGive(jobs_mutex);

    char *jobs_string = cJSON_PrintUnformatted(jobs_json_array);
    if (jobs_string) {
        err = nvs_set_str(nvs_handle, JOB_NVS_KEY, jobs_string);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to save jobs to NVS: %s", esp_err_to_name(err));
        } else {
            err = nvs_commit(nvs_handle);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "NVS commit failed: %s", esp_err_to_name(err));
            } else {
                ESP_LOGI(TAG, "Jobs saved to NVS successfully.");
            }
        }
        free(jobs_string);
    } else {
        ESP_LOGE(TAG, "Failed to print jobs JSON to string");
    }

    cJSON_Delete(jobs_json_array);
    nvs_close(nvs_handle);
}

static void load_jobs_from_nvs() {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(JOB_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (err != ESP_OK) {
        if (err == ESP_ERR_NVS_NOT_FOUND) {
            ESP_LOGI(TAG, "Jobs not found in NVS. Starting fresh.");
        } else {
            ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        }
        return;
    }

    size_t required_size = 0;
    err = nvs_get_str(nvs_handle, JOB_NVS_KEY, NULL, &required_size);
    if (err == ESP_OK && required_size > 1) {
        char* jobs_string = malloc(required_size);
        if (jobs_string == NULL) {
            ESP_LOGE(TAG, "Failed to allocate memory for jobs string");
            nvs_close(nvs_handle);
            return;
        }
        
        err = nvs_get_str(nvs_handle, JOB_NVS_KEY, jobs_string, &required_size);
        if (err == ESP_OK) {
            cJSON *jobs_json_array = cJSON_Parse(jobs_string);
            if (jobs_json_array != NULL) {
                int num_jobs = cJSON_GetArraySize(jobs_json_array);
                xSemaphoreTake(jobs_mutex, portMAX_DELAY);
                job_count = 0; // Reset current job count
                for (int i = 0; i < num_jobs && i < MAX_JOBS; i++) {
                    cJSON *job_json = cJSON_GetArrayItem(jobs_json_array, i);
                    cJSON *id_json = cJSON_GetObjectItem(job_json, "id");
                    cJSON *cron_json = cJSON_GetObjectItem(job_json, "cron");
                    cJSON *command_json = cJSON_GetObjectItem(job_json, "command");
                    cJSON *is_active_json = cJSON_GetObjectItem(job_json, "is_active");

                    if (cJSON_IsString(id_json) && cJSON_IsString(cron_json) && cJSON_IsString(command_json) && cJSON_IsBool(is_active_json)) {
                        job_scheduler_add_job(id_json->valuestring, cron_json->valuestring, command_json->valuestring, cJSON_IsTrue(is_active_json));
                    }
                }
                xSemaphoreGive(jobs_mutex);
                ESP_LOGI(TAG, "Loaded %d jobs from NVS.", job_count);
            } else {
                ESP_LOGE(TAG, "Failed to parse jobs JSON from NVS.");
            }
            cJSON_Delete(jobs_json_array);
        } else {
            ESP_LOGE(TAG, "Failed to read jobs from NVS: %s", esp_err_to_name(err));
        }
        free(jobs_string);
    }
    nvs_close(nvs_handle);
}


static void job_scheduler_task(void *pvParameters) {
    ESP_LOGI(TAG, "Job scheduler task started.");
    while (1) {
        time_t now;
        time(&now);
        
        xSemaphoreTake(jobs_mutex, portMAX_DELAY);
        for (int i = 0; i < job_count; i++) {
            if (scheduled_jobs[i].is_active && now >= scheduled_jobs[i].next_run) {
                ESP_LOGI(TAG, "Executing job ID %s: %s", scheduled_jobs[i].id, scheduled_jobs[i].command);
                
                // Execute the command
                cJSON *cmd_json = cJSON_Parse(scheduled_jobs[i].command);
                if (cmd_json) {
                    command_processor_execute_json(cmd_json);
                    cJSON_Delete(cmd_json);
                } else {
                    ESP_LOGE(TAG, "Failed to parse job command JSON: %s", scheduled_jobs[i].command);
                }

                // Calculate next run time
                scheduled_jobs[i].next_run = cron_next(&scheduled_jobs[i].expr, now);
                ESP_LOGI(TAG, "Job ID %s next run scheduled for: %lld", scheduled_jobs[i].id, scheduled_jobs[i].next_run);
            }
        }
        xSemaphoreGive(jobs_mutex);

        vTaskDelay(pdMS_TO_TICKS(1000)); // Check every second
    }
}

void job_scheduler_init() {
    jobs_mutex = xSemaphoreCreateMutex();
    if (jobs_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create jobs mutex.");
        return;
    }

    load_jobs_from_nvs();

    xTaskCreate(job_scheduler_task, "job_scheduler_task", JOB_SCHEDULER_TASK_STACK_SIZE, NULL, 5, &job_scheduler_task_handle);
    ESP_LOGI(TAG, "Job scheduler initialized.");
}

esp_err_t job_scheduler_add_job(const char* id, const char* cron_string, const char* command, bool is_active) {
    xSemaphoreTake(jobs_mutex, portMAX_DELAY);
    
    // Check if job with this ID already exists
    for (int i = 0; i < job_count; i++) {
        if (strcmp(scheduled_jobs[i].id, id) == 0) {
            // Update existing job
            strncpy(scheduled_jobs[i].cron_string, cron_string, sizeof(scheduled_jobs[i].cron_string) - 1);
            strncpy(scheduled_jobs[i].command, command, sizeof(scheduled_jobs[i].command) - 1);
            scheduled_jobs[i].is_active = is_active;
            
            const char* err = NULL;
            cron_parse_expr(cron_string, &scheduled_jobs[i].expr, &err);
            if (err) {
                ESP_LOGE(TAG, "Error parsing cron string for job %s: %s", id, err);
                xSemaphoreGive(jobs_mutex);
                return ESP_FAIL;
            }
            
            time_t now;
            time(&now);
            scheduled_jobs[i].next_run = cron_next(&scheduled_jobs[i].expr, now);
            ESP_LOGI(TAG, "Updated job ID %s. Next run: %lld", id, scheduled_jobs[i].next_run);
            
            xSemaphoreGive(jobs_mutex);
            save_jobs_to_nvs();
            return ESP_OK;
        }
    }

    // Add new job if there is space
    if (job_count >= MAX_JOBS) {
        ESP_LOGE(TAG, "Cannot add new job, maximum number of jobs reached.");
        xSemaphoreGive(jobs_mutex);
        return ESP_FAIL;
    }

    job_t* new_job = &scheduled_jobs[job_count];
    strncpy(new_job->id, id, sizeof(new_job->id) - 1);
    strncpy(new_job->cron_string, cron_string, sizeof(new_job->cron_string) - 1);
    strncpy(new_job->command, command, sizeof(new_job->command) - 1);
    new_job->is_active = is_active;

    const char* err = NULL;
    cron_parse_expr(cron_string, &new_job->expr, &err);
    if (err) {
        ESP_LOGE(TAG, "Error parsing cron string for new job %s: %s", id, err);
        xSemaphoreGive(jobs_mutex);
        return ESP_FAIL;
    }

    time_t now;
    time(&now);
    new_job->next_run = cron_next(&new_job->expr, now);
    
    job_count++;
    ESP_LOGI(TAG, "Added new job ID %s. Next run: %lld", id, new_job->next_run);
    
    xSemaphoreGive(jobs_mutex);
    save_jobs_to_nvs();
    return ESP_OK;
}

esp_err_t job_scheduler_remove_job(const char* id) {
    xSemaphoreTake(jobs_mutex, portMAX_DELAY);
    int found_index = -1;
    for (int i = 0; i < job_count; i++) {
        if (strcmp(scheduled_jobs[i].id, id) == 0) {
            found_index = i;
            break;
        }
    }

    if (found_index != -1) {
        // Shift remaining jobs to fill the gap
        for (int i = found_index; i < job_count - 1; i++) {
            scheduled_jobs[i] = scheduled_jobs[i + 1];
        }
        job_count--;
        ESP_LOGI(TAG, "Removed job ID %s.", id);
        xSemaphoreGive(jobs_mutex);
        save_jobs_to_nvs();
        return ESP_OK;
    } else {
        ESP_LOGW(TAG, "Job ID %s not found for removal.", id);
        xSemaphoreGive(jobs_mutex);
        return ESP_ERR_NOT_FOUND;
    }
}

cJSON* job_scheduler_get_jobs_json() {
    cJSON *jobs_array = cJSON_CreateArray();
    if (jobs_array == NULL) {
        ESP_LOGE(TAG, "Failed to create JSON array for jobs list.");
        return NULL;
    }

    xSemaphoreTake(jobs_mutex, portMAX_DELAY);
    for (int i = 0; i < job_count; i++) {
        cJSON *job_json = cJSON_CreateObject();
        cJSON_AddStringToObject(job_json, "id", scheduled_jobs[i].id);
        cJSON_AddStringToObject(job_json, "cron", scheduled_jobs[i].cron_string);
        cJSON_AddStringToObject(job_json, "command", scheduled_jobs[i].command);
        cJSON_AddBoolToObject(job_json, "is_active", scheduled_jobs[i].is_active);
        cJSON_AddNumberToObject(job_json, "next_run", scheduled_jobs[i].next_run);
        cJSON_AddItemToArray(jobs_array, job_json);
    }
    xSemaphoreGive(jobs_mutex);

    return jobs_array;
}
