// =====================================================================================================================
// AgroPulse Firmware - Advanced Distributed Systems Engine (C++)
// P2P networking, consensus protocols, distributed transactions, mesh networking, DHT
// =====================================================================================================================

#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

// Network protocols
typedef enum NetworkProtocol {
    PROTO_TCP,
    PROTO_UDP,
    PROTO_QUIC,
    PROTO_WEBSOCKET,
    PROTO_CUSTOM
} NetworkProtocol;

// Node roles in distributed system
typedef enum NodeRole {
    ROLE_FULL_NODE,
    ROLE_LIGHT_NODE,
    ROLE_VALIDATOR,
    ROLE_OBSERVER,
    ROLE_ARCHIVAL
} NodeRole;

// Message types
typedef enum MessageType {
    MSG_HANDSHAKE,
    MSG_PING,
    MSG_PONG,
    MSG_GET_PEERS,
    MSG_PEERS_LIST,
    MSG_BLOCK_REQUEST,
    MSG_BLOCK_RESPONSE,
    MSG_TX_BROADCAST,
    MSG_CONSENSUS_VOTE,
    MSG_STATE_SYNC
} MessageType;

// Network peer
typedef struct NetworkPeer {
    uint8_t peer_id[32];
    uint8_t ip_address[16];
    uint16_t port;
    NodeRole role;
    uint64_t last_seen;
    uint32_t latency_ms;
    uint32_t reputation;
    bool is_connected;
    bool is_trusted;
    uint32_t failed_attempts;
} NetworkPeer;

// Peer pool
typedef struct PeerPool {
    NetworkPeer* peers;
    uint32_t count;
    uint32_t capacity;
    uint32_t max_peers;
} PeerPool;

// Message header
typedef struct MessageHeader {
    MessageType type;
    uint32_t protocol_version;
    uint32_t payload_size;
    uint8_t sender_id[32];
    uint64_t timestamp;
    uint8_t signature[64];
} MessageHeader;

// Network message
typedef struct NetworkMessage {
    MessageHeader header;
    uint8_t* payload;
} NetworkMessage;

// DHT (Distributed Hash Table) entry
typedef struct DHTEntry {
    uint8_t key[32];
    uint8_t* value;
    uint32_t value_size;
    uint64_t timestamp;
    uint32_t ttl;
    uint8_t closest_nodes[20][32];
} DHTEntry;

// DHT routing table
typedef struct DHTRoutingTable {
    DHTEntry* entries;
    uint32_t count;
    uint32_t capacity;
    uint8_t local_id[32];
} DHTRoutingTable;

// Kademlia k-bucket
typedef struct KBucket {
    uint8_t node_ids[20][32];
    uint32_t node_count;
    uint32_t prefix_length;
    uint64_t last_updated;
} KBucket;

// Gossip protocol state
typedef struct GossipState {
    uint8_t** message_ids;
    uint32_t message_count;
    uint32_t capacity;
    uint32_t fanout;
    uint32_t ttl;
} GossipState;

// Raft consensus state
typedef enum RaftRole {
    RAFT_FOLLOWER,
    RAFT_CANDIDATE,
    RAFT_LEADER
} RaftRole;

typedef struct RaftState {
    RaftRole role;
    uint64_t current_term;
    uint8_t voted_for[32];
    uint64_t commit_index;
    uint64_t last_applied;
    uint32_t election_timeout;
    uint32_t heartbeat_interval;
    uint64_t last_heartbeat;
} RaftState;

// Paxos instance
typedef struct PaxosInstance {
    uint64_t proposal_number;
    uint64_t promised_number;
    uint8_t* accepted_value;
    uint32_t value_size;
    bool decided;
} PaxosInstance;

// Vector clock for causal ordering
typedef struct VectorClock {
    uint64_t* timestamps;
    uint8_t** node_ids;
    uint32_t node_count;
} VectorClock;

// Merkle tree for data verification
typedef struct MerkleTree {
    uint8_t** hashes;
    uint32_t* levels;
    uint32_t height;
    uint32_t leaf_count;
} MerkleTree;

