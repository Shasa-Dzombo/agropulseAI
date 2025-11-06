idf_component_register(SRCS "security_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES nvs_flash secure_element_manager mbedtls)
