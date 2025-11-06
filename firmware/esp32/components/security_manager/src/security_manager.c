#include "security_manager.h"
#include "secure_element_manager.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include <string.h>
#include <stdio.h>

// mbedTLS headers
#include "mbedtls/ssl.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/pk.h"
#include "mbedtls/x509_csr.h"
#include "mbedtls/x509_crt.h"
#include "mbedtls/error.h"

#include "secure_element_manager.h"
#include "subscription_manager.h"
#include "kyber/kem.h"

#define KYBER_PUBLIC_KEY_SIZE KEM_PUBLICKEYBYTES
#define KYBER_SECRET_KEY_SIZE KEM_SECRETKEYBYTES
#define KYBER_CIPHERTEXT_SIZE KEM_CIPHERTEXTBYTES
#define KYBER_SHARED_SECRET_SIZE KEM_BYTES

static const char *TAG = "SECURITY_MGR";

// NVS constants for storing the certificate
#define NVS_NAMESPACE "sec_mgr"
#define NVS_KEY_CERT "dev_cert"

// Static variables to hold the custom PK context and certificate
static mbedtls_pk_context atecc608a_pk_ctx;
static char *device_cert_pem = NULL;
static bool is_provisioned = false;

// Post-Quantum State
static uint8_t pq_public_key[KYBER_PUBLIC_KEY_SIZE];
static uint8_t pq_secret_key[KYBER_SECRET_KEY_SIZE];
static bool pq_keys_generated = false;

/**
 * @brief Custom signing function for mbedTLS that uses the ATECC608A.
 *
 * This function is called by mbedTLS during the TLS handshake when a signature
 * is required. It delegates the signing operation to the secure element.
 *
 * @param ctx The mbedTLS PK context (not used, we use a global context).
 * @param md_alg The message digest algorithm (unused).
 * @param hash The 32-byte hash to be signed.
 * @param hash_len The length of the hash (must be 32).
 * @param sig Buffer to store the generated signature.
 * @param sig_len Pointer to store the length of the signature.
 * @param f_rng The random number generator function (unused).
 * @param p_rng The RNG context (unused).
 * @return 0 on success, or an mbedTLS error code on failure.
 */
static int atecc_ecdsa_sign(void *ctx, mbedtls_md_type_t md_alg,
                            const unsigned char *hash, size_t hash_len,
                            unsigned char *sig, size_t *sig_len,
                            int (*f_rng)(void *, unsigned char *, size_t),
                            void *p_rng) {
    if (hash_len != 32) {
        ESP_LOGE(TAG, "Invalid hash length for signing: %d", hash_len);
        return MBEDTLS_ERR_PK_BAD_INPUT_DATA;
    }

    uint8_t raw_signature[ATCA_SIG_SIZE];
    size_t raw_sig_len = sizeof(raw_signature);

    esp_err_t esp_ret = secure_element_manager_sign(DEVICE_PRIVATE_KEY_SLOT, hash, raw_signature, &raw_sig_len);
    if (esp_ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to sign hash with secure element");
        return MBEDTLS_ERR_PK_HW_ACCEL_FAILED;
    }

    // Convert the raw R/S signature from the ATECC608A to an ASN.1 DER encoded signature
    // which is what mbedTLS expects.
    mbedtls_ecdsa_context ecdsa_ctx;
    mbedtls_ecdsa_init(&ecdsa_ctx);

    // We need to associate the keypair with the context to get the group info
    mbedtls_pk_context *pk = &atecc_pk_ctx;
    mbedtls_ecp_keypair *keypair = mbedtls_pk_ec(*pk);
    mbedtls_ecdsa_from_keypair(&ecdsa_ctx, keypair);

    int ret = mbedtls_ecdsa_signature_to_asn1_der(&ecdsa_ctx, raw_signature, raw_signature + 32, sig, sig_len);
    mbedtls_ecdsa_free(&ecdsa_ctx);

    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to convert signature to ASN.1 DER: -0x%04X", -ret);
        return ret;
    }

    return 0;
}