// Bloom filter for membership testing
typedef struct BloomFilter {
    uint8_t* bits;
    uint32_t size;
    uint32_t num_hashes;
    uint64_t element_count;
} BloomFilter;

// Consistent hashing ring
typedef struct ConsistentHashRing {
    uint8_t** node_hashes;
    uint8_t** node_ids;
    uint32_t* virtual_nodes;
    uint32_t node_count;
    uint32_t vnodes_per_node;
} ConsistentHashRing;

// =====================================================================================================================
// Utility Functions
// =====================================================================================================================

uint32_t xor_distance(uint8_t* a, uint8_t* b, uint32_t len) {
    uint32_t distance = 0;
    for (uint32_t i = 0; i < len; i++) {
        uint8_t xor = a[i] ^ b[i];
        while (xor) {
            distance++;
            xor &= (xor - 1);
        }
    }
    return distance;
}

void generate_random_id(uint8_t* id, uint32_t len) {
    for (uint32_t i = 0; i < len; i++) {
        id[i] = rand() % 256;
    }
}

uint32_t hash_fnv1a(uint8_t* data, uint32_t len) {
    uint32_t hash = 2166136261u;
    for (uint32_t i = 0; i < len; i++) {
        hash ^= data[i];
        hash *= 16777619u;
    }
    return hash;
}

// =====================================================================================================================
// Peer Pool Management
// =====================================================================================================================

PeerPool* peer_pool_create(uint32_t max_peers) {
    PeerPool* pool = (PeerPool*)malloc(sizeof(PeerPool));
    pool->max_peers = max_peers;
    pool->capacity = max_peers * 2;
    pool->count = 0;
    pool->peers = (NetworkPeer*)malloc(sizeof(NetworkPeer) * pool->capacity);
    return pool;
}

void peer_pool_destroy(PeerPool* pool) {
    free(pool->peers);
    free(pool);
}

bool peer_pool_add(PeerPool* pool, NetworkPeer* peer) {
    if (pool->count >= pool->max_peers) {
        // Remove lowest reputation peer
        uint32_t min_idx = 0;
        for (uint32_t i = 1; i < pool->count; i++) {
            if (pool->peers[i].reputation < pool->peers[min_idx].reputation) {
                min_idx = i;
            }
        }
        
        if (peer->reputation <= pool->peers[min_idx].reputation) {
            return false;
        }
        
        memcpy(&pool->peers[min_idx], peer, sizeof(NetworkPeer));
    } else {
        memcpy(&pool->peers[pool->count], peer, sizeof(NetworkPeer));
        pool->count++;
    }
    
    return true;
}

NetworkPeer* peer_pool_find(PeerPool* pool, uint8_t* peer_id) {
    for (uint32_t i = 0; i < pool->count; i++) {
        if (memcmp(pool->peers[i].peer_id, peer_id, 32) == 0) {
            return &pool->peers[i];
        }
    }
    return NULL;
}

void peer_pool_update_reputation(PeerPool* pool, uint8_t* peer_id, int32_t delta) {
    NetworkPeer* peer = peer_pool_find(pool, peer_id);
    if (peer) {
        if (delta > 0) {
            peer->reputation += delta;
            if (peer->reputation > 1000) peer->reputation = 1000;
        } else {
            if ((int32_t)peer->reputation + delta < 0) {
                peer->reputation = 0;
            } else {
                peer->reputation += delta;
            }
        }
        
        if (peer->reputation < 10) {
            peer->is_trusted = false;
        }
    }
}

NetworkPeer** peer_pool_get_random_peers(PeerPool* pool, uint32_t count) {
    if (count > pool->count) count = pool->count;
    
    NetworkPeer** selected = (NetworkPeer**)malloc(sizeof(NetworkPeer*) * count);
    bool* used = (bool*)calloc(pool->count, sizeof(bool));
    
    for (uint32_t i = 0; i < count; i++) {
        uint32_t idx;
        do {
            idx = rand() % pool->count;
        } while (used[idx]);
        
        used[idx] = true;
        selected[i] = &pool->peers[idx];
    }
    
    free(used);
    return selected;
}

