# CMakeLists for the protocols component

# This tells the build system to embed the web content into the binary
target_add_binary_data(
    ${COMPONENT_TARGET}
    "web_content/index.html"
    TEXT
)

idf_component_register(SRCS "src/protocol_init.c"
                          "src/wifi_manager.c"
                          "src/mqtt_client.c"
                          "src/http_server.c"
                          "src/dns_server.c"
                          "src/ble_manager.c"
                    INCLUDE_DIRS "include" "web_content"
                    REQUIRES core system mqtt esp_http_server)
