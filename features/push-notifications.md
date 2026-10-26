# Push notifications

Status: adopted.

Push notifications let a sender give a recipient a delivery hint outside the normal group-message fetch path.

Push notification support is optional. A group MUST still work when no client supports push notifications.

## Surfaces

- App payload: token gossip event kinds `447`, `448`, and `449`, carried inside ordinary encrypted group messages (see
  "Token gossip event shapes") and sent at the times "Token distribution" defines.
- Owner authentication: local-only Nostr signing event kind `451`, whose signature is carried as `owner_sig` inside a
  token or removal entry (see "Owner authentication"). The signing event is never published.
- Transport: Nostr push notification rumor kind `446` for the current Nostr binding. Unlike the kinds above, `446` is
  not an inner group payload: it is the rumor inside a separately gift-wrapped trigger addressed to the notification
  server's inbox. The Nostr binding owns that outer envelope and its publish targets.
- Group state: no group-state transition.

No persistent group app component is required for push notifications v1.

## Behavior

A push notification hint MAY tell a recipient that new encrypted group content is available. It MUST NOT carry message
plaintext, media plaintext, MLS secrets, exporter output, or group-state-changing bytes.

Receiving or missing a push notification does not affect group state. The recipient still fetches and processes the
normal Marmot transport messages.

## Notification servers

A notification server is identified by its Nostr public key. That key and an optional relay hint travel inside token
gossip records (see "Token gossip event shapes"); they are per-token data, not group state.

A notification server is an ordinary Nostr account. Its inbox relays are the Nostr binding's account inbox relays
([../transports/nostr.md](../transports/nostr.md)); this feature does not define a server-specific relay-list event
kind.

Each application provides its own notification server's public key, for example as a build-time default. This is
structural, not provisional: Apple and Google require application-level credentials to trigger native push, so a
notification server can only wake the application whose platform push credentials it holds. A server's public key is
therefore tied to the application it serves, and this feature defines no protocol-level server discovery.

## Token encryption

When a device enables native push, it encrypts its platform token to the notification server's Nostr public key.

The encrypted token format is:

```text
TokenPlaintext = platform[1] || token_length[2] || device_token[token_length] || random_padding
EncryptedToken = ephemeral_pubkey[32] || nonce[12] || ciphertext[1040]
```

`TokenPlaintext` is exactly 1024 bytes. `EncryptedToken` is exactly 1084 bytes.

- `platform` is one byte: `0x01` for APNs or `0x02` for FCM. No other value is valid.
- `token_length` is a 2-byte big-endian unsigned integer: the length of `device_token` in bytes, between 1 and 1021
  inclusive.
- `device_token` is the raw platform token bytes.
- `random_padding` is random bytes filling `TokenPlaintext` to exactly 1024 bytes.

The encryption key is derived with secp256k1 ECDH and HKDF-SHA256:

```text
shared_x       = secp256k1_ecdh(ephemeral_privkey, server_pubkey)
prk            = HKDF-SHA256-Extract(salt = "marmot-push-token-v1", IKM = shared_x)
encryption_key = HKDF-SHA256-Expand(prk, info = "marmot-push-token-encryption", 32)
```

The HKDF hash is SHA-256 in both steps. `shared_x` is input keying material passed through Extract with the 20-byte
ASCII salt `marmot-push-token-v1`; it is not used as a precomputed PRK. The Expand info is the 28-byte ASCII string
`marmot-push-token-encryption` with no length prefix, and the output is a 32-byte key.

`server_pubkey` is a 32-byte x-only secp256k1 key. ECDH lifts it to the curve point with even Y, following the BIP-340
convention. `shared_x` is the 32-byte big-endian X coordinate of the resulting shared point, with no Y parity byte and
no hashing before HKDF. `ephemeral_privkey` is a fresh secp256k1 scalar; its x-only public key is the
`ephemeral_pubkey[32]` carried in `EncryptedToken`.

Both encryption and decryption MUST reject an invalid x-only public key, an invalid local scalar, any ECDH failure, or
an all-zero `shared_x`. A failed or all-zero result MUST NOT be passed to HKDF.

The token is encrypted with ChaCha20-Poly1305, a random 12-byte nonce, and empty AAD. `ciphertext[1040]` is the combined
AEAD output: the 1024-byte ciphertext of `TokenPlaintext` followed by the 16-byte Poly1305 authentication tag as a
suffix (1024 + 16 = 1040). A recipient splits off the trailing 16 bytes as the tag and authenticates before decrypting.

Native platform tokens are required; iOS clients use APNs directly and MUST NOT use FCM as an iOS proxy.

## Token gossip event shapes

Token distribution uses Marmot app events carried inside ordinary group messages:

- kind `447`: token request, self-token update, and announce;
- kind `448`: token list;
- kind `449`: token removal.

These are unsigned Marmot app payloads like all inner app events; the envelope shape is owned by
[../foundation/application-messages.md](../foundation/application-messages.md). This section defines their `content`.

The `content` of each kind is a JSON object carrying a version member `v` that MUST be the string `marmot-push-v1`. A
recipient MUST reject a payload with any other `v` value, and ignores unknown members. Senders also tag each gossip
event with `["v", "marmot-push-v1"]`; the content member is the validated value.

### Token entries (kinds 447 and 448)

Kinds `447` and `448` share one content shape:

```json
{
  "v": "marmot-push-v1",
  "tokens": [
    {
      "member_id_hex": "<64 lowercase hex characters>",
      "leaf_index": 3,
      "platform": "apns",
      "token_fingerprint": "sha256:<24 hex characters>",
      "server_pubkey_hex": "<64 lowercase hex characters>",
      "relay_hint": "wss://relay.example.com",
      "encrypted_token": "<standard base64 of one 1084-byte EncryptedToken>",
      "owner_ts": 1735680000000,
      "owner_sig": "<128 lowercase hex characters>"
    }
  ]
}
```

