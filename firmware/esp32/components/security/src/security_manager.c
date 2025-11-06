#include "security_manager.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/pk.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/sha256.h"
#include "mbedtls/base64.h"
#include "cJSON.h"
#include <time.h>
#include <string.h>

static const char *TAG = "SECURITY_MANAGER";
#define NVS_NAMESPACE "security"
#define PRIVATE_KEY_NVS_KEY "device_prv_key"

// mbedTLS context for our private key
static mbedtls_pk_context s_pk_ctx;
static bool s_key_loaded = false;

// Forward declarations
static esp_err_t generate_and_save_private_key(void);
static esp_err_t load_private_key(void);

esp_err_t security_manager_init(void) {
    esp_err_t ret = load_private_key();
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "Device private key not found in NVS. Generating a new one.");
        ret = generate_and_save_private_key();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Failed to generate and save new private key!");
            return ret;
        }
        // Try loading again
        ret = load_private_key();
    }

    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Security manager initialized successfully.");
    } else {
        ESP_LOGE(TAG, "Failed to initialize security manager.");
    }
    
    return ret;
}

esp_err_t security_manager_get_public_key_pem(char** pem_buffer) {
    if (!s_key_loaded) {
        return ESP_FAIL;
    }

    unsigned char output_buf[1024];
    memset(output_buf, 0, sizeof(output_buf));

    if (mbedtls_pk_write_pubkey_pem(&s_pk_ctx, output_buf, sizeof(output_buf)) != 0) {
        ESP_LOGE(TAG, "Failed to write public key to PEM format.");
        return ESP_FAIL;
    }

    *pem_buffer = strdup((char*)output_buf);
    if (*pem_buffer == NULL) {
        return ESP_ERR_NO_MEM;
    }

    return ESP_OK;
}

esp_err_t security_manager_sign_digest(const uint8_t* digest, uint8_t* signature_buffer, size_t* signature_size) {
    if (!s_key_loaded) {
        return ESP_FAIL;
    }

    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);

    const char *pers = "esp32_signer";
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, (const unsigned char *)pers, strlen(pers));
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_ctr_drbg_seed failed: -0x%04x", -ret);
        mbedtls_ctr_drbg_free(&ctr_drbg);
        mbedtls_entropy_free(&entropy);
        return ESP_FAIL;
    }

    ret = mbedtls_pk_sign(&s_pk_ctx, MBEDTLS_MD_SHA256, digest, 32, signature_buffer, *signature_size, signature_size, mbedtls_ctr_drbg_random, &ctr_drbg);
    
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);

    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_pk_sign failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    return ESP_OK;
}

esp_err_t security_manager_verify_signature(const uint8_t* digest, const uint8_t* signature, size_t signature_len, const char* pub_key_pem) {
    mbedtls_pk_context pk_ctx;
    mbedtls_pk_init(&pk_ctx);

    int ret = mbedtls_pk_parse_public_key(&pk_ctx, (const unsigned char*)pub_key_pem, strlen(pub_key_pem) + 1);
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to parse public key PEM: -0x%04x", -ret);
        mbedtls_pk_free(&pk_ctx);
        return ESP_FAIL;
    }

    ret = mbedtls_pk_verify(&pk_ctx, MBEDTLS_MD_SHA256, digest, 32, signature, signature_len);
    mbedtls_pk_free(&pk_ctx);

    if (ret != 0) {
        ESP_LOGE(TAG, "Signature verification failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    return ESP_OK;
}

esp_err_t security_manager_generate_jwt(const char* project_id, uint32_t expiry_minutes, char** jwt_buffer) {
    if (!s_key_loaded) {
        ESP_LOGE(TAG, "Cannot generate JWT, private key not loaded.");
        return ESP_FAIL;
    }

    // 1. Create JWT Header
    cJSON *header_json = cJSON_CreateObject();
    cJSON_AddStringToObject(header_json, "alg", "ES256");
    cJSON_AddStringToObject(header_json, "typ", "JWT");
    char *header_str = cJSON_PrintUnformatted(header_json);
    cJSON_Delete(header_json);

    // 2. Create JWT Payload (Claims)
    time_t now = time(NULL);
    cJSON *payload_json = cJSON_CreateObject();
    cJSON_AddNumberToObject(payload_json, "iat", now);
    cJSON_AddNumberToObject(payload_json, "exp", now + (expiry_minutes * 60));
    cJSON_AddStringToObject(payload_json, "aud", project_id);
    char *payload_str = cJSON_PrintUnformatted(payload_json);
    cJSON_Delete(payload_json);

    // 3. Base64-url encode Header and Payload
    size_t header_b64_len, payload_b64_len;
    unsigned char *header_b64 = NULL, *payload_b64 = NULL;

    mbedtls_base64_encode(NULL, 0, &header_b64_len, (const unsigned char*)header_str, strlen(header_str));
    header_b64 = malloc(header_b64_len);
    mbedtls_base64_encode(header_b64, header_b64_len, &header_b64_len, (const unsigned char*)header_str, strlen(header_str));

    mbedtls_base64_encode(NULL, 0, &payload_b64_len, (const unsigned char*)payload_str, strlen(payload_str));
    payload_b64 = malloc(payload_b64_len);
    mbedtls_base64_encode(payload_b64, payload_b64_len, &payload_b64_len, (const unsigned char*)payload_str, strlen(payload_str));

    free(header_str);
    free(payload_str);

    // 4. Create the signing input
    char* signing_input = malloc(header_b64_len + payload_b64_len + 2);
    sprintf(signing_input, "%s.%s", header_b64, payload_b64);
    free(header_b64);
    free(payload_b64);

    // 5. Sign the input
    unsigned char digest[32];
    mbedtls_sha256_ret((const unsigned char*)signing_input, strlen(signing_input), digest, 0);

    unsigned char signature[MBEDTLS_ECDSA_MAX_LEN];
    size_t sig_len = sizeof(signature);
    esp_err_t ret = security_manager_sign_digest(digest, signature, &sig_len);
    free(signing_input);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to sign JWT.");
        return ret;
    }

    // 6. Base64-url encode the signature
    size_t sig_b64_len;
    unsigned char* sig_b64 = NULL;
    mbedtls_base64_encode(NULL, 0, &sig_b64_len, signature, sig_len);
    sig_b64 = malloc(sig_b64_len);
    mbedtls_base64_encode(sig_b64, sig_b64_len, &sig_b64_len, signature, sig_len);

    // 7. Assemble the final JWT
    *jwt_buffer = malloc(strlen(signing_input) + sig_b64_len + 2);
    sprintf(*jwt_buffer, "%s.%s", signing_input, sig_b64);
    free(sig_b64);

    ESP_LOGI(TAG, "Generated JWT successfully.");
    return ESP_OK;
}


