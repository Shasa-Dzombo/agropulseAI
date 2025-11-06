#include <string.h>
#include "indcpa.h"
#include "polyvec.h"
#include "poly.h"
#include "randombytes.h"
#include "symmetric.h"

/*************************************************
* Name:        pack_pk
*
* Description: Serialize the public key as concatenation of the
*              serialized vector of polynomials pk
*              and the public seed used to generate the matrix A.
*
* Arguments:   uint8_t *r:          pointer to the output serialized public key
*              const poly *pk:            pointer to the input public-key polynomial
*              const uint8_t *seed: pointer to the input public seed
**************************************************/
static void pack_pk(uint8_t *r, polyvec *pk, const uint8_t *seed)
{
  polyvec_compress(r, pk);
  memcpy(r+KEM_K*320, seed, 32);
}

/*************************************************
* Name:        unpack_pk
*
* Description: De-serialize and decompress public key from a byte array;
*              approximate inverse of pack_pk
*
* Arguments:   - poly *pk:                   pointer to output public-key polynomial
*              - uint8_t *seed:              pointer to output public seed
*              - const uint8_t *packedpk:    pointer to input serialized public key
**************************************************/
static void unpack_pk(polyvec *pk, uint8_t *seed, const uint8_t *packedpk)
{
  polyvec_decompress(pk, packedpk);
  memcpy(seed, packedpk+KEM_K*320, 32);
}

/*************************************************
* Name:        pack_sk
*
* Description: Serialize the secret key
*
* Arguments:   - uint8_t *r:  pointer to output serialized secret key
*              - const poly *sk: pointer to input secret-key polynomial
**************************************************/
static void pack_sk(uint8_t *r, polyvec *sk)
{
  polyvec_tobytes(r, sk);
}

/*************************************************
* Name:        unpack_sk
*
* Description: De-serialize the secret key;
*              inverse of pack_sk
*
* Arguments:   - poly *sk:                   pointer to output secret-key polynomial
*              - const uint8_t *packedsk:    pointer to input serialized secret key
**************************************************/
static void unpack_sk(polyvec *sk, const uint8_t *packedsk)
{
  polyvec_frombytes(sk, packedsk);
}

/*************************************************
* Name:        pack_ciphertext
*
* Description: Serialize the ciphertext as concatenation of the
*              compressed and serialized vector of polynomials b
*              and the compressed and serialized polynomial v
*
* Arguments:   uint8_t *r:          pointer to the output serialized ciphertext
*              const poly *b:             pointer to the input vector of polynomials b
*              const poly *v:             pointer to the input polynomial v
**************************************************/
static void pack_ciphertext(uint8_t *r, polyvec *b, poly *v)
{
  polyvec_compress(r, b);
  poly_compress(r+KEM_K*KEM_DU*32, v);
}

/*************************************************
* Name:        unpack_ciphertext
*
* Description: De-serialize and decompress ciphertext from a byte array;
*              approximate inverse of pack_ciphertext
*
* Arguments:   - poly *b:             pointer to the output vector of polynomials b
*              - poly *v:             pointer to the output polynomial v
*              - const uint8_t *c:    pointer to the input serialized ciphertext
**************************************************/
static void unpack_ciphertext(polyvec *b, poly *v, const uint8_t *c)
{
  polyvec_decompress(b, c);
  poly_decompress(v, c+KEM_K*KEM_DU*32);
}

/*************************************************
* Name:        rej_uniform
*
* Description: Run rejection sampling on uniform random bytes to generate
*              uniform random integers mod q
*
* Arguments:   - int16_t *r:          pointer to output array
*              - unsigned int len:    requested number of 16-bit integers (uniform mod q)
*              - const uint8_t *buf:  pointer to input buffer
*              - unsigned int buflen: length of input buffer
*
* Returns number of sampled 16-bit integers (at most len)
**************************************************/
static unsigned int rej_uniform(int16_t *r, unsigned int len, const uint8_t *buf, unsigned int buflen)
{
  unsigned int ctr, pos;
  uint16_t val;

  ctr = pos = 0;
  while(ctr < len && pos + 2 <= buflen)
  {
    val = buf[pos] | ((uint16_t)buf[pos+1] << 8);
    pos += 2;

    if(val < 19*3329) // 19*q
    {
      val %= 3329;
      r[ctr++] = val;
    }
  }

  return ctr;
}

#define GEN_A_MAX_ATTEMPTS 1000
/*************************************************
* Name:        gen_a
*
* Description: Generation of matrix A (or A^T)
*
* Arguments:   - polyvec *a:      pointer to output matrix A
*              - const uint8_t *seed: pointer to input seed
*              - int transposed:      boolean deciding whether A or A^T is generated
**************************************************/
void gen_a(polyvec *a, const uint8_t *seed, int transposed)
{
  unsigned int ctr, i, j;
  int16_t r[672];
  uint8_t buf[SHAKE128_RATE];
  keccak_state state;

  for(i=0;i<KEM_K;i++)
  {
    for(j=0;j<KEM_K;j++)
    {
      shake128_absorb(&state, seed, i, j);
      shake128_squeezeblocks(buf, 1, &state);
      ctr = rej_uniform(r, KEM_N, buf, SHAKE128_RATE);

      while(ctr < KEM_N)
      {
        shake128_squeezeblocks(buf, 1, &state);
        ctr += rej_uniform(r+ctr, KEM_N-ctr, buf, SHAKE128_RATE);
      }

      if(transposed)
        poly_frombytes(&a[j].vec[i], (uint8_t *)r);
      else
        poly_frombytes(&a[i].vec[j], (uint8_t *)r);
    }
  }
}