// =====================================================================================================================
// DHT (Distributed Hash Table) Operations
// =====================================================================================================================

DHTRoutingTable* dht_create(uint8_t* local_id) {
    DHTRoutingTable* dht = (DHTRoutingTable*)malloc(sizeof(DHTRoutingTable));
    dht->capacity = 1000;
    dht->count = 0;
    dht->entries = (DHTEntry*)malloc(sizeof(DHTEntry) * dht->capacity);
    memcpy(dht->local_id, local_id, 32);
    return dht;
}

void dht_destroy(DHTRoutingTable* dht) {
    for (uint32_t i = 0; i < dht->count; i++) {
        free(dht->entries[i].value);
    }
    free(dht->entries);
    free(dht);
}

void dht_put(DHTRoutingTable* dht, uint8_t* key, uint8_t* value, uint32_t value_size, uint32_t ttl) {
    // Check if key exists
    for (uint32_t i = 0; i < dht->count; i++) {
        if (memcmp(dht->entries[i].key, key, 32) == 0) {
            free(dht->entries[i].value);
            dht->entries[i].value = (uint8_t*)malloc(value_size);
            memcpy(dht->entries[i].value, value, value_size);
            dht->entries[i].value_size = value_size;
            dht->entries[i].timestamp = time(NULL);
            dht->entries[i].ttl = ttl;
            return;
        }
    }
    
    // Add new entry
    if (dht->count >= dht->capacity) {
        dht->capacity *= 2;
        dht->entries = (DHTEntry*)realloc(dht->entries, sizeof(DHTEntry) * dht->capacity);
    }
    
    memcpy(dht->entries[dht->count].key, key, 32);
    dht->entries[dht->count].value = (uint8_t*)malloc(value_size);
    memcpy(dht->entries[dht->count].value, value, value_size);
    dht->entries[dht->count].value_size = value_size;
    dht->entries[dht->count].timestamp = time(NULL);
    dht->entries[dht->count].ttl = ttl;
    dht->count++;
}

DHTEntry* dht_get(DHTRoutingTable* dht, uint8_t* key) {
    for (uint32_t i = 0; i < dht->count; i++) {
        if (memcmp(dht->entries[i].key, key, 32) == 0) {
            // Check TTL
            uint64_t now = time(NULL);
            if (now - dht->entries[i].timestamp > dht->entries[i].ttl) {
                return NULL;
            }
            return &dht->entries[i];
        }
    }
    return NULL;
}

void dht_expire_entries(DHTRoutingTable* dht) {
    uint64_t now = time(NULL);
    uint32_t write_idx = 0;
    
    for (uint32_t read_idx = 0; read_idx < dht->count; read_idx++) {
        if (now - dht->entries[read_idx].timestamp <= dht->entries[read_idx].ttl) {
            if (write_idx != read_idx) {
                memcpy(&dht->entries[write_idx], &dht->entries[read_idx], sizeof(DHTEntry));
            }
            write_idx++;
        } else {
            free(dht->entries[read_idx].value);
        }
    }
    
    dht->count = write_idx;
}

// Find k closest nodes to target
void dht_find_closest_nodes(DHTRoutingTable* dht, uint8_t* target, uint8_t result[][32], uint32_t k) {
    uint32_t* distances = (uint32_t*)malloc(sizeof(uint32_t) * dht->count);
    uint32_t* indices = (uint32_t*)malloc(sizeof(uint32_t) * dht->count);
    
    // Calculate distances
    for (uint32_t i = 0; i < dht->count; i++) {
        distances[i] = xor_distance(dht->entries[i].key, target, 32);
        indices[i] = i;
    }
    
    // Sort by distance (simple selection sort for k elements)
    for (uint32_t i = 0; i < k && i < dht->count; i++) {
        uint32_t min_idx = i;
        for (uint32_t j = i + 1; j < dht->count; j++) {
            if (distances[j] < distances[min_idx]) {
                min_idx = j;
            }
        }
        
        if (min_idx != i) {
            uint32_t temp = distances[i];
            distances[i] = distances[min_idx];
            distances[min_idx] = temp;
            
            temp = indices[i];
            indices[i] = indices[min_idx];
            indices[min_idx] = temp;
        }
        
        memcpy(result[i], dht->entries[indices[i]].key, 32);
    }
    
    free(distances);
    free(indices);
}

