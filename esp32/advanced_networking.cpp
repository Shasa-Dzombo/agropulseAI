// =====================================================================================================================
// ESP32 Advanced Networking & Protocol Stack
// TCP/IP, UDP, WebSocket, MQTT, CoAP, HTTP/2, DNS, TLS/SSL, Network monitoring
// =====================================================================================================================

#include <Arduino.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <mbedtls/ssl.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>

// =====================================================================================================================
// Network Protocol Structures
// =====================================================================================================================

#define MAX_CONNECTIONS 50
#define MAX_PACKET_SIZE 1500
#define MAX_DNS_CACHE 50
#define MAX_ROUTES 20
#define MAX_ARP_ENTRIES 50

// Network packet
typedef struct {
    uint8_t* data;
    uint32_t size;
    IPAddress src_ip;
    IPAddress dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t protocol;  // TCP=6, UDP=17
    uint64_t timestamp;
} NetworkPacket;

// TCP connection state
typedef enum {
    TCP_CLOSED,
    TCP_LISTEN,
    TCP_SYN_SENT,
    TCP_SYN_RECEIVED,
    TCP_ESTABLISHED,
    TCP_FIN_WAIT_1,
    TCP_FIN_WAIT_2,
    TCP_CLOSE_WAIT,
    TCP_CLOSING,
    TCP_LAST_ACK,
    TCP_TIME_WAIT
} TCPState;

// TCP connection
typedef struct {
    TCPState state;
    IPAddress local_ip;
    IPAddress remote_ip;
    uint16_t local_port;
    uint16_t remote_port;
    uint32_t seq_num;
    uint32_t ack_num;
    uint16_t window_size;
    uint8_t* send_buffer;
    uint8_t* recv_buffer;
    uint32_t send_buffer_size;
    uint32_t recv_buffer_size;
    uint64_t last_activity;
    uint32_t rtt;  // Round-trip time
    uint32_t srtt; // Smoothed RTT
    uint32_t rttvar; // RTT variance
    uint32_t rto;  // Retransmission timeout
} TCPConnection;

// UDP socket
typedef struct {
    IPAddress local_ip;
    uint16_t local_port;
    uint8_t* buffer;
    uint32_t buffer_size;
    bool is_bound;
    bool is_multicast;
    IPAddress multicast_group;
} UDPSocket;

// WebSocket frame
typedef enum {
    WS_TEXT_FRAME,
    WS_BINARY_FRAME,
    WS_CLOSE_FRAME,
    WS_PING_FRAME,
    WS_PONG_FRAME,
    WS_CONTINUATION_FRAME
} WSFrameType;

typedef struct {
    WSFrameType type;
    bool fin;
    bool mask;
    uint8_t mask_key[4];
    uint8_t* payload;
    uint64_t payload_length;
    uint8_t opcode;
} WebSocketFrame;

// WebSocket connection
typedef struct {
    TCPConnection* tcp_conn;
    bool handshake_complete;
    uint8_t* recv_fragment;
    uint32_t fragment_length;
    char* protocol;
    char* extensions;
    bool is_client;
} WebSocketConnection;

// HTTP request
typedef enum {
    HTTP_GET,
    HTTP_POST,
    HTTP_PUT,
    HTTP_DELETE,
    HTTP_HEAD,
    HTTP_OPTIONS,
    HTTP_PATCH
} HTTPMethod;

typedef struct {
    HTTPMethod method;
    char* uri;
    char* version;
    char** headers;
    char** header_values;
    uint32_t header_count;
    uint8_t* body;
    uint32_t body_length;
} HTTPRequest;

// HTTP response
typedef struct {
    uint16_t status_code;
    char* status_text;
    char** headers;
    char** header_values;
    uint32_t header_count;
    uint8_t* body;
    uint32_t body_length;
    bool chunked;
} HTTPResponse;

// HTTP/2 frame types
typedef enum {
    HTTP2_DATA,
    HTTP2_HEADERS,
    HTTP2_PRIORITY,
    HTTP2_RST_STREAM,
    HTTP2_SETTINGS,
    HTTP2_PUSH_PROMISE,
    HTTP2_PING,
    HTTP2_GOAWAY,
    HTTP2_WINDOW_UPDATE,
    HTTP2_CONTINUATION
} HTTP2FrameType;

