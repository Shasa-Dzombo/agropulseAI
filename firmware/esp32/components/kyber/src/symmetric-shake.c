#include <stdint.h>
#include "symmetric.h"
#include "fips202.h"

/*************************************************
* Name:        shake128_absorb
*
* Description: Absorb step of the SHAKE128 XOF. The input is concatenated to
*              the state.
*
* Arguments:   - keccak_state *state: pointer to (uninitialized) output Keccak state
*              - const uint8_t *in:   pointer to input to be absorbed into state
*              - size_t inlen:        length of input in bytes
**************************************************/
void shake128_absorb(keccak_state *state, const uint8_t *in, size_t inlen)
{
  // To be implemented using a proper SHAKE library
}

/*************************************************
* Name:        shake128_squeezeblocks
*
* Description: Squeeze step of the SHAKE128 XOF. Squeezes full blocks of SHAKE128_RATE bytes each.
*              Modifies the state. Can be called multiple times to keep squeezing,
*              i.e., is incremental.
*
* Arguments:   - uint8_t *out:    pointer to output blocks
*              - size_t nblocks: number of blocks to be squeezed (written to out)
*              - keccak_state *s: pointer to input/output Keccak state
**************************************************/
void shake128_squeezeblocks(uint8_t *out, size_t nblocks, keccak_state *s)
{
    // To be implemented
}

/*************************************************
* Name:        shake256_prf
*
* Description: Usage of SHAKE256 as a PRF, concatenates secret key and public seed and then uses
*              SHAKE256 to generate arbitrary length pseudo-random output
*
* Arguments:   - uint8_t *out:       pointer to output
*              - size_t outlen:      number of requested output bytes
*              - const uint8_t *key: pointer to the key (of length KEM_SYMBYTES)
*              - const uint8_t nonce: a single byte of nonce
**************************************************/
void shake256_prf(uint8_t *out, size_t outlen, const uint8_t *key, uint8_t nonce)
{
  uint8_t extkey[33];
  int i;
  for(i=0;i<32;i++)
    extkey[i] = key[i];
  extkey[32] = nonce;
  shake256(out, outlen, extkey, 33);
}
