# This CMakeLists.txt file is for the platform component.
# It uses the IDF_TARGET variable to conditionally compile the correct
# source file for the target hardware.

# The public interface is always the same, defined in the include directory.
idf_component_register(INCLUDE_DIRS "include")

# Conditionally add the source file based on the target.
# For any ESP32 variant, we use the esp32 implementation.
if(IDF_TARGET STREQUAL "esp32" OR IDF_TARGET STREQUAL "esp32s2" OR IDF_TARGET STREQUAL "esp32s3" OR IDF_TARGET STREQUAL "esp32c3")
    set(PLATFORM_SRC "src/esp32/platform_esp32.c")
    # The ESP32 implementation requires the secure_element_manager and nvs_flash
    set(PLATFORM_REQUIRES secure_element_manager nvs_flash)
    message(STATUS "Platform component: Compiling for ESP32 target.")
else()
    # For other targets (like native linux), we use the posix implementation.
    set(PLATFORM_SRC "src/posix/platform_posix.c")
    # The POSIX version might have different dependencies in the future.
    set(PLATFORM_REQUIRES "")
    message(STATUS "Platform component: Compiling for POSIX target.")
endif()

# Set the final source files and dependencies for the component registration.
idf_component_register(SRCS ${PLATFORM_SRC}
                    REQUIRES ${PLATFORM_REQUIRES})