- `tokens` MUST be an array of at most 32 token entries. A missing `tokens` member is read as an empty array. A present
  non-array `tokens` member is advisory-invalid and contributes no entries. A sender with more records splits them
  across multiple app events (see "Event size"). If the decoded array contains more than 32 entries, the recipient
  treats the entire array as advisory-invalid before performing any entry signature verification; the carrying group
  message remains valid.
- `member_id_hex` is the owning member's account public key as 32-byte lowercase hex.
- `leaf_index` is the owning device's MLS leaf index as an unsigned-integer JSON number.
- `platform` is the string `apns` or `fcm`.
- `token_fingerprint` is the string `sha256:` followed by the first 24 lowercase hex characters of
  `SHA-256(platform_byte || device_token)`, where `platform_byte` is the one-byte platform value from "Token
  encryption". It names a token in gossip and removals without revealing token bytes.
- `server_pubkey_hex` is the notification server's Nostr public key as 32-byte lowercase hex.
- `relay_hint` is an optional relay URL where the server accepts notification triggers. It is omitted when not set,
  and a recipient treats an empty or whitespace-only value as absent.
- `encrypted_token` is one 1084-byte `EncryptedToken` as standard base64 with padding.
- `owner_ts` is the owning member's claimed Unix time in milliseconds as an unsigned-integer JSON number. It is the
  owner-signed ordering stamp for this record (see "Owner authentication" and "Record key and ordering primitive"); a
  recipient MUST NOT substitute the carrying event's `created_at` for it. At entry validation, `owner_ts` MUST NOT be
  more than `3,600,000` milliseconds (one hour) ahead of the recipient's local wall clock.
- `owner_sig` is the owner's BIP-340 Schnorr signature over the local-only owner-proof event id, as 64-byte (128
  lowercase hex character) signature bytes (see "Owner authentication"). It binds every other field to
  `member_id_hex`, so the record stays verifiable no matter which member relays it.

A recipient MUST reject an entry whose `member_id_hex` or `server_pubkey_hex` is not 32-byte lowercase hex, whose
`token_fingerprint` is not `sha256:` followed by exactly 24 hex characters, whose `platform` is unknown, whose
`encrypted_token` does not decode to exactly 1084 bytes, whose `owner_sig` is not 64-byte lowercase hex, or whose
`owner_sig` does not verify under "Owner authentication". It MUST also reject an entry whose `owner_ts` exceeds the
one-hour future bound above. This local-time check can temporarily differ across clients, but token records are advisory
local push state and never affect group-message or Commit validity; the finite bound prevents a far-future signed stamp
from becoming a permanent high-water mark.

### Owner authentication

Each token entry and each removal entry is self-authenticated by the member that owns it, independent of the member
that carries it. This lets one member relay another member's records and removals (see "List response" and "Token
distribution") so a group converges on the full token set without requiring every owner to be online, while preventing
a relaying member from forging, repointing, or rolling back another member's routing.

#### Canonical record bytes

Each entry has the following canonical byte string:

```text
SignedRecord = domain_tag
            || group_id_len[2]            big-endian u16
            || group_id[group_id_len]     the carrying group's MLS group id
            || member_id[32]
            || leaf_index[4]              big-endian u32
            || platform_byte[1]
            || server_pubkey[32]
            || token_fingerprint[12]      the 12 bytes the sha256: prefix encodes
            || owner_ts[8]                big-endian u64, milliseconds
            || relay_hint_len[2]          big-endian u16, 0 when absent or for a removal
            || relay_hint[relay_hint_len] UTF-8 bytes of the relay hint, empty when absent
            || encrypted_token[1084]      removal entries omit this field
```

`SignedRecord` deliberately uses this feature-specific fixed-width v1 encoding rather than the Marmot binary profile's
QUIC variable-length integers. Every integer is unsigned big-endian at the exact width shown, the two variable fields
use the shown `u16` byte lengths, and the fields are concatenated without alignment or padding. Signers and verifiers
MUST NOT substitute QUIC varints, TLS vectors, or a serialization-library default. A future incompatible encoding needs
a new push content version and domain tag; it cannot reinterpret the `marmot-push-v1` ordering digest or legacy
signature preimage.

`domain_tag` is the 27-byte ASCII string `marmot-push-token-record-v1` for token entries (kinds `447`/`448`) and the
28-byte ASCII string `marmot-push-token-removal-v1` for removal entries (kind `449`). A removal encodes
`relay_hint_len` as zero, includes no `relay_hint` bytes, and omits the trailing `encrypted_token`. `group_id` is the raw
MLS group id of the carrying group and is length-prefixed because the MLS group id is variable-length. `member_id` and
`server_pubkey` are the raw 32-byte values the corresponding hex fields encode (both are Nostr x-only public keys).

`SHA-256(SignedRecord)` is the record digest used only as the deterministic ordering tie-breaker in current groups. It
is not the current `owner_sig` signature preimage.

#### Current owner-proof signing event

The current proof is a BIP-340 signature over the id of an exact, unpublished Nostr event. It is a feature-specific
signature carrier and does not use the 104-byte `MarmotAuthorizationProof` envelope from
[../foundation/authorization-proofs.md](../foundation/authorization-proofs.md).

For a token entry, construct:

```text
pubkey     = member_id_hex
created_at = 0
kind       = 451
tags       = [
  ["d", "marmot-push-token-record-v1"],
  ["group_id", group_id_hex],
  ["member_id", member_id_hex],
  ["leaf_index", leaf_index_decimal],
  ["platform", platform],
  ["server_pubkey", server_pubkey_hex],
  ["token_fingerprint", token_fingerprint],
  ["owner_ts", owner_ts_decimal],
  ["relay_hint", relay_hint_or_empty],
  ["encrypted_token_encoding", "base64"]
]
content    = encrypted_token_base64
```

