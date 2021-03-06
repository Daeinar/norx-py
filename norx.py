"""
   Python2 implementation of NORX.
   ------

   :author: Philipp Jovanovic <philipp@jovanovic.io>, 2014-2015.
   :license: CC0, see LICENSE for more details.
"""

from struct import pack, unpack


class NORX(object):

    def __init__(self, w=64, r=4, d=1, t=256):
        assert w in [32, 64]
        assert r >= 1
        assert d >= 0
        assert 10 * w >= t >= 0
        self.NORX_W = w
        self.NORX_R = r
        self.NORX_D = d
        self.NORX_T = t
        self.NORX_N = w * 2
        self.NORX_K = w * 4
        self.NORX_B = w * 16
        self.NORX_C = w * 6
        self.RATE = self.NORX_B - self.NORX_C
        self.HEADER_TAG = 1 << 0
        self.PAYLOAD_TAG = 1 << 1
        self.TRAILER_TAG = 1 << 2
        self.FINAL_TAG = 1 << 3
        self.BRANCH_TAG = 1 << 4
        self.MERGE_TAG = 1 << 5
        self.BYTES_WORD = w / 8
        self.BYTES_TAG = t / 8
        self.WORDS_RATE = self.RATE / w
        self.BYTES_RATE = self.WORDS_RATE * self.BYTES_WORD
        if w == 32:
            self.R = (8, 11, 16, 31)
            self.U = (0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344, 0x254F537A,
                      0x38531D48, 0x839C6E83, 0xF97A3AE5, 0x8C91D88C, 0x11EAFB59)
            self.M = 0xffffffff
            self.fmt = '<L'
        elif w == 64:
            self.R = (8, 19, 40, 63)
            self.U = (0x243F6A8885A308D3, 0x13198A2E03707344, 0xA4093822299F31D0, 0x082EFA98EC4E6C89, 0xAE8858DC339325A1,
                      0x670A134EE52D7FA6, 0xC4316D80CD967541, 0xD21DFBF8B630B762, 0x375A18D261E7F892, 0x343D1F187D92285B)
            self.M = 0xffffffffffffffff
            self.fmt = '<Q'

    def load(self, x):
        return unpack(self.fmt, x)[0]

    def store(self, x):
        return pack(self.fmt, x)

    def ROTR(self, a, r):
        return ((a >> r) | (a << (self.NORX_W - r))) & self.M

    def H(self, a, b):
        return ((a ^ b) ^ ((a & b) << 1)) & self.M

    def G(self, a, b, c, d):
        a = self.H(a, b)
        d = self.ROTR(a ^ d, self.R[0])
        c = self.H(c, d)
        b = self.ROTR(b ^ c, self.R[1])
        a = self.H(a, b)
        d = self.ROTR(a ^ d, self.R[2])
        c = self.H(c, d)
        b = self.ROTR(b ^ c, self.R[3])
        return a, b, c, d

    def F(self, S):
        # Column step
        S[0], S[4], S[8], S[12] = self.G(S[0], S[4], S[8], S[12])
        S[1], S[5], S[9], S[13] = self.G(S[1], S[5], S[9], S[13])
        S[2], S[6], S[10], S[14] = self.G(S[2], S[6], S[10], S[14])
        S[3], S[7], S[11], S[15] = self.G(S[3], S[7], S[11], S[15])
        # Diagonal step
        S[0], S[5], S[10], S[15] = self.G(S[0], S[5], S[10], S[15])
        S[1], S[6], S[11], S[12] = self.G(S[1], S[6], S[11], S[12])
        S[2], S[7], S[8], S[13] = self.G(S[2], S[7], S[8], S[13])
        S[3], S[4], S[9], S[14] = self.G(S[3], S[4], S[9], S[14])

    def permute(self, S):
        for i in xrange(self.NORX_R):
            self.F(S)

    def pad(self, x):
        y = bytearray(self.BYTES_RATE)
        y[:len(x)] = x
        y[len(x)] = 0x01
        y[self.BYTES_RATE-1] |= 0x80
        return y

    def init(self, S, n, k):
        b = self.BYTES_WORD
        K = [self.load(k[b*i:b*(i+1)]) for i in xrange(self.NORX_K / self.NORX_W)]
        N = [self.load(n[b*i:b*(i+1)]) for i in xrange(self.NORX_N / self.NORX_W)]
        U = self.U
        S[0], S[1], S[2], S[3] = U[0], N[0], N[1], U[1]
        S[4], S[5], S[6], S[7] = K[0], K[1], K[2], K[3]
        S[8], S[9], S[10], S[11] = U[2], U[3], U[4], U[5]
        S[12], S[13], S[14], S[15] = U[6], U[7], U[8], U[9]
        S[12] ^= self.NORX_W
        S[13] ^= self.NORX_R
        S[14] ^= self.NORX_D
        S[15] ^= self.NORX_T
        self.permute(S)

    def inject_tag(self, S, tag):
        S[15] ^= tag

    def process_header(self, S, x):
        return self.absorb_data(S, x, self.HEADER_TAG)

    def process_trailer(self, S, x):
        return self.absorb_data(S, x, self.TRAILER_TAG)

    def absorb_data(self, S, x, tag):
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                self.absorb_block(S, x[n*i:n*(i+1)], tag)
                inlen -= n
                i += 1
            self.absorb_lastblock(S, x[n*i:n*i+inlen], tag)

    def absorb_block(self, S, x, tag):
        b = self.BYTES_WORD
        self.inject_tag(S, tag)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            S[i] ^= self.load(x[b*i:b*(i+1)])

    def absorb_lastblock(self, S, x, tag):
        y = self.pad(x)
        self.absorb_block(S, y, tag)

    def encrypt_data(self, S, x):
        c = bytearray()
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                c += self.encrypt_block(S, x[n*i:n*(i+1)])
                inlen -= n
                i += 1
            c += self.encrypt_lastblock(S, x[n*i:n*i+inlen])
        return c

    def encrypt_block(self, S, x):
        c = bytearray()
        b = self.BYTES_WORD
        self.inject_tag(S, self.PAYLOAD_TAG)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            S[i] ^= self.load(x[b*i:b*(i+1)])
            c += self.store(S[i])
        return c[:self.BYTES_RATE]

    def encrypt_lastblock(self, S, x):
        y = self.pad(x)
        c = self.encrypt_block(S, y)
        return c[:len(x)]

    def decrypt_data(self, S, x):
        m = bytearray()
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                m += self.decrypt_block(S, x[n*i:n*(i+1)])
                inlen -= n
                i += 1
            m += self.decrypt_lastblock(S, x[n*i:n*i+inlen])
        return m

    def decrypt_block(self, S, x):
        m = bytearray()
        b = self.BYTES_WORD
        self.inject_tag(S, self.PAYLOAD_TAG)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            c = self.load(x[b*i:b*(i+1)])
            m += self.store(S[i] ^ c)
            S[i] = c
        return m[:self.BYTES_RATE]

    def decrypt_lastblock(self, S, x):
        m = bytearray()
        y = bytearray()
        b = self.BYTES_WORD
        self.inject_tag(S, self.PAYLOAD_TAG)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            y += self.store(S[i])
        y[:len(x)] = bytearray(x)
        y[len(x)] ^= 0x01
        y[self.BYTES_RATE-1] ^= 0x80
        for i in xrange(self.WORDS_RATE):
            c = self.load(y[b*i:b*(i+1)])
            m += self.store(S[i] ^ c)
            S[i] = c
        return m[:len(x)]

    def generate_tag(self, S):
        t = bytearray()
        self.inject_tag(S, self.FINAL_TAG)
        self.permute(S)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            t += self.store(S[i])
        return t[:self.BYTES_TAG]

    def verify_tag(self, t0, t1):
        acc = 0
        for i in xrange(self.BYTES_TAG):
            acc |= t0[i] ^ t1[i]
        return (((acc - 1) >> 8) & 1) - 1

    def aead_encrypt(self, h, m, t, n, k):
        assert len(k) == self.NORX_K / 8
        assert len(n) == self.NORX_N / 8
        c = bytearray()
        S = [0] * 16
        self.init(S, n, k)
        self.process_header(S, h)
        c += self.encrypt_data(S, m)
        self.process_trailer(S, t)
        c += self.generate_tag(S)
        return str(c)

    def aead_decrypt(self, h, c, t, n, k):
        assert len(k) == self.NORX_K / 8
        assert len(n) == self.NORX_N / 8
        assert len(c) >= self.BYTES_TAG
        m = bytearray()
        c = bytearray(c)
        S = [0] * 16
        d = len(c)-self.BYTES_TAG
        c, t0 = c[:d], c[d:]
        self.init(S, n, k)
        self.process_header(S, h)
        m += self.decrypt_data(S, c)
        self.process_trailer(S, t)
        t1 = self.generate_tag(S)
        if self.verify_tag(t0, t1) != 0:
            m = ''
        return str(m)
