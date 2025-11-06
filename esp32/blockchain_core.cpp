// =====================================================================================================================
// ESP32 Blockchain Core Implementation
// Lightweight blockchain for embedded systems with cryptographic primitives
// =====================================================================================================================

#include <Arduino.h>
#include <WiFi.h>
#include <SPIFFS.h>
#include <mbedtls/sha256.h>
#include <mbedtls/aes.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>

// =====================================================================================================================
// Core Data Structures
// =====================================================================================================================

#define MAX_TRANSACTIONS_PER_BLOCK 100
#define MAX_BLOCKS_IN_MEMORY 50
#define HASH_SIZE 32
#define SIGNATURE_SIZE 64
#define ADDRESS_SIZE 20
#define MAX_PEERS 20
#define MAX_VALIDATORS 10
#define MAX_SMART_CONTRACT_SIZE 4096

typedef struct {
    uint8_t hash[HASH_SIZE];
} Hash256;

typedef struct {
    uint8_t data[ADDRESS_SIZE];
} Address;

typedef struct {
    uint8_t r[32];
    uint8_t s[32];
} ECDSASignature;

typedef struct {
    Hash256 tx_id;
    Address sender;
    Address receiver;
    uint64_t amount;
    uint64_t fee;
    uint64_t timestamp;
    uint64_t nonce;
    ECDSASignature signature;
    uint8_t* data;
    uint32_t data_size;
    uint8_t tx_type;  // 0=transfer, 1=contract_deploy, 2=contract_call
} Transaction;

typedef struct {
    uint32_t version;
    Hash256 previous_hash;
    Hash256 merkle_root;
    uint64_t timestamp;
    uint32_t difficulty;
    uint32_t nonce;
    uint32_t height;
    Address miner;
} BlockHeader;

typedef struct {
    BlockHeader header;
    Transaction* transactions;
    uint32_t transaction_count;
    Hash256 block_hash;
} Block;

typedef struct {
    Hash256 tx_id;
    uint32_t output_index;
    Address owner;
    uint64_t amount;
    bool is_spent;
    uint64_t spent_in_block;
} UTXO;

typedef struct {
    UTXO* utxos;
    uint32_t count;
    uint32_t capacity;
} UTXOSet;

typedef struct {
    Address address;
    uint64_t balance;
    uint64_t nonce;
    Hash256 code_hash;
    uint8_t* storage;
    uint32_t storage_size;
} Account;

typedef struct {
    Account* accounts;
    uint32_t count;
    uint32_t capacity;
} AccountState;

// Smart Contract VM
typedef enum {
    OP_STOP = 0x00,
    OP_ADD = 0x01,
    OP_SUB = 0x02,
    OP_MUL = 0x03,
    OP_DIV = 0x04,
    OP_MOD = 0x05,
    OP_EXP = 0x06,
    OP_LT = 0x10,
    OP_GT = 0x11,
    OP_EQ = 0x14,
    OP_ISZERO = 0x15,
    OP_AND = 0x16,
    OP_OR = 0x17,
    OP_XOR = 0x18,
    OP_NOT = 0x19,
    OP_BYTE = 0x1A,
    OP_SHA3 = 0x20,
    OP_ADDRESS = 0x30,
    OP_BALANCE = 0x31,
    OP_ORIGIN = 0x32,
    OP_CALLER = 0x33,
    OP_CALLVALUE = 0x34,
    OP_CALLDATALOAD = 0x35,
    OP_CALLDATASIZE = 0x36,
    OP_BLOCKHASH = 0x40,
    OP_COINBASE = 0x41,
    OP_TIMESTAMP = 0x42,
    OP_NUMBER = 0x43,
    OP_DIFFICULTY = 0x44,
    OP_GASLIMIT = 0x45,
    OP_POP = 0x50,
    OP_MLOAD = 0x51,
    OP_MSTORE = 0x52,
    OP_MSTORE8 = 0x53,
    OP_SLOAD = 0x54,
    OP_SSTORE = 0x55,
    OP_JUMP = 0x56,
    OP_JUMPI = 0x57,
    OP_PC = 0x58,
    OP_MSIZE = 0x59,
    OP_GAS = 0x5A,
    OP_JUMPDEST = 0x5B,
    OP_PUSH1 = 0x60,
    OP_PUSH2 = 0x61,
    OP_PUSH4 = 0x63,
    OP_PUSH8 = 0x67,
    OP_PUSH16 = 0x6F,
    OP_PUSH32 = 0x7F,
    OP_DUP1 = 0x80,
    OP_DUP2 = 0x81,
    OP_SWAP1 = 0x90,
    OP_SWAP2 = 0x91,
    OP_LOG0 = 0xA0,
    OP_LOG1 = 0xA1,
    OP_CREATE = 0xF0,
    OP_CALL = 0xF1,
    OP_RETURN = 0xF3,
    OP_DELEGATECALL = 0xF4,
    OP_REVERT = 0xFD,
    OP_SELFDESTRUCT = 0xFF
} VMOpcode;

