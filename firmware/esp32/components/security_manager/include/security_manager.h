#ifndef SECURITY_MANAGER_H
#define SECURITY_MANAGER_H

#include "esp_err.h"
#include "esp_tls.h"

// Define the slot in the ATECC608A where the device's private key is stored.
#define DEVICE_PRIVATE_KEY_SLOT 0

/**
 * @brief Initializes the security manager.
 *
 * This function checks if a device certificate exists. If not, it will
 * generate a new private key in the secure element (if needed) and create
 * a Certificate Signing Request (CSR) to be sent to a Certificate Authority.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t security_manager_init(void);

/**
 * @brief Generates a Certificate Signing Request (CSR).
 *
 * Creates a CSR using the private key stored in the secure element. The CSR
 * can then be sent to a Certificate Authority (CA) to obtain a signed
 * device certificate. The output is in PEM format.
 *
 * @param csr_buf Buffer to store the PEM-formatted CSR.
 * @param csr_buf_len Size of the CSR buffer.
 * @param csr_len Pointer to a size_t to store the actual length of the generated CSR.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t security_manager_generate_csr(char *csr_buf, size_t csr_buf_len, size_t *csr_len);

/**
 * @brief Stores the device certificate in persistent storage.
 *
 * This function should be called after a signed certificate is received from
 * the CA. It stores the certificate in NVS for later use.
 *
 * @param cert_pem The PEM-formatted device certificate.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t security_manager_store_certificate(const char *cert_pem);

/**
 * @brief Gets the device certificate from storage.
 *
 * Retrieves the stored device certificate from NVS.
 *
 * @param cert_buf Buffer to store the PEM-formatted certificate.
 * @param cert_buf_len Size of the certificate buffer.
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if no certificate is stored,
 *         or another error code.
 */
esp_err_t security_manager_get_certificate(char *cert_buf, size_t cert_buf_len);

/**
 * @brief Creates an esp_tls_cfg_t structure for mTLS using the secure element.
 *
 * This is the key function for enabling mTLS. It configures a TLS connection
 * to use the device certificate and sets up callbacks to the secure element
 * for private key operations (signing) during the TLS handshake.
 *
 * @param server_root_ca_pem The PEM-formatted root CA certificate of the server.
 * @param esp_tls_cfg Pointer to an esp_tls_cfg_t structure to be configured.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t security_manager_get_mtls_config(const char *server_root_ca_pem, esp_tls_cfg_t *esp_tls_cfg);


#endif // SECURITY_MANAGER_H
