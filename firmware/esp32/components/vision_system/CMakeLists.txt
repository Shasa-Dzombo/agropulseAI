idf_component_register(SRCS "src/vision_system.c"
                    INCLUDE_DIRS "include"
                    REQUIRES camera_manager visual_intelligence gps_manager data_publisher)
