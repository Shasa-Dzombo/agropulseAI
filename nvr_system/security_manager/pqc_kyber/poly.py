# Polynomial class for Kyber
from .ntt import ntt, inv_ntt, ntt_multiply
from .cbd import cbd
from .symmetric import PRF
from .params import KEM_N, KEM_Q, KEM_ETA1
import ctypes

class Poly:
    def __init__(self, coeffs=None):
        if coeffs is None:
            self.coeffs = [0] * KEM_N
        else:
            self.coeffs = list(coeffs)

    def reduce(self):
        for i in range(KEM_N):
            self.coeffs[i] %= KEM_Q
        return self

    def add(self, other):
        for i in range(KEM_N):
            self.coeffs[i] += other.coeffs[i]
        return self

    def sub(self, other):
        for i in range(KEM_N):
            self.coeffs[i] = other.coeffs[i] - self.coeffs[i]
        return self

    def ntt(self):
        self.coeffs = ntt(self.coeffs)

    def inv_ntt(self):
        self.coeffs = inv_ntt(self.coeffs)

    @staticmethod
    def from_message(msg):
        p = Poly()
        for i in range(KEM_N // 8):
            for j in range(8):
                if (msg[i] >> j) & 1:
                    p.coeffs[8 * i + j] = (KEM_Q + 1) // 2
        return p

    def to_message(self):
        msg = bytearray(KEM_N // 8)
        for i in range(KEM_N // 8):
            for j in range(8):
                t = self.coeffs[8 * i + j]
                t += (t >> 15) & KEM_Q
                t = (((t << 1) + KEM_Q // 2) // KEM_Q) & 1
                msg[i] |= t << j
        return bytes(msg)

    @staticmethod
    def get_noise(seed, nonce, eta):
        return Poly(cbd(PRF(eta * KEM_N // 4, seed, nonce), eta))

    @staticmethod
    def from_uniform(seed, b1, b2):
        # Placeholder for uniform polynomial generation
        # In a real implementation, this would use SHAKE-128
        return Poly([int.from_bytes(PRF(2, seed, b1+b2+i), 'little') % KEM_Q for i in range(KEM_N)])

    def to_bytes(self):
        # Placeholder for serialization
        return b''.join(c.to_bytes(2, 'little') for c in self.coeffs)

    @staticmethod
    def from_bytes(b):
        # Placeholder for deserialization
        return Poly([int.from_bytes(b[i:i+2], 'little') for i in range(0, len(b), 2)])

    def compress(self):
        # Placeholder for compression
        return self.to_bytes()

    @staticmethod
    def decompress(b):
        # Placeholder for decompression
        return Poly.from_bytes(b)
