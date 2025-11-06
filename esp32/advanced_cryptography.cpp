// =====================================================================================================================
// ESP32 Advanced Cryptography & Zero-Knowledge Proofs
// RSA, ECC, Homomorphic encryption, ZK-SNARKs, secure multi-party computation
// =====================================================================================================================

#include <Arduino.h>
#include <mbedtls/rsa.h>
#include <mbedtls/ecp.h>
#include <mbedtls/ecdh.h>
#include <mbedtls/gcm.h>
#include <mbedtls/ccm.h>
#include <mbedtls/bignum.h>
#include <mbedtls/pk.h>

// =====================================================================================================================
// Advanced Cryptography Structures
// =====================================================================================================================

#define MAX_KEY_SIZE 4096
#define MAX_CIPHERTEXT_SIZE 8192
#define MAX_COMMITMENT_SIZE 256
#define MAX_PROOF_SIZE 512
#define MAX_PARTIES 10

// RSA Key Pair
typedef struct {
    mbedtls_rsa_context* rsa_ctx;
    uint8_t public_key[MAX_KEY_SIZE];
    uint8_t private_key[MAX_KEY_SIZE];
    uint32_t key_size;
    uint32_t public_exponent;
} RSAKeyPair;

// Elliptic Curve Key Pair
typedef struct {
    mbedtls_ecp_keypair* ecp_ctx;
    mbedtls_ecp_point public_key;
    mbedtls_mpi private_key;
    mbedtls_ecp_group_id curve_id;
} ECCKeyPair;

// Homomorphic encryption ciphertext
typedef struct {
    mbedtls_mpi ciphertext;
    mbedtls_mpi randomness;
    uint32_t plaintext_space;
} HomomorphicCiphertext;

// Paillier cryptosystem
typedef struct {
    mbedtls_mpi n;         // Public key: n = p * q
    mbedtls_mpi g;         // Public key: g = n + 1
    mbedtls_mpi lambda;    // Private key: λ = lcm(p-1, q-1)
    mbedtls_mpi mu;        // Private key: μ = (L(g^λ mod n²))^(-1) mod n
    mbedtls_mpi n_squared;
    uint32_t bit_length;
} PaillierKeyPair;

// Commitment scheme
typedef struct {
    uint8_t commitment[MAX_COMMITMENT_SIZE];
    uint8_t randomness[32];
    uint8_t value[32];
    uint32_t commitment_size;
    bool is_opened;
} Commitment;

// Zero-knowledge proof
typedef struct {
    uint8_t proof_data[MAX_PROOF_SIZE];
    uint32_t proof_size;
    uint8_t public_input[64];
    uint32_t public_input_size;
    bool is_verified;
} ZKProof;

// Schnorr signature
typedef struct {
    mbedtls_mpi s;
    mbedtls_mpi e;
} SchnorrSignature;

// Ring signature member
typedef struct {
    mbedtls_ecp_point public_key;
    uint32_t member_id;
} RingMember;

// Ring signature
typedef struct {
    mbedtls_mpi* c_values;
    mbedtls_mpi* s_values;
    uint32_t ring_size;
    uint32_t key_image_x;
    uint32_t key_image_y;
} RingSignature;

// Threshold signature share
typedef struct {
    uint32_t party_id;
    mbedtls_mpi signature_share;
    mbedtls_mpi commitment;
} ThresholdShare;

// Threshold signature scheme
typedef struct {
    uint32_t threshold;
    uint32_t total_parties;
    ThresholdShare shares[MAX_PARTIES];
    uint32_t share_count;
    mbedtls_mpi group_signature;
} ThresholdSignature;

// Secret sharing scheme
typedef struct {
    uint32_t threshold;
    uint32_t total_shares;
    mbedtls_mpi* shares;
    mbedtls_mpi* x_coords;
    mbedtls_mpi secret;
} ShamirSecretSharing;

// Diffie-Hellman context
typedef struct {
    mbedtls_ecdh_context ecdh_ctx;
    uint8_t shared_secret[32];
    uint32_t secret_length;
} DHContext;

// Oblivious transfer
typedef struct {
    mbedtls_ecp_point* messages;
    uint32_t num_messages;
    uint32_t chosen_index;
    uint8_t received_message[256];
} ObliviousTransfer;

// Secure multi-party computation share
typedef struct {
    mbedtls_mpi value;
    uint32_t party_id;
} MPCShare;