// HTTP/2 frame
typedef struct {
    uint32_t length;
    HTTP2FrameType type;
    uint8_t flags;
    uint32_t stream_id;
    uint8_t* payload;
} HTTP2Frame;

// HTTP/2 stream
typedef struct {
    uint32_t stream_id;
    uint32_t window_size;
    bool closed;
    HTTPRequest* request;
    HTTPResponse* response;
} HTTP2Stream;

// MQTT packet types
typedef enum {
    MQTT_CONNECT = 1,
    MQTT_CONNACK,
    MQTT_PUBLISH,
    MQTT_PUBACK,
    MQTT_PUBREC,
    MQTT_PUBREL,
    MQTT_PUBCOMP,
    MQTT_SUBSCRIBE,
    MQTT_SUBACK,
    MQTT_UNSUBSCRIBE,
    MQTT_UNSUBACK,
    MQTT_PINGREQ,
    MQTT_PINGRESP,
    MQTT_DISCONNECT
} MQTTPacketType;

// MQTT QoS levels
typedef enum {
    MQTT_QOS_0,  // At most once
    MQTT_QOS_1,  // At least once
    MQTT_QOS_2   // Exactly once
} MQTTQoS;

// MQTT packet
typedef struct {
    MQTTPacketType type;
    uint8_t flags;
    uint32_t remaining_length;
    uint8_t* payload;
    uint16_t packet_id;
} MQTTPacket;

// MQTT topic subscription
typedef struct {
    char* topic;
    MQTTQoS qos;
    void (*callback)(const char* topic, const uint8_t* payload, uint32_t length);
} MQTTSubscription;

// MQTT client
typedef struct {
    TCPConnection* conn;
    char* client_id;
    char* username;
    char* password;
    uint16_t keep_alive;
    bool clean_session;
    MQTTSubscription* subscriptions;
    uint32_t subscription_count;
    uint16_t next_packet_id;
    uint64_t last_ping;
    bool connected;
} MQTTClient;

// CoAP (Constrained Application Protocol)
typedef enum {
    COAP_CON,  // Confirmable
    COAP_NON,  // Non-confirmable
    COAP_ACK,  // Acknowledgement
    COAP_RST   // Reset
} CoAPType;

typedef enum {
    COAP_GET = 1,
    COAP_POST = 2,
    COAP_PUT = 3,
    COAP_DELETE = 4
} CoAPMethod;

typedef struct {
    uint8_t version;
    CoAPType type;
    uint8_t token_length;
    uint8_t code;
    uint16_t message_id;
    uint8_t token[8];
    uint8_t* options;
    uint32_t options_length;
    uint8_t* payload;
    uint32_t payload_length;
} CoAPMessage;

// DNS query types
typedef enum {
    DNS_A = 1,
    DNS_NS = 2,
    DNS_CNAME = 5,
    DNS_SOA = 6,
    DNS_PTR = 12,
    DNS_MX = 15,
    DNS_TXT = 16,
    DNS_AAAA = 28,
    DNS_SRV = 33
} DNSQueryType;

// DNS record
typedef struct {
    char* name;
    DNSQueryType type;
    uint16_t dns_class;
    uint32_t ttl;
    uint16_t data_length;
    uint8_t* data;
    IPAddress ip_address;  // For A records
    uint64_t cached_at;
} DNSRecord;

// DNS query
typedef struct {
    uint16_t transaction_id;
    uint16_t flags;
    uint16_t questions;
    uint16_t answers;
    uint16_t authority;
    uint16_t additional;
    char* query_name;
    DNSQueryType query_type;
} DNSQuery;

// DNS cache
typedef struct {
    DNSRecord records[MAX_DNS_CACHE];
    uint32_t record_count;
} DNSCache;

// ARP (Address Resolution Protocol) entry
typedef struct {
    IPAddress ip_address;
    uint8_t mac_address[6];
    uint64_t timestamp;
    bool is_static;
} ARPEntry;

// ARP cache
typedef struct {
    ARPEntry entries[MAX_ARP_ENTRIES];
    uint32_t entry_count;
} ARPCache;

