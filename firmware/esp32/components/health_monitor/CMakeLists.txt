idf_component_register(SRCS "src/health_monitor.c"
                    INCLUDE_DIRS "include"
                    REQUIRES app_config mqtt_client cJSON time_manager wifi_manager)
