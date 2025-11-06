#include <string.h>
#include "kem.h"
#include "indcpa.h"
#include "symmetric.h"
#include "randombytes.h"

/*************************************************
* Name:        crypto_kem_keypair
*
* Description: Generates public and private key
*              for CCA-secure Kyber key encapsulation mechanism
*
* Arguments:   - uint8_t *pk: pointer to output public key (an already allocated array of KEM_PUBLICKEYBYTES bytes)
*              - uint8_t *sk: pointer to output private key (an already allocated array of KEM_SECRETKEYBYTES bytes)
*
* Returns 0 (success)
**************************************************/
int crypto_kem_keypair(uint8_t *pk, uint8_t *sk)
{
  size_t i;
  indcpa_keypair(pk, sk);
  for(i=0;i<KEM_PUBLICKEYBYTES;i++)
    sk[i+KEM_INDCPA_SECRETKEYBYTES] = pk[i];
  hash_h(sk+KEM_SECRETKEYBYTES-64, pk, KEM_PUBLICKEYBYTES);
  randombytes(sk+KEM_SECRETKEYBYTES-32, 32); /* Value z for pseudo-random output on reject */
  return 0;
}

/*************************************************
* Name:        crypto_kem_enc
*
* Description: Generates cipher text and shared
*              secret for given public key
*
* Arguments:   - uint8_t *ct:       pointer to output cipher text (an already allocated array of KEM_CIPHERTEXTBYTES bytes)
*              - uint8_t *ss:       pointer to output shared secret (an already allocated array of KEM_SSBYTES bytes)
*              - const uint8_t *pk: pointer to input public key (an already allocated array of KEM_PUBLICKEYBYTES bytes)
*
* Returns 0 (success)
**************************************************/
int crypto_kem_enc(uint8_t *ct, uint8_t *ss, const uint8_t *pk)
{
  uint8_t  kr[64];                                   /* Will contain key, coins */
  uint8_t  buf[64];
  
  randombytes(buf, 32);
  hash_h(buf, buf, 32);                              /* Don't release system RNG output */

  hash_h(buf+32, pk, KEM_PUBLICKEYBYTES);             /* Multitarget countermeasure for coins + key */
  hash_g(kr, buf, 64);

  indcpa_enc(ct, buf, pk, kr+32);                   /* coins are in kr+32 */

  hash_h(kr+32, ct, KEM_CIPHERTEXTBYTES);            /* overwrite coins in kr with H(c) */
  kdf(ss, kr, 64);                                   /* hash concatenation of pre-key and H(c) to k */
  return 0;
}


/*************************************************
* Name:        crypto_kem_dec
*
* Description: Generates shared secret for given
*              cipher text and private key
*
* Arguments:   - uint8_t *ss:       pointer to output shared secret (an already allocated array of KEM_SSBYTES bytes)
*              - const uint8_t *ct: pointer to input cipher text (an already allocated array of KEM_CIPHERTEXTBYTES bytes)
*              - const uint8_t *sk: pointer to input private key (an already allocated array of KEM_SECRETKEYBYTES bytes)
*
* Returns 0 for sucess or -1 for failure
*
* On failure, ss will contain a pseudo-random value.
**************************************************/
int crypto_kem_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk)
{
  size_t i;
  int fail;
  uint8_t cmp[KEM_CIPHERTEXTBYTES];
  uint8_t buf[64];
  uint8_t kr[64];                                    /* Will contain key, coins */
  const uint8_t *pk = sk+KEM_INDCPA_SECRETKEYBYTES;

  indcpa_dec(buf, ct, sk);

  /* Multitarget countermeasure for coins + key */
  for(i=0;i<32;i++)
    buf[32+i] = sk[KEM_SECRETKEYBYTES-64+i];
  hash_g(kr, buf, 64);

  indcpa_enc(cmp, buf, pk, kr+32);                   /* coins are in kr+32 */

  fail = memcmp(ct, cmp, KEM_CIPHERTEXTBYTES);

  hash_h(kr+32, ct, KEM_CIPHERTEXTBYTES);            /* overwrite coins in kr with H(c) */
  
  kdf(ss, kr, 64);                                   /* hash concatenation of pre-key and H(c) to k */

  /* Overwrite pre-key with z on re-encryption failure */
  if(fail)
    memcpy(ss, sk+KEM_SECRETKEYBYTES-32, 32);

  return 0;
}
