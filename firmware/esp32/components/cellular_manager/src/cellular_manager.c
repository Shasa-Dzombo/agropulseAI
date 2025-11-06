#include "cellular_manager.h"
#include "esp_log.h"
#include "esp_modem.h"
#include "esp_modem_dce_service.h"
#include "esp_netif.h"
#include "driver/gpio.h"

static const char *TAG = "CELLULAR_MGR";

// Modem configuration (assuming a SIM7600 module connected via UART)
#define MODEM_UART_TX_PIN   (GPIO_NUM_26)
#define MODEM_UART_RX_PIN   (GPIO_NUM_25)
#define MODEM_PWRKEY_PIN    (GPIO_NUM_4)
#define MODEM_DTR_PIN       (GPIO_NUM_32)
#define MODEM_RI_PIN        (GPIO_NUM_33)

static esp_netif_t *ppp_netif = NULL;
static modem_dce_t *dce = NULL;

static void on_ppp_changed(void *arg, esp_event_base_t event_base,
                           int32_t event_id, void *event_data)
{
    if (event_id == IP_EVENT_PPP_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Cellular PPP connection established.");
        // Post a generic network connected event
        // event_bus_post(NETWORK_EVENT, NETWORK_EVENT_CONNECTED, ...);
    } else if (event_id == IP_EVENT_PPP_LOST_IP) {
        ESP_LOGW(TAG, "Cellular PPP connection lost.");
        // Post a generic network disconnected event
        // event_bus_post(NETWORK_EVENT, NETWORK_EVENT_DISCONNECTED, ...);
    }
}

esp_err_t cellular_manager_init(void) {
    // Initialize the underlying TCP/IP stack
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID, &on_ppp_changed, NULL));

    // Create the PPP network interface
    esp_netif_config_t netif_config = ESP_NETIF_DEFAULT_PPP();
    ppp_netif = esp_netif_new(&netif_config);
    assert(ppp_netif);

    // Configure the modem UART
    modem_uart_config_t uart_config = {
        .port_num = UART_NUM_1,
        .tx_io_num = MODEM_UART_TX_PIN,
        .rx_io_num = MODEM_UART_RX_PIN,
        .rx_buffer_size = 1024,
        .tx_buffer_size = 512,
        .event_queue_size = 30,
        .event_task_stack_size = 2048,
        .event_task_priority = 5,
    };

    // Configure the modem DCE
    modem_dce_config_t dce_config = MODEM_DCE_DEFAULT_CONFIG("internet"); // APN

    // Create the DTE (Data Terminal Equipment)
    modem_dte_config_t dte_config = MODEM_DTE_DEFAULT_CONFIG();
    dte_config.uart_config = uart_config;
    modem_dte_t *dte = esp_modem_dte_init(&dte_config);
    assert(dte);

    // Create the DCE (Data Circuit-terminating Equipment)
    dce = esp_modem_dce_init(&dce_config);
    assert(dce);

    // Set up the PPP interface
    esp_modem_set_netif(dce, ppp_netif);

    ESP_LOGI(TAG, "Cellular manager initialized.");
    return ESP_OK;
}

esp_err_t cellular_manager_start(void) {
    if (!dce) return ESP_ERR_INVALID_STATE;
    // In a real implementation, you would handle modem power-on sequences here.
    ESP_LOGI(TAG, "Starting cellular data connection...");
    return esp_modem_start_ppp(dce);
}

esp_err_t cellular_manager_stop(void) {
    if (!dce) return ESP_ERR_INVALID_STATE;
    ESP_LOGI(TAG, "Stopping cellular data connection...");
    return esp_modem_stop_ppp(dce);
}

esp_err_t cellular_manager_get_signal_quality(int *rssi) {
    if (!dce || !rssi) return ESP_ERR_INVALID_ARG;
    return esp_modem_get_signal_quality(dce, rssi);
}
