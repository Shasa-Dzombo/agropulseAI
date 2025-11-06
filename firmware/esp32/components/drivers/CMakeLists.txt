# CMakeLists for the drivers component

idf_component_register(SRCS "src/bme280_driver.c"
                          "src/bh1750_driver.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core)
