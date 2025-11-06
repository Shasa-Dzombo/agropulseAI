#include "secure_logger.h"
#include "esp_log.h"
#include "mbedtls/sha256.h"
#include <stdio.h>
#include <string.h>

static const char *TAG = "SECURE_LOGGER";
#define SECURE_LOG_FILE "/spiffs/secure_log.dat"

// The hash of the previously logged entry
static uint8_t last_log_hash[32] = {0};

esp_err_t secure_logger_init(void) {
    // In a real implementation, we would read the file to find the last hash
    memset(last_log_hash, 0, sizeof(last_log_hash));
    ESP_LOGI(TAG, "Secure logger initialized.");
    return ESP_OK;
}

esp_err_t secure_logger_log(const char* message) {
    FILE* f = fopen(SECURE_LOG_FILE, "a");
    if (f == NULL) {
        ESP_LOGE(TAG, "Failed to open secure log file.");
        return ESP_FAIL;
    }

    // 1. Create the log entry string
    char prev_hash_str[65];
    for (int i = 0; i < 32; i++) {
        sprintf(prev_hash_str + i * 2, "%02x", last_log_hash[i]);
    }
    
    char log_entry[512];
    snprintf(log_entry, sizeof(log_entry), "prev_hash=%s,ts=%lld,msg=%s", prev_hash_str, (long long)time(NULL), message);

    // 2. Calculate the hash of the current entry
    uint8_t current_hash[32];
    mbedtls_sha256((const unsigned char*)log_entry, strlen(log_entry), current_hash, 0);

    // 3. Write the full entry to the file
    fprintf(f, "%s\n", log_entry);
    fclose(f);

    // 4. Update the last_log_hash for the next entry
    memcpy(last_log_hash, current_hash, sizeof(last_log_hash));

    return ESP_OK;
}
