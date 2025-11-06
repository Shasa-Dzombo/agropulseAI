# CMakeLists for the security component

idf_component_register(SRCS "src/security_init.c"
                          "src/secure_element.c"
                          "src/ota_verifier.c"
                          "src/security_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core mbedtls nvs_flash)