For a removal entry, construct:

```text
pubkey     = member_id_hex
created_at = 0
kind       = 451
tags       = [
  ["d", "marmot-push-token-removal-v1"],
  ["group_id", group_id_hex],
  ["member_id", member_id_hex],
  ["leaf_index", leaf_index_decimal],
  ["platform", platform],
  ["server_pubkey", server_pubkey_hex],
  ["token_fingerprint", token_fingerprint],
  ["owner_ts", owner_ts_decimal],
  ["relay_hint", ""]
]
content    = ""
```

The event values are:

- `group_id_hex`: the raw MLS group id of the carrying group as lowercase hexadecimal with no prefix;
- `member_id_hex`: the entry's member id, which MUST also equal the event `pubkey`;
- `leaf_index_decimal`: the entry's unsigned `leaf_index` as canonical decimal ASCII, with no leading zero except that
  zero itself is `"0"`;
- `platform`: the entry's exact `apns` or `fcm` string;
- `server_pubkey_hex`: the entry's server public key as lowercase hexadecimal with no prefix;
- `token_fingerprint`: the entry's complete `sha256:`-prefixed lowercase fingerprint string;
- `owner_ts_decimal`: the entry's unsigned millisecond timestamp as canonical decimal ASCII, with no leading zero except
  that zero itself is `"0"`;
- `relay_hint_or_empty`: the entry's exact non-empty `relay_hint` string, with no Unicode normalization or whitespace
  trimming, or the empty string when the member is absent or whitespace-only; and
- `encrypted_token_base64`: standard base64 with padding of the exact 1084-byte `EncryptedToken`.

The tags MUST appear exactly once and in the order shown. The event has no other tags. Its id is the SHA-256 digest of
the NIP-01 canonical serialization

```text
[0, member_id_hex, 0, 451, tags, content]
```

using the Nostr-shaped-value rules in
[../foundation/canonical-encoding.md](../foundation/canonical-encoding.md). The event is only a signing template and
MUST NOT be published to relays.

##### Removal signing test vector

This fixture uses BIP-340 secret key `3` and all-zero 32-byte auxiliary randomness. The secret is test material only.
The NIP-01 canonical event serialization is:

```json
[0,"f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9",0,451,[["d","marmot-push-token-removal-v1"],["group_id","000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"],["member_id","f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9"],["leaf_index","3"],["platform","apns"],["server_pubkey","2f8bde4d1a07209355b4a7250a5c5128e88b84bddc619ab7cba8d569b240efe4"],["token_fingerprint","sha256:000102030405060708090a0b"],["owner_ts","1700000000000"],["relay_hint",""]],""]
```

The event id and resulting `owner_sig` are:

```text
event_id  = be12f4d029d3cac4034251949d6c013ff18eae00870e199012c7a97e8960b7a2
owner_sig = 04c3588a6533399aeaebb6c596fab896186dd0af1f9724f2926d984d2876490c76e1d149127e0fa697d7f19a0807aa373e942f0eb33edc63071567f274ce3bec
```

A producer MUST validate a signed event returned by an external signer before copying its signature into `owner_sig`.
The returned `pubkey`, `created_at`, `kind`, `tags`, and `content` MUST exactly equal the requested values, its event id
MUST equal the locally recomputed id, and its BIP-340 signature MUST verify for that id and public key.

A recipient reconstructs the exact event from the entry and carrying group's MLS group id, then verifies `owner_sig`
against the event id under `member_id_hex`. An entry whose signature does not verify is dropped as advisory-invalid and
never mutates the stored push-token records. Because the event binds `group_id`, `server_pubkey_hex`, `relay_hint`,
`encrypted_token`, and `owner_ts`, a relaying member cannot move the record to another group, repoint it at a different
notification server or relay, swap the token, or restamp it.

The carrying event stays an ordinary unsigned Marmot app payload and MUST NOT carry a `sig` member (see "Validation").
The local-only proof event itself is not carried; only its 64-byte signature is carried as `owner_sig` inside the
record.

#### Current and legacy group verification

A current-profile group is a group whose GroupContext requires component id `0x8009` under
[`marmot.member.account-identity-proof.v2`](../app-components/account-identity-proof-v2.md). Every member leaf in a
valid current-profile group also contains a valid `0x8009` component. In such a group, a producer MUST create the kind
`451` owner proof above, and a recipient MUST accept only that proof form. A raw
`SHA-256(SignedRecord)` signature or a push owner proof reconstructed with kind `450` is advisory-invalid in a
current-profile group.

A legacy group is an existing group outside that current profile. To let legacy and upgraded members remain in the
same group, an upgraded producer in a legacy group MUST still create the kind `451` proof, while an upgraded recipient
MUST accept any of these forms:

1. the current kind `451` owner proof above;
2. the transitional event-shaped proof deployed before kind `451` was allocated, reconstructed from the exact same
   tags and content above but with kind `450` and NIP-01 serialization
   `[0, member_id_hex, 0, 450, tags, content]`; or
3. the raw legacy proof: a BIP-340 signature under `member_id_hex` directly over the 32-byte
   `SHA-256(SignedRecord)` digest.

Kinds `450` and raw-digest proofs are verification-only legacy forms. A producer MUST NOT create either form. Legacy
acceptance is scoped to legacy groups and does not reserve kind `450` for push: kind `450` belongs to the current
account identity proof.

A record's authority comes only from `owner_sig` and current group membership, not from the carrying event's sender. A
recipient applies a verified entry regardless of whether `message.sender` equals `member_id_hex`, but MUST still drop
any entry — verified or not — whose `member_id_hex` is not a current group member.

### Request, update, and announce (kind 447)

