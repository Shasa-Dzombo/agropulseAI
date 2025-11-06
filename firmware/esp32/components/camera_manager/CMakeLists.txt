# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html

cmake_minimum_required(VERSION 3.5)

idf_component_register(SRCS "src/camera_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES app_config esp_camera)