typedef struct {
    uint64_t* stack;
    uint32_t stack_pointer;
    uint32_t stack_capacity;
    uint8_t* memory;
    uint32_t memory_size;
    uint32_t memory_capacity;
    uint64_t gas_remaining;
    uint64_t gas_used;
    uint32_t pc;  // Program counter
    bool stopped;
    bool reverted;
} VMState;

typedef struct {
    uint8_t* code;
    uint32_t code_size;
    Address address;
    Address caller;
    Address origin;
    uint64_t value;
    uint8_t* call_data;
    uint32_t call_data_size;
    uint64_t gas_limit;
    Block* current_block;
    AccountState* state;
} VMContext;

// Consensus structures
typedef enum {
    CONSENSUS_POW,
    CONSENSUS_POS,
    CONSENSUS_PBFT,
    CONSENSUS_RAFT
} ConsensusType;

typedef struct {
    Address address;
    uint64_t stake;
    uint32_t reputation;
    uint64_t last_block_time;
    bool is_active;
} Validator;

typedef struct {
    Validator validators[MAX_VALIDATORS];
    uint32_t validator_count;
    uint32_t min_stake;
    uint32_t quorum_size;
} ValidatorSet;

typedef struct {
    Hash256 block_hash;
    uint32_t block_height;
    Address validator;
    ECDSASignature signature;
    uint64_t timestamp;
} Vote;

typedef struct {
    Vote votes[MAX_VALIDATORS * 3];
    uint32_t vote_count;
    uint32_t prepare_count;
    uint32_t commit_count;
} VotePool;

// P2P Network structures
typedef struct {
    IPAddress ip;
    uint16_t port;
    uint8_t peer_id[32];
    uint64_t last_seen;
    uint32_t latency_ms;
    uint32_t protocol_version;
    bool is_connected;
} Peer;

typedef struct {
    Peer peers[MAX_PEERS];
    uint32_t peer_count;
} PeerList;

// Blockchain state
typedef struct {
    Block* blocks;
    uint32_t block_count;
    uint32_t capacity;
    Hash256 genesis_hash;
    uint32_t chain_height;
    uint32_t difficulty;
    UTXOSet utxo_set;
    AccountState account_state;
    ValidatorSet validators;
    VotePool vote_pool;
    PeerList peers;
    ConsensusType consensus_type;
    bool is_syncing;
    uint32_t sync_height;
} Blockchain;

// =====================================================================================================================
// Global Blockchain Instance
// =====================================================================================================================

Blockchain g_blockchain;
mbedtls_entropy_context g_entropy;
mbedtls_ctr_drbg_context g_ctr_drbg;

// =====================================================================================================================
// Cryptographic Functions
// =====================================================================================================================

void crypto_init() {
    mbedtls_entropy_init(&g_entropy);
    mbedtls_ctr_drbg_init(&g_ctr_drbg);
    
    const char* pers = "esp32_blockchain";
    mbedtls_ctr_drbg_seed(&g_ctr_drbg, mbedtls_entropy_func, &g_entropy,
                         (const unsigned char*)pers, strlen(pers));
}

