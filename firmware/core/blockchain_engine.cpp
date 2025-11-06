// =====================================================================================================================
// AgroPulse Firmware - Blockchain Engine (C++)
// Distributed ledger, consensus mechanisms, smart contracts, merkle trees, cryptographic verification
// =====================================================================================================================

#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

// SHA-256 Implementation for hashing
#define SHA256_BLOCK_SIZE 32

typedef struct {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
} SHA256_CTX;

// Blockchain structures
typedef struct BlockHeader {
    uint32_t version;
    uint8_t previous_hash[SHA256_BLOCK_SIZE];
    uint8_t merkle_root[SHA256_BLOCK_SIZE];
    uint32_t timestamp;
    uint32_t difficulty;
    uint32_t nonce;
    uint32_t height;
} BlockHeader;

typedef struct Transaction {
    uint8_t tx_id[SHA256_BLOCK_SIZE];
    uint8_t sender_address[32];
    uint8_t receiver_address[32];
    uint64_t amount;
    uint64_t fee;
    uint32_t timestamp;
    uint8_t signature[64];
    uint16_t data_size;
    uint8_t* data;
} Transaction;

typedef struct Block {
    BlockHeader header;
    uint32_t transaction_count;
    Transaction* transactions;
    uint8_t hash[SHA256_BLOCK_SIZE];
} Block;

typedef struct MerkleNode {
    uint8_t hash[SHA256_BLOCK_SIZE];
    struct MerkleNode* left;
    struct MerkleNode* right;
} MerkleNode;

typedef struct Blockchain {
    Block* blocks;
    uint32_t block_count;
    uint32_t max_blocks;
    uint32_t difficulty;
    uint64_t total_supply;
    uint32_t block_time_target;
} Blockchain;

typedef struct UTXO {
    uint8_t tx_id[SHA256_BLOCK_SIZE];
    uint32_t output_index;
    uint8_t address[32];
    uint64_t amount;
    bool spent;
} UTXO;

typedef struct UTXOSet {
    UTXO* utxos;
    uint32_t count;
    uint32_t capacity;
} UTXOSet;

// Smart Contract structures
typedef enum ContractOpcode {
    OP_NOP = 0x00,
    OP_PUSH = 0x01,
    OP_POP = 0x02,
    OP_DUP = 0x03,
    OP_ADD = 0x10,
    OP_SUB = 0x11,
    OP_MUL = 0x12,
    OP_DIV = 0x13,
    OP_MOD = 0x14,
    OP_EQ = 0x20,
    OP_GT = 0x21,
    OP_LT = 0x22,
    OP_AND = 0x30,
    OP_OR = 0x31,
    OP_NOT = 0x32,
    OP_JUMP = 0x40,
    OP_JUMPI = 0x41,
    OP_CALL = 0x50,
    OP_RETURN = 0x51,
    OP_REVERT = 0x52,
    OP_STORE = 0x60,
    OP_LOAD = 0x61,
    OP_BALANCE = 0x70,
    OP_TRANSFER = 0x71,
    OP_TIMESTAMP = 0x72,
    OP_BLOCKHASH = 0x73
} ContractOpcode;

typedef struct SmartContract {
    uint8_t contract_address[32];
    uint8_t* bytecode;
    uint32_t bytecode_size;
    uint8_t owner[32];
    uint64_t balance;
    uint32_t created_at;
    uint8_t storage[1024];
} SmartContract;

typedef struct VMStack {
    uint64_t* data;
    uint32_t size;
    uint32_t capacity;
} VMStack;

typedef struct VirtualMachine {
    VMStack stack;
    uint8_t* memory;
    uint32_t memory_size;
    uint32_t program_counter;
    uint64_t gas_limit;
    uint64_t gas_used;
    SmartContract* contract;
} VirtualMachine;

