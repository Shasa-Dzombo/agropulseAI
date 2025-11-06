#ifndef SECURITY_MANAGER_H
#define SECURITY_MANAGER_H

#include "esp_err.h"
#include "mbedtls/pk.h"

/**
 * @brief Initializes the security manager.
 * 
 * This function checks for the existence of a device private key in NVS.
 * If the key does not exist, it generates a new one and saves it.
 * 
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t security_manager_init(void);

/**
 * @brief Gets the device's public key in PEM format.
 * 
 * The caller is responsible for freeing the returned buffer.
 * 
 * @param[out] pem_buffer A pointer to a buffer that will be allocated and filled with the PEM string.
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t security_manager_get_public_key_pem(char** pem_buffer);

/**
 * @brief Signs a SHA-256 digest with the device's private key.
 * 
 * @param[in] digest The 32-byte SHA-256 hash to be signed.
 * @param[out] signature_buffer A buffer to store the generated signature.
 * @param[in,out] signature_size On input, the size of the buffer. On output, the actual size of the signature.
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t security_manager_sign_digest(const uint8_t* digest, uint8_t* signature_buffer, size_t* signature_size);

/**
 * @brief Verifies a signature against a SHA-256 digest using a given public key.
 * 
 * @param[in] digest The 32-byte SHA-256 hash.
 * @param[in] signature The signature to verify.
 * @param[in] signature_len The length of the signature.
 * @param[in] pub_key_pem The public key in PEM format to use for verification.
 * @return ESP_OK if the signature is valid, ESP_FAIL or other error codes if not.
 */
esp_err_t security_manager_verify_signature(const uint8_t* digest, const uint8_t* signature, size_t signature_len, const char* pub_key_pem);

/**
 * @brief Generates a JSON Web Token (JWT) for cloud authentication.
 * 
 * The caller is responsible for freeing the returned buffer.
 * 
 * @param[in] project_id The cloud project ID (e.g., Google Cloud project).
 * @param[out] jwt_buffer A pointer to a buffer that will be allocated and filled with the JWT string.
 * @param[in] expiry_minutes The lifetime of the token in minutes.
 * @return ESP_OK on success, or an error code on failure.
 */
esp_err_t security_manager_generate_jwt(const char* project_id, uint32_t expiry_minutes, char** jwt_buffer);


#endif // SECURITY_MANAGER_H