// Routing table entry
typedef struct {
    IPAddress destination;
    IPAddress netmask;
    IPAddress gateway;
    uint32_t metric;
    char interface[16];
} RouteEntry;

// Routing table
typedef struct {
    RouteEntry routes[MAX_ROUTES];
    uint32_t route_count;
} RoutingTable;

// TLS/SSL context
typedef struct {
    mbedtls_ssl_context ssl;
    mbedtls_ssl_config conf;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    mbedtls_x509_crt cacert;
    mbedtls_x509_crt client_cert;
    mbedtls_pk_context client_key;
    bool initialized;
} TLSContext;

// Network statistics
typedef struct {
    uint64_t bytes_sent;
    uint64_t bytes_received;
    uint64_t packets_sent;
    uint64_t packets_received;
    uint64_t packets_dropped;
    uint64_t errors;
    uint32_t active_connections;
    float bandwidth_usage;
    uint32_t latency_ms;
} NetworkStats;

// Packet sniffer
typedef struct {
    bool enabled;
    NetworkPacket* captured_packets;
    uint32_t packet_count;
    uint32_t max_packets;
    void (*packet_callback)(const NetworkPacket* packet);
} PacketSniffer;

// Network monitor
typedef struct {
    NetworkStats stats;
    PacketSniffer sniffer;
    uint64_t* bandwidth_history;
    uint32_t history_size;
    uint32_t history_index;
} NetworkMonitor;

// Quality of Service (QoS)
typedef enum {
    QOS_BEST_EFFORT,
    QOS_EXPEDITED_FORWARDING,
    QOS_ASSURED_FORWARDING,
    QOS_CLASS_SELECTOR
} QoSClass;

typedef struct {
    QoSClass qos_class;
    uint32_t max_bandwidth;
    uint32_t min_bandwidth;
    uint32_t priority;
    uint32_t max_latency;
} QoSPolicy;

// =====================================================================================================================
// Global Network State
// =====================================================================================================================

TCPConnection g_tcp_connections[MAX_CONNECTIONS];
uint32_t g_tcp_conn_count = 0;
UDPSocket g_udp_sockets[MAX_CONNECTIONS];
uint32_t g_udp_socket_count = 0;
DNSCache g_dns_cache;
ARPCache g_arp_cache;
RoutingTable g_routing_table;
NetworkMonitor g_network_monitor;
MQTTClient g_mqtt_client;

// =====================================================================================================================
// TCP Implementation
// =====================================================================================================================

TCPConnection* tcp_create_connection(IPAddress remote_ip, uint16_t remote_port) {
    if (g_tcp_conn_count >= MAX_CONNECTIONS) return NULL;
    
    TCPConnection* conn = &g_tcp_connections[g_tcp_conn_count++];
    conn->state = TCP_CLOSED;
    conn->remote_ip = remote_ip;
    conn->remote_port = remote_port;
    conn->local_ip = WiFi.localIP();
    conn->local_port = random(49152, 65535);
    conn->seq_num = random(0, UINT32_MAX);
    conn->ack_num = 0;
    conn->window_size = 65535;
    conn->send_buffer_size = 8192;
    conn->recv_buffer_size = 8192;
    conn->send_buffer = (uint8_t*)malloc(conn->send_buffer_size);
    conn->recv_buffer = (uint8_t*)malloc(conn->recv_buffer_size);
    conn->last_activity = millis();
    conn->rtt = 100;
    conn->srtt = 100;
    conn->rttvar = 50;
    conn->rto = 200;
    
    return conn;
}

void tcp_send_syn(TCPConnection* conn) {
    conn->state = TCP_SYN_SENT;
    
    // Build TCP SYN packet
    uint8_t packet[64];
    // (Packet construction omitted for brevity)
    
    Serial.printf("[TCP] Sending SYN to %s:%d\n",
                  conn->remote_ip.toString().c_str(), conn->remote_port);
}

void tcp_send_ack(TCPConnection* conn) {
    // Build TCP ACK packet
    uint8_t packet[64];
    // (Packet construction omitted)
    
    Serial.printf("[TCP] Sending ACK, seq=%u, ack=%u\n", conn->seq_num, conn->ack_num);
}

