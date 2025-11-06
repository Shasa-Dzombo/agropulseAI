#ifndef SECURE_LOGGER_H
#define SECURE_LOGGER_H

#include "esp_err.h"

esp_err_t secure_logger_init(void);
esp_err_t secure_logger_log(const char* message);

#endif // SECURE_LOGGER_H
