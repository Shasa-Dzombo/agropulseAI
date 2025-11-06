/**
 * @file dns_server.c
 * @brief Implementation of the simple DNS server for the captive portal.
 */

#include "dns_server.h"
#include "esp_log.h"
#include "lwip/sockets.h"
#include "lwip/dns.h"

static const char *TAG = "DNS_SERVER";
#define DNS_PORT 53
static int udp_socket = -1;
static TaskHandle_t dns_task_handle = NULL;

// DNS Header Structure
typedef struct {
    uint16_t id;
    uint16_t flags;
    uint16_t qdcount;
    uint16_t ancount;
    uint16_t nscount;
    uint16_t arcount;
} dns_header_t;

static void dns_server_task(void *pvParameters) {
    uint8_t rx_buffer[128];
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);

    while (1) {
        int len = recvfrom(udp_socket, rx_buffer, sizeof(rx_buffer), 0, (struct sockaddr *)&client_addr, &client_addr_len);
        if (len < 0) {
            ESP_LOGE(TAG, "recvfrom failed: errno %d", errno);
            break;
        }

        dns_header_t *header = (dns_header_t *)rx_buffer;
        // Check if it's a standard query
        if ((header->flags & 0x8000) == 0 && header->qdcount > 0) {
            header->flags |= htons(0x8000 | 0x0400); // Standard response, authoritative answer
            header->ancount = header->qdcount;

            // Find the end of the question section
            uint8_t *query_end = rx_buffer + sizeof(dns_header_t);
            while (*query_end != 0) {
                query_end += (*query_end + 1);
            }
            query_end += 5; // Skip null terminator and QTYPE/QCLASS

            // Build the answer
            uint8_t *p = query_end;
            *p++ = 0xC0; // Pointer to the name in the query
            *p++ = 0x0C;
            *p++ = 0x00; // Type A
            *p++ = 0x01;
            *p++ = 0x00; // Class IN
            *p++ = 0x01;
            *p++ = 0x00; // TTL (4 bytes)
            *p++ = 0x00;
            *p++ = 0x00;
            *p++ = 0x78; // 120 seconds
            *p++ = 0x00; // RDLENGTH (2 bytes)
            *p++ = 0x04;
            
            // The IP address to return (AP's IP)
            *p++ = 192;
            *p++ = 168;
            *p++ = 4;
            *p++ = 1;

            sendto(udp_socket, rx_buffer, (p - rx_buffer), 0, (struct sockaddr *)&client_addr, client_addr_len);
        }
    }
    vTaskDelete(NULL);
}

esp_err_t dns_server_start(void) {
    udp_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (udp_socket < 0) {
        ESP_LOGE(TAG, "Failed to create socket");
        return ESP_FAIL;
    }

    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(DNS_PORT);

    if (bind(udp_socket, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "Failed to bind socket");
        close(udp_socket);
        udp_socket = -1;
        return ESP_FAIL;
    }

    xTaskCreate(dns_server_task, "dns_server", 3072, NULL, 5, &dns_task_handle);
    ESP_LOGI(TAG, "DNS server started.");
    return ESP_OK;
}

void dns_server_stop(void) {
    if (dns_task_handle) {
        vTaskDelete(dns_task_handle);
        dns_task_handle = NULL;
    }
    if (udp_socket >= 0) {
        close(udp_socket);
        udp_socket = -1;
    }
    ESP_LOGI(TAG, "DNS server stopped.");
}
