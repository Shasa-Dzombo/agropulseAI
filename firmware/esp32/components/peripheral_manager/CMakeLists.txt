#
# Component Makefile
#
set(COMPONENT_SRCS "src/peripheral_manager.c" "src/peripheral_init.c")
set(COMPONENT_ADD_INCLUDEDIRS "include")

# Add dependencies to other components
set(COMPONENT_REQUIRES core)

