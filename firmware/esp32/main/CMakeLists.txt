# CMakeLists.txt for the main component

idf_component_register(SRCS "main.c"
                    INCLUDE_DIRS "."
                                        REQUIRES core system protocols security edge_ai storage application actuators))
