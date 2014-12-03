"""
   NORX reference Python2 implementation.
   ------

   :copyright: (c) 2014 by Philipp Jovanovic <philipp@jovanovic.io>.
   :license: CC0, see LICENSE for more details.
"""

from struct import unpack, pack

class NORX:

    def __init__(self,w=64,r=4,d=1,t=256):
        assert w in [32,64]
        assert r >= 1
        assert d >= 0
        assert 10*w >= t >= 0
        self.NORX_W = w
        self.NORX_R = r
        self.NORX_D = d
        self.NORX_T = t
        self.NORX_N = w * 2
        self.NORX_K = w * 4
        self.NORX_B = w * 16
        self.NORX_C = w * 6
        self.RATE = self.NORX_B - self.NORX_C
        self.HEADER_TAG =  1 << 0
        self.PAYLOAD_TAG = 1 << 1
        self.TRAILER_TAG = 1 << 2
        self.FINAL_TAG =   1 << 3
        self.BRANCH_TAG =  1 << 4
        self.MERGE_TAG =   1 << 5

        self.BYTES_WORD = w / 8
        self.BYTES_TAG = t / 8
        self.WORDS_RATE = self.RATE / w
        self.BYTES_RATE = self.WORDS_RATE * self.BYTES_WORD

        if w == 32:
            self.R = (8,11,16,31)
            self.U = (0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344, 0x254F537A,
                      0x38531D48, 0x839C6E83, 0xF97A3AE5, 0x8C91D88C, 0x11EAFB59)
            self.M = 0xffffffff
            self.fmt = '<L'
        elif w == 64:
            self.R = (8,19,40,63)
            self.U = (0x243F6A8885A308D3, 0x13198A2E03707344, 0xA4093822299F31D0, 0x082EFA98EC4E6C89, 0xAE8858DC339325A1,
                      0x670A134EE52D7FA6, 0xC4316D80CD967541, 0xD21DFBF8B630B762, 0x375A18D261E7F892, 0x343D1F187D92285B)
            self.M = 0xffffffffffffffff
            self.fmt = '<Q'

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

    def permute(self,S):
        for i in xrange(self.NORX_R):
            self.F(S)

    def pad(self,x):
        x += chr(0x01) + chr(0x00) * (self.BYTES_RATE-len(x)-1)
        return x[:-1] + chr(ord(x[self.BYTES_RATE - 1]) | 0x80)

    def init(self,S,n,k):
        assert len(k) == self.NORX_K / 8
        assert len(n) == self.NORX_N / 8

        b = self.BYTES_WORD
        K = [ unpack(self.fmt, k[b*i:b*(i+1)])[0] for i in xrange(self.NORX_K / self.NORX_W) ]
        N = [ unpack(self.fmt, n[b*i:b*(i+1)])[0] for i in xrange(self.NORX_N / self.NORX_W) ]
        U = self.U

        S[ 0], S[ 1], S[ 2], S[ 3] = U[0], N[0], N[1], U[1]
        S[ 4], S[ 5], S[ 6], S[ 7] = K[0], K[1], K[2], K[3]
        S[ 8], S[ 9], S[10], S[11] = U[2], U[3], U[4], U[5]
        S[12], S[13], S[14], S[15] = U[6], U[7], U[8], U[9]

        S[12] ^= self.NORX_W
        S[13] ^= self.NORX_R
        S[14] ^= self.NORX_D
        S[15] ^= self.NORX_T

        self.permute(S)

    def inject_tag(self,S,tag):
        S[15] ^= tag

    def process_header(self,S,x):
        return self.absorb_data(S,x,self.HEADER_TAG)

    def process_trailer(self,S,x):
        return self.absorb_data(S,x,self.TRAILER_TAG)

    def absorb_data(self,S,x,tag):
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                self.absorb_block(S,x[n*i:n*(i+1)],tag)
                inlen -= n
                i += 1
            self.absorb_block(S,self.pad(x[n*i:n*i+inlen]),tag)

    def absorb_block(self,S,x,tag):
        b = self.BYTES_WORD
        self.inject_tag(S,tag)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            S[i] ^= unpack(self.fmt,x[b*i:b*(i+1)])[0]

    def encrypt_data(self,S,x):
        c = ''
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                c += self.encrypt_block(S,x[n*i:n*(i+1)],n)
                inlen -= n
                i +=1
            c += self.encrypt_block(S,self.pad(x[n*i:n*i+inlen]),inlen)
        return c

    def encrypt_block(self,S,x,xlen):
        c = ''
        b = self.BYTES_WORD
        self.inject_tag(S,self.PAYLOAD_TAG)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            S[i] ^= unpack(self.fmt,x[b*i:b*(i+1)])[0]
            c += pack(self.fmt,S[i])
        return c[:xlen]

    def decrypt_data(self,S,x):
        m = ''
        inlen = len(x)
        if inlen > 0:
            i, n = 0, self.BYTES_RATE
            while inlen >= n:
                m += decrypt_block(S,x,xlen)
                inlen -= n
                i +=1
            m += self.decrypt_lastblock(S,x[n*i:n*i+inlen],inlen)
        return m

    def decrypt_block(self,S,x,xlen):
        m = ''
        b = self.BYTES_WORD
        self.inject_tag(S,self.PAYLOAD_TAG)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            c = unpack(self.fmt,x[b*i:b*(i+1)])[0]
            m += pack(self.fmt,S[i] ^ c)
            S[i] = c
        return m[:xlen]

    def decrypt_lastblock(self,S,x,xlen):
        m = ''
        y = '' # lastblock
        b = self.BYTES_WORD
        self.inject_tag(S,self.PAYLOAD_TAG)
        self.permute(S)

        for i in xrange(self.WORDS_RATE):
            y += pack(self.fmt,S[i])

        y = x + y[xlen:]
        y = y[:xlen] + chr(ord(y[xlen]) ^ 0x01) + y[xlen+1:self.BYTES_RATE-1] + chr(ord(y[self.BYTES_RATE - 1]) ^ 0x80) + y[self.BYTES_RATE:]

        for i in xrange(self.WORDS_RATE):
            c = unpack(self.fmt,y[b*i:b*(i+1)])[0]
            m += pack(self.fmt,S[i] ^ c)
            S[i] = c
        return m[:xlen]

    def generate_tag(self,S):
        t = ''
        self.inject_tag(S,self.FINAL_TAG)
        self.permute(S)
        self.permute(S)
        for i in xrange(self.WORDS_RATE):
            t += pack(self.fmt,S[i])
        return t[:self.BYTES_TAG]

    def verify_tag(self):
        pass

    def aead_encrypt(self,h,m,t,nonce,key):
        S = [0] * 16
        c = ''
        self.init(S,nonce,key)
        self.process_header(S,h)
        c += self.encrypt_data(S,m)
        self.process_trailer(S,t)
        c += self.generate_tag(S)
        return c

    def aead_decrypt(self,h,c,t,nonce,key):
        S = [0] * 16
        m = ''
        n = len(c)-self.BYTES_TAG
        c,tag = c[:n],c[n:]
        self.init(S,nonce,key)
        self.process_header(S,h)
        m += self.decrypt_data(S,c)
        self.process_trailer(S,t)
        gtag = self.generate_tag(S)
        if tag != gtag:
            m = ''
        return m