// Custom mbedTLS PK info structure for our ATECC608A key
static const mbedtls_pk_info_t atecc_pk_info = {
    .type = MBEDTLS_PK_ECKEY,
    .name = "ATECC_ECKEY",
    .get_bitlen = mbedtls_pk_get_bitlen_default,
    .can_do = mbedtls_pk_can_do_default,
    .verify_func = NULL, // Verification is done with the public key, not needed here
    .sign_func = atecc_ecdsa_sign,
    .decrypt_func = NULL,
    .encrypt_func = NULL,
    .check_pair_func = mbedtls_pk_check_pair_default,
    .ctx_alloc_func = mbedtls_pk_ctx_alloc_default,
    .ctx_free_func = mbedtls_pk_ctx_free_default,
    .debug_func = mbedtls_pk_debug_default,
};

static int atecc608a_sign_wrap(void *ctx, mbedtls_md_type_t md_alg,
                            const unsigned char *hash, size_t hash_len,
                            unsigned char *sig, size_t *sig_len,
                            int (*f_rng)(void *, unsigned char *, size_t),
                            void *p_rng) {
    // Call the original ATECC signing function
    int ret = atecc_ecdsa_sign(ctx, md_alg, hash, hash_len, sig, sig_len, f_rng, p_rng);

    // If successful, log the operation
    if (ret == 0) {
        ESP_LOGI(TAG, "ATECC608A signing operation successful.");
    } else {
        ESP_LOGE(TAG, "ATECC608A signing operation failed with error: -0x%04X", -ret);
    }

    return ret;
}

esp_err_t security_manager_init(void) {
    uint8_t public_key[ATCA_PUB_KEY_SIZE];
    size_t pub_key_len = sizeof(public_key);

    // Initialize the PK context
    mbedtls_pk_init(&atecc608a_pk_ctx);

    // Attempt to get the public key from the secure element
    esp_err_t ret = secure_element_manager_get_public_key(DEVICE_PRIVATE_KEY_SLOT, public_key, &pub_key_len);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to get public key from slot %d. Assuming key needs to be generated.", DEVICE_PRIVATE_KEY_SLOT);
        ret = secure_element_manager_gen_key(DEVICE_PRIVATE_KEY_SLOT);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Failed to generate new key in slot %d.", DEVICE_PRIVATE_KEY_SLOT);
            return ret;
        }
        // Try getting the public key again
        ret = secure_element_manager_get_public_key(DEVICE_PRIVATE_KEY_SLOT, public_key, &pub_key_len);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Failed to get public key even after generation.");
            return ret;
        }
        ESP_LOGI(TAG, "New private key generated in slot %d.", DEVICE_PRIVATE_KEY_SLOT);
    }

    // Setup the custom PK context to use our ATECC key info
    int mbed_ret = mbedtls_pk_setup(&atecc608a_pk_ctx, &atecc_pk_info);
    if (mbed_ret != 0) {
        ESP_LOGE(TAG, "Failed to setup PK context: -0x%04X", -mbed_ret);
        return ESP_FAIL;
    }

    // Load the public key into the mbedTLS keypair structure
    mbedtls_ecp_keypair *keypair = mbedtls_pk_ec(atecc608a_pk_ctx);
    mbedtls_ecp_group_load(&keypair->grp, MBEDTLS_ECP_DP_SECP256R1);
    mbed_ret = mbedtls_ecp_point_read_binary(&keypair->grp, &keypair->Q, public_key, pub_key_len);
    if (mbed_ret != 0) {
        ESP_LOGE(TAG, "Failed to parse public key: -0x%04X", -mbed_ret);
        return ESP_FAIL;
    }

    // Load the certificate from NVS
    size_t cert_len;
    nvs_handle_t nvs_handle;
    ret = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (ret == ESP_OK) {
        ret = nvs_get_blob(nvs_handle, NVS_KEY_CERT, NULL, &cert_len);
        if (ret == ESP_OK) {
            device_cert_pem = malloc(cert_len);
            if (device_cert_pem) {
                nvs_get_blob(nvs_handle, NVS_KEY_CERT, device_cert_pem, &cert_len);
                ESP_LOGI(TAG, "Device certificate loaded from NVS (%d bytes).", cert_len);
            }
        } else {
            ESP_LOGW(TAG, "Device certificate not found in NVS. Device needs provisioning.");
        }
        nvs_close(nvs_handle);
    }

    // Provisioning status check
    if (device_cert_pem && strlen(device_cert_pem) > 0) {
        is_provisioned = true;
        ESP_LOGI(TAG, "Device already provisioned.");
    } else {
        ESP_LOGW(TAG, "Device not provisioned. Please provision the device.");
    }

    ESP_LOGI(TAG, "Security Manager Initialized.");
    return ESP_OK;
}

