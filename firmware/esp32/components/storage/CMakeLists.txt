# CMakeLists for the storage component

idf_component_register(SRCS "src/storage_init.c"
                          "src/spiffs_manager.c"
                          "src/data_logger.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core)
