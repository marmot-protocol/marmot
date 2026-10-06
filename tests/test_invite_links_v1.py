"""Executable examples for the proposed invite profile, not a production client.

These fixtures check canonical bytes, consent binding, preview authentication and
bounds, plus an abstract candidate-parent transition model. They deliberately do
not implement MLS, NIP-59 or state convergence.
"""
import hashlib
import base64
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


def sign_content(operation, content, component_id=0x800e):
    operation_label = vector(b'MLS Component') + component_id.to_bytes(2, 'big') + vector(operation)
    return vector(b'MLS 1.0 ' + operation_label) + vector(content)


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


def request_context(context):
    if len(context) != 170:
        raise ValueError('context length')
    if context[:2] != b'\x00\x01' or not 0 < int.from_bytes(context[-8:], 'big') <= 9007199254740991:
        raise ValueError('context')
    secp_key(context[2:34])
    secp_key(context[98:130])
    return context


def request(b):
    r = Reader(b)
    context = request_context(r.take(170))
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
    preimage = sign_content(b'request', b[:-64])
    ed25519.Ed25519PublicKey.from_public_bytes(context[130:162]).verify(sig, preimage)
    return context, rev, prev, bearer, kp, event_id


def refresh(previous, current):
    a, b = request(previous), request(current)
    if b[0] != a[0] or b[1] != a[1]+1 or b[2] != hashlib.sha256(previous).digest() or b[3] != a[3]:
        raise ValueError('continuity')


def latest_revision(records):
    """Select a signed chain; assumes externally validated package/account evidence."""
    decoded = {record: request(record) for record in records}
    if len({fields[0] for fields in decoded.values()}) != 1:
        raise ValueError('different contexts')
    complete = {record for record, fields in decoded.items() if fields[1] == 0}
    for rev in range(1, 8):
        for record, fields in decoded.items():
            if fields[1] != rev:
                continue
            for ancestor in list(complete):
                if decoded[ancestor][1] != rev-1:
                    continue
                try:
                    refresh(ancestor, record)
                except ValueError:
                    continue
                complete.add(record)
    for rev in range(8):
        if sum(decoded[record][1] == rev for record in complete) > 1:
            raise ValueError('conflicting refresh')
    return max(complete, key=lambda record: decoded[record][1]) if complete else None


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


def parse_status(b):
    r = Reader(b)
    request_context(r.take(170))
    r.take(32)
    outcome = r.num(1)
    hashes = [r.take(32), r.take(32)]
    r.end()
    if outcome not in [0, 1, 2, 3] or any((h == bytes(32)) != (outcome != 2) for h in hashes):
        raise ValueError('status')
    return outcome


def withdrawal(b):
    r = Reader(b)
    context = request_context(r.take(170))
    signature = r.take(64)
    r.end()
    ed25519.Ed25519PublicKey.from_public_bytes(context[130:162]).verify(
        signature, sign_content(b'withdrawal', context))
    return context


def admin_batch(b):
    outer = Reader(b)
    r = Reader(outer.vec(1, 262144))
    outer.end()
    recipients = []
    while r.pos < len(r.b):
        recipient = r.take(32)
        secp_key(recipient)
        r.vec(1, 90000)  # Opaque transport bytes; no NIP-59 verification here.
        recipients.append(recipient)
    if not 1 <= len(recipients) <= 16 or recipients != sorted(set(recipients)):
        raise ValueError('recipient count or order')
    return recipients


def preview(b):
    r = Reader(b)
    if r.num(2) != 1:
        raise ValueError('preview version')
    inbox, link_id, bearer_hash = r.take(32), r.take(32), r.take(32)
    secp_key(inbox)
    expires_at, mode = r.num(8), r.num(1)
    if expires_at > 9007199254740991 or mode > 1:
        raise ValueError('preview policy')
    name, description = r.vec(1, 256), r.vec(0, 4096)
    name.decode('utf-8')
    description.decode('utf-8')
    image_type, image = r.num(1), r.vec(0, 49152)
    r.end()
    if image_type not in [0, 1, 2] or bool(image) != (image_type != 0):
        raise ValueError('image type/length')
    # The image field remains opaque here. Rendering needs a real bounded decoder.
    return inbox, link_id, bearer_hash, expires_at, mode, name, description, image_type, image