A kind `447` event with a non-empty `tokens` array is a self-update: the sender shares its own current token record,
normally as exactly one entry. A kind `447` event whose `tokens` array is empty and that has no `have` member is a token
request: it carries no records and asks other members to share theirs.

A kind `447` event MAY also carry a `have` member, which makes it an announce. An announce tells other members which
records and tombstones the sender holds, so they can send what it lacks (see "Token distribution"):

```json
{
  "v": "marmot-push-v1",
  "tokens": [],
  "have": ["<standard base64 of an 8-byte record digest>"]
}
```

- `have` lists every active token record and every tombstone the sender holds in the group. Each element is the first
  8 bytes of `SHA-256(SignedRecord)` for the entry that wrote that record or tombstone, which is the record digest the
  ordering primitive uses, as standard base64 with padding (12 characters). A tombstone's digest uses the removal form
  of `SignedRecord`.
- Order is not significant, and a repeated element counts once. An element that is not a string decoding to exactly 8
  bytes names no record and is ignored.
- `have` MUST NOT contain more than 4,096 elements. A sender that holds more records and tombstones than fit, under
  this limit or the size budget in "Event size", lists a subset; members may then send it entries it already holds,
  which costs bandwidth but changes no state.
- If `have` is present but is not an array, or the decoded array contains more than 4,096 elements, the recipient
  ignores the whole member before it decodes any element or does any other work on it. It sends no repair reply for
  that event, and still applies the event's `tokens` entries.

An announce carries the sender's own current records in `tokens`. A device with no record of its own sends `tokens: []`
with `have`.

A recipient applies each listed entry that passes "Owner authentication" and names a current member, and ignores the
rest, so a request changes no state. A self-update normally signs over `message.sender`'s own `member_id_hex`, but the
apply decision is the signature check, not a sender-equality check. `have` never changes a stored record or tombstone;
it only decides which entries a member sends in reply.

Recipients ignore unknown content members ("Token gossip event shapes"). A client that does not know `have` therefore
applies an announce as a plain self-update, or as a request when `tokens` is empty, and the announce changes nothing
else for it.

### List response (kind 448)

A kind `448` event lists active token records the sender holds, one entry per record, including records the sender
learned from other members. A member sends lists in a snapshot, with every record it holds, and in a repair reply, with
only the records an announcer lacks (see "Token distribution"). Each entry carries the original owner's `owner_sig` and
`owner_ts`, so a recipient applies it under the same "Owner authentication" rule as kind `447`: any entry whose owner
signature verifies and whose `member_id_hex` is a current member is applied, even when the sender is not its owner.
Entries that fail verification or name a non-member are dropped. To relay another member's record, a sender MUST
reproduce that member's `owner_sig` and `owner_ts` unchanged; it cannot mint records for members whose signatures it
does not hold.

### Removal (kind 449)

```json
{
  "v": "marmot-push-v1",
  "removals": [
    {
      "member_id_hex": "<64 lowercase hex characters>",
      "leaf_index": 3,
      "platform": "apns",
      "token_fingerprint": "sha256:<24 hex characters>",
      "server_pubkey_hex": "<64 lowercase hex characters>",
      "owner_ts": 1735680000000,
      "owner_sig": "<128 lowercase hex characters>"
    }
  ]
}
```

- `removals` MUST be an array of at most 32 removal entries. A missing `removals` member is read as an empty array. A
  present non-array `removals` member is advisory-invalid and contributes no removals. A sender with more removals
  splits them across multiple app events (see "Event size"). If the decoded array contains more than 32 entries, the
  recipient treats the entire array as advisory-invalid before performing any entry signature verification; the
  carrying group message remains valid.
- The first five members identify the token record being removed and use the encodings defined for token entries. A
  removal entry MUST carry `leaf_index` so it targets exactly one device's record and cannot revoke a sibling leaf's
  active token for the same account, platform, and server.
- `owner_ts` and `owner_sig` are the owner-authenticated ordering stamp and signature, using the removal signing event
  and the removal `SignedRecord` form (zero-length relay hint and no `encrypted_token`) from "Owner authentication".
  The same one-hour future bound on `owner_ts` applies to removals; a removal beyond it is advisory-invalid.

A recipient deletes the stored token record for the removal's record key (`member_id_hex`, `leaf_index`, `platform`,
`server_pubkey_hex`) only when the removal passes "Owner authentication", `member_id_hex` is a current member, and the
removal wins the record key's ordering primitive (see "Record key and ordering primitive"). A removal that fails
verification, names a non-member, or loses the ordering race is dropped as advisory-invalid.

