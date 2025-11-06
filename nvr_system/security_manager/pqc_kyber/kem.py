# Kyber Key Encapsulation Mechanism
from .indcpa import indcpa_keypair, indcpa_enc, indcpa_dec
from .symmetric import KDF, G, H
from .params import KEM_PUBLICKEYBYTES, KEM_SECRETKEYBYTES, KEM_CIPHERTEXTBYTES, KEM_BYTES
import os

def crypto_kem_keypair():
    """
    Generates public and private key for CCA-secure Kyber KEM.
    """
    pk, sk_indcpa = indcpa_keypair()
    sk = sk_indcpa + pk + H(pk) + os.urandom(KEM_BYTES)
    return pk, sk

def crypto_kem_enc(pk):
    """
    Generates cipher text and shared secret for given public key.
    """
    random_bytes = os.urandom(KEM_BYTES)
    m = H(random_bytes)
    
    h_pk = H(pk)
    kr = G(m + h_pk)
    k, r = kr[:KEM_BYTES], kr[KEM_BYTES:]
    
    c = indcpa_enc(m, pk, r)
    
    h_c = H(c)
    ss = KDF(k + h_c)
    
    return c, ss

def crypto_kem_dec(c, sk):
    """
    Generates shared secret for given cipher text and private key.
    """
    # Extract components from secret key
    sk_indcpa = sk[:12 * 32 * 3 // 8]
    pk = sk[12 * 32 * 3 // 8 : 12 * 32 * 3 // 8 + KEM_PUBLICKEYBYTES]
    h_pk = sk[12 * 32 * 3 // 8 + KEM_PUBLICKEYBYTES : 12 * 32 * 3 // 8 + KEM_PUBLICKEYBYTES + 32]
    z = sk[12 * 32 * 3 // 8 + KEM_PUBLICKEYBYTES + 32:]

    m_prime = indcpa_dec(c, sk_indcpa)
    
    kr_prime = G(m_prime + h_pk)
    k_prime, r_prime = kr_prime[:KEM_BYTES], kr_prime[KEM_BYTES:]
    
    c_prime = indcpa_enc(m_prime, pk, r_prime)
    
    h_c = H(c)
    
    if c == c_prime:
        ss = KDF(k_prime + h_c)
    else:
        ss = KDF(z + h_c)
        
    return ss