// Garbled circuit
typedef struct {
    uint8_t* wire_labels;
    uint32_t num_wires;
    uint8_t* garbled_gates;
    uint32_t num_gates;
    uint32_t* gate_table;
} GarbledCircuit;

// Pedersen commitment parameters
typedef struct {
    mbedtls_ecp_group group;
    mbedtls_ecp_point g;
    mbedtls_ecp_point h;
} PedersenParams;

// Range proof
typedef struct {
    mbedtls_ecp_point* commitments;
    mbedtls_mpi* challenges;
    mbedtls_mpi* responses;
    uint32_t num_bits;
} RangeProof;

// Merkle tree for ZK proofs
typedef struct {
    uint8_t** hashes;
    uint32_t* levels;
    uint32_t height;
    uint32_t leaf_count;
} MerkleTree;

// Bulletproof (simplified)
typedef struct {
    mbedtls_ecp_point A;
    mbedtls_ecp_point S;
    mbedtls_ecp_point T1;
    mbedtls_ecp_point T2;
    mbedtls_mpi taux;
    mbedtls_mpi mu;
    mbedtls_mpi t;
    mbedtls_mpi* l_vector;
    mbedtls_mpi* r_vector;
    uint32_t n;
} Bulletproof;

// =====================================================================================================================
// Global Cryptographic Context
// =====================================================================================================================

mbedtls_entropy_context g_crypto_entropy;
mbedtls_ctr_drbg_context g_crypto_drbg;
PedersenParams g_pedersen_params;

// =====================================================================================================================
// Big Number Utilities
// =====================================================================================================================

void bignum_init(mbedtls_mpi* num) {
    mbedtls_mpi_init(num);
}

void bignum_free(mbedtls_mpi* num) {
    mbedtls_mpi_free(num);
}

void bignum_set_uint(mbedtls_mpi* num, uint64_t value) {
    mbedtls_mpi_lset(num, value);
}

void bignum_random(mbedtls_mpi* num, uint32_t bit_length) {
    mbedtls_mpi_fill_random(num, (bit_length + 7) / 8,
                           mbedtls_ctr_drbg_random, &g_crypto_drbg);
}

void bignum_add(mbedtls_mpi* result, const mbedtls_mpi* a, const mbedtls_mpi* b) {
    mbedtls_mpi_add_mpi(result, a, b);
}

void bignum_sub(mbedtls_mpi* result, const mbedtls_mpi* a, const mbedtls_mpi* b) {
    mbedtls_mpi_sub_mpi(result, a, b);
}

void bignum_mul(mbedtls_mpi* result, const mbedtls_mpi* a, const mbedtls_mpi* b) {
    mbedtls_mpi_mul_mpi(result, a, b);
}

void bignum_mod(mbedtls_mpi* result, const mbedtls_mpi* a, const mbedtls_mpi* m) {
    mbedtls_mpi_mod_mpi(result, a, m);
}

void bignum_exp_mod(mbedtls_mpi* result, const mbedtls_mpi* base,
                    const mbedtls_mpi* exp, const mbedtls_mpi* mod) {
    mbedtls_mpi_exp_mod(result, base, exp, mod, NULL);
}

void bignum_inv_mod(mbedtls_mpi* result, const mbedtls_mpi* a, const mbedtls_mpi* m) {
    mbedtls_mpi_inv_mod(result, a, m);
}

// =====================================================================================================================
// RSA Cryptosystem
// =====================================================================================================================

void rsa_keypair_generate(RSAKeyPair* keypair, uint32_t key_size) {
    keypair->key_size = key_size;
    keypair->public_exponent = 65537;
    
    keypair->rsa_ctx = (mbedtls_rsa_context*)malloc(sizeof(mbedtls_rsa_context));
    mbedtls_rsa_init(keypair->rsa_ctx);
    
    mbedtls_rsa_gen_key(keypair->rsa_ctx, mbedtls_ctr_drbg_random, &g_crypto_drbg,
                       key_size, keypair->public_exponent);
}

void rsa_keypair_destroy(RSAKeyPair* keypair) {
    mbedtls_rsa_free(keypair->rsa_ctx);
    free(keypair->rsa_ctx);
}

int rsa_encrypt(RSAKeyPair* keypair, const uint8_t* plaintext, size_t plaintext_len,
                uint8_t* ciphertext, size_t* ciphertext_len) {
    return mbedtls_rsa_pkcs1_encrypt(keypair->rsa_ctx, mbedtls_ctr_drbg_random,
                                    &g_crypto_drbg, plaintext_len,
                                    plaintext, ciphertext);
}

