# CMakeLists for the edge_ai component

idf_component_register(SRCS "src/edge_ai_init.c"
                          "src/inference_engine.c"
                          "src/preprocessor.c"
                          "src/model_manager.c"
                    INCLUDE_DIRS "include"
                    REQUIRES core application storage)
