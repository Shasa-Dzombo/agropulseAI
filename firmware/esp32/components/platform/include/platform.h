#ifndef PLATFORM_H
#define PLATFORM_H

#include "esp_err.h"
#include <stdint.h>
#include <stddef.h>

/**
 * @brief Defines the supported hardware platforms.
 */
typedef enum {
    PLATFORM_TYPE_UNKNOWN,
    PLATFORM_TYPE_ESP32,
    PLATFORM_TYPE_RASPBERRY_PI,
} platform_type_t;

/**
 * @brief Structure to hold information about the chip/SoC.
 */
typedef struct {
    platform_type_t type;
    const char* model;
    uint8_t cores;
    uint32_t revision;
} platform_chip_info_t;

/**
 * @brief Initializes the platform abstraction layer.
 *
 * This function performs any necessary platform-specific setup and should be
 * one of the first functions called on boot.
 *
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t platform_init(void);

/**
 * @brief Gets detailed information about the underlying hardware.
 *
 * @param info Pointer to a platform_chip_info_t struct to be filled.
 */
void platform_get_chip_info(platform_chip_info_t *info);

/**
 * @brief Gets a unique identifier for the device.
 *
 * This could be a MAC address, a CPU serial number, or an ID from a
 * secure element, depending on the platform.
 *
 * @param id_buf Buffer to store the unique ID.
 * @param len Size of the buffer. On return, contains the length of the ID.
 * @return ESP_OK on success, or an error code otherwise.
 */
esp_err_t platform_get_unique_id(uint8_t *id_buf, size_t *len);

/**
 * @brief Reboots the device.
 */
void platform_reboot(void);

/**
 * @brief Gets the current free heap memory in bytes.
 *
 * @return The number of free bytes.
 */
size_t platform_get_free_heap_size(void);

/**
 * @brief Gets the system uptime in milliseconds.
 *
 * @return Uptime in milliseconds.
 */
int64_t platform_get_uptime_ms(void);

#endif // PLATFORM_H
