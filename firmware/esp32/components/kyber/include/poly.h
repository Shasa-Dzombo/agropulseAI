#ifndef POLY_H
#define POLY_H

#include <stdint.h>
#include "params.h"

typedef struct {
    int16_t coeffs[KEM_N];
} poly;

void poly_compress(uint8_t *r, const poly *a);
void poly_decompress(poly *r, const uint8_t *a);

void poly_tobytes(uint8_t *r, const poly *a);
void poly_frombytes(poly *r, const uint8_t *a);

void poly_frommsg(poly *r, const uint8_t *msg);
void poly_tomsg(uint8_t *msg, const poly *a);

void poly_getnoise(poly *r, const uint8_t *seed, uint8_t nonce);

void poly_ntt(poly *r);
void poly_invntt(poly *r);

void poly_add(poly *r, const poly *a, const poly *b);
void poly_sub(poly *r, const poly *a, const poly *b);

#endif
