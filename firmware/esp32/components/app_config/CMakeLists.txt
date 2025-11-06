# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html

cmake_minimum_required(VERSION 3.5)

idf_component_register(SRCS "src/app_config.c"
                    INCLUDE_DIRS "include"
                    REQUIRES config_manager_v2)
