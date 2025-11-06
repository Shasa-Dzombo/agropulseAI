# For more information about this file, please visit:
# https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/build-system.html#component-cmakelists-files

idf_component_register(SRCS "symmetric-shake.c" "fips202.c" "cbd.c" "indcpa.c" "kem.c" "ntt.c" "poly.c" "polyvec.c" "reduce.c" "verify.c"
                    INCLUDE_DIRS "include"
                    REQUIRES mbedtls)
