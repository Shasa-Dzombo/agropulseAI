# CMakeLists for the system component

idf_component_register(SRCS "src/system_init.c"
                          "src/time_manager.c"
                          "src/http_client.c"
                          "src/ota_manager.c"
                          "src/task_watchdog.c"
                          "src/power_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core security esp_http_client esp_task_wdt)