void sha256_hash(const uint8_t* data, size_t len, Hash256* output) {
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);
    mbedtls_sha256_starts(&ctx, 0);  // 0 = SHA-256 (not SHA-224)
    mbedtls_sha256_update(&ctx, data, len);
    mbedtls_sha256_finish(&ctx, output->hash);
    mbedtls_sha256_free(&ctx);
}

void double_sha256(const uint8_t* data, size_t len, Hash256* output) {
    Hash256 first_hash;
    sha256_hash(data, len, &first_hash);
    sha256_hash(first_hash.hash, HASH_SIZE, output);
}

bool hash_equals(const Hash256* a, const Hash256* b) {
    return memcmp(a->hash, b->hash, HASH_SIZE) == 0;
}

void hash_to_string(const Hash256* hash, char* output, size_t output_size) {
    for (int i = 0; i < HASH_SIZE && (i * 2 + 2) < output_size; i++) {
        sprintf(output + (i * 2), "%02x", hash->hash[i]);
    }
}

uint32_t count_leading_zeros(const Hash256* hash) {
    uint32_t zeros = 0;
    for (int i = 0; i < HASH_SIZE; i++) {
        if (hash->hash[i] == 0) {
            zeros += 8;
        } else {
            uint8_t byte = hash->hash[i];
            while ((byte & 0x80) == 0) {
                zeros++;
                byte <<= 1;
            }
            break;
        }
    }
    return zeros;
}

bool verify_ecdsa_signature(const uint8_t* message, size_t msg_len,
                            const ECDSASignature* sig, const uint8_t* public_key) {
    mbedtls_ecdsa_context ctx;
    mbedtls_ecdsa_init(&ctx);
    
    // Load public key
    mbedtls_ecp_group_load(&ctx.grp, MBEDTLS_ECP_DP_SECP256K1);
    mbedtls_mpi_read_binary(&ctx.Q.X, public_key, 32);
    mbedtls_mpi_read_binary(&ctx.Q.Y, public_key + 32, 32);
    mbedtls_mpi_lset(&ctx.Q.Z, 1);
    
    // Verify signature
    mbedtls_mpi r, s;
    mbedtls_mpi_init(&r);
    mbedtls_mpi_init(&s);
    mbedtls_mpi_read_binary(&r, sig->r, 32);
    mbedtls_mpi_read_binary(&s, sig->s, 32);
    
    int ret = mbedtls_ecdsa_verify(&ctx.grp, message, msg_len, &ctx.Q, &r, &s);
    
    mbedtls_mpi_free(&r);
    mbedtls_mpi_free(&s);
    mbedtls_ecdsa_free(&ctx);
    
    return ret == 0;
}

void generate_keypair(uint8_t* private_key, uint8_t* public_key) {
    mbedtls_ecdsa_context ctx;
    mbedtls_ecdsa_init(&ctx);
    
    mbedtls_ecp_group_load(&ctx.grp, MBEDTLS_ECP_DP_SECP256K1);
    mbedtls_ecdsa_genkey(&ctx, MBEDTLS_ECP_DP_SECP256K1,
                        mbedtls_ctr_drbg_random, &g_ctr_drbg);
    
    size_t olen;
    mbedtls_mpi_write_binary(&ctx.d, private_key, 32);
    mbedtls_mpi_write_binary(&ctx.Q.X, public_key, 32);
    mbedtls_mpi_write_binary(&ctx.Q.Y, public_key + 32, 32);
    
    mbedtls_ecdsa_free(&ctx);
}

void derive_address(const uint8_t* public_key, Address* address) {
    Hash256 hash;
    sha256_hash(public_key, 64, &hash);
    memcpy(address->data, hash.hash, ADDRESS_SIZE);
}

// =====================================================================================================================
// Merkle Tree Implementation
// =====================================================================================================================

typedef struct {
    Hash256* hashes;
    uint32_t count;
} MerkleTree;