/*************************************************
* Name:        indcpa_keypair
*
* Description: Generates public and private key for the CPA-secure
*              public-key encryption scheme underlying Kyber
*
* Arguments:   - uint8_t *pk: pointer to output public key (of length KEM_PUBLICKEYBYTES bytes)
*              - uint8_t *sk: pointer to output private key (of length KEM_SECRETKEYBYTES bytes)
**************************************************/
void indcpa_keypair(uint8_t *pk, uint8_t *sk)
{
  polyvec a[KEM_K], e, pkpv, skpv;
  uint8_t buf[64];
  uint8_t *publicseed = buf;
  uint8_t *noiseseed = buf+32;
  int i;
  uint8_t nonce = 0;

  randombytes(buf, 32);
  hash_g(buf, buf, 32);
  
  randombytes(buf, 32);
  hash_g(buf, buf, 32);

  gen_a(a, publicseed, 0);

  for(i=0;i<KEM_K;i++)
    poly_getnoise(skpv.vec+i, noiseseed, nonce++);
  for(i=0;i<KEM_K;i++)
    poly_getnoise(e.vec+i, noiseseed, nonce++);

  polyvec_ntt(&skpv);
  polyvec_ntt(&e);

  for(i=0;i<KEM_K;i++)
    polyvec_pointwise_acc(&pkpv.vec[i], &a[i], &skpv);
  
  polyvec_add(&pkpv, &pkpv, &e);

  pack_sk(sk, &skpv);
  pack_pk(pk, &pkpv, publicseed);
}


/*************************************************
* Name:        indcpa_enc
*
* Description: Encryption function of the CPA-secure
*              public-key encryption scheme underlying Kyber.
*
* Arguments:   - uint8_t *c:          pointer to output ciphertext (of length KEM_CIPHERTEXTBYTES bytes)
*              - const uint8_t *m:    pointer to input message (of length KEM_INDCPA_MSGBYTES bytes)
*              - const uint8_t *pk:   pointer to input public key (of length KEM_PUBLICKEYBYTES bytes)
*              - const uint8_t *coin: pointer to input random coins used as seed (of length KEM_SYMBYTES bytes)
*                                           to deterministically generate all randomness
**************************************************/
void indcpa_enc(uint8_t *c,
               const uint8_t *m,
               const uint8_t *pk,
               const uint8_t *coins)
{
  polyvec pkpv, sp, ep, at[KEM_K], bp;
  poly v, k, epp;
  uint8_t seed[32];
  int i;
  uint8_t nonce = 0;

  unpack_pk(&pkpv, seed, pk);
  poly_frommsg(&k, m);
  
  gen_a(at, seed, 1);

  for(i=0;i<KEM_K;i++)
    poly_getnoise(sp.vec+i, coins, nonce++);
  for(i=0;i<KEM_K;i++)
    poly_getnoise(ep.vec+i, coins, nonce++);
  poly_getnoise(&epp, coins, nonce++);

  polyvec_ntt(&sp);

  for(i=0;i<KEM_K;i++)
    polyvec_pointwise_acc(&bp.vec[i], &at[i], &sp);

  polyvec_invntt(&bp);
  polyvec_invntt(&pkpv);

  polyvec_add(&bp, &bp, &ep);
  
  polyvec_pointwise_acc(&v, &pkpv, &sp);
  poly_invntt(&v);

  poly_add(&v, &v, &epp);
  poly_add(&v, &v, &k);

  pack_ciphertext(c, &bp, &v);
}

/*************************************************
* Name:        indcpa_dec
*
* Description: Decryption function of the CPA-secure
*              public-key encryption scheme underlying Kyber.
*
* Arguments:   - uint8_t *m:        pointer to output decrypted message (of length KEM_INDCPA_MSGBYTES)
*              - const uint8_t *c:  pointer to input ciphertext (of length KEM_CIPHERTEXTBYTES)
*              - const uint8_t *sk: pointer to input secret key (of length KEM_SECRETKEYBYTES)
**************************************************/
void indcpa_dec(uint8_t *m,
               const uint8_t *c,
               const uint8_t *sk)
{
  polyvec bp, skpv;
  poly v, mp;

  unpack_ciphertext(&bp, &v, c);
  unpack_sk(&skpv, sk);

  polyvec_ntt(&bp);
  polyvec_pointwise_acc(&mp, &skpv, &bp);
  poly_invntt(&mp);

  poly_sub(&mp, &v, &mp);

  poly_tomsg(m, &mp);
}