// Consensus structures
typedef enum ConsensusType {
    CONSENSUS_POW,      // Proof of Work
    CONSENSUS_POS,      // Proof of Stake
    CONSENSUS_PBFT,     // Practical Byzantine Fault Tolerance
    CONSENSUS_RAFT,     // Raft consensus
    CONSENSUS_POA       // Proof of Authority
} ConsensusType;

typedef struct Validator {
    uint8_t address[32];
    uint64_t stake;
    uint32_t vote_count;
    bool active;
    uint32_t reputation;
} Validator;

typedef struct ConsensusEngine {
    ConsensusType type;
    Validator* validators;
    uint32_t validator_count;
    uint32_t min_validators;
    uint32_t byzantine_fault_tolerance;
} ConsensusEngine;

// =====================================================================================================================
// SHA-256 Implementation
// =====================================================================================================================

static const uint32_t k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

#define ROTLEFT(a,b) (((a) << (b)) | ((a) >> (32-(b))))
#define ROTRIGHT(a,b) (((a) >> (b)) | ((a) << (32-(b))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTRIGHT(x,2) ^ ROTRIGHT(x,13) ^ ROTRIGHT(x,22))
#define EP1(x) (ROTRIGHT(x,6) ^ ROTRIGHT(x,11) ^ ROTRIGHT(x,25))
#define SIG0(x) (ROTRIGHT(x,7) ^ ROTRIGHT(x,18) ^ ((x) >> 3))
#define SIG1(x) (ROTRIGHT(x,17) ^ ROTRIGHT(x,19) ^ ((x) >> 10))

