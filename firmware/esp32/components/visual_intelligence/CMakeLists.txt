# For more information about build system see
# https://docs.espressif.com/projects/esp-idf/en/latest/api-guides/build-system.html

cmake_minimum_required(VERSION 3.5)

# This component requires TensorFlow Lite Micro.
# The ESP-IDF build system needs to know where to find it.
# This is typically handled by adding it as a component to your project,
# for example, by cloning it into the `components` directory.
# `idf.py add-dependency "espressif/tflite-micro"`

set(TFLITE_MICRO_DIR "${CMAKE_CURRENT_LIST_DIR}/../../tflite-micro")

idf_component_register(SRCS "src/visual_intelligence.c"
                    INCLUDE_DIRS "include"
                    REQUIRES model_manager esp_camera # Add other dependencies as needed
                    PRIV_REQUIRES tensorflow)
