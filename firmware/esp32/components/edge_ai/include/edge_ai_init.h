/**
 * @file edge_ai_init.h
 * @brief Header for the Edge AI services initialization.
 */
#ifndef EDGE_AI_INIT_H
#define EDGE_AI_INIT_H

#include "esp_err.h"

/**
 * @brief Initializes all Edge AI services.
 *
 * This function orchestrates the initialization of AI-related services,
 * such as the inference engine and data preprocessor.
 *
 * @return
 *     - ESP_OK: If all services were initialized successfully.
 *     - ESP_FAIL: If any of the services failed to initialize.
 */
esp_err_t edge_ai_services_initialize(void);

#endif // EDGE_AI_INIT_H