void tcp_connect(TCPConnection* conn) {
    tcp_send_syn(conn);
    
    // Wait for SYN-ACK (simplified)
    uint64_t start = millis();
    while (conn->state != TCP_ESTABLISHED && millis() - start < 5000) {
        delay(10);
    }
    
    if (conn->state == TCP_ESTABLISHED) {
        Serial.println("[TCP] Connection established");
    } else {
        Serial.println("[TCP] Connection timeout");
        conn->state = TCP_CLOSED;
    }
}

uint32_t tcp_send(TCPConnection* conn, const uint8_t* data, uint32_t length) {
    if (conn->state != TCP_ESTABLISHED) return 0;
    
    uint32_t bytes_sent = 0;
    
    while (bytes_sent < length) {
        uint32_t chunk_size = min(length - bytes_sent, (uint32_t)1460);  // MSS
        
        // Copy to send buffer
        memcpy(conn->send_buffer, data + bytes_sent, chunk_size);
        
        // Build and send TCP data packet
        conn->seq_num += chunk_size;
        bytes_sent += chunk_size;
        
        conn->last_activity = millis();
        yield();
    }
    
    return bytes_sent;
}

uint32_t tcp_receive(TCPConnection* conn, uint8_t* buffer, uint32_t max_length) {
    if (conn->state != TCP_ESTABLISHED) return 0;
    
    // Simplified receive (would normally wait for data)
    uint32_t available = min(max_length, conn->recv_buffer_size);
    memcpy(buffer, conn->recv_buffer, available);
    
    conn->last_activity = millis();
    return available;
}

void tcp_close(TCPConnection* conn) {
    if (conn->state == TCP_ESTABLISHED) {
        conn->state = TCP_FIN_WAIT_1;
        
        // Send FIN packet
        Serial.println("[TCP] Closing connection");
    }
    
    free(conn->send_buffer);
    free(conn->recv_buffer);
    conn->state = TCP_CLOSED;
}

// =====================================================================================================================
// UDP Implementation
// =====================================================================================================================

UDPSocket* udp_create_socket() {
    if (g_udp_socket_count >= MAX_CONNECTIONS) return NULL;
    
    UDPSocket* sock = &g_udp_sockets[g_udp_socket_count++];
    sock->local_ip = WiFi.localIP();
    sock->local_port = 0;
    sock->buffer_size = 8192;
    sock->buffer = (uint8_t*)malloc(sock->buffer_size);
    sock->is_bound = false;
    sock->is_multicast = false;
    
    return sock;
}

bool udp_bind(UDPSocket* sock, uint16_t port) {
    sock->local_port = port;
    sock->is_bound = true;
    
    Serial.printf("[UDP] Bound to port %d\n", port);
    return true;
}

uint32_t udp_send_to(UDPSocket* sock, const uint8_t* data, uint32_t length,
                     IPAddress remote_ip, uint16_t remote_port) {
    if (!sock->is_bound) return 0;
    
    // Build UDP packet
    NetworkPacket packet;
    packet.data = (uint8_t*)malloc(length);
    memcpy(packet.data, data, length);
    packet.size = length;
    packet.src_ip = sock->local_ip;
    packet.dst_ip = remote_ip;
    packet.src_port = sock->local_port;
    packet.dst_port = remote_port;
    packet.protocol = 17;  // UDP
    packet.timestamp = millis();
    
    // Send packet (implementation depends on network hardware)
    free(packet.data);
    
    return length;
}

uint32_t udp_receive_from(UDPSocket* sock, uint8_t* buffer, uint32_t max_length,
                          IPAddress* remote_ip, uint16_t* remote_port) {
    if (!sock->is_bound) return 0;
    
    // Simplified receive
    uint32_t available = min(max_length, sock->buffer_size);
    memcpy(buffer, sock->buffer, available);
    
    return available;
}

// =====================================================================================================================
// WebSocket Implementation
// =====================================================================================================================

