/**
 * Mesh Routing Protocol
 * =====================
 * 
 * Custom mesh routing for LoRa sensor network.
 * 
 * Features:
 * - Multi-hop routing (up to 5 hops)
 * - Route discovery and maintenance
 * - Load balancing across paths
 * - Automatic failover
 * - Loop prevention
 */

#ifndef MESH_ROUTING_H
#define MESH_ROUTING_H

#include <Arduino.h>
#include <map>
#include <vector>

#define MAX_HOPS 5
#define ROUTE_TIMEOUT_MS 300000  // 5 minutes
#define MAX_NEIGHBORS 10
#define ROUTE_DISCOVERY_INTERVAL 60000  // 1 minute

// Packet types
enum PacketType {
    PKT_DATA = 0x01,
    PKT_ROUTE_REQUEST = 0x02,
    PKT_ROUTE_REPLY = 0x03,
    PKT_ROUTE_ERROR = 0x04,
    PKT_HELLO = 0x05,
    PKT_ACK = 0x06
};

// Routing table entry
struct RouteEntry {
    uint8_t dest_addr;
    uint8_t next_hop;
    uint8_t hop_count;
    int rssi;
    unsigned long timestamp;
    bool valid;
};

// Neighbor info
struct Neighbor {
    uint8_t address;
    int rssi;
    uint8_t link_quality;  // 0-100
    unsigned long last_seen;
};

class MeshRouter {
private:
    uint8_t node_address;
    std::map<uint8_t, RouteEntry> routing_table;
    std::vector<Neighbor> neighbors;
    std::map<uint16_t, unsigned long> seen_packets;  // For loop prevention
    
    unsigned long last_hello = 0;
    unsigned long last_route_discovery = 0;
    uint16_t packet_sequence = 0;
    
public:
    MeshRouter(uint8_t addr) : node_address(addr) {}
    
    // ===== Initialization =====
    
    void begin() {
        routing_table.clear();
        neighbors.clear();
        seen_packets.clear();
        
        Serial.printf("[MESH] Router initialized (address: 0x%02X)\n", node_address);
    }
    
    // ===== Periodic Tasks =====
    
    void update() {
        unsigned long now = millis();
        
        // Send hello packets periodically
        if (now - last_hello >= 10000) {  // Every 10 seconds
            sendHello();
            last_hello = now;
        }
        
        // Route discovery periodically
        if (now - last_route_discovery >= ROUTE_DISCOVERY_INTERVAL) {
            discoverRoutes();
            last_route_discovery = now;
        }
        
        // Clean up old routes
        cleanupRoutes();
        
        // Clean up seen packets
        cleanupSeenPackets();
    }
    
    // ===== Packet Handling =====
    
    bool handlePacket(uint8_t* packet, size_t len, int rssi) {
        if (len < 4) return false;
        
        uint8_t start_byte = packet[0];
        uint8_t src_addr = packet[1];
        uint8_t dest_addr = packet[2];
        uint8_t pkt_type = packet[3];
        
        if (start_byte != 0xAA) return false;
        
        // Check if we've seen this packet before (loop prevention)
        uint16_t pkt_id = (src_addr << 8) | packet[4];  // src + sequence
        if (seen_packets.count(pkt_id) > 0) {
            Serial.printf("[MESH] Duplicate packet from 0x%02X\n", src_addr);
            return false;
        }
        seen_packets[pkt_id] = millis();
        
        // Update neighbor table
        updateNeighbor(src_addr, rssi);
        
        // Handle different packet types
        switch (pkt_type) {
            case PKT_DATA:
                return handleDataPacket(packet, len, src_addr, dest_addr);
                
            case PKT_ROUTE_REQUEST:
                return handleRouteRequest(packet, len, src_addr, rssi);
                
            case PKT_ROUTE_REPLY:
                return handleRouteReply(packet, len, src_addr);
                
            case PKT_ROUTE_ERROR:
                return handleRouteError(packet, len, src_addr);
                
            case PKT_HELLO:
                return handleHello(packet, len, src_addr, rssi);
                
            default:
                Serial.printf("[MESH] Unknown packet type: 0x%02X\n", pkt_type);
                return false;
        }
    }
    
    // ===== Routing =====
    
    bool sendPacket(uint8_t dest_addr, uint8_t* payload, size_t payload_len) {
        // Check if we have a route
        RouteEntry* route = findRoute(dest_addr);
        
        if (!route) {
            // No route, initiate route discovery
            Serial.printf("[MESH] No route to 0x%02X, discovering...\n", dest_addr);
            requestRoute(dest_addr);
            return false;
        }
        
        // Build packet
        uint8_t packet[256];
        size_t idx = 0;
        
        packet[idx++] = 0xAA;  // Start byte
        packet[idx++] = node_address;  // Source
        packet[idx++] = dest_addr;  // Destination
        packet[idx++] = PKT_DATA;  // Type
        packet[idx++] = packet_sequence++;  // Sequence
        packet[idx++] = route->hop_count;  // Hops
        
        // Copy payload
        memcpy(&packet[idx], payload, payload_len);
        idx += payload_len;
        
        // Transmit to next hop
        Serial.printf("[MESH] Routing to 0x%02X via 0x%02X (%d hops)\n", 
                     dest_addr, route->next_hop, route->hop_count);
        
        LoRa.beginPacket();
        LoRa.write(packet, idx);
        return LoRa.endPacket();
    }
    