// =====================================================================================================================
// Kademlia Protocol
// =====================================================================================================================

KBucket* kbucket_create(uint32_t prefix_length) {
    KBucket* bucket = (KBucket*)malloc(sizeof(KBucket));
    bucket->node_count = 0;
    bucket->prefix_length = prefix_length;
    bucket->last_updated = time(NULL);
    return bucket;
}

bool kbucket_add_node(KBucket* bucket, uint8_t* node_id) {
    if (bucket->node_count >= 20) {
        return false;  // Bucket full
    }
    
    // Check if already exists
    for (uint32_t i = 0; i < bucket->node_count; i++) {
        if (memcmp(bucket->node_ids[i], node_id, 32) == 0) {
            return true;  // Already in bucket
        }
    }
    
    memcpy(bucket->node_ids[bucket->node_count], node_id, 32);
    bucket->node_count++;
    bucket->last_updated = time(NULL);
    
    return true;
}

bool kbucket_contains(KBucket* bucket, uint8_t* node_id) {
    for (uint32_t i = 0; i < bucket->node_count; i++) {
        if (memcmp(bucket->node_ids[i], node_id, 32) == 0) {
            return true;
        }
    }
    return false;
}

void kbucket_remove_node(KBucket* bucket, uint8_t* node_id) {
    for (uint32_t i = 0; i < bucket->node_count; i++) {
        if (memcmp(bucket->node_ids[i], node_id, 32) == 0) {
            // Shift remaining nodes
            for (uint32_t j = i; j < bucket->node_count - 1; j++) {
                memcpy(bucket->node_ids[j], bucket->node_ids[j + 1], 32);
            }
            bucket->node_count--;
            break;
        }
    }
}

// =====================================================================================================================
// Gossip Protocol
// =====================================================================================================================

GossipState* gossip_create(uint32_t fanout, uint32_t ttl) {
    GossipState* gossip = (GossipState*)malloc(sizeof(GossipState));
    gossip->fanout = fanout;
    gossip->ttl = ttl;
    gossip->capacity = 10000;
    gossip->message_count = 0;
    gossip->message_ids = (uint8_t**)malloc(sizeof(uint8_t*) * gossip->capacity);
    return gossip;
}

void gossip_destroy(GossipState* gossip) {
    for (uint32_t i = 0; i < gossip->message_count; i++) {
        free(gossip->message_ids[i]);
    }
    free(gossip->message_ids);
    free(gossip);
}

bool gossip_has_seen(GossipState* gossip, uint8_t* message_id) {
    for (uint32_t i = 0; i < gossip->message_count; i++) {
        if (memcmp(gossip->message_ids[i], message_id, 32) == 0) {
            return true;
        }
    }
    return false;
}

void gossip_mark_seen(GossipState* gossip, uint8_t* message_id) {
    if (gossip_has_seen(gossip, message_id)) {
        return;
    }
    
    if (gossip->message_count >= gossip->capacity) {
        // Remove oldest half
        for (uint32_t i = 0; i < gossip->capacity / 2; i++) {
            free(gossip->message_ids[i]);
        }
        
        for (uint32_t i = 0; i < gossip->capacity / 2; i++) {
            gossip->message_ids[i] = gossip->message_ids[i + gossip->capacity / 2];
        }
        
        gossip->message_count = gossip->capacity / 2;
    }
    
    gossip->message_ids[gossip->message_count] = (uint8_t*)malloc(32);
    memcpy(gossip->message_ids[gossip->message_count], message_id, 32);
    gossip->message_count++;
}

