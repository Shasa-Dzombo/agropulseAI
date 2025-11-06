/**
 * @file secure_element.c
 * @brief Simulated implementation of the secure element driver.
 */

#include "secure_element.h"
#include "esp_log.h"
#include "i2c_manager.h" // A real driver would use this

static const char *TAG = "SECURE_ELEMENT_SIM";
static bool is_initialized = false;

// In a real driver, you would include the vendor's library, e.g., "cryptoauthlib.h"

esp_err_t secure_element_init(void) {
    // A real driver would initialize the I2C interface and then
    // call the initialization function from the crypto library, e.g., atcab_init().
    
    ESP_LOGI(TAG, "Secure element driver initialized (simulated).");
    ESP_LOGI(TAG, "A real driver would now communicate with the crypto chip.");
    
    is_initialized = true;
    return ESP_OK;
}

esp_err_t secure_element_get_public_key(uint8_t* public_key, size_t* key_size) {
    if (!is_initialized || public_key == NULL || key_size == NULL || *key_size < 64) {
        return ESP_FAIL;
    }

    // Simulate generating a public key. A real driver would call e.g., atcab_get_pubkey().
    ESP_LOGI(TAG, "Generating public key (simulated).");
    const char* dummy_key = "This is a dummy 64-byte public key for simulation purposes only!!";
    memcpy(public_key, dummy_key, 64);
    *key_size = 64;

    return ESP_OK;
}

esp_err_t secure_element_sign_digest(const uint8_t* digest, uint8_t* signature, size_t* sig_size) {
    if (!is_initialized || digest == NULL || signature == NULL || sig_size == NULL || *sig_size < 64) {
        return ESP_FAIL;
    }

    // Simulate signing a digest. A real driver would call e.g., atcab_sign().
    ESP_LOGI(TAG, "Signing digest (simulated).");
    const char* dummy_sig = "This is a dummy 64-byte signature for simulation purposes only!!!";
    memcpy(signature, dummy_sig, 64);
    *sig_size = 64;

    return ESP_OK;
}

esp_err_t secure_element_get_serial_number(uint8_t* serial_number, size_t buf_size) {
    if (!is_initialized || serial_number == NULL || buf_size < 9) {
        return ESP_FAIL;
    }

    // Simulate reading the serial number. A real driver would call e.g., atcab_read_serial_number().
    ESP_LOGI(TAG, "Reading serial number (simulated).");
    const uint8_t dummy_serial[9] = {0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0xEE};
    memcpy(serial_number, dummy_serial, 9);

    return ESP_OK;
}