esp_err_t security_manager_generate_csr(char *csr_buf, size_t csr_buf_len, size_t *csr_len) {
    int ret;
    mbedtls_x509write_csr req;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    const char *pers = "x509_csr";

    mbedtls_x509write_csr_init(&req);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    mbedtls_entropy_init(&entropy);

    ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, (const unsigned char *)pers, strlen(pers));
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_ctr_drbg_seed failed: -0x%04X", -ret);
        goto cleanup;
    }

    // Set the subject key for the CSR to our custom ATECC PK context
    mbedtls_x509write_csr_set_key(&req, &atecc_pk_ctx);

    // Get the device serial number to use as the Common Name
    uint8_t serial_num[ATCA_SERIAL_NUM_SIZE];
    size_t serial_len = sizeof(serial_num);
    secure_element_manager_get_serial_number(serial_num, &serial_len);

    char serial_str[sizeof(serial_num) * 2 + 1];
    for (int i = 0; i < serial_len; i++) {
        sprintf(&serial_str[i * 2], "%02X", serial_num[i]);
    }
    serial_str[sizeof(serial_num) * 2] = '\0';

    char subject_name[128];
    snprintf(subject_name, sizeof(subject_name), "CN=%s,O=AgroPulse,C=US", serial_str);

    ret = mbedtls_x509write_csr_set_subject_name(&req, subject_name);
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_x509write_csr_set_subject_name failed: -0x%04X", -ret);
        goto cleanup;
    }

    // Set the message digest for the signature
    mbedtls_x509write_csr_set_md_alg(&req, MBEDTLS_MD_SHA256);

    // Write the CSR in PEM format
    ret = mbedtls_x509write_csr_pem(&req, (unsigned char *)csr_buf, csr_buf_len, mbedtls_ctr_drbg_random, &ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_x509write_csr_pem failed: -0x%04X", -ret);
        goto cleanup;
    }

    *csr_len = strlen(csr_buf);
    ESP_LOGI(TAG, "CSR generated successfully.");

cleanup:
    mbedtls_x509write_csr_free(&req);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    return (ret == 0) ? ESP_OK : ESP_FAIL;
}

esp_err_t security_manager_store_certificate(const char *cert_pem) {
    if (!cert_pem) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS handle: %s", esp_err_to_name(err));
        return err;
    }

    err = nvs_set_blob(nvs_handle, NVS_KEY_CERT, cert_pem, strlen(cert_pem) + 1);
    if (err == ESP_OK) {
        err = nvs_commit(nvs_handle);
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "Device certificate stored successfully in NVS.");
            // Update in-memory copy if it exists
            if (device_cert_pem) {
                free(device_cert_pem);
            }
            device_cert_pem = strdup(cert_pem);
        }
    }

    nvs_close(nvs_handle);
    return err;
}

esp_err_t security_manager_get_certificate(char *cert_buf, size_t cert_buf_len) {
    if (!device_cert_pem) {
        return ESP_ERR_NOT_FOUND;
    }
    if (strlen(device_cert_pem) + 1 > cert_buf_len) {
        return ESP_ERR_NO_MEM;
    }
    strcpy(cert_buf, device_cert_pem);
    return ESP_OK;
}

