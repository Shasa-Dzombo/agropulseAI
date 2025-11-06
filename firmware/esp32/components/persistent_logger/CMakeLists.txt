idf_component_register(SRCS "src/persistent_logger.c"
                    INCLUDE_DIRS "include"
                    REQUIRES storage_manager mqtt_client app_config)