void sha256_transform(SHA256_CTX* ctx, const uint8_t data[]) {
    uint32_t a, b, c, d, e, f, g, h, i, j, t1, t2, m[64];
    
    for (i = 0, j = 0; i < 16; ++i, j += 4)
        m[i] = (data[j] << 24) | (data[j + 1] << 16) | (data[j + 2] << 8) | (data[j + 3]);
    
    for (; i < 64; ++i)
        m[i] = SIG1(m[i - 2]) + m[i - 7] + SIG0(m[i - 15]) + m[i - 16];
    
    a = ctx->state[0];
    b = ctx->state[1];
    c = ctx->state[2];
    d = ctx->state[3];
    e = ctx->state[4];
    f = ctx->state[5];
    g = ctx->state[6];
    h = ctx->state[7];
    
    for (i = 0; i < 64; ++i) {
        t1 = h + EP1(e) + CH(e, f, g) + k[i] + m[i];
        t2 = EP0(a) + MAJ(a, b, c);
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }
    
    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

void sha256_init(SHA256_CTX* ctx) {
    ctx->datalen = 0;
    ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667;
    ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372;
    ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f;
    ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab;
    ctx->state[7] = 0x5be0cd19;
}

void sha256_update(SHA256_CTX* ctx, const uint8_t data[], size_t len) {
    uint32_t i;
    
    for (i = 0; i < len; ++i) {
        ctx->data[ctx->datalen] = data[i];
        ctx->datalen++;
        if (ctx->datalen == 64) {
            sha256_transform(ctx, ctx->data);
            ctx->bitlen += 512;
            ctx->datalen = 0;
        }
    }
}

void sha256_final(SHA256_CTX* ctx, uint8_t hash[]) {
    uint32_t i;
    
    i = ctx->datalen;
    
    if (ctx->datalen < 56) {
        ctx->data[i++] = 0x80;
        while (i < 56)
            ctx->data[i++] = 0x00;
    } else {
        ctx->data[i++] = 0x80;
        while (i < 64)
            ctx->data[i++] = 0x00;
        sha256_transform(ctx, ctx->data);
        memset(ctx->data, 0, 56);
    }
    
    ctx->bitlen += ctx->datalen * 8;
    ctx->data[63] = ctx->bitlen;
    ctx->data[62] = ctx->bitlen >> 8;
    ctx->data[61] = ctx->bitlen >> 16;
    ctx->data[60] = ctx->bitlen >> 24;
    ctx->data[59] = ctx->bitlen >> 32;
    ctx->data[58] = ctx->bitlen >> 40;
    ctx->data[57] = ctx->bitlen >> 48;
    ctx->data[56] = ctx->bitlen >> 56;
    sha256_transform(ctx, ctx->data);
    
    for (i = 0; i < 4; ++i) {
        hash[i] = (ctx->state[0] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 4] = (ctx->state[1] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 8] = (ctx->state[2] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 12] = (ctx->state[3] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 16] = (ctx->state[4] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 20] = (ctx->state[5] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 24] = (ctx->state[6] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 28] = (ctx->state[7] >> (24 - i * 8)) & 0x000000ff;
    }
}

// =====================================================================================================================
// Merkle Tree Implementation
// =====================================================================================================================

MerkleNode* merkle_create_node(uint8_t* hash) {
    MerkleNode* node = (MerkleNode*)malloc(sizeof(MerkleNode));
    memcpy(node->hash, hash, SHA256_BLOCK_SIZE);
    node->left = NULL;
    node->right = NULL;
    return node;
}

void merkle_hash_pair(uint8_t* left_hash, uint8_t* right_hash, uint8_t* result) {
    SHA256_CTX ctx;
    uint8_t combined[SHA256_BLOCK_SIZE * 2];
    
    memcpy(combined, left_hash, SHA256_BLOCK_SIZE);
    memcpy(combined + SHA256_BLOCK_SIZE, right_hash, SHA256_BLOCK_SIZE);
    
    sha256_init(&ctx);
    sha256_update(&ctx, combined, SHA256_BLOCK_SIZE * 2);
    sha256_final(&ctx, result);
}

MerkleNode* merkle_build_tree(Transaction* transactions, uint32_t count) {
    if (count == 0) return NULL;
    
    MerkleNode** nodes = (MerkleNode**)malloc(sizeof(MerkleNode*) * count);
    
    // Create leaf nodes
    for (uint32_t i = 0; i < count; i++) {
        nodes[i] = merkle_create_node(transactions[i].tx_id);
    }
    
    uint32_t level_count = count;
    
    // Build tree bottom-up
    while (level_count > 1) {
        uint32_t new_count = (level_count + 1) / 2;
        MerkleNode** new_nodes = (MerkleNode**)malloc(sizeof(MerkleNode*) * new_count);
        
        for (uint32_t i = 0; i < new_count; i++) {
            MerkleNode* left = nodes[i * 2];
            MerkleNode* right = (i * 2 + 1 < level_count) ? nodes[i * 2 + 1] : nodes[i * 2];
            
            uint8_t parent_hash[SHA256_BLOCK_SIZE];
            merkle_hash_pair(left->hash, right->hash, parent_hash);
            
            MerkleNode* parent = merkle_create_node(parent_hash);
            parent->left = left;
            parent->right = right;
            
            new_nodes[i] = parent;
        }
        
        free(nodes);
        nodes = new_nodes;
        level_count = new_count;
    }
    
    MerkleNode* root = nodes[0];
    free(nodes);
    
    return root;
}

// =====================================================================================================================
// Block Operations
// =====================================================================================================================

void block_calculate_hash(Block* block) {
    SHA256_CTX ctx;
    sha256_init(&ctx);
    
    // Hash the header
    sha256_update(&ctx, (uint8_t*)&block->header, sizeof(BlockHeader));
    
    // Hash transaction count
    sha256_update(&ctx, (uint8_t*)&block->transaction_count, sizeof(uint32_t));
    
    // Hash all transactions
    for (uint32_t i = 0; i < block->transaction_count; i++) {
        sha256_update(&ctx, block->transactions[i].tx_id, SHA256_BLOCK_SIZE);
    }
    
    sha256_final(&ctx, block->hash);
}

bool block_validate_hash(Block* block) {
    uint8_t calculated_hash[SHA256_BLOCK_SIZE];
    SHA256_CTX ctx;
    
    sha256_init(&ctx);
    sha256_update(&ctx, (uint8_t*)&block->header, sizeof(BlockHeader));
    sha256_update(&ctx, (uint8_t*)&block->transaction_count, sizeof(uint32_t));
    
    for (uint32_t i = 0; i < block->transaction_count; i++) {
        sha256_update(&ctx, block->transactions[i].tx_id, SHA256_BLOCK_SIZE);
    }
    
    sha256_final(&ctx, calculated_hash);
    
    return memcmp(calculated_hash, block->hash, SHA256_BLOCK_SIZE) == 0;
}

bool block_meets_difficulty(Block* block, uint32_t difficulty) {
    uint32_t leading_zeros = 0;
    
    for (uint32_t i = 0; i < SHA256_BLOCK_SIZE; i++) {
        if (block->hash[i] == 0) {
            leading_zeros += 8;
        } else {
            uint8_t byte = block->hash[i];
            while (byte < 128) {
                leading_zeros++;
                byte <<= 1;
            }
            break;
        }
    }
    
    return leading_zeros >= difficulty;
}

bool block_mine(Block* block, uint32_t difficulty) {
    block->header.nonce = 0;
    
    while (block->header.nonce < UINT32_MAX) {
        block_calculate_hash(block);
        
        if (block_meets_difficulty(block, difficulty)) {
            return true;
        }
        
        block->header.nonce++;
    }
    
    return false;
}

// =====================================================================================================================
// Transaction Operations
// =====================================================================================================================

void transaction_calculate_id(Transaction* tx) {
    SHA256_CTX ctx;
    sha256_init(&ctx);
    
    sha256_update(&ctx, tx->sender_address, 32);
    sha256_update(&ctx, tx->receiver_address, 32);
    sha256_update(&ctx, (uint8_t*)&tx->amount, sizeof(uint64_t));
    sha256_update(&ctx, (uint8_t*)&tx->fee, sizeof(uint64_t));
    sha256_update(&ctx, (uint8_t*)&tx->timestamp, sizeof(uint32_t));
    
    if (tx->data && tx->data_size > 0) {
        sha256_update(&ctx, tx->data, tx->data_size);
    }
    
    sha256_final(&ctx, tx->tx_id);
}

bool transaction_validate(Transaction* tx) {
    // Validate transaction has non-zero amount
    if (tx->amount == 0) return false;
    
    // Validate addresses are different
    if (memcmp(tx->sender_address, tx->receiver_address, 32) == 0) return false;
    
    // Validate timestamp is reasonable
    uint32_t current_time = (uint32_t)time(NULL);
    if (tx->timestamp > current_time + 3600) return false; // Not more than 1 hour in future
    
    // Calculate and verify transaction ID
    uint8_t calculated_id[SHA256_BLOCK_SIZE];
    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, tx->sender_address, 32);
    sha256_update(&ctx, tx->receiver_address, 32);
    sha256_update(&ctx, (uint8_t*)&tx->amount, sizeof(uint64_t));
    sha256_update(&ctx, (uint8_t*)&tx->fee, sizeof(uint64_t));
    sha256_update(&ctx, (uint8_t*)&tx->timestamp, sizeof(uint32_t));
    if (tx->data && tx->data_size > 0) {
        sha256_update(&ctx, tx->data, tx->data_size);
    }
    sha256_final(&ctx, calculated_id);
    
    return memcmp(calculated_id, tx->tx_id, SHA256_BLOCK_SIZE) == 0;
}