esp_err_t security_manager_get_mtls_config(const char *server_root_ca_pem, esp_tls_cfg_t *esp_tls_cfg) {
    if (!server_root_ca_pem || !esp_tls_cfg) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!device_cert_pem) {
        ESP_LOGE(TAG, "Cannot create mTLS config: Device certificate is not available.");
        return ESP_ERR_INVALID_STATE;
    }

    memset(esp_tls_cfg, 0, sizeof(esp_tls_cfg_t));
    esp_tls_cfg->cacert_pem_buf = (const unsigned char *)server_root_ca_pem;
    esp_tls_cfg->cacert_pem_bytes = strlen(server_root_ca_pem) + 1;
    esp_tls_cfg->clientcert_pem_buf = (const unsigned char *)device_cert_pem;
    esp_tls_cfg->clientcert_pem_bytes = strlen(device_cert_pem) + 1;

    // This is the most important part: setting the client key to our custom PK context.
    // This tells esp_tls to use our custom signing function, which uses the secure element.
    esp_tls_cfg->clientkey_ctx = &atecc_pk_ctx;

    return ESP_OK;
}

esp_err_t security_manager_get_ssl_config(mbedtls_ssl_config *conf) {
    if (!is_provisioned) {
        return ESP_ERR_INVALID_STATE;
    }

    // Load the device certificate
    mbedtls_x509_crt cert;
    mbedtls_x509_crt_init(&cert);

    esp_err_t ret = mbedtls_x509_crt_parse(&cert, (const unsigned char *)device_cert_pem, strlen(device_cert_pem) + 1);
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to parse device certificate: -0x%04X", -ret);
        return ESP_FAIL;
    }

    // Set the device certificate
    mbedtls_ssl_conf_cert(&conf, &cert);

    // Set the key exchange function
    mbedtls_ssl_conf_authmode(conf, MBEDTLS_SSL_VERIFY_REQUIRED);

    // Set the CA certificate
    mbedtls_x509_crt ca_cert;
    mbedtls_x509_crt_init(&ca_cert);

    ret = mbedtls_x509_crt_parse(&ca_cert, (const unsigned char *)server_root_ca_pem, strlen(server_root_ca_pem) + 1);
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to parse CA certificate: -0x%04X", -ret);
        return ESP_FAIL;
    }

    mbedtls_ssl_conf_ca_chain(conf, &ca_cert, NULL);

    // Hybrid Encryption: Post-Quantum Key Exchange
    if (pq_keys_generated) {
        ESP_LOGI(TAG, "Performing hybrid key exchange...");
        // In a real scenario, the client would send its pq_public_key to the server.
        // The server would then use it to encapsulate a shared secret and send the
        // ciphertext back to the client. Here we simulate this process.

        uint8_t kyber_ciphertext[KYBER_CIPHERTEXT_SIZE];
        uint8_t kyber_shared_secret_enc[KYBER_SHARED_SECRET_SIZE];
        uint8_t kyber_shared_secret_dec[KYBER_SHARED_SECRET_SIZE];

        // 1. (Server side) Encapsulate a shared secret using the client's public key
        if (crypto_kem_enc(kyber_ciphertext, kyber_shared_secret_enc, pq_public_key) != 0) {
            ESP_LOGE(TAG, "Kyber encapsulation failed.");
            return ESP_FAIL;
        }

        // 2. (Client side) Decapsulate the shared secret using the private key
        if (crypto_kem_dec(kyber_shared_secret_dec, kyber_ciphertext, pq_secret_key) != 0) {
            ESP_LOGE(TAG, "Kyber decapsulation failed.");
            return ESP_FAIL;
        }

        // 3. Verify the shared secrets match
        if (memcmp(kyber_shared_secret_enc, kyber_shared_secret_dec, KYBER_SHARED_SECRET_SIZE) != 0) {
            ESP_LOGE(TAG, "Kyber shared secrets do not match!");
            return ESP_FAIL;
        }

        ESP_LOGI(TAG, "Kyber key exchange successful. Shared secret established.");
        // 4. Use the PQC shared secret to derive a key for a symmetric cipher,
        // which would then be used to encrypt the session. This part is complex
        // and would typically be handled by the TLS stack itself if it supported
        // hybrid KEMs. For now, we just log the success.
    }

    return ESP_OK;
}