A removal entry is owner-signed like a token entry, so any member can relay it. To relay another member's removal, a
sender re-sends the entry in a kind `449` with every field, `owner_ts`, and `owner_sig` unchanged, and a recipient
applies it under the rules above whoever sends it. Members relay removals in snapshots and repair replies (see "Token
distribution"). Relaying a tombstone means re-sending the removal entry that wrote it, so a member can relay only
tombstones whose complete removal entry it kept. A tombstone kept only as its stamp still suppresses stale records
locally.

The `token_fingerprint` is bound by the owner-proof event and is part of `SignedRecord`, so it is authenticated and
states which token instance the owner intends to revoke, but it is **not** part of the record key and does not gate the
delete: the
`(owner_ts, record digest)` stamp is the single arbiter of which write to a record key wins. This is deliberate. A
removal only deletes a record older than itself (it must win the ordering race), so the realistic re-registration race —
an old token, its removal, and a newer token with a different fingerprint on the same key — converges correctly on the
newest record by stamp alone, and a relayed stale removal can never revoke a newer token because it loses the race. A
fingerprint-gated delete would not improve this and would weaken tombstones (a fingerprint-scoped tombstone could not
suppress a differently-fingerprinted stale record from resurrecting the key).

### Record state

Push v1 does not impose a one-record-per-leaf invariant. Clients store one token record per member id, leaf index,
platform, and server public key in a group: an incoming entry that matches a stored record on those four values addresses
the same record key — including its replaceable fingerprint, relay hint, and encrypted token — and any other entry
addresses a different key. A leaf may therefore have distinct active records for different platform or server values;
those records remain separate until individually removed or the leaf leaves the group. Whether a same-key entry replaces
the stored record is decided only by the ordering primitive below, never by its array position.

Token records are local push state, never group state. The rules below order and revoke them so that two members'
clients can converge on the same token set without any of it affecting group validity. None of this ordering touches
MLS state, commit selection, or message validity, and a client MUST NOT reject, delay, or reorder a valid group
message because of a token record's age, absence, or supersession.

#### Record key and ordering primitive

The record key is the tuple `(member_id_hex, leaf_index, platform, server_pubkey_hex)`. At most one active record
exists per key per group. `leaf_index` is part of the key because one Marmot account can participate from multiple MLS
leaves (see [../foundation/identity.md](../foundation/identity.md#accounts-and-members)); omitting it would collapse sibling devices, letting one leaf's list
entry or removal overwrite or suppress another leaf's active token.

Each entry carries its owner's `owner_ts` and `owner_sig` (see "Owner authentication"). The ordering primitive for a
record key is the pair `(owner_ts, record digest)`, compared as the integer `owner_ts` first and the lowercase-hex
`SHA-256(SignedRecord)` as the tie-breaker. The `owner_ts` half is an owner-supplied, latest-wins clock; the digest
tie-breaker makes two distinct records with an equal `owner_ts` converge deterministically. The owner-proof event binds
every field from which both halves are computed, so the primitive inherits the trust of `owner_sig` rather than the
carrying event's sender and stays deliberately advisory. A client MUST NOT substitute the carrying event's
`created_at`, transport arrival order, outer transport event ids, relay metadata, or local receive time for this
primitive. Using `owner_ts` rather than the carrying `created_at` is what makes the primitive relay-safe: a member
relaying another member's record in a kind `448` cannot advance or rewind that record's position, because it cannot
re-sign `owner_ts`.

A client stamps each stored record with the `(owner_ts, record digest)` of the entry that last wrote it. Apply an
incoming entry or removal to a record key only when its ordering primitive is strictly greater than the stored stamp
for that key; otherwise ignore it as stale. The same comparison applies between same-key entries in one array. Array
position is not a tie-breaker, so the highest-stamped entry wins regardless of where it appears.

#### Removal and tombstones

A kind `449` removal does not merely delete the matching record: it writes a tombstone for the record key stamped with
the removal entry's `(owner_ts, record digest)`. A tombstone suppresses any later-arriving but earlier-stamped kind
`447`/`448` entry for that key, so a token list assembled before the removal cannot resurrect a revoked token. A
subsequent kind `447`/`448` entry whose stamp is strictly greater than the tombstone re-establishes an active record
for the key and clears the tombstone.

A removal that wins writes its tombstone whether or not a record for the key is stored. A removal that arrives before
the record it revokes, or that a member relays to a leaf that never held the record, therefore still suppresses that
record when it arrives.

A tombstone is durable: it persists until a strictly-greater-stamped kind `447`/`448` entry clears it (as above) or
the owning member leaf is removed from the group, as defined in the final paragraph of this section. It MUST NOT be
garbage-collected on any wall-clock, `owner_ts`, or MLS-epoch basis. Owner authentication makes records relay-portable:
any current member can re-emit another member's still-valid `owner_sig`/`owner_ts` record inside a fresh, in-window kind
`448` at any later epoch. So a tombstone (and, equivalently, the stored ordering stamp for a live record) is the only
durable high-water mark that stops a relayed but stale signed record from resurrecting a revoked or superseded token,
and it cannot be bounded by the retained app-payload window: unlike a record that could only ever arrive in its original
carrying epoch, a relayed record's carrying epoch is unbounded. The per-key stamp and tombstone therefore persist for
the owning leaf's whole lifetime in the group, and are cleared only when that leaf leaves.

#### Race handling

- **Removal versus a stale list response.** A kind `449` and a kind `448` that both reference the same record key are
  resolved by their ordering primitives, not by arrival order. The higher-stamped event wins; a lower-stamped list
  entry is dropped even if it arrives later.
- **Removal versus a stale trigger.** Honest clients stop selecting a removed or superseded record for new kind `446`
  triggers. The notification server cannot determine that record state from a trigger; the residual behavior is defined
  under "Best-effort revocation" below. A trigger never deletes or mutates a record.
- **Concurrent self-updates.** Two kind `447` self-updates for the same key from re-registration are ordered by their
  primitives; the higher-stamped record is the active one. Equal `owner_ts` is broken by the record digest, so clients
  converge.
- **Equal stamps.** Two records that differ in any signed field have distinct digests, so the tie-breaker is decisive.
  Two entries with the same `owner_ts` and the same digest are the same signed record: applying it again is idempotent,
  whether it arrives as a fresh self-update or relayed in a kind `448`.

When an accepted canonical Commit removes a member leaf, clients delete every stored token record and tombstone whose
`member_id_hex` and `leaf_index` match that removed leaf. Records for another current leaf with the same account identity
remain active. No kind `449` event is required for this cleanup.

#### Best-effort revocation

The v1 record model is stateless and best-effort. Kind `449`, record replacement, and member cleanup change which
records honest group members select for future triggers; they do not register revocation state with a notification
server. The server does not receive the MLS-encrypted kind `447`/`448`/`449` events and has no group membership, record,
or tombstone view against which it could prove that a presented `EncryptedToken` is current.

Consequently, a cached `EncryptedToken` remains a wake capability for a removed or malicious member until the native
platform token stops working or is replaced outside this protocol. Marmot push v1 provides no cryptographic token
revocation guarantee after disclosure to a group member. Server-side abuse controls, rate limits, platform-token
rotation, and notification-server key rotation are application and operator concerns; they MUST NOT affect MLS message
or group-state validity.

## Token distribution

Token gossip travels in ordinary group messages, so every current member receives each one, and a member that was
offline can fetch it later. A member therefore already sees every record and removal shared after it joined. What it
cannot see is anything shared before it joined, or anything the transport lost. The rules below close those gaps: the
member that adds a leaf sends it a snapshot, the new leaf announces what it holds at the end of its join window, devices
announce again when their own record changes and from time to time, and a few members reply to an announce with what
it lacks.

These rules only decide when members send token gossip. They change no group state, and a member that never sends
token gossip remains a valid member.

### Snapshot on add

A member that commits a Commit adding one or more leaves SHOULD send a snapshot promptly after it merges the Commit.
This includes a same-account Commit that adds the committer's own devices
([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)) and a founding Add Commit
([../protocol-core/joining.md](../protocol-core/joining.md)). A snapshot is:

- kind `448` events listing every active token record the member holds in the group, including records it learned from
  other members; and
- kind `449` events relaying every tombstone the member holds in the group, each as the removal entry that wrote it (see
  "Removal (kind 449)").

A member that holds no records sends no kind `448`, and a member that holds no tombstones sends no kind `449`, so a
member that holds neither sends nothing. The new leaf does not rely on the snapshot being complete: the announce at the
end of its join window finds whatever the snapshot missed (see "Announce").

Tombstones are part of the snapshot because a new leaf has none. Without them, a stale record relayed later by a member
that is behind could revive a revoked token on the new leaf (see "Removal and tombstones").

One snapshot covers every leaf the Commit added. A member that commits several Commits adding leaves in quick
succession MAY send one snapshot after the last of them instead of one after each.

Existing members recognize a snapshot by its sender: after a Commit that adds leaves, the kind `448` events that the
committer's leaf sends in the epoch that Commit creates or a later one. Only the owner check below uses this, and it
can be wrong: a snapshot has no end marker, and a repair reply from the committer's leaf looks like a snapshot. A new
leaf never needs to recognize its snapshot, because it announces at the end of its join window whatever arrived.

A device whose own current record is missing from a snapshot SHOULD re-share it in a kind `447` self-update. The record
is missing when no entry in the snapshot's kind `448` events has its record key and an ordering stamp equal to or
greater than its own. A snapshot can span several events and has no end marker, so the device judges it only after
processing every snapshot event it has received, and re-shares at most once per Commit that added leaves. A device that
judges too early, or takes a repair reply from the committer for a snapshot, sends one redundant self-update. A device
does not judge the snapshot that follows the Commit adding its own leaf, because no other member can hold its record
yet; it shares its record in that group as a new record, in a plain self-update while its join window lasts (see
"Announce").

### Announce

A device SHOULD send an announce, a kind `447` carrying `have` (see "Request, update, and announce (kind 447)"), in a
group:

- when it shares a new or changed record of its own there after its join window has ended, instead of a plain
  self-update;
- once when its join window in the group ends, whether or not snapshot events arrived; and
- with the next group message it sends there after its join window has ended, when it has not announced there within
  the announce interval. A device that has never announced in a group has not announced within the interval, so it
  announces with the first group message it sends there after the window.

Inside its join window, a device that joined follows the window rules below instead: a record it shares goes in a plain
self-update, with no `have`. A group's creator has no join window there, so the first and third rules apply to it at
once.

A device's join completes when all of these hold:

- the receiving flow in [../protocol-core/joining.md](../protocol-core/joining.md) has stored the group state;
- the device's convergence status in the group has reached `Settled`
  ([../protocol-core/group-state.md](../protocol-core/group-state.md)); and
- the device has fetched the group messages that the group's delivery endpoints hold from its join epoch onward, and
  has processed them. `Settled` alone does not imply this, because it covers only input the device already holds.

Time during which the device cannot fetch the group's messages, for example while it is offline, does not count toward
T.

A device's join window in a group lasts from its join until T has passed since its join completed. Inside the window
the device sends no `have` in that group, and a record it shares there goes in a plain self-update. An announce sent
before the snapshot arrived would ask for records the snapshot is about to bring. A device that created the group has
no join window there.

The announce at the end of the window carries the device's own record, if it has one, and a `have` that already
includes whatever the snapshot brought. It is normally a check: when the device holds everything, no member owes it
anything and no member replies. It also finds what a snapshot missed, for example when part of a split snapshot was
lost, when the adder held nothing and sent no snapshot, or when the adder sends no snapshots at all. This announce
counts as the device's last announce for the third rule above.

Tying the periodic announce to sending spreads announces over time, rather than sending one to every group when an
application opens, and the device learns what it lacks just before its own notification triggers need it. A device
that only reads a group still converges: the snapshot and its join-window announce cover its join, and when another
member's announce lacks the device's record, the members that reply relay it.

### Repair

A device answers a request, a kind `447` with no `have` and an empty `tokens` array, as an announce whose `have` is
empty. Every rule in this section applies to that answer, the rate limit included.

A device that receives an announce works out what the announcer lacks: the active records and tombstones the device
holds in the group, after applying the announce's own entries, whose digests are not in `have`. Only a record or
removal entry the device holds in full, with its `owner_sig`, counts, because only those can be relayed. If the
announcer lacks nothing, the device sends nothing, so a group whose devices hold the same set sends no repair.

Otherwise the device ranks every non-blank leaf of the group's ratchet tree at the epoch in which the announce was
sent, except the announcer's leaf. The announcer's leaf is the MLS-authenticated sender leaf of the message that
carries the announce, not a leaf named in its entries; an announce with `tokens: []` names none. Each leaf's rank key
is:

```text
rank_key = SHA-256(announce_id[32] || leaf_index[4])
```

`announce_id` is the 32 bytes decoded from the announce's app event `id`, which is 64 lowercase hex characters
([../foundation/application-messages.md](../foundation/application-messages.md), "Shape"); the hash input is those
bytes, not the hex text. `leaf_index` is the ranked leaf's MLS leaf index as a big-endian `u32`. Leaves are sorted by
`rank_key` in ascending byte order, and the first has rank 0. Ranks belong to leaves, not accounts. The device at a
leaf of rank 0, 1, or 2 SHOULD send a repair reply after waiting `r` × the reply slot from when it processed the
announce, where `r` is its leaf's rank. A device whose leaf has any other rank MUST NOT send a repair reply to that
announce, even when another leaf of the same account ranks in the top three. A repair reply is kind `448` events
listing the missing records and kind `449` events relaying the missing tombstones, and nothing else.

- **Cancelling.** Before sending, a device drops every item that an entry in a kind `448` or `449` it has processed
  since the announce already covers. An entry covers an item when it was carried in a group message of the announce's
  epoch or a later epoch, passes "Owner authentication", names a current member, has the item's record key, and has an
  ordering stamp equal to or greater than the item's. An entry from an earlier epoch never covers an item, even when
  the device processes it after the announce, because a leaf that joined later cannot decrypt it. If no item is left,
  the device cancels its reply.
- **Catching up.** A device that receives an announce while processing a batch of earlier group messages decides
  whether to reply only after processing the whole batch, so replies that others already sent can cancel its own. It
  counts its wait from that point.
- **Rate limit.** A device SHOULD NOT send more than one repair reply per announcer's leaf, as defined above, in a
  group in any 24 hours. It still applies the entries in every kind `447` it receives, so the limit never delays a
  token change.

If none of the three devices replies, for example because all of them are offline, the announcer's next announce has
a new app event id and so a new ranking.

`have` never writes state. Every entry a repair reply carries is checked under "Owner authentication", membership, and
the ordering primitive like any other entry, so a false `have` can only make members send entries the announcer
already holds. An announce draws at most three replies. A member that lies in `have` can make each of them a full
snapshot, but a device that follows the rate limit sends one leaf at most one reply per 24 hours, however many
announces that leaf sends. The `have` element limit bounds the work of reading an announce.

### Event size

A sender splits the entries it sends across events by size. Each carrying group message, as the active transport binding
publishes it (for the Nostr binding, the kind `445` event in [../transports/nostr.md](../transports/nostr.md)), SHOULD
fit the size limits of the group's delivery endpoints. A sender that knows no larger limit uses 65,536 bytes.

Each array still holds at most 32 entries: the 32-entry maximums on `tokens` in kinds `447` and `448` and on `removals`
in kind `449` are unchanged. A recipient discards an array of more than 32 entries before checking any signature, so a
larger array would lose every entry in it. At the 65,536-byte default the byte budget is usually the tighter limit.

The 4,096-element maximum on `have` is in "Request, update, and announce (kind 447)". The 32-chunk maximum on kind `446`
triggers ("Notification trigger") is separate and unchanged.

### Timing values

- **T**, the length of a device's join window after its join completes: implementation-defined. T MUST be at least
  one minute, so that the adder's snapshot normally arrives before the device announces.
- **The reply slot**: implementation-defined.
- **The announce interval**: implementation-defined. Seven days is a reasonable choice; only cost depends on it.

### Mixed versions

A client that predates these rules applies the snapshots, announces, and repair replies it receives, but sends none of
them. Groups converge more fully as their clients upgrade. While a group may contain such clients, a device SHOULD
also re-share its own record after any Commit that adds leaves, whether or not a snapshot follows, so that a new leaf
whose adder sends no snapshot still gets it.

## Notification trigger

The kind `446` rumor contains:

- `content`: one standard-base64 string with 1 to 32 concatenated 1084-byte chunks, each either an `EncryptedToken` or
  random padding as defined under "Padding and batching". A sender puts at least one padding chunk in every trigger, so
  a trigger it builds carries at most 31 `EncryptedToken`s. Padding chunks count toward the 32-chunk maximum and toward
  any smaller per-trigger chunk limit a sender applies;
- a `["v", "marmot-push-v1"]` tag, and no other tag;
- `pubkey`: a fresh ephemeral key.

The content field follows the Nostr transport byte-encoding rule: standard base64 with padding and no `encoding` tag.

The Nostr binding owns the outer NIP-59 seal and gift wrap, recipient addressing, and the notification-trigger
publish-target rule ([../transports/nostr.md](../transports/nostr.md), "Push notification delivery").

### Replay and freshness

A kind `446` trigger is a delivery hint, not group data. Replaying, dropping, duplicating, or reordering triggers MUST
NOT affect group state and MUST NOT make any valid group message invalid. All handling below is local push hygiene.

A notification server SHOULD deduplicate incoming triggers. The dedup key is the kind `446` rumor's content hash —
`SHA-256` over the decoded trigger content (every concatenated chunk, padding included), not the outer gift-wrap event
id, which a replayer can change freely by re-wrapping. A server that has already acted on a content hash within its
retention window SHOULD ignore a later trigger with the same hash rather than wake the recipient again. Because the
outer wrap uses a fresh ephemeral key per publish, the server MUST NOT rely on the outer event id for dedup.

This dedup depends on the fresh padding chunk every sender adds ("Padding and batching"): a sender's `EncryptedToken`
chunks repeat byte for byte across triggers to the same recipients, so a replayed or re-wrapped copy of one trigger
keeps its hash, while two triggers a sender builds separately do not.

A server attempts to decrypt each well-formed token chunk and MAY dispatch a native wake for each successful result. It
ignores a chunk that does not decrypt or whose plaintext is invalid. The server is neither required nor able to match a
successfully decrypted chunk against group token-record history; removal and supersession are sender-side selection
rules under "Record state", not server-visible trigger checks.

A trigger can be redundant or stale and does not prove that corresponding group content is currently fetchable.
Applications using mutable notifications reconcile presentation with their eventual fetch result. The exact
platform-notification presentation is application policy, not protocol validity.

### Server retention

Trigger material is ephemeral. A notification server retains a decoded trigger and its content-hash dedup entry only as
long as needed to deliver the wake and suppress immediate replays — a short bound measured in minutes, not a durable
log. A server MUST discard each decrypted device token after its dispatch attempt and MUST NOT persist trigger
plaintext, group identifiers, or recipient linkage derived from a trigger. A server holds no group state and learns
nothing about group membership or message content from a trigger; the only material it needs is the platform token it
decrypts to dispatch the native push.

## Padding and batching

A sender MUST append at least one padding chunk to every kind `446` trigger it builds, and MAY append further padding
chunks to obscure the real chunk count from relays or other observers of the encrypted gift-wrap length. Each padding
chunk is exactly 1084 bytes, sampled independently and uniformly with a cryptographically secure random generator, and
fresh for every trigger. Padding is allowed to fail notification-server parsing or decryption, and the server discards
it through the same per-chunk path as a token chunk that fails to decrypt ("Validation"). Padding therefore hides the
real chunk count from relays and other observers but not from the notification server, which can tell padding from a
token it decrypts.

The required padding chunk is what keeps distinct triggers distinct. A sender carries each `EncryptedToken` exactly as
its owner published it in a token record ("Token entries"). Without fresh padding, every trigger a sender builds from
the same token records in the same order would have the same content, and a server deduplicating by content hash
("Replay and freshness") would ignore all but the first as replays. A notification server does not check for padding
(see "Validation").

A sender MAY batch notifications for a short period.

A sender MUST NOT use any real device token as padding. A decryptable token would cause a real mutable notification and
can produce a visible notification with no corresponding content. The 32-chunk trigger maximum includes padding, so
padding cannot create unbounded server work.

## Validation

A client MUST treat malformed push notification data as advisory failure. It MUST NOT reject valid group messages
because a related push hint was missing, delayed, duplicated, or malformed.

### Advisory push hygiene versus protocol-invalid group data

Push notifications draw a sharp line between two failure classes:

- **Advisory push hygiene.** Everything in this document — a malformed or unsupported token entry, an entry whose
  `owner_sig` fails to verify or names a non-member, a token entry or removal that loses an ordering race, a stale or
  replayed kind `446` trigger, a missing relay hint, a failed token decrypt at the server — is advisory. The correct
  response is to drop the offending datum and continue. None of it rejects a group message, mutates group state, or
  changes which commit wins. A single bad entry in a kind `447`/`448`/`449` event is dropped on its own; the rest of
  the array still applies and the carrying group message remains valid. In particular, an `owner_sig` that fails
  verification fails the entry, never the carrying group message.
- **Protocol-invalid group data.** Protocol-invalid conditions are the ones the owning foundation/transport docs define
  for the carrying surface (see [../foundation/application-messages.md](../foundation/application-messages.md),
  "Encoding"). Those are decided by the app-payload decoder, not by this feature, and they are not specific to push.
  This feature adds no new way for push content to invalidate a group message.

Put plainly: kind `447`/`448`/`449` are ordinary unsigned Marmot app events, so they share the app payload's
validity rules; their push-specific `content` checks below only decide whether an individual token entry or removal is
applied, never whether the group message is valid.

A recipient applies the per-field rejection rules in "Token entries" and "Removal" at the entry granularity: reject the
individual entry, keep processing the rest, and never let an entry failure propagate to group-message validity.

Notification servers MUST ignore malformed notification triggers and MUST NOT dispatch a notification for them,
including:

- missing or unsupported `v` tags;
- invalid base64 content;
- empty decoded content, content whose length is not a multiple of 1084 bytes, or content containing more than 32
  chunks (`34,688` decoded bytes); this length check occurs before any ECDH or AEAD work.

Within a structurally valid trigger, the server processes each 1084-byte chunk independently. It skips a chunk with an
invalid ephemeral key, failed ECDH/HKDF, failed AEAD authentication, invalid platform bytes, or invalid token length and
continues with the remaining chunks. Random padding is discarded through this same per-chunk path.

A server cannot tell a padding chunk from a token chunk it fails to decrypt. It MUST NOT ignore a structurally valid
trigger because the trigger appears to carry no padding, for example because every chunk decrypted. A trigger from a
sender that does not pad is processed like any other. A later unpadded trigger whose `EncryptedToken` chunks match an
earlier one byte for byte still shares that content hash, so the dedup rule in "Replay and freshness" can ignore the
later trigger.

## Status and interop surface

Push notifications are an optional feature. A group MUST keep working when no member supports them, and nothing in this
document changes group state.

The `marmot-push-v1` shapes above are the interop surface: JSON content with explicit member ids, leaf indexes,
fingerprints, event-signed token and removal entries, and a kind `446` rumor whose only tag is `v`. Kind `451` is the
current owner-proof versioning hook even though only its signature is carried in `owner_sig`. The optional `have`
member of kind `447` is part of `marmot-push-v1`; a recipient that does not know it ignores it. Raw-digest and
transitional kind `450` owner proofs remain accepted only under the explicit legacy-group rules above. Earlier
exploratory versions that carried token gossip in `token` tags with empty content, left the sender's leaf implicit,
defined no removal entries, or required an `["encoding", "base64"]` tag on the kind `446` rumor are not interoperable
with this version and predate the owner-authentication and per-record ordering rules; clients MUST reject any `v` other
than `marmot-push-v1`.