// =====================================================================================================================
// UTXO Set Operations
// =====================================================================================================================

UTXOSet* utxo_set_create(uint32_t capacity) {
    UTXOSet* set = (UTXOSet*)malloc(sizeof(UTXOSet));
    set->utxos = (UTXO*)malloc(sizeof(UTXO) * capacity);
    set->count = 0;
    set->capacity = capacity;
    return set;
}

void utxo_set_add(UTXOSet* set, UTXO* utxo) {
    if (set->count >= set->capacity) {
        set->capacity *= 2;
        set->utxos = (UTXO*)realloc(set->utxos, sizeof(UTXO) * set->capacity);
    }
    
    memcpy(&set->utxos[set->count], utxo, sizeof(UTXO));
    set->count++;
}

UTXO* utxo_set_find(UTXOSet* set, uint8_t* tx_id, uint32_t output_index) {
    for (uint32_t i = 0; i < set->count; i++) {
        if (memcmp(set->utxos[i].tx_id, tx_id, SHA256_BLOCK_SIZE) == 0 &&
            set->utxos[i].output_index == output_index) {
            return &set->utxos[i];
        }
    }
    return NULL;
}

bool utxo_set_spend(UTXOSet* set, uint8_t* tx_id, uint32_t output_index) {
    UTXO* utxo = utxo_set_find(set, tx_id, output_index);
    if (utxo && !utxo->spent) {
        utxo->spent = true;
        return true;
    }
    return false;
}

