#include <stddef.h>
#include <stdint.h>
#include "fips202.h"
#include "symmetric.h"

#include "mbedtls/sha3.h"

void shake128(uint8_t *output, size_t outlen, const uint8_t *input, size_t inlen)
{
  mbedtls_sha3_context ctx;
  mbedtls_sha3_init(&ctx);
  mbedtls_sha3_starts(&ctx, MBEDTLS_SHA3_SHAKE128);
  mbedtls_sha3_update(&ctx, input, inlen);
  mbedtls_sha3_finish(&ctx, output, outlen);
  mbedtls_sha3_free(&ctx);
}

void shake256(uint8_t *output, size_t outlen, const uint8_t *input, size_t inlen)
{
  mbedtls_sha3_context ctx;
  mbedtls_sha3_init(&ctx);
  mbedtls_sha3_starts(&ctx, MBEDTLS_SHA3_SHAKE256);
  mbedtls_sha3_update(&ctx, input, inlen);
  mbedtls_sha3_finish(&ctx, output, outlen);
  mbedtls_sha3_free(&ctx);
}
