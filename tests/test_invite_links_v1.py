"""Executable examples for the proposed invite profile, not a production client.

These fixtures check canonical bytes, consent binding, preview authentication and
bounds. They deliberately do not implement MLS, NIP-59 or state convergence.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric import ed25519, ec
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

ROOT = Path(__file__).resolve().parents[1]
V = json.loads((ROOT / 'tests/vectors/invite-links-v1.json').read_text())
CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


def qlen(n):
    for size, bound, flag in [(1, 64, 0), (2, 16384, 0x4000),
                              (4, 1 << 30, 0x80000000), (8, 1 << 62, 0xc000000000000000)]:
        if 0 <= n < bound:
            return (n | flag).to_bytes(size, 'big')
    raise ValueError('length')


def vector(b):
    return qlen(len(b)) + b


class Reader:
    def __init__(self, b):
        self.b = b
        self.pos = 0

    def take(self, n):
        if n < 0 or self.pos + n > len(self.b):
            raise ValueError('truncated')
        out = self.b[self.pos:self.pos+n]
        self.pos += n
        return out

    def num(self, n):
        return int.from_bytes(self.take(n), 'big')

    def vec(self, lo, hi):
        first = self.take(1)[0]
        size = 1 << (first >> 6)
        raw = bytes([first]) + self.take(size - 1)
        n = int.from_bytes(raw, 'big') & ((1 << (size*8-2))-1)
        if not lo <= n <= hi or raw != qlen(n):
            raise ValueError('noncanonical or bound')
        return self.take(n)

    def end(self):
        if self.pos != len(self.b):
            raise ValueError('trailing')


def secp_key(b):
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), b'\x02' + b)


def relay_list(b, allow_empty=False):
    r = Reader(b)
    items = []
    while r.pos < len(b):
        url = r.vec(1, 512)
        # Fixtures use the adopted profile's ASCII WSS subset.
        if not re.fullmatch(rb'wss://[a-z0-9.-]+(?:/[a-z0-9/-]*)?', url):
            raise ValueError('relay')
        items.append(url)
    if not (0 if allow_empty else 1) <= len(items) <= 8 or sorted(set(items)) != items:
        raise ValueError('relay list')
    return items


def code(b):
    r = Reader(b)
    if r.num(2) != 1:
        raise ValueError('version')
    inbox = r.take(32)
    secp_key(inbox)
    fields = [inbox] + [r.take(32) for _ in range(3)]
    relays = relay_list(r.vec(1, 4096))
    r.end()
    return fields, relays


def component(b):
    outer = Reader(b)
    r = Reader(outer.vec(0, 1096))
    outer.end()
    rows = []
    while r.pos < len(r.b):
        row = r.take(137)
        secp_key(row[32:64])
        if int.from_bytes(row[128:136], 'big') > 9007199254740991 or row[136] > 1:
            raise ValueError('policy')
        rows.append(row)
    ids = [x[:32] for x in rows]
    inboxes = [x[32:64] for x in rows]
    if ids != sorted(set(ids)) or len(inboxes) != len(set(inboxes)):
        raise ValueError('duplicate or order')
    return rows


def request(b):
    r = Reader(b)
    context = r.take(170)
    if context[:2] != b'\x00\x01' or not 0 < int.from_bytes(context[-8:], 'big') <= 9007199254740991:
        raise ValueError('context')
    secp_key(context[2:34])
    secp_key(context[98:130])
    rev = r.num(4)
    if rev > 7:
        raise ValueError('revision')
    prev, bearer, kp = r.take(32), r.take(32), r.take(32)
    offer = Reader(r.vec(1, 8192))
    event_id = offer.take(32)
    relay_list(offer.vec(0, 4096), allow_empty=True)
    offer.end()
    sig = r.take(64)
    r.end()
    if rev == 0 and prev != bytes(32):
        raise ValueError('initial predecessor')
    preimage = vector(b'MLS 1.0 marmot invite request v1') + vector(b[:-64])
    ed25519.Ed25519PublicKey.from_public_bytes(context[130:162]).verify(sig, preimage)
    return context, rev, prev, bearer, kp, event_id


def refresh(previous, current):
    a, b = request(previous), request(current)
    if b[0] != a[0] or b[1] != a[1]+1 or b[2] != hashlib.sha256(previous).digest() or b[3] != a[3]:
        raise ValueError('continuity')


def polymod(values):
    chk = 1
    gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i, g in enumerate(gen):
            if top >> i & 1:
                chk ^= g
    return chk


def convert(data, a, b, pad):
    acc = bits = 0
    out = []
    for value in data:
        if value >> a:
            raise ValueError('word')
        acc = ((acc << a) | value) & ((1 << (a+b-1))-1)
        bits += a
        while bits >= b:
            bits -= b
            out.append((acc >> bits) & ((1 << b)-1))
    if pad and bits:
        out.append((acc << (b-bits)) & ((1 << b)-1))
    elif not pad and (bits >= a or ((acc << (b-bits)) & ((1 << b)-1))):
        raise ValueError('padding')
    return out


def bech32m(b, checksum=0x2bc830a3, hrp='marmot'):
    data = convert(b, 8, 5, True)
    expanded = [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    check = polymod(expanded + data + [0]*6) ^ checksum
    return hrp + '1' + ''.join(CHARSET[x] for x in data + [(check >> (5*(5-i))) & 31 for i in range(6)])


def decode_code(s):
    if len(s) > 7000 or s != s.lower() and s != s.upper():
        raise ValueError('case or size')
    s = s.lower()
    hrp, sep, payload = s.rpartition('1')
    if hrp != 'marmot' or not sep or len(payload) < 6:
        raise ValueError('prefix')
    try:
        data = [CHARSET.index(x) for x in payload]
    except ValueError:
        raise ValueError('alphabet') from None
    expanded = [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    if polymod(expanded + data) != 0x2bc830a3:
        raise ValueError('checksum')
    b = bytes(convert(data[:-6], 5, 8, False))
    code(b)
    return b


def padded_len(n):
    if n <= 32:
        return 32
    power = 1 << (n-1).bit_length()
    chunk = 32 if power <= 256 else power // 8
    return chunk * ((n-1)//chunk + 1)


def nip44_length(n):
    return 4 * ((1 + 32 + 2 + padded_len(n) + 32 + 2)//3)


class InviteFixtures(unittest.TestCase):
    def test_frozen_encodings(self):
        self.assertEqual(137, len(bytes.fromhex(V['entry_hex'])))
        self.assertEqual([bytes.fromhex(V['entry_hex'])], component(bytes.fromhex(V['component_hex'])))
        self.assertEqual([], component(b'\x00'))
        b = bytes.fromhex(V['code_hex'])
        self.assertEqual(V['code_bech32m'], bech32m(b))
        self.assertEqual(b, decode_code(V['code_bech32m'].upper()))

    def test_noncanonical_component_rejections(self):
        e = bytes.fromhex(V['entry_hex'])
        for b in [b'\x40\x00', b'\x80\x00\x00\x89'+e, vector(e)+b'\0', vector(e*2),
                  vector(e*9), vector(e[:-1]+b'\x02'), vector(e[:32]+b'\xff'*32+e[64:])]:
            with self.subTest(b=b[:8].hex()), self.assertRaises(ValueError):
                component(b)
        a = b'\x01'*32 + e[32:]
        z = b'\xff'*32 + e[32:]
        for b in [vector(z+a), vector(a+z)]:
            with self.assertRaises(ValueError):
                component(b)

    def test_code_rejections(self):
        s = V['code_bech32m']
        b = bytes.fromhex(V['code_hex'])
        for bad in ['M'+s[1:], s[:-1]+('q' if s[-1] != 'q' else 'p'),
                    bech32m(b, checksum=1), bech32m(b, hrp='nostr'),
                    bech32m(b'\0\x02'+b[2:]), 'marmot1'+'q'*7000,
                    bech32m(b+b'\0'), bech32m(b[:130]+b'\x40\x00')]:
            with self.subTest(prefix=bad[:10]), self.assertRaises(ValueError):
                decode_code(bad)
        for words in [[1], [0, 1], [0, 0, 0]]:
            with self.assertRaises(ValueError):
                convert(words, 5, 8, False)

    def test_relay_bounds(self):
        for items in [[b'wss://b.example', b'wss://a.example'], [b'wss://a.example']*2,
                      [b'https://a.example'], [b'wss://'+bytes([97+i])+b'.example' for i in range(9)]]:
            with self.assertRaises(ValueError):
                relay_list(b''.join(vector(x) for x in items))

    def test_request_signature_and_refresh(self):
        r0 = bytes.fromhex(V['request_hex'])
        r1 = bytes.fromhex(V['refresh_hex'])
        refresh(r0, r1)
        self.assertEqual(V['request_hash'], hashlib.sha256(r0).hexdigest())
        self.assertEqual(V['request_sign_content_hex'],
                         (vector(b'MLS 1.0 marmot invite request v1')+vector(r0[:-64])).hex())
        for offset in [34, 66, 98, 130, 169, 173, 210, 242, len(r0)-1]:
            bad = bytearray(r0)
            bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises((ValueError, InvalidSignature)):
                request(bytes(bad))
        with self.assertRaises(ValueError):
            refresh(r1, r0)
        with self.assertRaises(ValueError):
            request(r0+b'\0')

    def test_signed_refresh_cannot_change_identity_or_bearer(self):
        original = bytes.fromhex(V['request_hex'])
        valid = bytes.fromhex(V['refresh_hex'])
        signer = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(V['consent_seed_hex']))
        for offset in [66, 169, 180, 210]:
            bad = bytearray(valid[:-64])
            bad[offset] ^= 1
            changed = bytes(bad)
            signed = changed + signer.sign(vector(b'MLS 1.0 marmot invite request v1')+vector(changed))
            request(signed)  # Cryptographically valid, but wrong continuity.
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                refresh(original, signed)

    def test_withdrawal_domain_and_context(self):
        signed = bytes.fromhex(V['withdrawal_hex'])
        ctx, signature = signed[:-64], signed[-64:]
        key = ed25519.Ed25519PublicKey.from_public_bytes(ctx[130:162])
        key.verify(signature, vector(b'MLS 1.0 marmot invite withdrawal v1')+vector(ctx))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, vector(b'MLS 1.0 marmot invite request v1')+vector(ctx))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, vector(b'MLS 1.0 marmot invite withdrawal v1')+vector(ctx[:-1]+b'\0'))

    def test_preview_crypto_binding(self):
        key = bytes.fromhex(V['preview_key_hex'])
        aad = bytes.fromhex(V['preview_aad_hex'])
        nonce = bytes.fromhex(V['preview_nonce_hex'])
        plain = bytes.fromhex(V['preview_hex'])
        cipher = bytes.fromhex(V['preview_ciphertext_hex'])
        self.assertEqual(cipher, ChaCha20Poly1305(key).encrypt(nonce, plain, aad))
        self.assertEqual(V['preview_hash'], hashlib.sha256(plain).hexdigest())
        for k, a, c in [(bytes(32), aad, cipher), (key, aad[:-1]+b'\xff', cipher),
                        (key, aad, cipher[:-1]+bytes([cipher[-1]^1]))]:
            with self.assertRaises(InvalidTag):
                ChaCha20Poly1305(k).decrypt(nonce, c, a)

    def test_nip44_nested_size_budget(self):
        # Bound complete JSON objects conservatively (event metadata < 1024 bytes).
        admin_record_max = 2+255+8+32+1+4+24576
        rumor_max = 1024 + 4*((admin_record_max+2)//3)
        seal_max = 1024 + nip44_length(rumor_max)
        wrap_max = 1024 + nip44_length(seal_max)
        self.assertLessEqual(rumor_max, 65535)
        self.assertLessEqual(seal_max, 65535)
        self.assertLessEqual(wrap_max, 90000)
        max_request = 170+4+96+2+8192+64
        self.assertLessEqual(max_request+2+12288, 24576)
        max_preview = 2+96+8+1+2+256+2+4096+1+4+49152
        self.assertLessEqual(12+max_preview+16, 54000)
        self.assertLessEqual(7+((130+2+4096)*8+4)//5+6, 7000)

    def test_registry_and_surface_sync(self):
        expected = {'0x800e': 'app-components/group-invite-links-v1.md',
                    '459': 'transports/nostr-invite-links.md', '460': 'transports/nostr-invite-links.md',
                    '461': 'transports/nostr-invite-links.md', '30444': 'transports/nostr-invite-links.md'}
        registry = (ROOT/'foundation/registries.md').read_text()
        layout = (ROOT/'layout.md').read_text()
        for value, path in expected.items():
            self.assertIn('`'+value+'`', registry)
            self.assertIn('`'+value+'`', (ROOT/path).read_text())
            self.assertIn(Path(path).name, layout)
        for path in ['foundation/invite-link-records.md', 'features/group-invite-links.md']:
            self.assertIn(Path(path).name, layout)
            self.assertIn(Path(path).name, (ROOT/Path(path).parent/'README.md').read_text())
        for path in expected.values():
            self.assertIn(Path(path).name, (ROOT/Path(path).parent/'README.md').read_text())
        idea = (ROOT/'ideas/group-invite-links.md').read_text()
        self.assertNotRegex(idea, r'\b(?:MUST|SHOULD|MAY)\b|0x[0-9a-f]+|struct\s*\{')


if __name__ == '__main__':
    unittest.main()