uint64_t utxo_set_get_balance(UTXOSet* set, uint8_t* address) {
    uint64_t balance = 0;
    
    for (uint32_t i = 0; i < set->count; i++) {
        if (!set->utxos[i].spent && 
            memcmp(set->utxos[i].address, address, 32) == 0) {
            balance += set->utxos[i].amount;
        }
    }
    
    return balance;
}

// =====================================================================================================================
// Smart Contract VM Implementation
// =====================================================================================================================

VirtualMachine* vm_create(uint64_t gas_limit) {
    VirtualMachine* vm = (VirtualMachine*)malloc(sizeof(VirtualMachine));
    
    vm->stack.capacity = 1024;
    vm->stack.size = 0;
    vm->stack.data = (uint64_t*)malloc(sizeof(uint64_t) * vm->stack.capacity);
    
    vm->memory_size = 4096;
    vm->memory = (uint8_t*)calloc(vm->memory_size, sizeof(uint8_t));
    
    vm->program_counter = 0;
    vm->gas_limit = gas_limit;
    vm->gas_used = 0;
    vm->contract = NULL;
    
    return vm;
}

void vm_destroy(VirtualMachine* vm) {
    free(vm->stack.data);
    free(vm->memory);
    free(vm);
}

bool vm_stack_push(VirtualMachine* vm, uint64_t value) {
    if (vm->stack.size >= vm->stack.capacity) {
        return false;
    }
    
    vm->stack.data[vm->stack.size++] = value;
    return true;
}

bool vm_stack_pop(VirtualMachine* vm, uint64_t* value) {
    if (vm->stack.size == 0) {
        return false;
    }
    
    *value = vm->stack.data[--vm->stack.size];
    return true;
}

bool vm_use_gas(VirtualMachine* vm, uint64_t amount) {
    if (vm->gas_used + amount > vm->gas_limit) {
        return false;
    }
    
    vm->gas_used += amount;
    return true;
}

