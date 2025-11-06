#ifndef NTT_H
#define NTT_H

#include <stdint.h>

extern const int16_t zetas[128];

void ntt(int16_t *poly);
void invntt(int16_t *poly);

#endif
