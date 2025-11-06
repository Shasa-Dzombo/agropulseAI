#include "platform.h"
#include <stdio.h>
#include <unistd.h>
#include <sys/sysinfo.h>
#include <sys/utsname.h>

// POSIX implementation of the Platform Abstraction Layer

esp_err_t platform_init(void) {
    // No specific init needed for POSIX
    return ESP_OK;
}

void platform_get_chip_info(platform_chip_info_t *info) {
    if (!info) return;
    struct utsname uts;
    uname(&uts);
    info->type = PLATFORM_TYPE_RASPBERRY_PI;
    info->model = uts.machine;
    info->cores = get_nprocs();
    info->revision = 0; // Not easily available
}

esp_err_t platform_get_unique_id(uint8_t *id_buf, size_t *len) {
    // Use host ID as a unique identifier
    if (*len < sizeof(long)) return ESP_ERR_NO_MEM;
    long hostid = gethostid();
    memcpy(id_buf, &hostid, sizeof(long));
    *len = sizeof(long);
    return ESP_OK;
}

void platform_reboot(void) {
    // This is a drastic measure on a Linux system
    sync();
    reboot(RB_AUTOBOOT);
}

size_t platform_get_free_heap_size(void) {
    // Not a direct equivalent, return free RAM
    struct sysinfo info;
    sysinfo(&info);
    return info.freeram;
}

int64_t platform_get_uptime_ms(void) {
    struct sysinfo info;
    sysinfo(&info);
    return info.uptime * 1000;
}