int vm_execute(VirtualMachine* vm, SmartContract* contract) {
    vm->contract = contract;
    vm->program_counter = 0;
    vm->gas_used = 0;
    
    while (vm->program_counter < contract->bytecode_size) {
        if (!vm_use_gas(vm, 1)) {
            return -1; // Out of gas
        }
        
        uint8_t opcode = contract->bytecode[vm->program_counter++];
        
        switch (opcode) {
            case OP_NOP:
                break;
                
            case OP_PUSH: {
                if (vm->program_counter + 8 > contract->bytecode_size) return -2;
                uint64_t value = 0;
                memcpy(&value, &contract->bytecode[vm->program_counter], 8);
                vm->program_counter += 8;
                if (!vm_stack_push(vm, value)) return -3;
                break;
            }
            
            case OP_POP: {
                uint64_t value;
                if (!vm_stack_pop(vm, &value)) return -4;
                break;
            }
            
            case OP_DUP: {
                if (vm->stack.size == 0) return -5;
                uint64_t value = vm->stack.data[vm->stack.size - 1];
                if (!vm_stack_push(vm, value)) return -6;
                break;
            }
            
            case OP_ADD: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -7;
                if (!vm_stack_push(vm, a + b)) return -8;
                break;
            }
            
            case OP_SUB: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -9;
                if (!vm_stack_push(vm, a - b)) return -10;
                break;
            }
            
            case OP_MUL: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -11;
                if (!vm_stack_push(vm, a * b)) return -12;
                break;
            }
            
            case OP_DIV: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -13;
                if (b == 0) return -14; // Division by zero
                if (!vm_stack_push(vm, a / b)) return -15;
                break;
            }
            
            case OP_EQ: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -16;
                if (!vm_stack_push(vm, a == b ? 1 : 0)) return -17;
                break;
            }
            
            case OP_GT: {
                uint64_t a, b;
                if (!vm_stack_pop(vm, &b) || !vm_stack_pop(vm, &a)) return -18;
                if (!vm_stack_push(vm, a > b ? 1 : 0)) return -19;
                break;
            }
            
            case OP_STORE: {
                uint64_t addr, value;
                if (!vm_stack_pop(vm, &value) || !vm_stack_pop(vm, &addr)) return -20;
                if (addr >= 1024) return -21;
                memcpy(&contract->storage[addr], &value, sizeof(uint64_t));
                break;
            }
            
            case OP_LOAD: {
                uint64_t addr;
                if (!vm_stack_pop(vm, &addr)) return -22;
                if (addr >= 1024) return -23;
                uint64_t value;
                memcpy(&value, &contract->storage[addr], sizeof(uint64_t));
                if (!vm_stack_push(vm, value)) return -24;
                break;
            }
            
            case OP_BALANCE: {
                if (!vm_stack_push(vm, contract->balance)) return -25;
                break;
            }
            
            case OP_TIMESTAMP: {
                uint32_t timestamp = (uint32_t)time(NULL);
                if (!vm_stack_push(vm, timestamp)) return -26;
                break;
            }
            
            case OP_RETURN: {
                return 0; // Success
            }
            
            case OP_REVERT: {
                return -27; // Revert
            }
            
            default:
                return -28; // Unknown opcode
        }
    }
    
    return 0;
}

// =====================================================================================================================
// Blockchain Operations
// =====================================================================================================================

Blockchain* blockchain_create(uint32_t max_blocks, uint32_t difficulty) {
    Blockchain* chain = (Blockchain*)malloc(sizeof(Blockchain));
    chain->blocks = (Block*)malloc(sizeof(Block) * max_blocks);
    chain->block_count = 0;
    chain->max_blocks = max_blocks;
    chain->difficulty = difficulty;
    chain->total_supply = 0;
    chain->block_time_target = 600; // 10 minutes
    
    return chain;
}

Block* blockchain_create_genesis_block(Blockchain* chain) {
    Block* genesis = &chain->blocks[0];
    
    genesis->header.version = 1;
    memset(genesis->header.previous_hash, 0, SHA256_BLOCK_SIZE);
    memset(genesis->header.merkle_root, 0, SHA256_BLOCK_SIZE);
    genesis->header.timestamp = (uint32_t)time(NULL);
    genesis->header.difficulty = chain->difficulty;
    genesis->header.nonce = 0;
    genesis->header.height = 0;
    
    genesis->transaction_count = 0;
    genesis->transactions = NULL;
    
    block_mine(genesis, chain->difficulty);
    
    chain->block_count = 1;
    
    return genesis;
}