def canonical_base64(value, decoded_max):
    if len(value) > 4*((decoded_max+2)//3):
        raise ValueError('encoded size')
    decoded = base64.b64decode(value, validate=True)
    if len(decoded) > decoded_max or base64.b64encode(decoded) != value:
        raise ValueError('noncanonical base64')
    return decoded


def request_delivery(b):
    r = Reader(b)
    operation = r.num(1)
    record = r.vec(1, 16384)
    publication = r.vec(0, 12288)
    r.end()
    if operation == 0:
        request(record)
        if not publication:
            raise ValueError('missing package evidence')
    elif operation == 1:
        withdrawal(record)
        if publication:
            raise ValueError('withdrawal evidence')
    else:
        raise ValueError('operation')
    # Publication bytes are opaque; their NIP-01 authentication is an integration gate.
    return operation, record, publication


def transition(parent, result, actor, parent_admins, result_admins, *,
               removed_leaf_accounts=(), self_remove_accounts=(),
               required=True, supported=True, disband=False):
    """Abstract policy model; caller supplies already MLS-authenticated facts.

    None means absent component. Leaves resolve to account identities in the
    authenticated candidate parent. Adopted core admin-policy updates, Remove
    authorization and last-leaf coupling must already pass; this model checks
    invite-component policy only and does not authenticate MLS inputs.
    """
    old = component(parent) if parent is not None else []
    new = component(result) if result is not None else []
    if parent is not None and result is None:
        raise ValueError('component removal')
    if result is not None and (not required or not supported):
        raise ValueError('capability')
    if disband:
        if (parent != result or self_remove_accounts or actor not in parent_admins
                or set(result_admins) != {actor}):
            raise ValueError('restricted disband shape')
        return
    if not result_admins:
        raise ValueError('last admin needs successor')
    demoted = set(parent_admins) - set(result_admins)
    removed_admin = set(removed_leaf_accounts) & set(parent_admins)
    if self_remove_accounts:
        if set(self_remove_accounts) & set(parent_admins):
            raise ValueError('admin SelfRemove')
        if parent != result or removed_leaf_accounts or demoted:
            raise ValueError('SelfRemove-only shape')
    if (parent != result or demoted or removed_admin) and actor not in parent_admins:
        raise ValueError('parent authorization')
    retained = {row[:32]: row for row in old}
    if any(row[:32] in retained and row != retained[row[:32]] for row in new):
        raise ValueError('immutable generation')
    if result is not None and (demoted or removed_admin):
        if {row[:32] for row in old} & {row[:32] for row in new}:
            raise ValueError('retired id retained')
        if {row[32:64] for row in old} & {row[32:64] for row in new}:
            raise ValueError('retired inbox retained')
        if actor in demoted and new:
            raise ValueError('departing committer knows replacement keys')


def parse_admin(b):
    r = Reader(b)
    r.vec(1, 255)
    r.take(8)
    link_id = r.take(32)
    action = r.num(1)
    body = Reader(r.vec(1, 24576))
    r.end()
    if action == 0:
        entry = body.take(137)
        component(vector(entry))
        scalar = int.from_bytes(body.take(32), 'big')
        pub = ec.derive_private_key(scalar, ec.SECP256K1()).public_key().public_numbers().x.to_bytes(32, 'big')
        fields, relays = code(body.vec(1, 8192))
        if (entry[:32] != link_id or entry[32:64] != pub
                or fields[:2] != [entry[32:64], link_id]
                or hashlib.sha256(fields[2]).digest() != entry[64:96]):
            raise ValueError('grant binding')
    elif action == 1:
        # Locate the signature after the request's last vector; preserve those exact bytes.
        start = Reader(body.b)
        start.take(270)
        start.vec(1, 8192)
        start.take(64)
        original = body.take(start.pos)
        ctx = request(original)[0]
        if ctx[34:66] != link_id:
            raise ValueError('forward binding')
        json.loads(body.vec(1, 12288))  # Illustrative evidence, not NIP-01 verification.
    elif action == 2:
        ctx = withdrawal(body.take(234))
        if ctx[34:66] != link_id:
            raise ValueError('withdrawal binding')
    elif action in [3, 4]:
        status = body.take(267)
        if parse_status(status) != action - 2 or status[34:66] != link_id:
            raise ValueError('decision binding')
    else:
        raise ValueError('unsupported example action')
    body.end()
    return action


class InviteFixtures(unittest.TestCase):
    def test_frozen_encodings(self):
        self.assertEqual(137, len(bytes.fromhex(V['entry_hex'])))
        self.assertEqual([bytes.fromhex(V['entry_hex'])], component(bytes.fromhex(V['component_hex'])))
        self.assertEqual([], component(b'\x00'))
        b = bytes.fromhex(V['code_hex'])
        self.assertEqual(V['code_bech32m'], bech32m(b))
        self.assertEqual(b, decode_code(V['code_bech32m'].upper()))

    def test_fixture_cross_bindings(self):
        fields, _ = code(bytes.fromhex(V['code_hex']))
        e = bytes.fromhex(V['entry_hex'])
        p = Reader(bytes.fromhex(V['preview_hex']))
        self.assertEqual(1, p.num(2))
        self.assertEqual(e[32:64], p.take(32))
        self.assertEqual(fields[1], p.take(32))
        self.assertEqual(e[64:96], p.take(32))
        self.assertEqual(e[128:136], p.take(8))
        self.assertEqual(e[136], p.num(1))
        self.assertEqual(b'Book club', p.vec(1, 256))
        self.assertEqual(b"Thursday nights. Bring whatever you're reading.", p.vec(0, 4096))
        self.assertEqual(0, p.num(1))
        self.assertEqual(b'', p.vec(0, 49152))
        p.end()
        self.assertEqual(fields[0], e[32:64])
        self.assertEqual(fields[1], e[:32])
        self.assertEqual(hashlib.sha256(fields[2]).digest(), e[64:96])
        self.assertEqual(V['preview_hash'], e[96:128].hex())
        self.assertEqual(b'\0\1'+fields[0]+fields[1], bytes.fromhex(V['preview_aad_hex']))
        ctx, _, _, bearer, _, _ = request(bytes.fromhex(V['request_hex']))
        self.assertEqual(fields[:2], [ctx[2:34], ctx[34:66]])
        self.assertEqual(fields[2], bearer)

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
                         sign_content(b'request', r0[:-64]).hex())
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
            signed = changed + signer.sign(sign_content(b'request', changed))
            request(signed)  # Cryptographically valid, but wrong continuity.
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                refresh(original, signed)

    def test_withdrawal_domain_and_context(self):
        signed = bytes.fromhex(V['withdrawal_hex'])
        ctx, signature = signed[:-64], signed[-64:]
        key = ed25519.Ed25519PublicKey.from_public_bytes(ctx[130:162])
        key.verify(signature, sign_content(b'withdrawal', ctx))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, sign_content(b'request', ctx))
        with self.assertRaises(InvalidSignature):
            key.verify(signature, sign_content(b'withdrawal', ctx[:-1]+b'\0'))

    def test_component_signature_domain_and_revision_limit(self):
        r = bytes.fromhex(V['request_hex'])
        key = ed25519.Ed25519PublicKey.from_public_bytes(r[130:162])
        with self.assertRaises(InvalidSignature):
            key.verify(r[-64:], sign_content(b'request', r[:-64], component_id=0x800d))
        signer = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(V['consent_seed_hex']))
        tbs = r[:170]+(8).to_bytes(4, 'big')+r[174:-64]
        signed = tbs+signer.sign(sign_content(b'request', tbs))
        with self.assertRaises(ValueError):
            request(signed)

    def test_status_and_admin_records(self):
        status = bytes.fromhex(V['status_hex'])
        self.assertEqual(2, parse_status(status))
        self.assertEqual(3, parse_status(bytes.fromhex(V['retired_status_hex'])))
        for outcome in [0, 1]:
            self.assertEqual(outcome, parse_status(status[:202]+bytes([outcome])+bytes(64)))
        for bad in [status+b'\0', status[:202]+b'\x04'+status[203:],
                    status[:203]+bytes(32)+status[235:], status[:202]+b'\0'+status[203:]]:
            with self.assertRaises(ValueError):
                parse_status(bad)
        grant = bytes.fromhex(V['grant_record_hex'])
        self.assertEqual(0, parse_admin(grant))
        forwarded = bytes.fromhex(V['forward_record_hex'])
        self.assertEqual(1, parse_admin(forwarded))
        for bad in [grant+b'\0', grant[:-1]]:
            with self.assertRaises(ValueError):
                parse_admin(bad)

    def test_grant_carries_complete_code_and_rejects_substitution(self):
        entry = bytes.fromhex(V['entry_hex'])
        complete_code = bytes.fromhex(V['code_hex'])
        prefix = vector(b'synthetic-group')+(7).to_bytes(8, 'big')+entry[:32]+b'\0'
        def grant(code_bytes, scalar=1):
            return prefix+vector(entry+scalar.to_bytes(32, 'big')+vector(code_bytes))
        self.assertEqual(0, parse_admin(grant(complete_code)))
        self.assertEqual([b'wss://relay.example'], code(complete_code)[1])
        for offset in [34, 66]:
            changed = bytearray(complete_code)
            changed[offset] ^= 1
            with self.assertRaises(ValueError):
                parse_admin(grant(bytes(changed)))
        with self.assertRaises(ValueError):
            parse_admin(grant(complete_code, scalar=2))
        with self.assertRaises(ValueError):
            parse_admin(grant(complete_code[:130]+vector(b'')))

    def test_request_delivery_keeps_ancestor_evidence(self):
        evidence = b'{"example":"public synthetic publication placeholder"}'
        for name in ['request_hex', 'refresh_hex']:
            record = bytes.fromhex(V[name])
            delivered = b'\0'+vector(record)+vector(evidence)
            self.assertEqual((0, record, evidence), request_delivery(delivered))
        withdrawn = bytes.fromhex(V['withdrawal_hex'])
        valid = b'\1'+vector(withdrawn)+vector(b'')
        self.assertEqual((1, withdrawn, b''), request_delivery(valid))
        for invalid in [b'\0'+vector(record)+vector(b''),
                        b'\0'+vector(record)+vector(bytes(12289)),
                        b'\1'+vector(withdrawn)+vector(evidence),
                        b'\2'+vector(withdrawn)+vector(b''), valid+b'\0']:
            with self.assertRaises(ValueError):
                request_delivery(invalid)

    def test_highest_complete_revision_and_conflicts(self):
        r0, r1 = [bytes.fromhex(V[name]) for name in ['request_hex', 'refresh_hex']]
        self.assertEqual(r1, latest_revision([r1, r0, r1]))
        self.assertEqual(r1, latest_revision([r0, r1]))
        self.assertIsNone(latest_revision([r1]))
        signer = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(V['consent_seed_hex']))
        # A cryptographically valid second child of revision zero is ambiguous consent.
        changed = bytearray(r1[:-64])
        changed[242] ^= 1
        branch = bytes(changed)+signer.sign(sign_content(b'request', bytes(changed)))
        with self.assertRaises(ValueError):
            latest_revision([r0, r1, branch])
        # A revision two with missing revision one cannot supersede revision zero.
        tbs = r1[:170]+(2).to_bytes(4, 'big')+hashlib.sha256(r1).digest()+r1[206:-64]
        r2 = tbs+signer.sign(sign_content(b'request', tbs))
        self.assertEqual(r0, latest_revision([r2, r0]))
        self.assertEqual(r2, latest_revision([r2, r0, r1]))

    def test_status_context_rejections(self):
        valid = bytes.fromhex(V['status_hex'])
        for offset, replacement in [(0, b'\x00\x02'), (2, b'\xff'*32),
                                    (98, b'\xff'*32), (162, bytes(8)),
                                    (162, (9007199254740992).to_bytes(8, 'big'))]:
            invalid = valid[:offset] + replacement + valid[offset+len(replacement):]
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                parse_status(invalid)

    def test_withdrawal_decoder_and_original_binding(self):
        signed = bytes.fromhex(V['withdrawal_hex'])
        self.assertEqual(request(bytes.fromhex(V['request_hex']))[0], withdrawal(signed))
        for invalid in [signed[:-1], signed+b'\0', signed[:66]+b'\xff'+signed[67:]]:
            with self.assertRaises((ValueError, InvalidSignature)):
                withdrawal(invalid)
        # Even a correctly signed withdrawal for another context must not close this one.
        signer = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(V['consent_seed_hex']))
        different = signed[:66]+b'\xff'+signed[67:170]
        other = different + signer.sign(sign_content(b'withdrawal', different))
        self.assertNotEqual(withdrawal(signed), withdrawal(other))

    def test_all_admin_actions_and_body_bindings(self):
        ctx = bytes.fromhex(V['request_hex'])[:170]
        invited = bytes.fromhex(V['status_hex'])
        declined = invited[:202]+b'\x01'+bytes(64)
        prefix = vector(b'synthetic-group')+(7).to_bytes(8, 'big')+ctx[34:66]
        examples = {2: bytes.fromhex(V['withdrawal_hex']), 3: declined, 4: invited}
        for action, body in examples.items():
            valid = prefix+bytes([action])+vector(body)
            with self.subTest(action=action):
                self.assertEqual(action, parse_admin(valid))
                for invalid in [valid+b'\0', prefix+bytes([action])+vector(body+b'\0'),
                                prefix[:-32]+b'\xff'*32+bytes([action])+vector(body)]:
                    with self.assertRaises(ValueError):
                        parse_admin(invalid)
        for action, body in [(3, invited), (4, declined), (5, invited)]:
            with self.assertRaises(ValueError):
                parse_admin(prefix+bytes([action])+vector(body))

    def test_admin_batch_count_order_and_size(self):
        recipients = sorted(ec.derive_private_key(i, ec.SECP256K1()).public_key().public_numbers().x.to_bytes(32, 'big')
                            for i in range(1, 18))
        # Placeholder envelope bytes exercise only the canonical outer batch structure.
        envelope = b'{}'
        rows = [key+vector(envelope) for key in recipients]
        self.assertEqual(recipients[:16], admin_batch(vector(b''.join(rows[:16]))))
        # Kind 461 has different schemas selected by its authenticated container.
        # These examples must not be accepted by the opposite structural decoder.
        with self.assertRaises(ValueError):
            admin_batch(bytes.fromhex(V['grant_record_hex']))
        with self.assertRaises(ValueError):
            parse_admin(vector(rows[0]))
        for invalid in [vector(b''), vector(b''.join(rows)), vector(rows[0]*2),
                        vector(rows[1]+rows[0]), vector(rows[0])+b'\0',
                        vector(recipients[0]+vector(b'')),
                        vector(recipients[0]+vector(bytes(90001))),
                        vector(b''.join(k+vector(bytes(90000)) for k in recipients[:3])),
                        b'\x40\x23'+rows[0]]:
            with self.assertRaises(ValueError):
                admin_batch(invalid)

    def test_preview_structure_and_image_discriminants(self):
        valid = bytes.fromhex(V['preview_hex'])
        self.assertEqual(0, preview(valid)[7])
        for image_type in [1, 2]:
            # Nonempty bytes check the field contract, not actual image decoding.
            self.assertEqual(image_type, preview(valid[:-2]+bytes([image_type])+vector(b'image'))[7])
        invalids = [valid+b'\0', b'\0\2'+valid[2:], valid[:-2]+b'\3\0',
                    valid[:-2]+b'\1\0', valid[:-2]+b'\0'+vector(b'image'),
                    valid[:-2]+b'\2'+vector(bytes(49153)),
                    valid[:107]+vector(b'\xff')+vector(b'')+b'\0\0']
        for invalid in invalids:
            with self.assertRaises(ValueError):
                preview(invalid)

    def test_canonical_base64_and_predecode_bound(self):
        self.assertEqual(b'\x00', canonical_base64(b'AA==', 1))
        for invalid in [b'AB==', b'AA', b'AA===', b'AA==\n', b'AA-_', b'AAA=']:
            with self.assertRaises(ValueError):
                canonical_base64(invalid, 1)

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
        request_delivery_max = 1+4+16384+2+12288
        request_rumor_max = 1024+4*((request_delivery_max+2)//3)
        request_seal_max = 1024+nip44_length(request_rumor_max)
        self.assertLessEqual(request_rumor_max, 65535)
        self.assertLessEqual(request_seal_max, 65535)
        self.assertLessEqual(1024+nip44_length(request_seal_max), 90000)
        max_code = 130+2+4096
        self.assertLessEqual(137+32+2+max_code, 24576)
        max_preview = 2+96+8+1+2+256+2+4096+1+4+49152
        self.assertLessEqual(12+max_preview+16, 54000)
        self.assertLessEqual(7+((130+2+4096)*8+4)//5+6, 7000)

    def test_safe_sign_literal_framing(self):
        # Source-checked literal for draft-10 sections 4.1/4.3 and RFC SignContent;
        # not another generator call, nor an independently produced MLS vector.
        tbs = bytes.fromhex(V['request_hex'])[:-64]
        label = b'\x0dMLS Component\x80\x0e\x07request'
        expected = b'\x20MLS 1.0 ' + label + qlen(len(tbs)) + tbs
        self.assertEqual(expected.hex(), V['request_sign_content_hex'])

    def test_transition_activation_and_immutable_generation(self):
        p = bytes.fromhex(V['component_hex'])
        transition(None, p, 'alice', {'alice'}, {'alice'})
        transition(p, p, 'bob', {'alice'}, {'alice'})
        transition(p, b'\0', 'alice', {'alice'}, {'alice'})
        for kwargs in [{'required': False}, {'supported': False}]:
            with self.assertRaises(ValueError):
                transition(None, p, 'alice', {'alice'}, {'alice'}, **kwargs)
        for result in [None, vector(bytes.fromhex(V['entry_hex'])[:-1]+b'\1')]:
            with self.assertRaises(ValueError):
                transition(p, result, 'alice', {'alice'}, {'alice'})
        with self.assertRaises(ValueError):
            transition(p, b'\0', 'bob', {'alice'}, {'alice', 'bob'})

    def test_transition_departure_and_rotation(self):
        p = bytes.fromhex(V['component_hex'])
        entry = bytes.fromhex(V['entry_hex'])
        fresh_key = ec.derive_private_key(3, ec.SECP256K1()).public_key().public_numbers().x.to_bytes(32, 'big')
        fresh = vector(b'\x99'*32 + fresh_key + entry[64:])
        # Self-demotion disables links, then a staying admin can create new ones.
        transition(p, b'\0', 'alice', {'alice', 'bob'}, {'bob'})
        with self.assertRaises(ValueError):
            transition(p, fresh, 'alice', {'alice', 'bob'}, {'bob'})
        transition(b'\0', fresh, 'bob', {'bob'}, {'bob'})
        # Another admin can demote Alice and create replacement generations.
        transition(p, fresh, 'bob', {'alice', 'bob'}, {'bob'})
        # Removing one admin leaf retires links even if its account stays admin.
        transition(p, fresh, 'bob', {'alice', 'bob'}, {'alice', 'bob'}, removed_leaf_accounts=['alice'])
        for result in [p, vector(b'\x99'*32+entry[32:])]:
            with self.assertRaises(ValueError):
                transition(p, result, 'bob', {'alice', 'bob'}, {'alice', 'bob'}, removed_leaf_accounts=['alice'])
        # Promotion alone preserves a generation.
        transition(p, p, 'alice', {'alice'}, {'alice', 'bob'})

    def test_transition_self_remove_and_terminal_exception(self):
        p = bytes.fromhex(V['component_hex'])
        transition(p, p, 'charlie', {'bob'}, {'bob'}, self_remove_accounts=['alice'])
        with self.assertRaises(ValueError):
            transition(p, p, 'bob', {'alice', 'bob'}, {'bob'}, self_remove_accounts=['alice'])
        with self.assertRaises(ValueError):
            transition(p, b'\0', 'bob', {'bob'}, {'bob'}, self_remove_accounts=['alice'])
        with self.assertRaises(ValueError):
            transition(p, b'\0', 'alice', {'alice'}, set())
        # Adopted disband does not append an unrelated component update.
        transition(p, p, 'alice', {'alice'}, {'alice'}, disband=True)
        with self.assertRaises(ValueError):
            transition(p, b'\0', 'alice', {'alice'}, {'alice'}, disband=True)

        for actor, admins in [('bob', {'bob'}), ('alice', set()), ('alice', {'alice', 'bob'})]:
            with self.assertRaises(ValueError):
                transition(p, p, actor, {'alice'}, admins, disband=True)

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
