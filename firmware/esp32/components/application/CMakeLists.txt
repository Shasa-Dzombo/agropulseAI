# CMakeLists for the application component

idf_component_register(SRCS "src/application_init.c"
                          "src/sensor_sampler.c"
                          "src/data_publisher.c"
                          "src/command_processor.c"
                          "src/status_publisher.c"
                          "src/device_shadow.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core protocols drivers edge_ai storage actuators system)