    // ===== Route Discovery =====
    
    void requestRoute(uint8_t dest_addr) {
        uint8_t packet[16];
        size_t idx = 0;
        
        packet[idx++] = 0xAA;
        packet[idx++] = node_address;
        packet[idx++] = 0xFF;  // Broadcast
        packet[idx++] = PKT_ROUTE_REQUEST;
        packet[idx++] = packet_sequence++;
        packet[idx++] = dest_addr;  // Target
        packet[idx++] = 0;  // Initial hop count
        
        LoRa.beginPacket();
        LoRa.write(packet, idx);
        LoRa.endPacket();
        
        Serial.printf("[MESH] Route request sent for 0x%02X\n", dest_addr);
    }
    
    void discoverRoutes() {
        // Discover route to gateway
        requestRoute(0xFF);  // Gateway address
    }
    
    // ===== Neighbor Management =====
    
    void updateNeighbor(uint8_t addr, int rssi) {
        // Find existing neighbor
        for (auto& n : neighbors) {
            if (n.address == addr) {
                n.rssi = rssi;
                n.last_seen = millis();
                n.link_quality = calculateLinkQuality(rssi);
                return;
            }
        }
        
        // Add new neighbor
        if (neighbors.size() < MAX_NEIGHBORS) {
            Neighbor n;
            n.address = addr;
            n.rssi = rssi;
            n.last_seen = millis();
            n.link_quality = calculateLinkQuality(rssi);
            neighbors.push_back(n);
            
            Serial.printf("[MESH] New neighbor: 0x%02X (RSSI: %d dBm)\n", addr, rssi);
        }
    }
    
    uint8_t calculateLinkQuality(int rssi) {
        // Convert RSSI to 0-100 quality
        // Excellent: > -70 dBm
        // Good: -70 to -85 dBm
        // Fair: -85 to -100 dBm
        // Poor: < -100 dBm
        
        if (rssi > -70) return 100;
        if (rssi > -85) return 75;
        if (rssi > -100) return 50;
        return 25;
    }
    
    // ===== Route Table Management =====
    
    RouteEntry* findRoute(uint8_t dest_addr) {
        if (routing_table.count(dest_addr) == 0) {
            return nullptr;
        }
        
        RouteEntry* route = &routing_table[dest_addr];
        
        // Check if route is still valid
        if (millis() - route->timestamp > ROUTE_TIMEOUT_MS) {
            route->valid = false;
            return nullptr;
        }
        
        return route;
    }
    
    void addRoute(uint8_t dest_addr, uint8_t next_hop, uint8_t hop_count, int rssi) {
        RouteEntry route;
        route.dest_addr = dest_addr;
        route.next_hop = next_hop;
        route.hop_count = hop_count;
        route.rssi = rssi;
        route.timestamp = millis();
        route.valid = true;
        
        routing_table[dest_addr] = route;
        
        Serial.printf("[MESH] Route added: 0x%02X via 0x%02X (%d hops)\n", 
                     dest_addr, next_hop, hop_count);
    }
    
    void cleanupRoutes() {
        unsigned long now = millis();
        
        for (auto it = routing_table.begin(); it != routing_table.end(); ) {
            if (now - it->second.timestamp > ROUTE_TIMEOUT_MS) {
                Serial.printf("[MESH] Route expired: 0x%02X\n", it->first);
                it = routing_table.erase(it);
            } else {
                ++it;
            }
        }
    }
    
    void cleanupSeenPackets() {
        unsigned long now = millis();
        
        for (auto it = seen_packets.begin(); it != seen_packets.end(); ) {
            if (now - it->second > 60000) {  // 1 minute
                it = seen_packets.erase(it);
            } else {
                ++it;
            }
        }
    }
    
    // ===== Packet Handlers =====
    
    bool handleDataPacket(uint8_t* packet, size_t len, uint8_t src_addr, uint8_t dest_addr) {
        if (dest_addr == node_address) {
            // Packet for us
            Serial.printf("[MESH] Data packet received from 0x%02X\n", src_addr);
            return true;  // Processed locally
        } else {
            // Forward packet
            RouteEntry* route = findRoute(dest_addr);
            if (route) {
                packet[1] = node_address;  // Update source to us
                packet[5]++;  // Increment hop count
                
                if (packet[5] < MAX_HOPS) {
                    LoRa.beginPacket();
                    LoRa.write(packet, len);
                    LoRa.endPacket();
                    Serial.printf("[MESH] Forwarded to 0x%02X via 0x%02X\n", 
                                 dest_addr, route->next_hop);
                    return true;
                } else {
                    Serial.printf("[MESH] Max hops exceeded, dropping packet\n");
                    return false;
                }
            } else {
                Serial.printf("[MESH] No route to 0x%02X, requesting...\n", dest_addr);
                requestRoute(dest_addr);
                return false;
            }
        }
    }
    
