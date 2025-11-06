#include "secure_element_manager.h"
#include "esp_log.h"
#include "cryptoauthlib.h"
#include "atca_hal.h"
#include "atca_device.h"
#include "atca_basic.h"
#include "hal/atca_hal.h"

static const char *TAG = "SECURE_ELEMENT";

// The global configuration for the ATECC608A device.
// This is required by the cryptoauthlib library.
ATCAIfaceCfg cfg = {
    .iface_type             = ATCA_I2C_IFACE,
    .devtype                = ATECC608A,
    .atcai2c.slave_address  = 0xC0, // Default ATECC608A I2C address
    .atcai2c.bus            = 1,    // Default I2C bus for ESP32
    .atcai2c.baud           = 400000, // 400 KHz
    .wake_delay             = 1500,
    .rx_retries             = 20
};

esp_err_t secure_element_manager_init(void) {
    ATCA_STATUS status = atcab_init(&cfg);

    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to initialize cryptoauthlib. Status: 0x%02X", status);
        return ESP_FAIL;
    }

    uint8_t revision[4];
    status = atcab_info(revision);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to get device info. Status: 0x%02X", status);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "ATECC608A Initialized Successfully. Revision: %02X %02X %02X %02X",
             revision[0], revision[1], revision[2], revision[3]);

    return ESP_OK;
}

void secure_element_manager_deinit(void) {
    atcab_release();
    ESP_LOGI(TAG, "Secure element released.");
}

esp_err_t secure_element_manager_get_serial_number(uint8_t *serial_number, size_t *len) {
    if (!serial_number || !len || *len < ATCA_SERIAL_NUM_SIZE) {
        return ESP_ERR_INVALID_ARG;
    }

    ATCA_STATUS status = atcab_read_serial_number(serial_number);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to read serial number. Status: 0x%02X", status);
        return ESP_FAIL;
    }

    *len = ATCA_SERIAL_NUM_SIZE;
    return ESP_OK;
}

esp_err_t secure_element_manager_gen_key(uint8_t slot) {
    ATCA_STATUS status = atcab_genkey(slot, NULL);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to generate key in slot %d. Status: 0x%02X", slot, status);
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "Successfully generated new private key in slot %d.", slot);
    return ESP_OK;
}

esp_err_t secure_element_manager_get_public_key(uint8_t slot, uint8_t *public_key, size_t *len) {
    if (!public_key || !len || *len < ATCA_PUB_KEY_SIZE) {
        return ESP_ERR_INVALID_ARG;
    }

    ATCA_STATUS status = atcab_get_pubkey(slot, public_key);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to get public key from slot %d. Status: 0x%02X", slot, status);
        return ESP_FAIL;
    }

    *len = ATCA_PUB_KEY_SIZE;
    return ESP_OK;
}

esp_err_t secure_element_manager_sign(uint8_t slot, const uint8_t *message_digest, uint8_t *signature, size_t *len) {
    if (!message_digest || !signature || !len || *len < ATCA_SIG_SIZE) {
        return ESP_ERR_INVALID_ARG;
    }

    ATCA_STATUS status = atcab_sign(slot, message_digest, signature);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to sign message with key in slot %d. Status: 0x%02X", slot, status);
        return ESP_FAIL;
    }

    *len = ATCA_SIG_SIZE;
    return ESP_OK;
}

esp_err_t secure_element_manager_ecdh(uint8_t slot, const uint8_t *peer_public_key, uint8_t *shared_secret) {
    if (!peer_public_key || !shared_secret) {
        return ESP_ERR_INVALID_ARG;
    }

    ATCA_STATUS status = atcab_ecdh(slot, peer_public_key, shared_secret);
    if (status != ATCA_SUCCESS) {
        ESP_LOGE(TAG, "Failed to perform ECDH. Status: 0x%02X", status);
        return ESP_FAIL;
    }

    return ESP_OK;
}
