#ifndef PARAMS_H
#define PARAMS_H

#define KEM_N 256
#define KEM_K 3
#define KEM_DU 10
#define KEM_DV 4
#define KEM_ETA1 2
#define KEM_ETA2 2

#define KEM_PUBLICKEYBYTES (KEM_K * 320 + 32)
#define KEM_SECRETKEYBYTES (KEM_K * 384 * 2 + 32 + 32)
#define KEM_CIPHERTEXTBYTES (KEM_DU * KEM_K * 32 + KEM_DV * 32)
#define KEM_BYTES 32

#endif