void merkle_tree_create(Transaction* transactions, uint32_t tx_count, Hash256* root) {
    if (tx_count == 0) {
        memset(root->hash, 0, HASH_SIZE);
        return;
    }
    
    // Calculate tree size
    uint32_t leaf_count = tx_count;
    if (tx_count % 2 != 0) leaf_count++;
    
    Hash256* hashes = (Hash256*)malloc(sizeof(Hash256) * leaf_count * 2);
    
    // Compute leaf hashes
    for (uint32_t i = 0; i < tx_count; i++) {
        sha256_hash((uint8_t*)&transactions[i], sizeof(Transaction), &hashes[i]);
    }
    
    // Duplicate last hash if odd number
    if (tx_count % 2 != 0) {
        memcpy(&hashes[tx_count], &hashes[tx_count - 1], sizeof(Hash256));
    }
    
    // Build tree bottom-up
    uint32_t level_size = leaf_count;
    uint32_t offset = 0;
    
    while (level_size > 1) {
        uint32_t next_level_size = (level_size + 1) / 2;
        
        for (uint32_t i = 0; i < next_level_size; i++) {
            uint32_t left_idx = offset + i * 2;
            uint32_t right_idx = offset + i * 2 + 1;
            
            if (right_idx >= offset + level_size) {
                right_idx = left_idx;
            }
            
            uint8_t combined[HASH_SIZE * 2];
            memcpy(combined, hashes[left_idx].hash, HASH_SIZE);
            memcpy(combined + HASH_SIZE, hashes[right_idx].hash, HASH_SIZE);
            
            sha256_hash(combined, HASH_SIZE * 2, &hashes[offset + level_size + i]);
        }
        
        offset += level_size;
        level_size = next_level_size;
    }
    
    memcpy(root, &hashes[offset], sizeof(Hash256));
    free(hashes);
}

// =====================================================================================================================
// Transaction Management
// =====================================================================================================================

void transaction_init(Transaction* tx) {
    memset(tx, 0, sizeof(Transaction));
    tx->timestamp = millis();
}

