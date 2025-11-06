# CMakeLists for the actuators component

idf_component_register(SRCS "src/actuator_control.c"
                          "src/water_pump_controller.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core application protocols)