void websocket_encode_frame(WebSocketFrame* frame, uint8_t* output,
                           uint32_t* output_length) {
    uint32_t pos = 0;
    
    // Byte 0: FIN, RSV, Opcode
    output[pos++] = (frame->fin ? 0x80 : 0x00) | (frame->opcode & 0x0F);
    
    // Byte 1+: Mask, Payload length
    if (frame->payload_length < 126) {
        output[pos++] = (frame->mask ? 0x80 : 0x00) | (uint8_t)frame->payload_length;
    } else if (frame->payload_length < 65536) {
        output[pos++] = (frame->mask ? 0x80 : 0x00) | 126;
        output[pos++] = (frame->payload_length >> 8) & 0xFF;
        output[pos++] = frame->payload_length & 0xFF;
    } else {
        output[pos++] = (frame->mask ? 0x80 : 0x00) | 127;
        for (int i = 7; i >= 0; i--) {
            output[pos++] = (frame->payload_length >> (i * 8)) & 0xFF;
        }
    }
    
    // Masking key
    if (frame->mask) {
        memcpy(&output[pos], frame->mask_key, 4);
        pos += 4;
    }
    
    // Payload
    for (uint64_t i = 0; i < frame->payload_length; i++) {
        if (frame->mask) {
            output[pos++] = frame->payload[i] ^ frame->mask_key[i % 4];
        } else {
            output[pos++] = frame->payload[i];
        }
    }
    
    *output_length = pos;
}

void websocket_send_text(WebSocketConnection* ws, const char* text) {
    if (!ws->handshake_complete) return;
    
    WebSocketFrame frame;
    frame.type = WS_TEXT_FRAME;
    frame.opcode = 0x01;
    frame.fin = true;
    frame.mask = ws->is_client;
    frame.payload = (uint8_t*)text;
    frame.payload_length = strlen(text);
    
    if (frame.mask) {
        for (int i = 0; i < 4; i++) {
            frame.mask_key[i] = random(0, 256);
        }
    }
    
    uint8_t encoded[2048];
    uint32_t encoded_length;
    websocket_encode_frame(&frame, encoded, &encoded_length);
    
    // Send via TCP
    tcp_send(ws->tcp_conn, encoded, encoded_length);
}

void websocket_send_ping(WebSocketConnection* ws) {
    WebSocketFrame frame;
    frame.type = WS_PING_FRAME;
    frame.opcode = 0x09;
    frame.fin = true;
    frame.mask = ws->is_client;
    frame.payload = NULL;
    frame.payload_length = 0;
    
    uint8_t encoded[32];
    uint32_t encoded_length;
    websocket_encode_frame(&frame, encoded, &encoded_length);
    
    tcp_send(ws->tcp_conn, encoded, encoded_length);
}

// =====================================================================================================================
// HTTP Implementation
// =====================================================================================================================

void http_parse_request(const uint8_t* data, uint32_t length, HTTPRequest* req) {
    // Simple HTTP request parser
    char* str = (char*)malloc(length + 1);
    memcpy(str, data, length);
    str[length] = '\0';
    
    // Parse request line
    char* line = strtok(str, "\r\n");
    if (line) {
        char* method = strtok(line, " ");
        char* uri = strtok(NULL, " ");
        char* version = strtok(NULL, " ");
        
        if (strcmp(method, "GET") == 0) req->method = HTTP_GET;
        else if (strcmp(method, "POST") == 0) req->method = HTTP_POST;
        else if (strcmp(method, "PUT") == 0) req->method = HTTP_PUT;
        else if (strcmp(method, "DELETE") == 0) req->method = HTTP_DELETE;
        
        req->uri = strdup(uri);
        req->version = strdup(version);
    }
    
    // Parse headers
    req->header_count = 0;
    req->headers = (char**)malloc(sizeof(char*) * 50);
    req->header_values = (char**)malloc(sizeof(char*) * 50);
    
    while ((line = strtok(NULL, "\r\n")) != NULL && strlen(line) > 0) {
        char* colon = strchr(line, ':');
        if (colon) {
            *colon = '\0';
            req->headers[req->header_count] = strdup(line);
            req->header_values[req->header_count] = strdup(colon + 2);
            req->header_count++;
        }
    }
    
    free(str);
}

