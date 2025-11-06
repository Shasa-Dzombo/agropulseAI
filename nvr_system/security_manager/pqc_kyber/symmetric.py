# Symmetric primitives for Kyber (SHAKE-based)
import pysha3

def SHAKE128(data, length):
    return pysha3.shake_128(data).digest(length)

def SHAKE256(data, length):
    return pysha3.shake_256(data).digest(length)

def PRF(length, key, nonce):
    """
    Pseudo-Random Function using SHAKE-256.
    """
    return SHAKE256(key + nonce.to_bytes(1, 'big'), length)

def KDF(data):
    """
    Key Derivation Function using SHAKE-256.
    """
    return SHAKE256(data, 32)

def G(data):
    """
    Function G using SHAKE-256, returns two 32-byte outputs.
    """
    output = SHAKE256(data, 64)
    return output[:32], output[32:]

def H(data):
    """
    Function H using SHAKE-256, returns one 32-byte output.
    """
    return SHAKE256(data, 32)