void gossip_broadcast(GossipState* gossip, PeerPool* pool, uint8_t* message, 
                      uint32_t message_size) {
    uint8_t message_id[32];
    generate_random_id(message_id, 32);
    
    if (gossip_has_seen(gossip, message_id)) {
        return;
    }
    
    gossip_mark_seen(gossip, message_id);
    
    // Select random peers
    NetworkPeer** peers = peer_pool_get_random_peers(pool, gossip->fanout);
    
    // Send to selected peers (implementation would use actual network send)
    for (uint32_t i = 0; i < gossip->fanout && i < pool->count; i++) {
        // Network send would happen here
        peers[i]->last_seen = time(NULL);
    }
    
    free(peers);
}

// =====================================================================================================================
// Raft Consensus
// =====================================================================================================================

RaftState* raft_create() {
    RaftState* raft = (RaftState*)malloc(sizeof(RaftState));
    raft->role = RAFT_FOLLOWER;
    raft->current_term = 0;
    memset(raft->voted_for, 0, 32);
    raft->commit_index = 0;
    raft->last_applied = 0;
    raft->election_timeout = 150 + (rand() % 150);  // 150-300ms
    raft->heartbeat_interval = 50;  // 50ms
    raft->last_heartbeat = time(NULL);
    return raft;
}

void raft_destroy(RaftState* raft) {
    free(raft);
}

void raft_start_election(RaftState* raft) {
    raft->role = RAFT_CANDIDATE;
    raft->current_term++;
    // Vote for self
    generate_random_id(raft->voted_for, 32);  // Would be own ID
}

bool raft_receive_vote(RaftState* raft, uint64_t term, uint8_t* candidate_id) {
    if (term < raft->current_term) {
        return false;
    }
    
    if (term > raft->current_term) {
        raft->current_term = term;
        raft->role = RAFT_FOLLOWER;
        memset(raft->voted_for, 0, 32);
    }
    
    bool already_voted = false;
    for (uint32_t i = 0; i < 32; i++) {
        if (raft->voted_for[i] != 0) {
            already_voted = true;
            break;
        }
    }
    
    if (!already_voted) {
        memcpy(raft->voted_for, candidate_id, 32);
        return true;
    }
    
    return memcmp(raft->voted_for, candidate_id, 32) == 0;
}

void raft_become_leader(RaftState* raft) {
    raft->role = RAFT_LEADER;
}

void raft_step_down(RaftState* raft) {
    raft->role = RAFT_FOLLOWER;
    memset(raft->voted_for, 0, 32);
}

bool raft_append_entries(RaftState* raft, uint64_t term, uint64_t prev_log_index,
                        uint64_t prev_log_term) {
    if (term < raft->current_term) {
        return false;
    }
    
    if (term > raft->current_term) {
        raft->current_term = term;
        raft_step_down(raft);
    }
    
    raft->last_heartbeat = time(NULL);
    return true;
}

// =====================================================================================================================
// Paxos Consensus
// =====================================================================================================================

PaxosInstance* paxos_create() {
    PaxosInstance* paxos = (PaxosInstance*)malloc(sizeof(PaxosInstance));
    paxos->proposal_number = 0;
    paxos->promised_number = 0;
    paxos->accepted_value = NULL;
    paxos->value_size = 0;
    paxos->decided = false;
    return paxos;
}

void paxos_destroy(PaxosInstance* paxos) {
    if (paxos->accepted_value) {
        free(paxos->accepted_value);
    }
    free(paxos);
}

bool paxos_prepare(PaxosInstance* paxos, uint64_t proposal_number) {
    if (proposal_number > paxos->promised_number) {
        paxos->promised_number = proposal_number;
        return true;
    }
    return false;
}