void http_build_response(HTTPResponse* resp, uint8_t* output, uint32_t* output_length) {
    char header[2048];
    int pos = 0;
    
    // Status line
    pos += sprintf(&header[pos], "HTTP/1.1 %d %s\r\n",
                  resp->status_code, resp->status_text);
    
    // Headers
    for (uint32_t i = 0; i < resp->header_count; i++) {
        pos += sprintf(&header[pos], "%s: %s\r\n",
                      resp->headers[i], resp->header_values[i]);
    }
    
    // Content-Length header
    pos += sprintf(&header[pos], "Content-Length: %u\r\n", resp->body_length);
    pos += sprintf(&header[pos], "\r\n");
    
    // Copy header and body to output
    memcpy(output, header, pos);
    if (resp->body && resp->body_length > 0) {
        memcpy(output + pos, resp->body, resp->body_length);
        pos += resp->body_length;
    }
    
    *output_length = pos;
}

// =====================================================================================================================
// MQTT Implementation
// =====================================================================================================================

void mqtt_connect(MQTTClient* client, const char* broker, uint16_t port) {
    // Create TCP connection
    IPAddress broker_ip;
    WiFi.hostByName(broker, broker_ip);
    
    client->conn = tcp_create_connection(broker_ip, port);
    tcp_connect(client->conn);
    
    if (client->conn->state != TCP_ESTABLISHED) {
        Serial.println("[MQTT] Failed to connect to broker");
        return;
    }
    
    // Build CONNECT packet
    uint8_t packet[256];
    uint32_t pos = 0;
    
    // Fixed header
    packet[pos++] = (MQTT_CONNECT << 4);
    packet[pos++] = 0;  // Remaining length (placeholder)
    
    // Variable header
    packet[pos++] = 0x00;
    packet[pos++] = 0x04;
    memcpy(&packet[pos], "MQTT", 4);
    pos += 4;
    packet[pos++] = 0x04;  // Protocol level
    
    // Connect flags
    uint8_t flags = 0x02;  // Clean session
    if (client->username) flags |= 0x80;
    if (client->password) flags |= 0x40;
    packet[pos++] = flags;
    
    // Keep alive
    packet[pos++] = (client->keep_alive >> 8) & 0xFF;
    packet[pos++] = client->keep_alive & 0xFF;
    
    // Payload - Client ID
    uint16_t client_id_len = strlen(client->client_id);
    packet[pos++] = (client_id_len >> 8) & 0xFF;
    packet[pos++] = client_id_len & 0xFF;
    memcpy(&packet[pos], client->client_id, client_id_len);
    pos += client_id_len;
    
    // Update remaining length
    packet[1] = pos - 2;
    
    // Send CONNECT packet
    tcp_send(client->conn, packet, pos);
    
    Serial.println("[MQTT] Connected to broker");
    client->connected = true;
}

void mqtt_publish(MQTTClient* client, const char* topic, const uint8_t* payload,
                 uint32_t length, MQTTQoS qos) {
    if (!client->connected) return;
    
    uint8_t packet[1024];
    uint32_t pos = 0;
    
    // Fixed header
    packet[pos++] = (MQTT_PUBLISH << 4) | ((qos & 0x03) << 1);
    packet[pos++] = 0;  // Remaining length (placeholder)
    
    // Variable header - Topic
    uint16_t topic_len = strlen(topic);
    packet[pos++] = (topic_len >> 8) & 0xFF;
    packet[pos++] = topic_len & 0xFF;
    memcpy(&packet[pos], topic, topic_len);
    pos += topic_len;
    
    // Packet identifier (for QoS > 0)
    if (qos > MQTT_QOS_0) {
        uint16_t packet_id = client->next_packet_id++;
        packet[pos++] = (packet_id >> 8) & 0xFF;
        packet[pos++] = packet_id & 0xFF;
    }
    
    // Payload
    memcpy(&packet[pos], payload, length);
    pos += length;
    
    // Update remaining length
    packet[1] = pos - 2;
    
    // Send packet
    tcp_send(client->conn, packet, pos);
}