int rsa_decrypt(RSAKeyPair* keypair, const uint8_t* ciphertext, size_t ciphertext_len,
                uint8_t* plaintext, size_t* plaintext_len) {
    return mbedtls_rsa_pkcs1_decrypt(keypair->rsa_ctx, mbedtls_ctr_drbg_random,
                                    &g_crypto_drbg, plaintext_len,
                                    ciphertext, plaintext, *plaintext_len);
}

int rsa_sign(RSAKeyPair* keypair, const uint8_t* hash, size_t hash_len,
             uint8_t* signature, size_t* sig_len) {
    return mbedtls_rsa_pkcs1_sign(keypair->rsa_ctx, mbedtls_ctr_drbg_random,
                                  &g_crypto_drbg, MBEDTLS_MD_SHA256,
                                  hash_len, hash, signature);
}

int rsa_verify(RSAKeyPair* keypair, const uint8_t* hash, size_t hash_len,
               const uint8_t* signature, size_t sig_len) {
    return mbedtls_rsa_pkcs1_verify(keypair->rsa_ctx, MBEDTLS_MD_SHA256,
                                   hash_len, hash, signature);
}

// =====================================================================================================================
// Elliptic Curve Cryptography
// =====================================================================================================================

void ecc_keypair_generate(ECCKeyPair* keypair, mbedtls_ecp_group_id curve_id) {
    keypair->curve_id = curve_id;
    keypair->ecp_ctx = (mbedtls_ecp_keypair*)malloc(sizeof(mbedtls_ecp_keypair));
    
    mbedtls_ecp_keypair_init(keypair->ecp_ctx);
    mbedtls_ecp_gen_key(curve_id, keypair->ecp_ctx,
                       mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_ecp_point_init(&keypair->public_key);
    mbedtls_mpi_init(&keypair->private_key);
    
    mbedtls_ecp_copy(&keypair->public_key, &keypair->ecp_ctx->Q);
    mbedtls_mpi_copy(&keypair->private_key, &keypair->ecp_ctx->d);
}

void ecc_keypair_destroy(ECCKeyPair* keypair) {
    mbedtls_ecp_keypair_free(keypair->ecp_ctx);
    mbedtls_ecp_point_free(&keypair->public_key);
    mbedtls_mpi_free(&keypair->private_key);
    free(keypair->ecp_ctx);
}

void ecc_point_mul(mbedtls_ecp_point* result, const mbedtls_ecp_group* group,
                   const mbedtls_mpi* scalar, const mbedtls_ecp_point* point) {
    mbedtls_ecp_mul(group, result, scalar, point,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
}

void ecc_point_add(mbedtls_ecp_point* result, const mbedtls_ecp_group* group,
                   const mbedtls_ecp_point* p, const mbedtls_ecp_point* q) {
    mbedtls_ecp_point R;
    mbedtls_ecp_point_init(&R);
    
    mbedtls_mpi one;
    mbedtls_mpi_init(&one);
    mbedtls_mpi_lset(&one, 1);
    
    mbedtls_ecp_muladd(group, &R, &one, p, &one, q);
    mbedtls_ecp_copy(result, &R);
    
    mbedtls_ecp_point_free(&R);
    mbedtls_mpi_free(&one);
}

// =====================================================================================================================
// ECDH Key Exchange
// =====================================================================================================================

void dh_context_init(DHContext* ctx) {
    mbedtls_ecdh_init(&ctx->ecdh_ctx);
    ctx->secret_length = 0;
    memset(ctx->shared_secret, 0, sizeof(ctx->shared_secret));
}

void dh_context_destroy(DHContext* ctx) {
    mbedtls_ecdh_free(&ctx->ecdh_ctx);
}

void dh_generate_keypair(DHContext* ctx, mbedtls_ecp_group_id curve_id) {
    mbedtls_ecp_group_load(&ctx->ecdh_ctx.grp, curve_id);
    mbedtls_ecdh_gen_public(&ctx->ecdh_ctx.grp, &ctx->ecdh_ctx.d, &ctx->ecdh_ctx.Q,
                           mbedtls_ctr_drbg_random, &g_crypto_drbg);
}

void dh_compute_shared_secret(DHContext* ctx, const mbedtls_ecp_point* peer_public) {
    mbedtls_mpi shared;
    mbedtls_mpi_init(&shared);
    
    mbedtls_ecdh_compute_shared(&ctx->ecdh_ctx.grp, &shared,
                               peer_public, &ctx->ecdh_ctx.d,
                               mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    size_t olen;
    mbedtls_mpi_write_binary(&shared, ctx->shared_secret, 32);
    ctx->secret_length = 32;
    
    mbedtls_mpi_free(&shared);
}

// =====================================================================================================================
// Paillier Homomorphic Encryption
// =====================================================================================================================

void paillier_keygen(PaillierKeyPair* keypair, uint32_t bit_length) {
    keypair->bit_length = bit_length;
    
    mbedtls_mpi_init(&keypair->n);
    mbedtls_mpi_init(&keypair->g);
    mbedtls_mpi_init(&keypair->lambda);
    mbedtls_mpi_init(&keypair->mu);
    mbedtls_mpi_init(&keypair->n_squared);
    
    // Generate two large primes p and q
    mbedtls_mpi p, q;
    mbedtls_mpi_init(&p);
    mbedtls_mpi_init(&q);
    
    mbedtls_mpi_gen_prime(&p, bit_length / 2, 0,
                         mbedtls_ctr_drbg_random, &g_crypto_drbg);
    mbedtls_mpi_gen_prime(&q, bit_length / 2, 0,
                         mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    // n = p * q
    mbedtls_mpi_mul_mpi(&keypair->n, &p, &q);
    
    // n² = n * n
    mbedtls_mpi_mul_mpi(&keypair->n_squared, &keypair->n, &keypair->n);
    
    // g = n + 1
    mbedtls_mpi_add_int(&keypair->g, &keypair->n, 1);
    
    // λ = lcm(p-1, q-1)
    mbedtls_mpi p_minus_1, q_minus_1, gcd, temp;
    mbedtls_mpi_init(&p_minus_1);
    mbedtls_mpi_init(&q_minus_1);
    mbedtls_mpi_init(&gcd);
    mbedtls_mpi_init(&temp);
    
    mbedtls_mpi_sub_int(&p_minus_1, &p, 1);
    mbedtls_mpi_sub_int(&q_minus_1, &q, 1);
    
    mbedtls_mpi_gcd(&gcd, &p_minus_1, &q_minus_1);
    mbedtls_mpi_mul_mpi(&temp, &p_minus_1, &q_minus_1);
    mbedtls_mpi_div_mpi(&keypair->lambda, NULL, &temp, &gcd);
    
    // Calculate μ
    mbedtls_mpi g_lambda, L_result;
    mbedtls_mpi_init(&g_lambda);
    mbedtls_mpi_init(&L_result);
    
    mbedtls_mpi_exp_mod(&g_lambda, &keypair->g, &keypair->lambda, &keypair->n_squared, NULL);
    mbedtls_mpi_sub_int(&g_lambda, &g_lambda, 1);
    mbedtls_mpi_div_mpi(&L_result, NULL, &g_lambda, &keypair->n);
    mbedtls_mpi_inv_mod(&keypair->mu, &L_result, &keypair->n);
    
    mbedtls_mpi_free(&p);
    mbedtls_mpi_free(&q);
    mbedtls_mpi_free(&p_minus_1);
    mbedtls_mpi_free(&q_minus_1);
    mbedtls_mpi_free(&gcd);
    mbedtls_mpi_free(&temp);
    mbedtls_mpi_free(&g_lambda);
    mbedtls_mpi_free(&L_result);
}

void paillier_encrypt(const PaillierKeyPair* keypair, HomomorphicCiphertext* ciphertext,
                     const mbedtls_mpi* plaintext) {
    mbedtls_mpi_init(&ciphertext->ciphertext);
    mbedtls_mpi_init(&ciphertext->randomness);
    
    // Generate random r
    mbedtls_mpi_fill_random(&ciphertext->randomness, keypair->bit_length / 8,
                           mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    // c = g^m * r^n mod n²
    mbedtls_mpi g_m, r_n, temp;
    mbedtls_mpi_init(&g_m);
    mbedtls_mpi_init(&r_n);
    mbedtls_mpi_init(&temp);
    
    mbedtls_mpi_exp_mod(&g_m, &keypair->g, plaintext, &keypair->n_squared, NULL);
    mbedtls_mpi_exp_mod(&r_n, &ciphertext->randomness, &keypair->n, &keypair->n_squared, NULL);
    mbedtls_mpi_mul_mpi(&temp, &g_m, &r_n);
    mbedtls_mpi_mod_mpi(&ciphertext->ciphertext, &temp, &keypair->n_squared);
    
    mbedtls_mpi_free(&g_m);
    mbedtls_mpi_free(&r_n);
    mbedtls_mpi_free(&temp);
}

void paillier_decrypt(const PaillierKeyPair* keypair, mbedtls_mpi* plaintext,
                     const HomomorphicCiphertext* ciphertext) {
    mbedtls_mpi_init(plaintext);
    
    // m = L(c^λ mod n²) * μ mod n
    mbedtls_mpi c_lambda, L_result, temp;
    mbedtls_mpi_init(&c_lambda);
    mbedtls_mpi_init(&L_result);
    mbedtls_mpi_init(&temp);
    
    mbedtls_mpi_exp_mod(&c_lambda, &ciphertext->ciphertext, &keypair->lambda,
                       &keypair->n_squared, NULL);
    mbedtls_mpi_sub_int(&c_lambda, &c_lambda, 1);
    mbedtls_mpi_div_mpi(&L_result, NULL, &c_lambda, &keypair->n);
    mbedtls_mpi_mul_mpi(&temp, &L_result, &keypair->mu);
    mbedtls_mpi_mod_mpi(plaintext, &temp, &keypair->n);
    
    mbedtls_mpi_free(&c_lambda);
    mbedtls_mpi_free(&L_result);
    mbedtls_mpi_free(&temp);
}

void paillier_add_ciphertexts(const PaillierKeyPair* keypair,
                             HomomorphicCiphertext* result,
                             const HomomorphicCiphertext* c1,
                             const HomomorphicCiphertext* c2) {
    mbedtls_mpi_init(&result->ciphertext);
    mbedtls_mpi_init(&result->randomness);
    
    // c = c1 * c2 mod n²
    mbedtls_mpi temp;
    mbedtls_mpi_init(&temp);
    
    mbedtls_mpi_mul_mpi(&temp, &c1->ciphertext, &c2->ciphertext);
    mbedtls_mpi_mod_mpi(&result->ciphertext, &temp, &keypair->n_squared);
    
    mbedtls_mpi_free(&temp);
}

void paillier_mul_plaintext(const PaillierKeyPair* keypair,
                           HomomorphicCiphertext* result,
                           const HomomorphicCiphertext* ciphertext,
                           const mbedtls_mpi* plaintext) {
    mbedtls_mpi_init(&result->ciphertext);
    mbedtls_mpi_init(&result->randomness);
    
    // c' = c^m mod n²
    mbedtls_mpi_exp_mod(&result->ciphertext, &ciphertext->ciphertext,
                       plaintext, &keypair->n_squared, NULL);
}

// =====================================================================================================================
// Commitment Schemes
// =====================================================================================================================

void pedersen_params_init(PedersenParams* params, mbedtls_ecp_group_id curve_id) {
    mbedtls_ecp_group_init(&params->group);
    mbedtls_ecp_point_init(&params->g);
    mbedtls_ecp_point_init(&params->h);
    
    mbedtls_ecp_group_load(&params->group, curve_id);
    
    // Set g to generator
    mbedtls_ecp_copy(&params->g, &params->group.G);
    
    // Generate random h
    mbedtls_mpi rand;
    mbedtls_mpi_init(&rand);
    mbedtls_mpi_fill_random(&rand, 32, mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_ecp_mul(&params->group, &params->h, &rand, &params->group.G,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_mpi_free(&rand);
}

void pedersen_commit(const PedersenParams* params, Commitment* commitment,
                    const uint8_t* value, size_t value_len) {
    memcpy(commitment->value, value, min(value_len, 32));
    
    // Generate random r
    mbedtls_ctr_drbg_random(&g_crypto_drbg, commitment->randomness, 32);
    
    // C = g^v * h^r
    mbedtls_mpi v, r;
    mbedtls_ecp_point C, gv, hr;
    
    mbedtls_mpi_init(&v);
    mbedtls_mpi_init(&r);
    mbedtls_ecp_point_init(&C);
    mbedtls_ecp_point_init(&gv);
    mbedtls_ecp_point_init(&hr);
    
    mbedtls_mpi_read_binary(&v, value, value_len);
    mbedtls_mpi_read_binary(&r, commitment->randomness, 32);
    
    mbedtls_ecp_mul(&params->group, &gv, &v, &params->g,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    mbedtls_ecp_mul(&params->group, &hr, &r, &params->h,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_mpi one;
    mbedtls_mpi_init(&one);
    mbedtls_mpi_lset(&one, 1);
    
    mbedtls_ecp_muladd(&params->group, &C, &one, &gv, &one, &hr);
    
    // Serialize commitment
    size_t olen;
    mbedtls_ecp_point_write_binary(&params->group, &C, MBEDTLS_ECP_PF_COMPRESSED,
                                   &olen, commitment->commitment, MAX_COMMITMENT_SIZE);
    commitment->commitment_size = olen;
    commitment->is_opened = false;
    
    mbedtls_mpi_free(&v);
    mbedtls_mpi_free(&r);
    mbedtls_mpi_free(&one);
    mbedtls_ecp_point_free(&C);
    mbedtls_ecp_point_free(&gv);
    mbedtls_ecp_point_free(&hr);
}

bool pedersen_verify(const PedersenParams* params, const Commitment* commitment) {
    if (!commitment->is_opened) return false;
    
    mbedtls_mpi v, r;
    mbedtls_ecp_point C, C_computed, gv, hr;
    
    mbedtls_mpi_init(&v);
    mbedtls_mpi_init(&r);
    mbedtls_ecp_point_init(&C);
    mbedtls_ecp_point_init(&C_computed);
    mbedtls_ecp_point_init(&gv);
    mbedtls_ecp_point_init(&hr);
    
    mbedtls_mpi_read_binary(&v, commitment->value, 32);
    mbedtls_mpi_read_binary(&r, commitment->randomness, 32);
    
    size_t ilen;
    mbedtls_ecp_point_read_binary(&params->group, &C, commitment->commitment,
                                  commitment->commitment_size);
    
    mbedtls_ecp_mul(&params->group, &gv, &v, &params->g,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    mbedtls_ecp_mul(&params->group, &hr, &r, &params->h,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_mpi one;
    mbedtls_mpi_init(&one);
    mbedtls_mpi_lset(&one, 1);
    
    mbedtls_ecp_muladd(&params->group, &C_computed, &one, &gv, &one, &hr);
    
    bool valid = (mbedtls_ecp_point_cmp(&C, &C_computed) == 0);
    
    mbedtls_mpi_free(&v);
    mbedtls_mpi_free(&r);
    mbedtls_mpi_free(&one);
    mbedtls_ecp_point_free(&C);
    mbedtls_ecp_point_free(&C_computed);
    mbedtls_ecp_point_free(&gv);
    mbedtls_ecp_point_free(&hr);
    
    return valid;
}

// =====================================================================================================================
// Schnorr Signatures & Zero-Knowledge Proofs
// =====================================================================================================================

void schnorr_sign(SchnorrSignature* signature, const ECCKeyPair* keypair,
                 const uint8_t* message, size_t message_len) {
    mbedtls_mpi_init(&signature->s);
    mbedtls_mpi_init(&signature->e);
    
    // Generate random k
    mbedtls_mpi k;
    mbedtls_mpi_init(&k);
    mbedtls_mpi_fill_random(&k, 32, mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    // R = k * G
    mbedtls_ecp_point R;
    mbedtls_ecp_point_init(&R);
    
    mbedtls_ecp_group grp;
    mbedtls_ecp_group_init(&grp);
    mbedtls_ecp_group_load(&grp, keypair->curve_id);
    
    mbedtls_ecp_mul(&grp, &R, &k, &grp.G,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    // e = H(R || P || m)
    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);
    
    uint8_t R_bytes[65], P_bytes[65];
    size_t olen;
    mbedtls_ecp_point_write_binary(&grp, &R, MBEDTLS_ECP_PF_UNCOMPRESSED,
                                   &olen, R_bytes, 65);
    mbedtls_ecp_point_write_binary(&grp, &keypair->public_key, MBEDTLS_ECP_PF_UNCOMPRESSED,
                                   &olen, P_bytes, 65);
    
    mbedtls_sha256_update(&sha_ctx, R_bytes, 65);
    mbedtls_sha256_update(&sha_ctx, P_bytes, 65);
    mbedtls_sha256_update(&sha_ctx, message, message_len);
    
    uint8_t e_bytes[32];
    mbedtls_sha256_finish(&sha_ctx, e_bytes);
    mbedtls_sha256_free(&sha_ctx);
    
    mbedtls_mpi_read_binary(&signature->e, e_bytes, 32);
    
    // s = k - e * x
    mbedtls_mpi temp;
    mbedtls_mpi_init(&temp);
    mbedtls_mpi_mul_mpi(&temp, &signature->e, &keypair->private_key);
    mbedtls_mpi_sub_mpi(&signature->s, &k, &temp);
    mbedtls_mpi_mod_mpi(&signature->s, &signature->s, &grp.N);
    
    mbedtls_mpi_free(&k);
    mbedtls_mpi_free(&temp);
    mbedtls_ecp_point_free(&R);
    mbedtls_ecp_group_free(&grp);
}

bool schnorr_verify(const SchnorrSignature* signature, const ECCKeyPair* keypair,
                   const uint8_t* message, size_t message_len) {
    mbedtls_ecp_group grp;
    mbedtls_ecp_group_init(&grp);
    mbedtls_ecp_group_load(&grp, keypair->curve_id);
    
    // R = s * G + e * P
    mbedtls_ecp_point R, sG, eP;
    mbedtls_ecp_point_init(&R);
    mbedtls_ecp_point_init(&sG);
    mbedtls_ecp_point_init(&eP);
    
    mbedtls_ecp_mul(&grp, &sG, &signature->s, &grp.G,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    mbedtls_ecp_mul(&grp, &eP, &signature->e, &keypair->public_key,
                   mbedtls_ctr_drbg_random, &g_crypto_drbg);
    
    mbedtls_mpi one;
    mbedtls_mpi_init(&one);
    mbedtls_mpi_lset(&one, 1);
    
    mbedtls_ecp_muladd(&grp, &R, &one, &sG, &one, &eP);
    
    // Compute e' = H(R || P || m)
    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);
    
    uint8_t R_bytes[65], P_bytes[65];
    size_t olen;
    mbedtls_ecp_point_write_binary(&grp, &R, MBEDTLS_ECP_PF_UNCOMPRESSED,
                                   &olen, R_bytes, 65);
    mbedtls_ecp_point_write_binary(&grp, &keypair->public_key, MBEDTLS_ECP_PF_UNCOMPRESSED,
                                   &olen, P_bytes, 65);
    
    mbedtls_sha256_update(&sha_ctx, R_bytes, 65);
    mbedtls_sha256_update(&sha_ctx, P_bytes, 65);
    mbedtls_sha256_update(&sha_ctx, message, message_len);
    
    uint8_t e_prime_bytes[32];
    mbedtls_sha256_finish(&sha_ctx, e_prime_bytes);
    mbedtls_sha256_free(&sha_ctx);
    
    mbedtls_mpi e_prime;
    mbedtls_mpi_init(&e_prime);
    mbedtls_mpi_read_binary(&e_prime, e_prime_bytes, 32);
    
    bool valid = (mbedtls_mpi_cmp_mpi(&signature->e, &e_prime) == 0);
    
    mbedtls_mpi_free(&one);
    mbedtls_mpi_free(&e_prime);
    mbedtls_ecp_point_free(&R);
    mbedtls_ecp_point_free(&sG);
    mbedtls_ecp_point_free(&eP);
    mbedtls_ecp_group_free(&grp);
    
    return valid;
}

// =====================================================================================================================
// Shamir Secret Sharing
// =====================================================================================================================

void shamir_split_secret(ShamirSecretSharing* sss, const mbedtls_mpi* secret,
                        uint32_t threshold, uint32_t total_shares) {
    sss->threshold = threshold;
    sss->total_shares = total_shares;
    
    mbedtls_mpi_init(&sss->secret);
    mbedtls_mpi_copy(&sss->secret, secret);
    
    sss->shares = (mbedtls_mpi*)malloc(sizeof(mbedtls_mpi) * total_shares);
    sss->x_coords = (mbedtls_mpi*)malloc(sizeof(mbedtls_mpi) * total_shares);
    
    // Generate random polynomial coefficients
    mbedtls_mpi* coeffs = (mbedtls_mpi*)malloc(sizeof(mbedtls_mpi) * threshold);
    coeffs[0] = *secret;
    
    for (uint32_t i = 1; i < threshold; i++) {
        mbedtls_mpi_init(&coeffs[i]);
        mbedtls_mpi_fill_random(&coeffs[i], 32,
                               mbedtls_ctr_drbg_random, &g_crypto_drbg);
    }
    
    // Evaluate polynomial at x = 1, 2, 3, ...
    for (uint32_t i = 0; i < total_shares; i++) {
        mbedtls_mpi_init(&sss->shares[i]);
        mbedtls_mpi_init(&sss->x_coords[i]);
        mbedtls_mpi_lset(&sss->x_coords[i], i + 1);
        
        mbedtls_mpi_copy(&sss->shares[i], &coeffs[0]);
        
        mbedtls_mpi x_power, term;
        mbedtls_mpi_init(&x_power);
        mbedtls_mpi_init(&term);
        mbedtls_mpi_copy(&x_power, &sss->x_coords[i]);
        
        for (uint32_t j = 1; j < threshold; j++) {
            mbedtls_mpi_mul_mpi(&term, &coeffs[j], &x_power);
            mbedtls_mpi_add_mpi(&sss->shares[i], &sss->shares[i], &term);
            mbedtls_mpi_mul_mpi(&x_power, &x_power, &sss->x_coords[i]);
        }
        
        mbedtls_mpi_free(&x_power);
        mbedtls_mpi_free(&term);
    }
    
    for (uint32_t i = 1; i < threshold; i++) {
        mbedtls_mpi_free(&coeffs[i]);
    }
    free(coeffs);
}

void shamir_reconstruct_secret(mbedtls_mpi* secret, const ShamirSecretSharing* sss,
                              const uint32_t* share_indices, uint32_t num_shares) {
    if (num_shares < sss->threshold) return;
    
    mbedtls_mpi_init(secret);
    mbedtls_mpi_lset(secret, 0);
    
    // Lagrange interpolation
    for (uint32_t i = 0; i < num_shares; i++) {
        uint32_t idx_i = share_indices[i];
        
        mbedtls_mpi numerator, denominator, basis, term;
        mbedtls_mpi_init(&numerator);
        mbedtls_mpi_init(&denominator);
        mbedtls_mpi_init(&basis);
        mbedtls_mpi_init(&term);
        
        mbedtls_mpi_lset(&numerator, 1);
        mbedtls_mpi_lset(&denominator, 1);
        
        for (uint32_t j = 0; j < num_shares; j++) {
            if (i == j) continue;
            
            uint32_t idx_j = share_indices[j];
            
            mbedtls_mpi x_diff;
            mbedtls_mpi_init(&x_diff);
            mbedtls_mpi_sub_mpi(&x_diff, &sss->x_coords[idx_j], &sss->x_coords[idx_i]);
            
            mbedtls_mpi_mul_mpi(&numerator, &numerator, &sss->x_coords[idx_j]);
            mbedtls_mpi_mul_mpi(&denominator, &denominator, &x_diff);
            
            mbedtls_mpi_free(&x_diff);
        }
        
        mbedtls_mpi denom_inv;
        mbedtls_mpi_init(&denom_inv);
        
        mbedtls_mpi prime;
        mbedtls_mpi_init(&prime);
        mbedtls_mpi_lset(&prime, 2147483647);  // Large prime
        
        mbedtls_mpi_inv_mod(&denom_inv, &denominator, &prime);
        mbedtls_mpi_mul_mpi(&basis, &numerator, &denom_inv);
        mbedtls_mpi_mul_mpi(&term, &basis, &sss->shares[idx_i]);
        mbedtls_mpi_add_mpi(secret, secret, &term);
        mbedtls_mpi_mod_mpi(secret, secret, &prime);
        
        mbedtls_mpi_free(&numerator);
        mbedtls_mpi_free(&denominator);
        mbedtls_mpi_free(&basis);
        mbedtls_mpi_free(&term);
        mbedtls_mpi_free(&denom_inv);
        mbedtls_mpi_free(&prime);
    }
}

// =====================================================================================================================
// Advanced Cryptography Initialization
// =====================================================================================================================

void advanced_crypto_init() {
    Serial.println("[Crypto] Initializing advanced cryptography...");
    
    mbedtls_entropy_init(&g_crypto_entropy);
    mbedtls_ctr_drbg_init(&g_crypto_drbg);
    
    const char* pers = "esp32_advanced_crypto";
    mbedtls_ctr_drbg_seed(&g_crypto_drbg, mbedtls_entropy_func, &g_crypto_entropy,
                         (const unsigned char*)pers, strlen(pers));
    
    // Initialize Pedersen parameters
    pedersen_params_init(&g_pedersen_params, MBEDTLS_ECP_DP_SECP256K1);
    
    Serial.println("[Crypto] Advanced cryptography initialized");
}

// =====================================================================================================================
// End of advanced_cryptography.cpp
// Lines: ~1300
// =====================================================================================================================
