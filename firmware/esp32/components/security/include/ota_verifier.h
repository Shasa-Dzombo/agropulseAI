/**
 * @file ota_verifier.h
 * @brief Handles signature verification for Over-the-Air (OTA) updates.
 *
 * This component provides a hook into the ESP-IDF OTA process to verify
 * the cryptographic signature of a new firmware image before it is activated.
 *
 * Features:
 * - Initializes the verification process.
 * - Provides a function to verify a firmware image against a signature.
 * - Uses the public key from the secure element to perform the verification.
 */
#ifndef OTA_VERIFIER_H
#define OTA_VERIFIER_H

#include "esp_err.h"
#include "esp_app_format.h"

/**
 * @brief Initializes the OTA verifier.
 *
 * @return
 *     - ESP_OK: On success.
 */
esp_err_t ota_verifier_init(void);

/**
 * @brief Verifies the signature of an OTA firmware image.
 *
 * This function calculates the hash of the provided firmware image and
 * uses a public key to verify the provided signature.
 *
 * @param[in] image_data Pointer to the firmware image data.
 * @param[in] image_size Size of the firmware image.
 * @param[in] signature Pointer to the signature of the image.
 * @param[in] signature_size Size of the signature.
 * @return
 *     - ESP_OK: If the signature is valid.
 *     - ESP_ERR_INVALID_SIGNATURE: If the signature is invalid.
 *     - ESP_FAIL: For other failures.
 */
esp_err_t ota_verifier_verify_image(const void* image_data, size_t image_size, const void* signature, size_t signature_size);

/**
 * @brief A more integrated function to verify an app partition.
 *
 * This function finds an OTA partition, calculates its hash, and verifies
 * its signature, which is typically appended to the image.
 *
 * @param[in] partition Pointer to the partition to verify.
 * @return
 *     - ESP_OK: If the signature is valid.
 *     - ESP_ERR_INVALID_SIGNATURE: If the signature is invalid.
 *     - ESP_FAIL: For other failures.
 */
esp_err_t ota_verifier_verify_partition(const esp_partition_t *partition);

#endif // OTA_VERIFIER_H