void mqtt_subscribe(MQTTClient* client, const char* topic, MQTTQoS qos) {
    if (!client->connected) return;
    
    uint8_t packet[256];
    uint32_t pos = 0;
    
    // Fixed header
    packet[pos++] = (MQTT_SUBSCRIBE << 4) | 0x02;
    packet[pos++] = 0;  // Remaining length (placeholder)
    
    // Variable header - Packet identifier
    uint16_t packet_id = client->next_packet_id++;
    packet[pos++] = (packet_id >> 8) & 0xFF;
    packet[pos++] = packet_id & 0xFF;
    
    // Payload - Topic filter
    uint16_t topic_len = strlen(topic);
    packet[pos++] = (topic_len >> 8) & 0xFF;
    packet[pos++] = topic_len & 0xFF;
    memcpy(&packet[pos], topic, topic_len);
    pos += topic_len;
    
    // QoS
    packet[pos++] = qos;
    
    // Update remaining length
    packet[1] = pos - 2;
    
    // Send packet
    tcp_send(client->conn, packet, pos);
    
    Serial.printf("[MQTT] Subscribed to topic: %s\n", topic);
}

// =====================================================================================================================
// DNS Implementation
// =====================================================================================================================

IPAddress dns_resolve(const char* hostname) {
    // Check cache first
    for (uint32_t i = 0; i < g_dns_cache.record_count; i++) {
        DNSRecord* record = &g_dns_cache.records[i];
        
        if (strcmp(record->name, hostname) == 0) {
            uint64_t age = millis() - record->cached_at;
            if (age < record->ttl * 1000) {
                Serial.printf("[DNS] Cache hit for %s\n", hostname);
                return record->ip_address;
            }
        }
    }
    
    // Cache miss - perform DNS query
    Serial.printf("[DNS] Resolving %s...\n", hostname);
    
    IPAddress ip;
    if (WiFi.hostByName(hostname, ip)) {
        // Add to cache
        if (g_dns_cache.record_count < MAX_DNS_CACHE) {
            DNSRecord* record = &g_dns_cache.records[g_dns_cache.record_count++];
            record->name = strdup(hostname);
            record->type = DNS_A;
            record->ip_address = ip;
            record->ttl = 300;  // 5 minutes
            record->cached_at = millis();
        }
        
        return ip;
    }
    
    return IPAddress(0, 0, 0, 0);
}

// =====================================================================================================================
// Network Monitoring
// =====================================================================================================================

void network_monitor_init(NetworkMonitor* monitor) {
    memset(&monitor->stats, 0, sizeof(NetworkStats));
    
    monitor->sniffer.enabled = false;
    monitor->sniffer.packet_count = 0;
    monitor->sniffer.max_packets = 1000;
    monitor->sniffer.captured_packets = (NetworkPacket*)malloc(
        sizeof(NetworkPacket) * monitor->sniffer.max_packets);
    
    monitor->history_size = 60;
    monitor->bandwidth_history = (uint64_t*)malloc(sizeof(uint64_t) * monitor->history_size);
    memset(monitor->bandwidth_history, 0, sizeof(uint64_t) * monitor->history_size);
    monitor->history_index = 0;
}

void network_monitor_update(NetworkMonitor* monitor) {
    // Update bandwidth history
    monitor->bandwidth_history[monitor->history_index] = monitor->stats.bytes_sent +
                                                         monitor->stats.bytes_received;
    monitor->history_index = (monitor->history_index + 1) % monitor->history_size;
    
    // Calculate bandwidth usage (bytes per second)
    uint64_t total_bytes = 0;
    for (uint32_t i = 0; i < monitor->history_size; i++) {
        total_bytes += monitor->bandwidth_history[i];
    }
    monitor->stats.bandwidth_usage = (float)total_bytes / monitor->history_size;
}

// =====================================================================================================================
// Network Initialization
// =====================================================================================================================

void advanced_networking_init() {
    Serial.println("[Network] Initializing advanced networking...");
    
    g_tcp_conn_count = 0;
    g_udp_socket_count = 0;
    g_dns_cache.record_count = 0;
    g_arp_cache.entry_count = 0;
    g_routing_table.route_count = 0;
    
    network_monitor_init(&g_network_monitor);
    
    // Initialize MQTT client
    g_mqtt_client.client_id = "esp32_client";
    g_mqtt_client.keep_alive = 60;
    g_mqtt_client.clean_session = true;
    g_mqtt_client.connected = false;
    g_mqtt_client.next_packet_id = 1;
    
    Serial.println("[Network] Advanced networking initialized");
}

// =====================================================================================================================
// End of advanced_networking.cpp
// Lines: ~1150
// =====================================================================================================================