bool paxos_accept(PaxosInstance* paxos, uint64_t proposal_number, 
                  uint8_t* value, uint32_t value_size) {
    if (proposal_number >= paxos->promised_number) {
        paxos->proposal_number = proposal_number;
        
        if (paxos->accepted_value) {
            free(paxos->accepted_value);
        }
        
        paxos->accepted_value = (uint8_t*)malloc(value_size);
        memcpy(paxos->accepted_value, value, value_size);
        paxos->value_size = value_size;
        
        return true;
    }
    return false;
}

void paxos_decide(PaxosInstance* paxos) {
    paxos->decided = true;
}

// =====================================================================================================================
// Vector Clock
// =====================================================================================================================

VectorClock* vector_clock_create(uint32_t node_count) {
    VectorClock* clock = (VectorClock*)malloc(sizeof(VectorClock));
    clock->node_count = node_count;
    clock->timestamps = (uint64_t*)calloc(node_count, sizeof(uint64_t));
    clock->node_ids = (uint8_t**)malloc(sizeof(uint8_t*) * node_count);
    
    for (uint32_t i = 0; i < node_count; i++) {
        clock->node_ids[i] = (uint8_t*)malloc(32);
        generate_random_id(clock->node_ids[i], 32);
    }
    
    return clock;
}

void vector_clock_destroy(VectorClock* clock) {
    free(clock->timestamps);
    for (uint32_t i = 0; i < clock->node_count; i++) {
        free(clock->node_ids[i]);
    }
    free(clock->node_ids);
    free(clock);
}

void vector_clock_increment(VectorClock* clock, uint32_t node_index) {
    if (node_index < clock->node_count) {
        clock->timestamps[node_index]++;
    }
}

void vector_clock_merge(VectorClock* clock, VectorClock* other) {
    for (uint32_t i = 0; i < clock->node_count && i < other->node_count; i++) {
        if (other->timestamps[i] > clock->timestamps[i]) {
            clock->timestamps[i] = other->timestamps[i];
        }
    }
}

int vector_clock_compare(VectorClock* a, VectorClock* b) {
    bool a_greater = false;
    bool b_greater = false;
    
    for (uint32_t i = 0; i < a->node_count && i < b->node_count; i++) {
        if (a->timestamps[i] > b->timestamps[i]) a_greater = true;
        if (b->timestamps[i] > a->timestamps[i]) b_greater = true;
    }
    
    if (a_greater && !b_greater) return 1;   // a > b
    if (b_greater && !a_greater) return -1;  // b > a
    if (!a_greater && !b_greater) return 0;  // a == b
    return 2;  // Concurrent (a || b)
}

// =====================================================================================================================
// Bloom Filter
// =====================================================================================================================

BloomFilter* bloom_filter_create(uint32_t size, uint32_t num_hashes) {
    BloomFilter* bloom = (BloomFilter*)malloc(sizeof(BloomFilter));
    bloom->size = size;
    bloom->num_hashes = num_hashes;
    bloom->element_count = 0;
    bloom->bits = (uint8_t*)calloc(size / 8 + 1, sizeof(uint8_t));
    return bloom;
}

void bloom_filter_destroy(BloomFilter* bloom) {
    free(bloom->bits);
    free(bloom);
}

void bloom_filter_add(BloomFilter* bloom, uint8_t* data, uint32_t len) {
    for (uint32_t i = 0; i < bloom->num_hashes; i++) {
        uint32_t hash = hash_fnv1a(data, len) + i * 0x9e3779b9;
        uint32_t bit_pos = hash % bloom->size;
        bloom->bits[bit_pos / 8] |= (1 << (bit_pos % 8));
    }
    bloom->element_count++;
}

bool bloom_filter_contains(BloomFilter* bloom, uint8_t* data, uint32_t len) {
    for (uint32_t i = 0; i < bloom->num_hashes; i++) {
        uint32_t hash = hash_fnv1a(data, len) + i * 0x9e3779b9;
        uint32_t bit_pos = hash % bloom->size;
        
        if (!(bloom->bits[bit_pos / 8] & (1 << (bit_pos % 8)))) {
            return false;
        }
    }
    return true;
}

