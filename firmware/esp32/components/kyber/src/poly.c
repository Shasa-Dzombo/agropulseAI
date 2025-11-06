#include <string.h>
#include "poly.h"
#include "ntt.h"
#include "reduce.h"
#include "cbd.h"
#include "symmetric.h"

/*************************************************
* Name:        poly_compress
*
* Description: Compression and subsequent serialization of a polynomial
*
* Arguments:   - uint8_t *r: pointer to output byte array (of length KEM_POLYCOMPRESSEDBYTES)
*              - const poly *a:    pointer to input polynomial
**************************************************/
void poly_compress(uint8_t *r, const poly *a)
{
  uint8_t t[8];
  int i,j,k=0;

  for(i=0;i<KEM_N;i+=8)
  {
    for(j=0;j<8;j++)
      t[j] = (((((uint16_t)a->coeffs[i+j] << 4) + 1664) / 3329) & 0xf);

    r[k++] = t[0] | (t[1] << 4);
    r[k++] = t[2] | (t[3] << 4);
    r[k++] = t[4] | (t[5] << 4);
    r[k++] = t[6] | (t[7] << 4);
  }
}

/*************************************************
* Name:        poly_decompress
*
* Description: De-serialization and subsequent decompression of a polynomial;
*              approximate inverse of poly_compress
*
* Arguments:   - poly *r:          pointer to output polynomial
*              - const uint8_t *a: pointer to input byte array (of length KEM_POLYCOMPRESSEDBYTES)
**************************************************/
void poly_decompress(poly *r, const uint8_t *a)
{
  int i;
  for(i=0;i<KEM_N/2;i++)
  {
    r->coeffs[2*i+0] = (((uint16_t)(a[i] & 15)*3329) + 8) >> 4;
    r->coeffs[2*i+1] = (((uint16_t)(a[i] >> 4)*3329) + 8) >> 4;
  }
}

/*************************************************
* Name:        poly_tobytes
*
* Description: Serialization of a polynomial
*
* Arguments:   - uint8_t *r: pointer to output byte array (needs space for KEM_POLYBYTES)
*              - const poly *a:    pointer to input polynomial
**************************************************/
void poly_tobytes(uint8_t *r, const poly *a)
{
  int i;
  uint16_t t0, t1;

  for(i=0;i<KEM_N/2;i++)
  {
    t0 = barrett_reduce(a->coeffs[2*i+0]);
    t1 = barrett_reduce(a->coeffs[2*i+1]);
    r[3*i+0] = t0 & 0xff;
    r[3*i+1] = (t0 >> 8) | ((t1 & 0xf) << 4);
    r[3*i+2] = (t1 >> 4) & 0xff;
  }
}

/*************************************************
* Name:        poly_frombytes
*
* Description: De-serialization of a polynomial;
*              inverse of poly_tobytes
*
* Arguments:   - poly *r:          pointer to output polynomial
*              - const uint8_t *a: pointer to input byte array (of KEM_POLYBYTES bytes)
**************************************************/
void poly_frombytes(poly *r, const uint8_t *a)
{
  int i;
  for(i=0;i<KEM_N/2;i++)
  {
    r->coeffs[2*i+0] = a[3*i+0] | ((uint16_t)(a[3*i+1] & 0x0f) << 8);
    r->coeffs[2*i+1] = (a[3*i+1] >> 4) | ((uint16_t)a[3*i+2] << 4);
  }
}

/*************************************************
* Name:        poly_frommsg
*
* Description: Convert 32-byte message to polynomial
*
* Arguments:   - poly *r:            pointer to output polynomial
*              - const uint8_t *msg: pointer to input message
**************************************************/
void poly_frommsg(poly *r, const uint8_t *msg)
{
  int i,j;
  int16_t mask;

  for(i=0;i<32;i++)
  {
    for(j=0;j<8;j++)
    {
      mask = -((msg[i] >> j)&1);
      r->coeffs[8*i+j] = mask & ((3329+1)/2);
    }
  }
}

/*************************************************
* Name:        poly_tomsg
*
* Description: Convert polynomial to 32-byte message
*
* Arguments:   - uint8_t *msg: pointer to output message
*              - const poly *a:      pointer to input polynomial
**************************************************/
void poly_tomsg(uint8_t *msg, const poly *a)
{
  int i,j;
  uint16_t t;

  for(i=0;i<32;i++)
  {
    msg[i] = 0;
    for(j=0;j<8;j++)
    {
      t = (((barrett_reduce(a->coeffs[8*i+j]) << 1) + 1665) / 3329) & 1;
      msg[i] |= t << j;
    }
  }
}

/*************************************************
* Name:        poly_getnoise
*
* Description: Sample a polynomial deterministically from a seed and a nonce,
*              with output polynomial close to centered binomial distribution
*              with parameter KEM_ETA
*
* Arguments:   - poly *r:                   pointer to output polynomial
*              - const uint8_t *seed:       pointer to input seed (of length KEM_SYMBYTES)
*              - uint8_t nonce:             one-byte input nonce
**************************************************/
void poly_getnoise(poly *r, const uint8_t *seed, uint8_t nonce)
{
  uint8_t buf[KEM_N];
  prf(buf, KEM_N, seed, nonce);
  cbd(r, buf);
}

/*************************************************
* Name:        poly_ntt
*
* Description: Computes number-theoretic transform (NTT) of a polynomial in place;
*              inputs assumed to be in normal order, output in bitreversed order
*
* Arguments:   - poly *r: pointer to in/output polynomial
**************************************************/
void poly_ntt(poly *r)
{
  ntt(r->coeffs);
}

/*************************************************
* Name:        poly_invntt
*
* Description: Computes inverse of number-theoretic transform (NTT) of a polynomial in place;
*              inputs assumed to be in bitreversed order, output in normal order
*
* Arguments:   - poly *r: pointer to in/output polynomial
**************************************************/
void poly_invntt(poly *r)
{
  invntt(r->coeffs);
}

/*************************************************
* Name:        poly_add
*
* Description: Add two polynomials
*
* Arguments: - poly *r:       pointer to output polynomial
*            - const poly *a: pointer to first input polynomial
*            - const poly *b: pointer to second input polynomial
**************************************************/
void poly_add(poly *r, const poly *a, const poly *b)
{
  int i;
  for(i=0;i<KEM_N;i++)
    r->coeffs[i] = barrett_reduce(a->coeffs[i] + b->coeffs[i]);
}

/*************************************************
* Name:        poly_sub
*
* Description: Subtract two polynomials
*
* Arguments: - poly *r:       pointer to output polynomial
*            - const poly *a: pointer to first input polynomial
*            - const poly *b: pointer to second input polynomial
**************************************************/
void poly_sub(poly *r, const poly *a, const poly *b)
{
  int i;
  for(i=0;i<KEM_N;i++)
    r->coeffs[i] = barrett_reduce(a->coeffs[i] - b->coeffs[i]);
}
