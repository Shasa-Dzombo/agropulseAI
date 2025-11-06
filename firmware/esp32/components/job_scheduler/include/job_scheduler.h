#ifndef JOB_SCHEDULER_H
#define JOB_SCHEDULER_H

#include "esp_err.h"
#include "cJSON.h"

/**
 * @brief Initializes the job scheduler.
 *
 * This function loads persisted jobs from NVS and starts the scheduler task.
 *
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t job_scheduler_init(void);

/**
 * @brief Adds a new job to the scheduler.
 *
 * The job is saved to NVS to persist across reboots.
 *
 * @param name A unique name for the job.
 * @param schedule A cron-like string for the schedule (e.g., "0 * * * *").
 * @param command The command to execute.
 * @param payload The JSON payload for the command.
 * @return esp_err_t ESP_OK on success, or an error code on failure.
 */
esp_err_t job_scheduler_add_job(const char* name, const char* schedule, const char* command, cJSON* payload);

/**
 * @brief Removes a job from the scheduler.
 *
 * The job is removed from NVS.
 *
 * @param name The name of the job to remove.
 * @return esp_err_t ESP_OK on success, ESP_ERR_NOT_FOUND if not found.
 */
esp_err_t job_scheduler_remove_job(const char* name);

/**
 * @brief Gets a JSON string representing all scheduled jobs.
 *
 * The caller is responsible for freeing the returned string.
 *
 * @return char* A dynamically allocated JSON string, or NULL on failure.
 */
char* job_scheduler_get_jobs_json(void);

#endif // JOB_SCHEDULER_H
