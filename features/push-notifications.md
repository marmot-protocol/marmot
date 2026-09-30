# Push notifications

Status: adopted.

Push notifications let a sender give a recipient a delivery hint outside the normal group-message fetch path.

Push notification support is optional. A group MUST still work when no client supports push notifications.

## Surfaces

- App payload: token gossip event kinds `447`, `448`, and `449`, carried inside ordinary encrypted group messages (see
  "Token gossip event shapes").
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

- kind `447`: token request and self-token update;
- kind `448`: token list response;
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
  across multiple app events. If the decoded array contains more than 32 entries, the recipient treats the entire
  array as advisory-invalid before performing any entry signature verification; the carrying group message remains
  valid.
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
that carries it. This lets one member relay another member's records (see "List response") so a group converges on the
full token set without requiring every owner to be online, while preventing a relaying member from forging, repointing,
or rolling back another member's routing.

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

### Request and update (kind 447)

A kind `447` event with a non-empty `tokens` array is a self-update: the sender announces its own current token
record, normally as exactly one entry. A kind `447` event whose `tokens` array is empty is a token request: it carries
no records and asks other members to share theirs.

A recipient applies each listed entry that passes "Owner authentication" and names a current member, and ignores the
rest, so an empty request changes no state. A self-update normally signs over `message.sender`'s own `member_id_hex`,
but the apply decision is the signature check, not a sender-equality check.

### List response (kind 448)

A kind `448` event is a response listing the responder's current view of the group's active token records, one entry
per record, including records the responder learned from other members. Each entry carries the original owner's
`owner_sig` and `owner_ts`, so a recipient applies it under the same "Owner authentication" rule as kind `447`: any
entry whose owner signature verifies and whose `member_id_hex` is a current member is applied, even when the responder
is not its owner. Entries that fail verification or name a non-member are dropped. To relay another member's record, a
responder MUST reproduce that member's `owner_sig` and `owner_ts` unchanged; it cannot mint records for members whose
signatures it does not hold.

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
  splits them across multiple app events. If the decoded array contains more than 32 entries, the recipient treats the
  entire array as advisory-invalid before performing any entry signature verification; the carrying group message
  remains valid.
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

## Notification trigger

The kind `446` rumor contains:

- `content`: one standard-base64 string with 1 to 32 concatenated 1084-byte chunks, each either an `EncryptedToken` or
  optional random padding as defined below;
- a `["v", "marmot-push-v1"]` tag, and no other tag;
- `pubkey`: a fresh ephemeral key.

The content field follows the Nostr transport byte-encoding rule: standard base64 with padding and no `encoding` tag.

The Nostr binding owns the outer NIP-59 seal and gift wrap, recipient addressing, and the notification-trigger
publish-target rule ([../transports/nostr.md](../transports/nostr.md), "Push notification delivery").

### Replay and freshness

A kind `446` trigger is a delivery hint, not group data. Replaying, dropping, duplicating, or reordering triggers MUST
NOT affect group state and MUST NOT make any valid group message invalid. All handling below is local push hygiene.

A notification server SHOULD deduplicate incoming triggers. The dedup key is the kind `446` rumor's content hash —
`SHA-256` over the decoded trigger content (the concatenated `EncryptedToken` bytes), not the outer gift-wrap event id,
which a replayer can change freely by re-wrapping. A server that has already acted on a content hash within its
retention window SHOULD ignore a later trigger with the same hash rather than wake the recipient again. Because the
outer wrap uses a fresh ephemeral key per publish, the server MUST NOT rely on the outer event id for dedup.

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

Clients MAY batch notifications for a short period and MAY append padding to obscure the real chunk count from relays
or other observers of the encrypted gift-wrap length. Each padding chunk is exactly 1084 bytes sampled independently
and uniformly with a cryptographically secure random generator. Padding is allowed to fail notification-server parsing
or decryption and is distinguishable to that server.

A sender MUST NOT use any real device token as padding. A decryptable token would cause a real mutable notification and
can produce a visible notification with no corresponding content. The 32-chunk trigger maximum includes padding, so
padding cannot create unbounded server work.

## Validation

A client MUST treat malformed push notification data as advisory failure. It MUST NOT reject valid group messages
because a related push hint was missing, delayed, duplicated, or malformed.

### Advisory push hygiene versus protocol-invalid group data

Push notifications draw a sharp line between two failure classes:

- **Advisory push hygiene.** Everything in this document — a malformed or unsupported token entry, an entry whose
  `owner_sig` fails to verify or names a non-member, a removal that matches no record, a stale or replayed kind `446`
  trigger, a token list that loses an ordering race, a missing relay hint, a failed token decrypt at the server — is
  advisory. The correct response is to drop the offending datum and continue. None of it rejects a group message,
  mutates group state, or changes which commit wins. A single bad entry in a kind `447`/`448`/`449` event is dropped on
  its own; the rest of the array still applies and the carrying group message remains valid. In particular, an
  `owner_sig` that fails verification fails the entry, never the carrying group message.
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

## Status and interop surface

Push notifications are an optional feature. A group MUST keep working when no member supports them, and nothing in this
document changes group state.

The `marmot-push-v1` shapes above are the interop surface: JSON content with explicit member ids, leaf indexes,
fingerprints, event-signed token and removal entries, and a kind `446` rumor whose only tag is `v`. Kind `451` is the
current owner-proof versioning hook even though only its signature is carried in `owner_sig`. Raw-digest and
transitional kind `450` owner proofs remain accepted only under the explicit legacy-group rules above. Earlier
exploratory versions that carried token gossip in `token` tags with empty content, left the sender's leaf implicit,
defined no removal entries, or required an `["encoding", "base64"]` tag on the kind `446` rumor are not interoperable
with this version and predate the owner-authentication and per-record ordering rules; clients MUST reject any `v` other
than `marmot-push-v1`.
