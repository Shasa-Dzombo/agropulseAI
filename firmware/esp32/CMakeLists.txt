# Top-level CMakeLists.txt for AgroPulse ESP32 Firmware

# Minimum CMake version
cmake_minimum_required(VERSION 3.16)

# Include the ESP-IDF project build system
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# Add custom components directory
set(EXTRA_COMPONENT_DIRS
    ${CMAKE_CURRENT_LIST_DIR}/components/core
    ${CMAKE_CURRENT_LIST_DIR}/components/protocols
    ${CMAKE_CURRENT_LIST_DIR}/components/drivers
    ${CMAKE_CURRENT_LIST_DIR}/components/system
    ${CMAKE_CURRENT_LIST_DIR}/components/application
    ${CMAKE_CURRENT_LIST_DIR}/components/storage
    ${CMAKE_CURRENT_LIST_DIR}/components/edge_ai
    ${CMAKE_CURRENT_LIST_DIR}/components/security
    ${CMAKE_CURRENT_LIST_DIR}/components/ble
    ${CMAKE_CURRENT_LIST_DIR}/components/peripheral_manager
    ${CMAKE_CURRENT_LIST_DIR}/components/display
    ${CMAKE_CURRENT_LIST_DIR}/components/ui
    ${CMAKE_CURRENT_LIST_DIR}/components/diagnostics
    ${CMAKE_CURRENT_LIST_DIR}/components/command_registry
    ${CMAKE_CURRENT_LIST_DIR}/components/logging
)

# Project name
project(agropulse-firmware)

