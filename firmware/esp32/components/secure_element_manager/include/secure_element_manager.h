#ifndef SECURE_ELEMENT_MANAGER_H
#define SECURE_ELEMENT_MANAGER_H

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

/**
 * @brief Initializes the ATECC608A secure element.
 *
 * This function establishes the I2C communication with the secure element,
 * checks its status, and prepares it for cryptographic operations.
 * It should be called once during the device boot sequence.
 *
 * @return ESP_OK on successful initialization, or an error code otherwise.
 */
esp_err_t secure_element_manager_init(void);

/**
 * @brief Deinitializes the ATECC608A secure element.
 *
 * Releases resources used by the secure element manager.
 */
void secure_element_manager_deinit(void);

/**
 * @brief Gets the device's unique serial number from the secure element.
 *
 * The ATECC608A contains a factory-provisioned, globally unique 9-byte serial number.
 * This is the most reliable way to identify a device.
 *
 * @param serial_number Buffer to store the 9-byte serial number.
 * @param len Pointer to a size_t variable, which should be at least 9.
 *            On successful return, it will contain the number of bytes written.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t secure_element_manager_get_serial_number(uint8_t *serial_number, size_t *len);

/**
 * @brief Generates a new private key in a specified slot.
 *
 * This function commands the ATECC608A to generate a new ECC P256 private key
 * and store it internally in one of its 16 slots. The private key can never
 * be extracted from the device.
 *
 * @param slot The slot number (0-15) where the key should be generated.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t secure_element_manager_gen_key(uint8_t slot);

/**
 * @brief Gets the public key corresponding to a private key in a slot.
 *
 * This function derives the public key from the private key stored in the
 * specified slot and returns it.
 *
 * @param slot The slot number (0-15) of the private key.
 * @param public_key Buffer to store the 64-byte public key (X and Y coordinates).
 * @param len Pointer to a size_t variable, should be at least 64.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t secure_element_manager_get_public_key(uint8_t slot, uint8_t *public_key, size_t *len);

/**
 * @brief Performs an ECDSA sign operation.
 *
 * This function uses a private key stored in the secure element to sign a
 * 32-byte message digest (e.g., a SHA-256 hash).
 *
 * @param slot The slot number (0-15) of the private key to use for signing.
 * @param message_digest A 32-byte buffer containing the hash to be signed.
 * @param signature Buffer to store the resulting 64-byte ECDSA signature.
 * @param len Pointer to a size_t variable, should be at least 64.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t secure_element_manager_sign(uint8_t slot, const uint8_t *message_digest, uint8_t *signature, size_t *len);

/**
 * @brief Performs an ECDH (Elliptic Curve Diffie-Hellman) key agreement.
 *
 * This function uses a private key from a slot and a peer's public key to
 * generate a shared secret.
 *
 * @param slot The slot number (0-15) of the private key to use.
 * @param peer_public_key The 64-byte public key of the other party.
 * @param shared_secret Buffer to store the resulting 32-byte shared secret.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t secure_element_manager_ecdh(uint8_t slot, const uint8_t *peer_public_key, uint8_t *shared_secret);

#endif // SECURE_ELEMENT_MANAGER_H
