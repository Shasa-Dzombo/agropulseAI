/**
 * @file ota_verifier.c
 * @brief Implementation of the OTA signature verifier.
 */

#include "ota_verifier.h"
#include "esp_log.h"
#include "mbedtls/sha256.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/platform.h"
#include "secure_element.h" // To get the public key

static const char *TAG = "OTA_VERIFIER";

static mbedtls_ecdsa_context ecdsa_ctx;
static bool is_initialized = false;

esp_err_t ota_verifier_init(void) {
    uint8_t public_key[64];
    size_t key_size = sizeof(public_key);

    // Initialize the mbedTLS context
    mbedtls_ecdsa_init(&ecdsa_ctx);

    // Get the public key from the secure element
    if (secure_element_get_public_key(public_key, &key_size) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get public key from secure element.");
        return ESP_FAIL;
    }

    // Load the public key into the mbedTLS context
    // We assume an uncompressed SECP256r1 key (x and y coordinates)
    if (mbedtls_ecp_group_load(&ecdsa_ctx.grp, MBEDTLS_ECP_DP_SECP256R1) != 0) {
        ESP_LOGE(TAG, "Failed to load ECP group.");
        return ESP_FAIL;
    }
    if (mbedtls_ecp_point_read_binary(&ecdsa_ctx.grp, &ecdsa_ctx.Q, public_key, key_size) != 0) {
        ESP_LOGE(TAG, "Failed to read public key into ECP point.");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "OTA Verifier initialized with public key from secure element.");
    is_initialized = true;
    return ESP_OK;
}

esp_err_t ota_verifier_verify_image(const void* image_data, size_t image_size, const void* signature, size_t signature_size) {
    if (!is_initialized) {
        ESP_LOGE(TAG, "Verifier not initialized.");
        return ESP_FAIL;
    }

    uint8_t hash[32];
    
    // 1. Calculate the SHA-256 hash of the firmware image
    ESP_LOGI(TAG, "Calculating hash of image (size: %d bytes)...", image_size);
    int ret = mbedtls_sha256_ret((const unsigned char*)image_data, image_size, hash, 0);
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to calculate SHA-256 hash, mbedtls error: -0x%x", -ret);
        return ESP_FAIL;
    }

    // 2. Verify the hash against the signature using the public key
    ESP_LOGI(TAG, "Verifying signature...");
    ret = mbedtls_ecdsa_read_signature(&ecdsa_ctx, hash, sizeof(hash), (const unsigned char*)signature, signature_size);
    if (ret == 0) {
        ESP_LOGI(TAG, "Signature is VALID.");
        return ESP_OK;
    } else {
        ESP_LOGE(TAG, "Signature is INVALID, mbedtls error: -0x%x", -ret);
        return ESP_ERR_INVALID_SIGNATURE;
    }
}

esp_err_t ota_verifier_verify_partition(const esp_partition_t *partition) {
    if (partition == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    // In a real OTA implementation, the signature is often appended to the
    // firmware binary. The esp_ota_ops.h provides functions to get the
    // app description, which can include the signature location.
    // For this simulation, we assume the signature is not present and return an error.

    ESP_LOGE(TAG, "Verifying a full partition is not yet implemented in this simulation.");
    ESP_LOGI(TAG, "A real implementation would read the app descriptor, find the signature, map the partition, and call ota_verifier_verify_image.");
    
    return ESP_ERR_NOT_SUPPORTED;
}
