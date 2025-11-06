/**
 * @file secure_element.h
 * @brief An interface for a hardware secure element (e.g., ATECC608A).
 *
 * This component provides an abstraction layer for interacting with a
 * hardware secure element for cryptographic operations and secure key storage.
 *
 * Features:
 * - Initialization of the secure element.
 * - Secure storage and retrieval of the device's private key.
 * - Generation of a public key from the stored private key.
 * - Signing a digest (hash) using the private key.
 *
 * NOTE: This is a simulated driver. A real implementation would require
 *       integrating the specific SDK for the secure element hardware.
 */
#ifndef SECURE_ELEMENT_H
#define SECURE_ELEMENT_H

#include "esp_err.h"
#include <stdint.h>
#include <stddef.h>

/**
 * @brief Initializes the secure element.
 *
 * This function establishes communication with the secure element (e.g., over I2C)
 * and performs a health check.
 *
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: If the secure element cannot be contacted or initialized.
 */
esp_err_t secure_element_init(void);

/**
 * @brief Gets the public key from the secure element.
 *
 * This function commands the secure element to generate the public key
 * corresponding to a private key stored in a specific slot.
 *
 * @param[out] public_key Buffer to store the generated public key (e.g., 64 bytes for P256).
 * @param[in,out] key_size As input, the size of the buffer. As output, the actual size of the key.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t secure_element_get_public_key(uint8_t* public_key, size_t* key_size);

/**
 * @brief Signs a digest using a private key stored in the secure element.
 *
 * @param[in] digest The 32-byte hash (e.g., SHA-256) to be signed.
 * @param[out] signature Buffer to store the resulting ECDSA signature.
 * @param[in,out] sig_size As input, the size of the buffer. As output, the actual size of the signature.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t secure_element_sign_digest(const uint8_t* digest, uint8_t* signature, size_t* sig_size);

/**
 * @brief Gets the device's unique serial number from the secure element.
 *
 * @param[out] serial_number Buffer to store the serial number (typically 9 bytes).
 * @param[in] buf_size The size of the buffer.
 * @return
 *     - ESP_OK: On success.
 *     - ESP_FAIL: On failure.
 */
esp_err_t secure_element_get_serial_number(uint8_t* serial_number, size_t buf_size);

#endif // SECURE_ELEMENT_H
