"""
   NORX reference Python2 implementation.
   ------

   :copyright: (c) 2014 by Philipp Jovanovic <philipp@jovanovic.io>.
   :license: CC0, see LICENSE for more details.
"""
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
            self.U = (0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344)
            self.M = 0xffffffff
        elif w == 64:
            self.R = (8,19,40,63)
            self.U = (0x243F6A8885A308D3, 0x13198A2E03707344, 0xA4093822299F31D0, 0x082EFA98EC4E6C89)
            self.M = 0xffffffffffffffff

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
        a = self.H(a,b)
        d = self.ROTR(a^d,self.R[0])
        c = self.H(c,d)
        b = self.ROTR(b^c,self.R[1])
        a = self.H(a,b)
        d = self.ROTR(a^d,self.R[2])
        c = self.H(c,d)
        b = self.ROTR(b^c,self.R[3])
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
