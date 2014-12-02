"""
   NORX reference Python2 implementation.
   ------

   :copyright: (c) 2014 by Philipp Jovanovic <philipp@jovanovic.io>.
   :license: CC0, see LICENSE for more details.
"""

import struct

class NORX:

    def __init__(self,w=64,r=4,d=1,t=256):
        assert w in [32,64]
        assert r >= 1
        assert d >= 0
        assert t >= 0
        self.NORX_W = w
        self.NORX_R = r
        self.NORX_D = d
        self.NORX_T = t
        self.NORX_N = w * 2
        self.NORX_K = w * 4
        self.NORX_B = w * 16
        self.NORX_C = w * 6
        self.RATE = self.NORX_B - self.NORX_C

        if w == 32:
            self.R = (8,11,16,31)
            self.U = (0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344,
                      0x254F537A, 0x38531D48, 0x839C6E83, 0xF97A3AE5,
                      0x8C91D88C, 0x11EAFB59)
            self.M = 0xffffffff
            self.fmt = '<L'
        elif w == 64:
            self.R = (8,19,40,63)
            self.U = (0x243F6A8885A308D3, 0x13198A2E03707344, 0xA4093822299F31D0, 0x082EFA98EC4E6C89,
                      0xAE8858DC339325A1, 0x670A134EE52D7FA6, 0xC4316D80CD967541, 0xD21DFBF8B630B762,
                      0x375A18D261E7F892, 0x343D1F187D92285B)
            self.M = 0xffffffffffffffff
            self.fmt = '<Q'

        self.DS = {
            'HEADER_TAG':  1 << 0,
            'PAYLOAD_TAG': 1 << 1,
            'TRAILER_TAG': 1 << 2,
            'FINAL_TAG':   1 << 3,
            'BRANCH_TAG':  1 << 4,
            'MERGE_TAG':   1 << 5,
        }

    def ROTR(self,a,r):
        return ((a >> r) | (a << (self.NORX_W - r))) & self.M

    def H(self,a,b):
        return ((a ^ b) ^ ((a & b) << 1)) & self.M

    def G(self,a,b,c,d):
        a = self.H(a, b)
        d = self.ROTR(a ^ d, self.R[0])
        c = self.H(c, d)
        b = self.ROTR(b ^ c, self.R[1])
        a = self.H(a, b)
        d = self.ROTR(a ^ d, self.R[2])
        c = self.H(c, d)
        b = self.ROTR(b ^ c, self.R[3])
        return a,b,c,d

    def F(self,S):
        # Column step
        S[ 0], S[ 4], S[ 8], S[12] = self.G(S[ 0], S[ 4], S[ 8], S[12]);
        S[ 1], S[ 5], S[ 9], S[13] = self.G(S[ 1], S[ 5], S[ 9], S[13]);
        S[ 2], S[ 6], S[10], S[14] = self.G(S[ 2], S[ 6], S[10], S[14]);
        S[ 3], S[ 7], S[11], S[15] = self.G(S[ 3], S[ 7], S[11], S[15]);
        # Diagonal step
        S[ 0], S[ 5], S[10], S[15] = self.G(S[ 0], S[ 5], S[10], S[15]);
        S[ 1], S[ 6], S[11], S[12] = self.G(S[ 1], S[ 6], S[11], S[12]);
        S[ 2], S[ 7], S[ 8], S[13] = self.G(S[ 2], S[ 7], S[ 8], S[13]);
        S[ 3], S[ 4], S[ 9], S[14] = self.G(S[ 3], S[ 4], S[ 9], S[14]);
        return S

    def FR(self,S):
        for i in xrange(self.NORX_R):
            S = self.F(S)
        return S

    def pad(self):
        pass

    def init(self,k,n):
        assert len(k) == self.NORX_K / 8
        assert len(n) == self.NORX_N / 8

        S = [0] * 16
        K = [ struct.unpack(self.fmt, k[4*i:4*(i+1)])[0] for i in xrange(4) ]
        N = [ struct.unpack(self.fmt, n[4*i:4*(i+1)])[0] for i in xrange(2) ]
        U = self.U

        S[ 0], S[ 1], S[ 2], S[ 3] = U[0], N[0], N[1], U[1]
        S[ 4], S[ 5], S[ 6], S[ 7] = K[0], K[1], K[2], K[3]
        S[ 8], S[ 9], S[10], S[11] = U[2], U[3], U[4], U[5]
        S[12], S[13], S[14], S[15] = U[6], U[7], U[8], U[9]

        S[12] ^= self.NORX_W
        S[13] ^= self.NORX_R
        S[14] ^= self.NORX_D
        S[15] ^= self.NORX_T

        S = self.FR(S)

        return S

    def absorb(self):
        pass

    def absorb_block(self):
        pass

    def encrypt(self):
        pass

    def encrypt_block(self):
        pass

    def decrypt(self):
        pass

    def decrypt_block(self):
        pass

    def generate_tag(self):
        pass

    def verify_tag(self):
        pass

    def aead_encrypt(self):
        pass

    def aead_decrypt(self):
        pass
