#include "polyvec.h"
#include "poly.h"

/*************************************************
* Name:        polyvec_compress
*
* Description: Compress and serialize vector of polynomials
*
* Arguments:   - uint8_t *r: pointer to output byte array (needs space for KEM_POLYVECCOMPRESSEDBYTES)
*              - const polyvec *a: pointer to input vector of polynomials
**************************************************/
void polyvec_compress(uint8_t *r, const polyvec *a)
{
  int i,j,k;

  for(i=0;i<KEM_K;i++)
  {
    for(j=0;j<KEM_N/4;j++)
    {
      for(k=0;k<4;k++)
        r[i*320+j*5+k] = ((((uint32_t)a->vec[i].coeffs[4*j+k] << 10) + 1664) / 3329) & 0x3ff;
    }
  }
}

/*************************************************
* Name:        polyvec_decompress
*
* Description: De-serialize and decompress vector of polynomials;
*              approximate inverse of polyvec_compress
*
* Arguments:   - polyvec *r:       pointer to output vector of polynomials
*              - const uint8_t *a: pointer to input byte array (of length KEM_POLYVECCOMPRESSEDBYTES)
**************************************************/
void polyvec_decompress(polyvec *r, const uint8_t *a)
{
  int i,j;
  for(i=0;i<KEM_K;i++)
  {
    for(j=0;j<KEM_N/2;j++)
    {
      r->vec[i].coeffs[2*j+0] = (((uint32_t)(a[i*160+j] & 15)*3329)+8)>>4;
      r->vec[i].coeffs[2*j+1] = (((uint32_t)(a[i*160+j] >> 4)*3329)+8)>>4;
    }
  }
}

/*************************************************
* Name:        polyvec_tobytes
*
* Description: Serialize vector of polynomials
*
* Arguments:   - uint8_t *r: pointer to output byte array (needs space for KEM_POLYVECBYTES)
*              - const polyvec *a: pointer to input vector of polynomials
**************************************************/
void polyvec_tobytes(uint8_t *r, const polyvec *a)
{
  int i;
  for(i=0;i<KEM_K;i++)
    poly_tobytes(r+i*KEM_POLYBYTES, &a->vec[i]);
}

/*************************************************
* Name:        polyvec_frombytes
*
* Description: De-serialize vector of polynomials;
*              inverse of polyvec_tobytes
*
* Arguments:   - uint8_t *r: pointer to output byte array
*              - const polyvec *a: pointer to input vector of polynomials (of length KEM_POLYVECBYTES)
**************************************************/
void polyvec_frombytes(polyvec *r, const uint8_t *a)
{
  int i;
  for(i=0;i<KEM_K;i++)
    poly_frombytes(&r->vec[i], a+i*KEM_POLYBYTES);
}

/*************************************************
* Name:        polyvec_ntt
*
* Description: Apply forward NTT to all elements of a vector of polynomials
*
* Arguments:   - polyvec *r: pointer to in/output vector of polynomials
**************************************************/
void polyvec_ntt(polyvec *r)
{
  int i;
  for(i=0;i<KEM_K;i++)
    poly_ntt(&r->vec[i]);
}

/*************************************************
* Name:        polyvec_invntt
*
* Description: Apply inverse NTT to all elements of a vector of polynomials
*
* Arguments:   - polyvec *r: pointer to in/output vector of polynomials
**************************************************/
void polyvec_invntt(polyvec *r)
{
  int i;
  for(i=0;i<KEM_K;i++)
    poly_invntt(&r->vec[i]);
}

/*************************************************
* Name:        polyvec_pointwise_acc
*
* Description: Pointwise multiply elements of a and b and accumulate into r
*
* Arguments: - poly *r:          pointer to output polynomial
*            - const polyvec *a: pointer to first input vector of polynomials
*            - const polyvec *b: pointer to second input vector of polynomials
**************************************************/
void polyvec_pointwise_acc(poly *r, const polyvec *a, const polyvec *b)
{
  int i,j;
  int16_t t;

  for(j=0;j<KEM_N;j++)
    r->coeffs[j] = 0;

  for(i=0;i<KEM_K;i++)
  {
    for(j=0;j<KEM_N;j++)
    {
      t = montgomery_reduce((int32_t)a->vec[i].coeffs[j] * b->vec[i].coeffs[j]);
      r->coeffs[j] = barrett_reduce(r->coeffs[j] + t);
    }
  }
}

/*************************************************
* Name:        polyvec_add
*
* Description: Add vectors of polynomials
*
* Arguments: - polyvec *r:       pointer to output vector of polynomials
*            - const polyvec *a: pointer to first input vector of polynomials
*            - const polyvec *b: pointer to second input vector of polynomials
**************************************************/
void polyvec_add(polyvec *r, const polyvec *a, const polyvec *b)
{
  int i;
  for(i=0;i<KEM_K;i++)
    poly_add(&r->vec[i], &a->vec[i], &b->vec[i]);
}
