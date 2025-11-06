# IND-CPA secure Public Key Encryption
from .polyvec import Polyvec
from .poly import Poly
from .symmetric import PRF, G
from .params import KEM_K, KEM_N, KEM_Q, KEM_ETA1, KEM_SYMBYTES
import os

def _gen_matrix(seed, transposed=False):
    """
    Generate matrix A (or A^T) from a seed.
    """
    A = [[Poly() for _ in range(KEM_K)] for _ in range(KEM_K)]
    for i in range(KEM_K):
        for j in range(KEM_K):
            if transposed:
                A[i][j] = Poly.from_uniform(seed, i, j)
            else:
                A[i][j] = Poly.from_uniform(seed, j, i)
    return A

def indcpa_keypair():
    """
    Generates public and private key for the IND-CPA scheme.
    """
    d = os.urandom(KEM_SYMBYTES)
    rho, sigma = G(d)
    
    A = _gen_matrix(rho)
    
    s = Polyvec.get_noise(sigma, 0, KEM_K, KEM_ETA1)
    e = Polyvec.get_noise(sigma, KEM_K, KEM_K, KEM_ETA1)
    
    s.ntt()
    e.ntt()
    
    pk_polyvec = Polyvec()
    for i in range(KEM_K):
        pk_polyvec.vec[i] = Polyvec.pointwise_multiply(A[i], s).reduce()
    
    pk_polyvec.add(e)
    pk_polyvec.reduce()
    
    pk = pk_polyvec.to_bytes() + rho
    sk = s.to_bytes()
    
    return pk, sk

def indcpa_enc(m, pk, coins):
    """
    Encrypts a message using the public key.
    """
    rho = pk[-KEM_SYMBYTES:]
    pk_polyvec = Polyvec.from_bytes(pk)
    
    A_t = _gen_matrix(rho, transposed=True)
    
    r = Polyvec.get_noise(coins, 0, KEM_K, KEM_ETA1)
    e1 = Polyvec.get_noise(coins, KEM_K, KEM_K, KEM_ETA1)
    e2 = Poly.get_noise(coins, 2 * KEM_K, KEM_ETA1)
    
    r.ntt()
    
    u = Polyvec()
    for i in range(KEM_K):
        u.vec[i] = Polyvec.pointwise_multiply(A_t[i], r).reduce()
    u.inv_ntt()
    u.add(e1)
    u.reduce()
    
    k = Poly.from_message(m)
    
    v_poly = Polyvec.pointwise_multiply(pk_polyvec, r).reduce()
    v_poly.inv_ntt()
    v_poly.add(e2)
    v_poly.add(k)
    v_poly.reduce()
    
    c1 = u.compress()
    c2 = v_poly.compress()
    
    return c1 + c2

def indcpa_dec(c, sk):
    """
    Decrypts a ciphertext using the secret key.
    """
    u = Polyvec.decompress(c)
    v = Poly.decompress(c[KEM_K * 320:])
    
    sk_polyvec = Polyvec.from_bytes(sk)
    
    u.ntt()
    
    mp = Polyvec.pointwise_multiply(sk_polyvec, u).reduce()
    mp.inv_ntt()
    
    mp.sub(v)
    mp.reduce()
    
    return mp.to_message()