bool blockchain_add_block(Blockchain* chain, Block* block) {
    if (chain->block_count >= chain->max_blocks) {
        return false;
    }
    
    // Validate previous hash
    if (chain->block_count > 0) {
        Block* prev_block = &chain->blocks[chain->block_count - 1];
        if (memcmp(block->header.previous_hash, prev_block->hash, SHA256_BLOCK_SIZE) != 0) {
            return false;
        }
    }
    
    // Validate block hash
    if (!block_validate_hash(block)) {
        return false;
    }
    
    // Validate difficulty
    if (!block_meets_difficulty(block, chain->difficulty)) {
        return false;
    }
    
    // Add block
    memcpy(&chain->blocks[chain->block_count], block, sizeof(Block));
    chain->block_count++;
    
    return true;
}

Block* blockchain_get_latest_block(Blockchain* chain) {
    if (chain->block_count == 0) return NULL;
    return &chain->blocks[chain->block_count - 1];
}

bool blockchain_validate_chain(Blockchain* chain) {
    for (uint32_t i = 1; i < chain->block_count; i++) {
        Block* current = &chain->blocks[i];
        Block* previous = &chain->blocks[i - 1];
        
        // Validate hash
        if (!block_validate_hash(current)) {
            return false;
        }
        
        // Validate previous hash link
        if (memcmp(current->header.previous_hash, previous->hash, SHA256_BLOCK_SIZE) != 0) {
            return false;
        }
        
        // Validate difficulty
        if (!block_meets_difficulty(current, chain->difficulty)) {
            return false;
        }
    }
    
    return true;
}

// =====================================================================================================================
// Consensus Engine Implementation
// =====================================================================================================================

ConsensusEngine* consensus_create(ConsensusType type, uint32_t min_validators) {
    ConsensusEngine* engine = (ConsensusEngine*)malloc(sizeof(ConsensusEngine));
    engine->type = type;
    engine->validators = NULL;
    engine->validator_count = 0;
    engine->min_validators = min_validators;
    engine->byzantine_fault_tolerance = (min_validators * 2) / 3 + 1;
    
    return engine;
}

void consensus_add_validator(ConsensusEngine* engine, uint8_t* address, uint64_t stake) {
    engine->validator_count++;
    engine->validators = (Validator*)realloc(engine->validators, 
                                             sizeof(Validator) * engine->validator_count);
    
    Validator* validator = &engine->validators[engine->validator_count - 1];
    memcpy(validator->address, address, 32);
    validator->stake = stake;
    validator->vote_count = 0;
    validator->active = true;
    validator->reputation = 100;
}

bool consensus_pow_validate(ConsensusEngine* engine, Block* block) {
    return block_meets_difficulty(block, block->header.difficulty);
}

Validator* consensus_pos_select_validator(ConsensusEngine* engine) {
    if (engine->validator_count == 0) return NULL;
    
    uint64_t total_stake = 0;
    for (uint32_t i = 0; i < engine->validator_count; i++) {
        if (engine->validators[i].active) {
            total_stake += engine->validators[i].stake;
        }
    }
    
    if (total_stake == 0) return NULL;
    
    uint64_t random_stake = rand() % total_stake;
    uint64_t current_stake = 0;
    
    for (uint32_t i = 0; i < engine->validator_count; i++) {
        if (engine->validators[i].active) {
            current_stake += engine->validators[i].stake;
            if (current_stake > random_stake) {
                return &engine->validators[i];
            }
        }
    }
    
    return NULL;
}

bool consensus_pbft_validate(ConsensusEngine* engine, Block* block) {
    uint32_t votes = 0;
    
    for (uint32_t i = 0; i < engine->validator_count; i++) {
        if (engine->validators[i].active && engine->validators[i].vote_count > 0) {
            votes++;
        }
    }
    
    return votes >= engine->byzantine_fault_tolerance;
}

// =====================================================================================================================
// End of Blockchain Engine Module
// Lines: ~1050
// =====================================================================================================================