// --- Static Helper Functions ---

static esp_err_t generate_and_save_private_key(void) {
    mbedtls_pk_context key_ctx;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    
    mbedtls_pk_init(&key_ctx);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    mbedtls_entropy_init(&entropy);

    const char *pers = "esp32_key_gen";
    int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, (const unsigned char *)pers, strlen(pers));
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_ctr_drbg_seed failed: -0x%04x", -ret);
        goto cleanup;
    }

    ESP_LOGI(TAG, "Generating 256-bit EC private key (SECP256R1)...");
    ret = mbedtls_pk_setup(&key_ctx, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_pk_setup failed: -0x%04x", -ret);
        goto cleanup;
    }

    ret = mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(key_ctx), mbedtls_ctr_drbg_random, &ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_ecp_gen_key failed: -0x%04x", -ret);
        goto cleanup;
    }

    // Key generated, now save it to NVS
    unsigned char key_buf[1024];
    ret = mbedtls_pk_write_key_pem(&key_ctx, key_buf, sizeof(key_buf));
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_pk_write_key_pem failed: -0x%04x", -ret);
        goto cleanup;
    }

    nvs_handle_t nvs_handle;
    ret = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace.");
        goto cleanup;
    }

    ret = nvs_set_str(nvs_handle, PRIVATE_KEY_NVS_KEY, (char*)key_buf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to save private key to NVS.");
    } else {
        ESP_LOGI(TAG, "New private key saved to NVS.");
        ret = nvs_commit(nvs_handle);
    }

    nvs_close(nvs_handle);

cleanup:
    mbedtls_pk_free(&key_ctx);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    return (ret == 0) ? ESP_OK : ESP_FAIL;
}

static esp_err_t load_private_key(void) {
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (ret != ESP_OK) {
        return ret;
    }

    size_t required_size = 0;
    ret = nvs_get_str(nvs_handle, PRIVATE_KEY_NVS_KEY, NULL, &required_size);
    if (ret != ESP_OK) {
        nvs_close(nvs_handle);
        return ret;
    }

    char* key_pem = malloc(required_size);
    if (key_pem == NULL) {
        nvs_close(nvs_handle);
        return ESP_ERR_NO_MEM;
    }

    ret = nvs_get_str(nvs_handle, PRIVATE_KEY_NVS_KEY, key_pem, &required_size);
    nvs_close(nvs_handle);

    if (ret != ESP_OK) {
        free(key_pem);
        return ret;
    }

    mbedtls_pk_init(&s_pk_ctx);
    int mbed_ret = mbedtls_pk_parse_key(&s_pk_ctx, (const unsigned char*)key_pem, required_size, NULL, 0, mbedtls_ctr_drbg_random, NULL);
    free(key_pem);

    if (mbed_ret != 0) {
        ESP_LOGE(TAG, "Failed to parse private key: -0x%04x", -mbed_ret);
        mbedtls_pk_free(&s_pk_ctx);
        s_key_loaded = false;
        return ESP_FAIL;
    }

    s_key_loaded = true;
    ESP_LOGI(TAG, "Successfully loaded device private key from NVS.");
    return ESP_OK;
}