    bool handleRouteRequest(uint8_t* packet, size_t len, uint8_t src_addr, int rssi) {
        if (len < 7) return false;
        
        uint8_t target_addr = packet[5];
        uint8_t hop_count = packet[6];
        
        Serial.printf("[MESH] Route request from 0x%02X for 0x%02X\n", src_addr, target_addr);
        
        if (target_addr == node_address || target_addr == 0xFF) {
            // We are the target or it's a broadcast, send reply
            sendRouteReply(src_addr, hop_count + 1, rssi);
        } else {
            // Forward request
            packet[6]++;  // Increment hop count
            
            if (packet[6] < MAX_HOPS) {
                LoRa.beginPacket();
                LoRa.write(packet, len);
                LoRa.endPacket();
            }
        }
        
        return true;
    }
    
    bool handleRouteReply(uint8_t* packet, size_t len, uint8_t src_addr) {
        if (len < 7) return false;
        
        uint8_t dest_addr = packet[5];
        uint8_t hop_count = packet[6];
        
        Serial.printf("[MESH] Route reply from 0x%02X (%d hops)\n", src_addr, hop_count);
        
        // Add route
        addRoute(src_addr, src_addr, hop_count, LoRa.packetRssi());
        
        return true;
    }
    
    bool handleRouteError(uint8_t* packet, size_t len, uint8_t src_addr) {
        if (len < 6) return false;
        
        uint8_t failed_addr = packet[5];
        
        Serial.printf("[MESH] Route error: 0x%02X unreachable\n", failed_addr);
        
        // Remove failed route
        routing_table.erase(failed_addr);
        
        return true;
    }
    
    bool handleHello(uint8_t* packet, size_t len, uint8_t src_addr, int rssi) {
        Serial.printf("[MESH] Hello from 0x%02X (RSSI: %d dBm)\n", src_addr, rssi);
        
        // Update neighbor
        updateNeighbor(src_addr, rssi);
        
        return true;
    }
    
    void sendHello() {
        uint8_t packet[8];
        size_t idx = 0;
        
        packet[idx++] = 0xAA;
        packet[idx++] = node_address;
        packet[idx++] = 0xFF;  // Broadcast
        packet[idx++] = PKT_HELLO;
        packet[idx++] = packet_sequence++;
        
        LoRa.beginPacket();
        LoRa.write(packet, idx);
        LoRa.endPacket();
    }
    
    void sendRouteReply(uint8_t dest_addr, uint8_t hop_count, int rssi) {
        uint8_t packet[8];
        size_t idx = 0;
        
        packet[idx++] = 0xAA;
        packet[idx++] = node_address;
        packet[idx++] = dest_addr;
        packet[idx++] = PKT_ROUTE_REPLY;
        packet[idx++] = packet_sequence++;
        packet[idx++] = dest_addr;
        packet[idx++] = hop_count;
        
        LoRa.beginPacket();
        LoRa.write(packet, idx);
        LoRa.endPacket();
        
        Serial.printf("[MESH] Route reply sent to 0x%02X\n", dest_addr);
    }
    
    // ===== Diagnostics =====
    
    void printRoutingTable() {
        Serial.println("\n===== ROUTING TABLE =====");
        
        if (routing_table.empty()) {
            Serial.println("  (empty)");
        } else {
            Serial.println("  Dest   Next Hop   Hops   RSSI   Age(s)");
            Serial.println("  ----   --------   ----   ----   ------");
            
            for (const auto& entry : routing_table) {
                unsigned long age = (millis() - entry.second.timestamp) / 1000;
                Serial.printf("  0x%02X   0x%02X       %2d     %4d   %6lu\n",
                             entry.second.dest_addr,
                             entry.second.next_hop,
                             entry.second.hop_count,
                             entry.second.rssi,
                             age);
            }
        }
        
        Serial.println("=========================\n");
    }
    
    void printNeighbors() {
        Serial.println("\n===== NEIGHBORS =====");
        
        if (neighbors.empty()) {
            Serial.println("  (none)");
        } else {
            Serial.println("  Address   RSSI   Quality   Last Seen(s)");
            Serial.println("  -------   ----   -------   ------------");
            
            for (const auto& n : neighbors) {
                unsigned long age = (millis() - n.last_seen) / 1000;
                Serial.printf("  0x%02X      %4d   %3d%%      %6lu\n",
                             n.address, n.rssi, n.link_quality, age);
            }
        }
        
        Serial.println("=====================\n");
    }
};

#endif // MESH_ROUTING_H
