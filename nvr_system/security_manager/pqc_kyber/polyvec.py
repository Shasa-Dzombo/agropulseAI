# Polynomial Vector class for Kyber
from .poly import Poly
from .params import KEM_K, KEM_N, KEM_Q, KEM_ETA1

class Polyvec:
    def __init__(self, vec=None):
        if vec is None:
            self.vec = [Poly() for _ in range(KEM_K)]
        else:
            self.vec = vec

    def reduce(self):
        for p in self.vec:
            p.reduce()
        return self

    def add(self, other):
        for i in range(KEM_K):
            self.vec[i].add(other.vec[i])
        return self

    def ntt(self):
        for p in self.vec:
            p.ntt()

    def inv_ntt(self):
        for p in self.vec:
            p.inv_ntt()

    @staticmethod
    def pointwise_multiply(a, b):
        # a is a list of Poly, b is a Polyvec
        r = Poly()
        for i in range(KEM_K):
            # This is a simplification. Real multiplication is more complex.
            for j in range(KEM_N):
                r.coeffs[j] += a[i].coeffs[j] * b.vec[i].coeffs[j]
        return r

    @staticmethod
    def get_noise(seed, offset, num_polys, eta):
        p = Polyvec([Poly() for _ in range(num_polys)])
        for i in range(num_polys):
            p.vec[i] = Poly.get_noise(seed, offset + i, eta)
        return p

    def to_bytes(self):
        return b"".join(p.to_bytes() for p in self.vec)

    @staticmethod
    def from_bytes(b):
        poly_bytes_len = KEM_N * 2
        return Polyvec([Poly.from_bytes(b[i*poly_bytes_len:(i+1)*poly_bytes_len]) for i in range(KEM_K)])

    def compress(self):
        # Placeholder
        return self.to_bytes()

    @staticmethod
    def decompress(b):
        # Placeholder
        return Polyvec.from_bytes(b)