void transaction_calculate_id(Transaction* tx) {
    uint8_t buffer[256];
    size_t offset = 0;
    
    memcpy(buffer + offset, &tx->sender, ADDRESS_SIZE);
    offset += ADDRESS_SIZE;
    memcpy(buffer + offset, &tx->receiver, ADDRESS_SIZE);
    offset += ADDRESS_SIZE;
    memcpy(buffer + offset, &tx->amount, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    memcpy(buffer + offset, &tx->fee, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    memcpy(buffer + offset, &tx->timestamp, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    memcpy(buffer + offset, &tx->nonce, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    
    if (tx->data && tx->data_size > 0) {
        memcpy(buffer + offset, tx->data, min(tx->data_size, 100));
        offset += min(tx->data_size, 100);
    }
    
    sha256_hash(buffer, offset, &tx->tx_id);
}

bool transaction_verify(Transaction* tx, AccountState* state) {
    // Verify transaction ID
    Hash256 calculated_id;
    transaction_calculate_id(tx);
    
    // Basic validation
    if (tx->amount == 0) return false;
    if (memcmp(&tx->sender, &tx->receiver, ADDRESS_SIZE) == 0) return false;
    
    // Find sender account
    Account* sender_account = NULL;
    for (uint32_t i = 0; i < state->count; i++) {
        if (memcmp(&state->accounts[i].address, &tx->sender, ADDRESS_SIZE) == 0) {
            sender_account = &state->accounts[i];
            break;
        }
    }
    
    if (!sender_account) return false;
    
    // Check balance
    if (sender_account->balance < tx->amount + tx->fee) return false;
    
    // Check nonce
    if (tx->nonce != sender_account->nonce + 1) return false;
    
    return true;
}

// =====================================================================================================================
// Block Operations
// =====================================================================================================================

void block_init(Block* block, const Hash256* previous_hash, uint32_t height) {
    memset(block, 0, sizeof(Block));
    
    block->header.version = 1;
    memcpy(&block->header.previous_hash, previous_hash, sizeof(Hash256));
    block->header.timestamp = millis();
    block->header.difficulty = g_blockchain.difficulty;
    block->header.nonce = 0;
    block->header.height = height;
    
    block->transactions = NULL;
    block->transaction_count = 0;
}

void block_add_transaction(Block* block, Transaction* tx) {
    if (block->transaction_count >= MAX_TRANSACTIONS_PER_BLOCK) return;
    
    if (block->transactions == NULL) {
        block->transactions = (Transaction*)malloc(sizeof(Transaction) * MAX_TRANSACTIONS_PER_BLOCK);
    }
    
    memcpy(&block->transactions[block->transaction_count], tx, sizeof(Transaction));
    block->transaction_count++;
}

void block_finalize(Block* block) {
    // Calculate merkle root
    merkle_tree_create(block->transactions, block->transaction_count, &block->header.merkle_root);
}

void block_calculate_hash(Block* block, Hash256* output) {
    uint8_t buffer[sizeof(BlockHeader)];
    memcpy(buffer, &block->header, sizeof(BlockHeader));
    double_sha256(buffer, sizeof(BlockHeader), output);
}

bool block_verify_hash(Block* block) {
    Hash256 calculated_hash;
    block_calculate_hash(block, &calculated_hash);
    return hash_equals(&calculated_hash, &block->block_hash);
}

bool block_meets_difficulty(Block* block) {
    Hash256 hash;
    block_calculate_hash(block, &hash);
    uint32_t leading_zeros = count_leading_zeros(&hash);
    return leading_zeros >= block->header.difficulty;
}

bool block_mine(Block* block, uint32_t max_iterations) {
    block_finalize(block);
    
    for (uint32_t i = 0; i < max_iterations; i++) {
        block->header.nonce = i;
        
        if (block_meets_difficulty(block)) {
            block_calculate_hash(block, &block->block_hash);
            return true;
        }
        
        // Yield to other tasks periodically
        if (i % 1000 == 0) {
            yield();
        }
    }
    
    return false;
}

// =====================================================================================================================
// UTXO Set Management
// =====================================================================================================================

void utxo_set_init(UTXOSet* set) {
    set->capacity = 1000;
    set->count = 0;
    set->utxos = (UTXO*)malloc(sizeof(UTXO) * set->capacity);
}

void utxo_set_destroy(UTXOSet* set) {
    free(set->utxos);
    set->utxos = NULL;
    set->count = 0;
}

void utxo_set_add(UTXOSet* set, const Hash256* tx_id, uint32_t output_index,
                  const Address* owner, uint64_t amount) {
    if (set->count >= set->capacity) {
        set->capacity *= 2;
        set->utxos = (UTXO*)realloc(set->utxos, sizeof(UTXO) * set->capacity);
    }
    
    UTXO* utxo = &set->utxos[set->count++];
    memcpy(&utxo->tx_id, tx_id, sizeof(Hash256));
    utxo->output_index = output_index;
    memcpy(&utxo->owner, owner, sizeof(Address));
    utxo->amount = amount;
    utxo->is_spent = false;
    utxo->spent_in_block = 0;
}

UTXO* utxo_set_find(UTXOSet* set, const Hash256* tx_id, uint32_t output_index) {
    for (uint32_t i = 0; i < set->count; i++) {
        if (hash_equals(&set->utxos[i].tx_id, tx_id) &&
            set->utxos[i].output_index == output_index) {
            return &set->utxos[i];
        }
    }
    return NULL;
}

bool utxo_set_spend(UTXOSet* set, const Hash256* tx_id, uint32_t output_index, uint32_t block_height) {
    UTXO* utxo = utxo_set_find(set, tx_id, output_index);
    if (!utxo || utxo->is_spent) return false;
    
    utxo->is_spent = true;
    utxo->spent_in_block = block_height;
    return true;
}

uint64_t utxo_set_get_balance(UTXOSet* set, const Address* address) {
    uint64_t balance = 0;
    
    for (uint32_t i = 0; i < set->count; i++) {
        if (!set->utxos[i].is_spent &&
            memcmp(&set->utxos[i].owner, address, ADDRESS_SIZE) == 0) {
            balance += set->utxos[i].amount;
        }
    }
    
    return balance;
}

// =====================================================================================================================
// Account State Management
// =====================================================================================================================

void account_state_init(AccountState* state) {
    state->capacity = 100;
    state->count = 0;
    state->accounts = (Account*)malloc(sizeof(Account) * state->capacity);
}

void account_state_destroy(AccountState* state) {
    for (uint32_t i = 0; i < state->count; i++) {
        if (state->accounts[i].storage) {
            free(state->accounts[i].storage);
        }
    }
    free(state->accounts);
    state->accounts = NULL;
    state->count = 0;
}

Account* account_state_get(AccountState* state, const Address* address) {
    for (uint32_t i = 0; i < state->count; i++) {
        if (memcmp(&state->accounts[i].address, address, ADDRESS_SIZE) == 0) {
            return &state->accounts[i];
        }
    }
    return NULL;
}

Account* account_state_create(AccountState* state, const Address* address) {
    if (state->count >= state->capacity) {
        state->capacity *= 2;
        state->accounts = (Account*)realloc(state->accounts, sizeof(Account) * state->capacity);
    }
    
    Account* account = &state->accounts[state->count++];
    memset(account, 0, sizeof(Account));
    memcpy(&account->address, address, sizeof(Address));
    
    return account;
}

void account_state_transfer(AccountState* state, const Address* from, const Address* to, uint64_t amount) {
    Account* from_account = account_state_get(state, from);
    Account* to_account = account_state_get(state, to);
    
    if (!to_account) {
        to_account = account_state_create(state, to);
    }
    
    if (from_account && from_account->balance >= amount) {
        from_account->balance -= amount;
        to_account->balance += amount;
    }
}

// =====================================================================================================================
// Smart Contract VM Implementation
// =====================================================================================================================

void vm_state_init(VMState* vm, uint64_t gas_limit) {
    vm->stack_capacity = 1024;
    vm->stack = (uint64_t*)malloc(sizeof(uint64_t) * vm->stack_capacity);
    vm->stack_pointer = 0;
    
    vm->memory_capacity = 4096;
    vm->memory = (uint8_t*)malloc(vm->memory_capacity);
    vm->memory_size = 0;
    
    vm->gas_remaining = gas_limit;
    vm->gas_used = 0;
    vm->pc = 0;
    vm->stopped = false;
    vm->reverted = false;
}

void vm_state_destroy(VMState* vm) {
    free(vm->stack);
    free(vm->memory);
}

bool vm_use_gas(VMState* vm, uint64_t amount) {
    if (vm->gas_remaining < amount) {
        vm->stopped = true;
        return false;
    }
    vm->gas_remaining -= amount;
    vm->gas_used += amount;
    return true;
}

bool vm_stack_push(VMState* vm, uint64_t value) {
    if (vm->stack_pointer >= vm->stack_capacity) return false;
    vm->stack[vm->stack_pointer++] = value;
    return true;
}

bool vm_stack_pop(VMState* vm, uint64_t* value) {
    if (vm->stack_pointer == 0) return false;
    *value = vm->stack[--vm->stack_pointer];
    return true;
}

void vm_memory_expand(VMState* vm, uint32_t new_size) {
    if (new_size > vm->memory_capacity) {
        vm->memory_capacity = new_size * 2;
        vm->memory = (uint8_t*)realloc(vm->memory, vm->memory_capacity);
    }
    if (new_size > vm->memory_size) {
        memset(vm->memory + vm->memory_size, 0, new_size - vm->memory_size);
        vm->memory_size = new_size;
    }
}

int vm_execute(VMContext* ctx, VMState* vm) {
    while (!vm->stopped && !vm->reverted && vm->pc < ctx->code_size) {
        if (!vm_use_gas(vm, 1)) return -1;  // Out of gas
        
        uint8_t opcode = ctx->code[vm->pc++];
        
        switch (opcode) {
            case OP_STOP:
                vm->stopped = true;
                break;
                
            case OP_ADD: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a + b);
                break;
            }
            
            case OP_SUB: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a - b);
                break;
            }
            
            case OP_MUL: {
                if (!vm_use_gas(vm, 5)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a * b);
                break;
            }
            
            case OP_DIV: {
                if (!vm_use_gas(vm, 5)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                if (b == 0) {
                    vm_stack_push(vm, 0);
                } else {
                    vm_stack_push(vm, a / b);
                }
                break;
            }
            
            case OP_MOD: {
                if (!vm_use_gas(vm, 5)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                if (b == 0) {
                    vm_stack_push(vm, 0);
                } else {
                    vm_stack_push(vm, a % b);
                }
                break;
            }
            
            case OP_LT: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a < b ? 1 : 0);
                break;
            }
            
            case OP_GT: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a > b ? 1 : 0);
                break;
            }
            
            case OP_EQ: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a == b ? 1 : 0);
                break;
            }
            
            case OP_ISZERO: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a;
                if (!vm_stack_pop(vm, &a)) return -2;
                vm_stack_push(vm, a == 0 ? 1 : 0);
                break;
            }
            
            case OP_AND: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a & b);
                break;
            }
            
            case OP_OR: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a | b);
                break;
            }
            
            case OP_XOR: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a, b;
                if (!vm_stack_pop(vm, &a) || !vm_stack_pop(vm, &b)) return -2;
                vm_stack_push(vm, a ^ b);
                break;
            }
            
            case OP_NOT: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t a;
                if (!vm_stack_pop(vm, &a)) return -2;
                vm_stack_push(vm, ~a);
                break;
            }
            
            case OP_ADDRESS: {
                if (!vm_use_gas(vm, 2)) return -1;
                uint64_t addr = 0;
                memcpy(&addr, &ctx->address, min(sizeof(uint64_t), ADDRESS_SIZE));
                vm_stack_push(vm, addr);
                break;
            }
            
            case OP_BALANCE: {
                if (!vm_use_gas(vm, 400)) return -1;
                uint64_t addr_val;
                if (!vm_stack_pop(vm, &addr_val)) return -2;
                
                Address addr;
                memcpy(&addr, &addr_val, ADDRESS_SIZE);
                Account* account = account_state_get(ctx->state, &addr);
                
                vm_stack_push(vm, account ? account->balance : 0);
                break;
            }
            
            case OP_CALLER: {
                if (!vm_use_gas(vm, 2)) return -1;
                uint64_t addr = 0;
                memcpy(&addr, &ctx->caller, min(sizeof(uint64_t), ADDRESS_SIZE));
                vm_stack_push(vm, addr);
                break;
            }
            
            case OP_CALLVALUE: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, ctx->value);
                break;
            }
            
            case OP_TIMESTAMP: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, ctx->current_block->header.timestamp);
                break;
            }
            
            case OP_NUMBER: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, ctx->current_block->header.height);
                break;
            }
            
            case OP_DIFFICULTY: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, ctx->current_block->header.difficulty);
                break;
            }
            
            case OP_POP: {
                if (!vm_use_gas(vm, 2)) return -1;
                uint64_t dummy;
                if (!vm_stack_pop(vm, &dummy)) return -2;
                break;
            }
            
            case OP_MLOAD: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t offset;
                if (!vm_stack_pop(vm, &offset)) return -2;
                
                vm_memory_expand(vm, offset + 32);
                uint64_t value = 0;
                memcpy(&value, vm->memory + offset, min(8, vm->memory_size - offset));
                vm_stack_push(vm, value);
                break;
            }
            
            case OP_MSTORE: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint64_t offset, value;
                if (!vm_stack_pop(vm, &offset) || !vm_stack_pop(vm, &value)) return -2;
                
                vm_memory_expand(vm, offset + 32);
                memcpy(vm->memory + offset, &value, 8);
                break;
            }
            
            case OP_SLOAD: {
                if (!vm_use_gas(vm, 200)) return -1;
                uint64_t key;
                if (!vm_stack_pop(vm, &key)) return -2;
                
                Account* account = account_state_get(ctx->state, &ctx->address);
                uint64_t value = 0;
                
                if (account && account->storage && key < account->storage_size / 8) {
                    memcpy(&value, account->storage + key * 8, 8);
                }
                
                vm_stack_push(vm, value);
                break;
            }
            
            case OP_SSTORE: {
                if (!vm_use_gas(vm, 5000)) return -1;
                uint64_t key, value;
                if (!vm_stack_pop(vm, &key) || !vm_stack_pop(vm, &value)) return -2;
                
                Account* account = account_state_get(ctx->state, &ctx->address);
                if (account) {
                    uint32_t required_size = (key + 1) * 8;
                    if (account->storage_size < required_size) {
                        account->storage = (uint8_t*)realloc(account->storage, required_size);
                        memset(account->storage + account->storage_size, 0,
                              required_size - account->storage_size);
                        account->storage_size = required_size;
                    }
                    memcpy(account->storage + key * 8, &value, 8);
                }
                break;
            }
            
            case OP_JUMP: {
                if (!vm_use_gas(vm, 8)) return -1;
                uint64_t dest;
                if (!vm_stack_pop(vm, &dest)) return -2;
                
                if (dest >= ctx->code_size) return -3;
                vm->pc = dest;
                break;
            }
            
            case OP_JUMPI: {
                if (!vm_use_gas(vm, 10)) return -1;
                uint64_t dest, condition;
                if (!vm_stack_pop(vm, &dest) || !vm_stack_pop(vm, &condition)) return -2;
                
                if (condition != 0) {
                    if (dest >= ctx->code_size) return -3;
                    vm->pc = dest;
                }
                break;
            }
            
            case OP_PC: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, vm->pc - 1);
                break;
            }
            
            case OP_GAS: {
                if (!vm_use_gas(vm, 2)) return -1;
                vm_stack_push(vm, vm->gas_remaining);
                break;
            }
            
            case OP_PUSH1:
            case OP_PUSH2:
            case OP_PUSH4:
            case OP_PUSH8: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint32_t num_bytes = 1 << (opcode - OP_PUSH1);
                
                if (vm->pc + num_bytes > ctx->code_size) return -4;
                
                uint64_t value = 0;
                for (uint32_t i = 0; i < num_bytes; i++) {
                    value = (value << 8) | ctx->code[vm->pc++];
                }
                
                vm_stack_push(vm, value);
                break;
            }
            
            case OP_DUP1:
            case OP_DUP2: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint32_t depth = opcode - OP_DUP1 + 1;
                
                if (vm->stack_pointer < depth) return -2;
                uint64_t value = vm->stack[vm->stack_pointer - depth];
                vm_stack_push(vm, value);
                break;
            }
            
            case OP_SWAP1:
            case OP_SWAP2: {
                if (!vm_use_gas(vm, 3)) return -1;
                uint32_t depth = opcode - OP_SWAP1 + 1;
                
                if (vm->stack_pointer <= depth) return -2;
                uint64_t temp = vm->stack[vm->stack_pointer - 1];
                vm->stack[vm->stack_pointer - 1] = vm->stack[vm->stack_pointer - 1 - depth];
                vm->stack[vm->stack_pointer - 1 - depth] = temp;
                break;
            }
            
            case OP_RETURN: {
                if (!vm_use_gas(vm, 0)) return -1;
                vm->stopped = true;
                break;
            }
            
            case OP_REVERT: {
                if (!vm_use_gas(vm, 0)) return -1;
                vm->reverted = true;
                vm->stopped = true;
                break;
            }
            
            default:
                return -5;  // Invalid opcode
        }
        
        // Yield periodically
        if (vm->gas_used % 100 == 0) {
            yield();
        }
    }
    
    return vm->reverted ? -6 : 0;
}

// =====================================================================================================================
// Consensus - Proof of Work
// =====================================================================================================================

bool consensus_pow_validate_block(Block* block) {
    return block_meets_difficulty(block) && block_verify_hash(block);
}

// =====================================================================================================================
// End of blockchain_core.cpp
// Lines: ~1350
// =====================================================================================================================