double bloom_filter_false_positive_rate(BloomFilter* bloom) {
    double k = bloom->num_hashes;
    double m = bloom->size;
    double n = bloom->element_count;
    
    return pow(1.0 - exp(-k * n / m), k);
}

// =====================================================================================================================
// Consistent Hashing
// =====================================================================================================================

ConsistentHashRing* consistent_hash_create(uint32_t vnodes_per_node) {
    ConsistentHashRing* ring = (ConsistentHashRing*)malloc(sizeof(ConsistentHashRing));
    ring->node_count = 0;
    ring->vnodes_per_node = vnodes_per_node;
    ring->node_hashes = NULL;
    ring->node_ids = NULL;
    ring->virtual_nodes = NULL;
    return ring;
}

void consistent_hash_destroy(ConsistentHashRing* ring) {
    for (uint32_t i = 0; i < ring->node_count; i++) {
        for (uint32_t j = 0; j < ring->vnodes_per_node; j++) {
            free(ring->node_hashes[i * ring->vnodes_per_node + j]);
        }
        free(ring->node_ids[i]);
    }
    free(ring->node_hashes);
    free(ring->node_ids);
    free(ring->virtual_nodes);
    free(ring);
}

void consistent_hash_add_node(ConsistentHashRing* ring, uint8_t* node_id) {
    ring->node_count++;
    uint32_t total_vnodes = ring->node_count * ring->vnodes_per_node;
    
    ring->node_ids = (uint8_t**)realloc(ring->node_ids, 
                                        sizeof(uint8_t*) * ring->node_count);
    ring->node_hashes = (uint8_t**)realloc(ring->node_hashes, 
                                           sizeof(uint8_t*) * total_vnodes);
    ring->virtual_nodes = (uint32_t*)realloc(ring->virtual_nodes, 
                                             sizeof(uint32_t) * total_vnodes);
    
    uint32_t node_idx = ring->node_count - 1;
    ring->node_ids[node_idx] = (uint8_t*)malloc(32);
    memcpy(ring->node_ids[node_idx], node_id, 32);
    
    // Create virtual nodes
    for (uint32_t i = 0; i < ring->vnodes_per_node; i++) {
        uint32_t vnode_idx = node_idx * ring->vnodes_per_node + i;
        ring->node_hashes[vnode_idx] = (uint8_t*)malloc(32);
        
        // Hash node_id + vnode_index
        uint8_t combined[36];
        memcpy(combined, node_id, 32);
        memcpy(combined + 32, &i, 4);
        
        uint32_t hash = hash_fnv1a(combined, 36);
        memcpy(ring->node_hashes[vnode_idx], &hash, 4);
        ring->virtual_nodes[vnode_idx] = node_idx;
    }
}

uint8_t* consistent_hash_get_node(ConsistentHashRing* ring, uint8_t* key) {
    if (ring->node_count == 0) return NULL;
    
    uint32_t key_hash = hash_fnv1a(key, 32);
    uint32_t total_vnodes = ring->node_count * ring->vnodes_per_node;
    
    // Find closest vnode
    uint32_t min_distance = UINT32_MAX;
    uint32_t closest_vnode = 0;
    
    for (uint32_t i = 0; i < total_vnodes; i++) {
        uint32_t vnode_hash;
        memcpy(&vnode_hash, ring->node_hashes[i], 4);
        
        uint32_t distance = (vnode_hash >= key_hash) ? 
                           (vnode_hash - key_hash) : 
                           (UINT32_MAX - key_hash + vnode_hash);
        
        if (distance < min_distance) {
            min_distance = distance;
            closest_vnode = i;
        }
    }
    
    uint32_t node_idx = ring->virtual_nodes[closest_vnode];
    return ring->node_ids[node_idx];
}

// =====================================================================================================================
// End of Distributed Systems Engine Module
// Lines: ~1000
// Total so far: ~4500 lines
// =====================================================================================================================
