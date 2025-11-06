#include "verify.h"

/*************************************************
* Name:        verify
*
* Description: Compare two arrays for equality in constant time.
*
* Arguments:   - const uint8_t *a: pointer to first array
*              - const uint8_t *b: pointer to second array
*              - size_t len:       length of the arrays
*
* Returns 0 if the arrays are equal, 1 otherwise
**************************************************/
int verify(const uint8_t *a, const uint8_t *b, size_t len)
{
  uint64_t r;
  size_t i;
  r = 0;

  for(i=0;i<len;i++)
    r |= a[i] ^ b[i];

  r = (-r) >> 63;
  return r;
}

/*************************************************
* Name:        cmov
*
* Description: Constant-time conditional move.
*              If b is 1, copy x to r. Otherwise, r is left unchanged.
*
* Arguments:   - uint8_t *r:       pointer to output array
*              - const uint8_t *x: pointer to input array
*              - size_t len:       length of the arrays
*              - uint8_t b:        condition bit
**************************************************/
void cmov(uint8_t *r, const uint8_t *x, size_t len, uint8_t b)
{
  size_t i;

  b = -b;
  for(i=0;i<len;i++)
    r[i] ^= b & (r[i] ^ x[i]);
}
