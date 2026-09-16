# Multi-device

Status: experimental.

This document specifies the experimental `marmot.same-account-membership.v1` feature. Requirement keywords are
normative for implementations that enable component `0x800d`; the feature is not part of the adopted base profile.

Multi-device support lets one Marmot account, as defined by [identity.md](../foundation/identity.md), participate in a
group from multiple independent MLS leaves. Each device has its own leaf, leaf secret, KeyPackages, and local group
state. Devices never share live MLS state.

## Surfaces and assignments

- Component `0x800d`, [`marmot.same-account-membership.v1`](../app-components/same-account-membership-v1.md), owns
  negotiation, Commit authorization, and the five-leaf invariant. It carries no component data.
- Protocol core owns candidate-parent validation, Welcome processing, publish-before-apply, and convergence.
- This document owns pairing records, enrollment intent, Welcome replay recovery, and app-event kind `452`.
- Kind `453` is the local-only pairing authorization proof. The pairing carrier contributes no authorization.
- Optional content synchronization is separate; see [account-sync.md](./account-sync.md).

## Pairing trust and descriptor

The existing device is the **sponsor** and trust root. It displays a QR descriptor; the joining device scans it. Both
devices already control the same Marmot account key. The QR carries a high-entropy secret, not a Diffie-Hellman key:
v1 deliberately accepts no forward secrecy for this short-lived channel so implementations can reuse HKDF-SHA256 and
ChaCha20-Poly1305 without adding a Noise stack.

```text
struct { opaque carrier<1..32>; opaque data<0..512>; } MarmotPairingRendezvousHintV1;

struct {
  uint8 format;
  opaque pairing_session_id[32];
  opaque pairing_secret[32];
  opaque account_identity[32];
  uint64 not_after;
  MarmotPairingRendezvousHintV1 rendezvous_hints<0..1024>;
} MarmotPairingDescriptorBodyV1;

struct {
  MarmotPairingDescriptorBodyV1 body;
  MarmotAuthorizationProof sponsor_proof;
} MarmotPairingDescriptorV1;
```

`format` is `1`. The session id and secret are independent, uniformly random 32-byte values and are single-use.
`not_after` is a Unix timestamp. Lifetime defaults to two minutes and MUST NOT exceed five minutes. `carrier` is
lowercase ASCII `[a-z0-9._-]+`; carrier names are unique and retain sponsor preference order. `data` is opaque. Carrier
names and hint contents do not acquire protocol authority or feature-specific semantics.

QR text is `marmot-pairing-v1:` followed by unpadded base64url of the canonical descriptor bytes and MUST NOT exceed
2,048 ASCII bytes. Decoders reject another prefix, padding, non-url-safe characters, non-canonical base64url, expired
descriptors, trailing bytes, or an oversized QR string.

### Pairing authorization proofs

Proofs use `MarmotAuthorizationProof` and [its common rules](../foundation/authorization-proofs.md). Their local signing
template is Nostr kind `453` and is never relayed.

```text
descriptor_hash = SHA-256(Marmot-Encode(MarmotPairingDescriptorBodyV1))
```

The sponsor proof event has `pubkey = account_identity`, content
`Authorize this Marmot same-account pairing session`, and exactly these ordered tags:

```text
["d", "marmot.same-account-pairing-proof.v1"]
["role", "sponsor"]
["session", lowerhex(pairing_session_id)]
["transcript", lowerhex(descriptor_hash)]
```

The joining device chooses a uniformly random nonce and encodes:

```text
struct { opaque descriptor_hash[32]; opaque joiner_nonce[32]; } MarmotPairingJoinerContextV1;
joiner_context_hash = SHA-256(Marmot-Encode(MarmotPairingJoinerContextV1))
```

Its kind-`453` proof uses the same pubkey, content, `d`, and session, but `role = joining-device` and
`transcript = lowerhex(joiner_context_hash)`. The sponsor verifies it before disclosing group information. These proofs
establish control of the same account key and one session, not device identity, group continuity, or sponsor honesty.

Both proof signers MUST equal `account_identity`. Before producing a joining proof or sending a hello, the joining
device MUST validate the descriptor format and bounds, account identity, session id, descriptor hash, exact sponsor
proof event fields and signature, and lifetime. The sponsor proof `created_at` MUST be no later than `not_after`, and
`not_after - created_at` MUST be at most 300 seconds. The joining proof MUST be produced and verified before
`not_after`. A session id or secret that has already established a channel MUST be rejected on later scans.

The joining device sends one plaintext pre-channel message through the selected carrier:

```text
struct {
  uint8 version;
  opaque pairing_session_id[32];
  opaque joiner_nonce[32];
  MarmotAuthorizationProof joining_proof;
} MarmotPairingHelloV1;
```

`version` is `1`. The sponsor verifies the session id and joining proof before deriving channel keys. The message need
not be confidential; its signature binds the nonce and descriptor, and the QR secret does not appear in it. Any other
pre-channel message is ignored. A second non-identical hello for the same session terminates that session.

## Pairing channel

The carrier MAY drop, duplicate, delay, or reorder records and supplies neither identity nor confidentiality. These
rules apply even when it claims a secure connection. Nostr and NIP-44 are not required pairing carriers.

### Key schedule

All labels are their exact UTF-8 bytes:

```text
pairing_salt = SHA-256("marmot.same-account-pairing.v1")
pairing_prk  = HKDF-Extract-SHA256(pairing_salt, pairing_secret)

struct {
  opaque label<V>;
  opaque descriptor_hash[32];
  opaque joiner_context_hash[32];
} MarmotPairingKdfInfoV1;
```

HKDF-Expand-SHA256 over that canonical structure derives a 32-byte key with label `sponsor-to-joiner key`, a 32-byte
key with `joiner-to-sponsor key`, and 12-byte nonce bases with `sponsor-to-joiner nonce` and
`joiner-to-sponsor nonce`. For sequence `n`, XOR the nonce base with `n` encoded as a 96-bit big-endian integer.
Sequences start at zero and MUST NOT wrap.

Fixed derivation vector (all values are hexadecimal):

```text
pairing_secret             = 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
descriptor_hash            = 202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f
joiner_context_hash        = 404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f
pairing_salt               = e3158d294a22a9158dcbc2fa7b9ca5604ce0acf17b06454527bb0c18cabb561b
pairing_prk                = 3a5038aa7c44c32860fb4f30291bfa217934d72633778b72b0d6fdc4d2cd6280
sponsor-to-joiner key      = 57a76b3c891e34108d112efd6ae4267e32ef6719c06838436ab99c40fd1bf32e
joiner-to-sponsor key      = fe9fb7dee3fc5a36e0310661727e3a9e48b4337f39b856e7ae217a98acbabaec
sponsor-to-joiner nonce    = f86baa07eaa5fe627f48fdb2
joiner-to-sponsor nonce    = 4b61dc790e7d4f2c47d890c9
```

### Records

```text
struct {
  uint8 version;
  opaque pairing_session_id[32];
  uint8 direction;
  uint64 sequence;
  uint8 record_type;
  uint8 flags;
  opaque ciphertext<16..65552>;
} MarmotPairingRecordV1;
```

`version` is `1`; direction `0` is sponsor-to-joiner and `1` is the reverse; flags are `0`. Maximum plaintext is
65,536 bytes. ChaCha20-Poly1305 AAD is the canonical concatenation of all fields before `ciphertext` followed by a
`uint32` equal to ciphertext length. Reject a key/direction mismatch, unsupported value, length mismatch, or failed
authentication.

Accept at most one ciphertext for each `(direction, sequence)`. An identical duplicate is ignored; a different one
terminates the session. Records may authenticate out of order. The channel has a five-minute idle timeout and a
thirty-minute absolute lifetime. Closing it does not undo published Commits.

Record types are `1 = sponsor_approval`, `2 = enrollment_object_chunk`, and `3 = session_close`. Approval plaintext is
`descriptor_hash[32] || joiner_context_hash[32]`; session-close plaintext is empty. Unknown record types are rejected.
The sponsor sends approval as its first encrypted record. No enrollment object is sent or accepted before the joining
device verifies it.

```text
struct {
  opaque object_id[32];
  uint8 object_type;
  uint64 total_length;
  uint64 offset;
  opaque bytes<V>;
} MarmotPairingObjectChunkV1;
```

An enrollment object is at most 16 MiB. Validate total length, offset arithmetic, overlap, and record limit before
allocation. Chunks may arrive out of order and MUST cover every byte exactly. Identical overlaps are ignored;
conflicting overlaps terminate the session. Verify before decoding:

```text
object_id = SHA-256("marmot.same-account-pairing-object.v1" || uint8(object_type) || complete_object_bytes)
```

Object types are `1 = catalog`, `2 = selection`, `3 = KeyPackage batch`, and `4 = enrollment-intent batch`:

```text
struct { opaque group_id<V>; } MarmotEnrollmentGroupV1;
struct { uint32 batch_number; uint8 is_last; MarmotEnrollmentGroupV1 groups<1..32>; }
  MarmotEnrollmentCatalogBatchV1;
struct { uint32 batch_number; MarmotEnrollmentGroupV1 groups<0..32>; }
  MarmotEnrollmentSelectionBatchV1;
struct { opaque group_id<V>; opaque key_package_mls_message<V>; } MarmotEnrollmentKeyPackageV1;
struct { uint32 batch_number; MarmotEnrollmentKeyPackageV1 entries<1..32>; }
  MarmotEnrollmentKeyPackageBatchV1;

struct {
  opaque pairing_session_id[32];
  opaque group_id<V>;
  opaque sponsor_account[32];
  opaque sponsor_leaf_signature_key<1..1024>;
  opaque key_package_ref<V>;
  uint64 approval_expires_at;
} MarmotSameAccountEnrollmentIntentV1;

struct { uint32 batch_number; MarmotSameAccountEnrollmentIntentV1 entries<1..32>; }
  MarmotEnrollmentIntentBatchV1;
```

Batch numbers start at zero and are unique per type. Catalog group ids are unique. Selection and KeyPackage entries
refer to cataloged groups. Each KeyPackage field is exactly one `mls_key_package` MLSMessage, is generated for and used
only by its named group in this session, carries a valid account proof, and advertises `0x800d`. The group association
is authenticated by the pairing object and later intent; it adds no field inside the MLS KeyPackage. Each intent
matches its group and KeyPackage reference. Its sponsor account is the paired account, and
`sponsor_leaf_signature_key` is the exact signature key of the sponsor's current group leaf. The sponsor MUST NOT
change that signature key in the enrollment Commit. Define:

```text
enrollment_intent_hash = SHA-256(Marmot-Encode(MarmotSameAccountEnrollmentIntentV1))
```

`approval_expires_at` MUST be no later than 30 minutes after the QR descriptor's `not_after` value. The joining device
rejects an intent that is already expired or exceeds that bound.

More than 32 groups use additional batches; there is no 32-group account limit. Only one attempt per group is active.

Catalogs expose only group ids needed for correlation. Display metadata and presets are local UI. The sponsor SHOULD
request explicit approval showing the account, joining device, group count, and selected groups before sending intents.
Optional history bootstrap has separate formats and MUST NOT increase these enrollment-control limits.

## Per-group enrollment

For every selected group:

1. The joining device creates a fresh group-bound KeyPackage and durably retains its private material.
2. The sponsor creates and sends the canonical intent defined above.
3. The joining device validates and durably approves the unexpired intent.
4. The sponsor creates exactly one inline-Add Commit, publishes it under publish-before-apply, then sends the Welcome
   through the active Welcome transport.
5. The joining device accepts only a matching Welcome, durably joins, sends the acknowledgement, and only then performs
   its post-join self-update.

Nostr-routed Welcomes remain kind `444` rumors inside NIP-59 gift wraps. Pairing does not replace the Welcome transport.
Sequential Add publication is valid. Four concurrently publishing Adds is recommended implementation guidance, not
protocol-visible behavior.

## Welcome authorization

If a Welcome's KeyPackageRef matches an active, approved same-account enrollment intent, the receiver MUST use this
same-account authorization path even when the sponsor is an active admin. It MUST NOT fall back to ordinary admin
authorization. The receiver validates ordinary Welcome and resulting-state requirements except the admin-only
membership-add check, then additionally requires:

- `0x800d` required in the resulting GroupContext;
- the exact local KeyPackage and approved intent;
- no `0x800d` component-data entry at any location;
- the GroupInfo signer account equals the joining account and approved sponsor account;
- the GroupInfo signer leaf uses the intent's exact `sponsor_leaf_signature_key`;
- the GroupInfo group id and Welcome KeyPackageRef match the intent;
- the local validation time is no later than the approved `approval_expires_at`;
- sponsor and joining leaves have valid account proofs; and
- no account exceeds five leaves.

The receiver retains exact serialized Welcome and GroupInfo digests. Success means **locally joined to the
sponsor-attested branch**, not global finality. A client MAY display it unverified until another account speaks, subject
to [Welcome-bootstrap trust](../protocol-core/joining.md#welcome-bootstrap-trust).

The sponsor is the trust root. Its GroupInfo signature authenticates the resulting branch; the fresh KeyPackageRef and
exact sponsor leaf key correlate that branch with the interactive pairing intent. The joiner does not independently
validate the candidate parent or Add-only Commit shape, and successful joining does not establish global finality.

Conformance cases include: an admin sponsor with a matching active intent MUST use this same-account path; an ordinary
admin invitation with no matching intent uses the admin path; and a matching intent with a different GroupInfo signer
leaf key is rejected.

## Enrollment acknowledgement and Welcome replay

The first post-join application payload MUST be kind `452`, precede the self-update, and not render as chat:

```text
welcome_digest    = SHA-256(serialized_welcome_mls_message)
group_info_digest = SHA-256(TLS-Serialize(group_info))

struct {
  opaque label<V>; // "marmot.same-account-enrollment.v1"
  opaque pairing_session_id[32];
  opaque group_id<V>;
  opaque key_package_ref<V>;
  opaque group_info_digest[32];
} MarmotStableEnrollmentIdInputV1;

stable_enrollment_id = SHA-256(Marmot-Encode(MarmotStableEnrollmentIdInputV1))
```

The inner event has empty content and exactly these ordered tags:

```text
["d", "marmot.same-account-enrollment-ack.v1"]
["enrollment", lowerhex(stable_enrollment_id)]
["pairing", lowerhex(pairing_session_id)]
["intent", lowerhex(enrollment_intent_hash)]
["key-package-ref", lowerhex(key_package_ref)]
["welcome", lowerhex(welcome_digest)]
["group-info", lowerhex(group_info_digest)]
["joined-epoch", canonical_decimal(joined_epoch)]
```

Its `pubkey` is the sender leaf's MLS-authenticated account identity, and its unsigned event id and receiver
authentication follow [application-messages.md](../foundation/application-messages.md). It has no inner `sig`.

Initially the MLS sender MUST be the exact added leaf. The sponsor completes only after authenticating that sender and
matching every field to its staged intent, Commit, Welcome, and epoch.

The joiner durably retains the stable id, all fields, and exact Welcome digest. On byte-identical Welcome replay it
matches the plaintext KeyPackageRef before MLS processing, does not process again or require the consumed `init_key`,
and republishes a fresh ack. Event id and timestamp may change; tags do not. A current descendant of the added leaf MAY
send this recovery ack after self-update only when its validated leaf lineage is an uninterrupted sequence of
self-updates from that leaf; a later Remove/Add is not a continuation. Same KeyPackageRef with a different digest is
rejected. If the group was discarded, the leaf was removed, or the record was invalidated, no ack is sent and fresh
pairing with a fresh KeyPackage is required.

## Convergence, removal, and recovery

Same-account Adds and Removes have ordinary convergence priority. A losing joiner discovers loss later through ordinary
convergence, not Welcome validation. A retry uses a fresh KeyPackage and intent. A lost ack retries the byte-identical
Welcome and MUST NOT issue another Add. An ack is not proof the Add is globally canonical.

Failure to receive an acknowledgement MUST NOT by itself make a published Add terminal. After a bounded local retry
window, the sponsor stops automatic Welcome retransmission and records the result as published-but-unacknowledged. It
retains the exact Welcome and enrollment correlation data for later acknowledgement recovery or fresh-pairing
reconciliation. Canonical loss, group deletion, or removal of the enrolled leaf terminates that retained attempt.

Enrollment is durable per group, not cross-group atomic. Session expiry does not roll back completed groups. A later
fresh pairing reconciles already-completed memberships before proposing another Add. Loss of unconsumed KeyPackage
private material makes that attempt terminal and requires a fresh KeyPackage.

Any current leaf may remove one to four other leaves of its account using the component's Remove-only shape. It cannot
remove itself through this path. At the five-leaf limit, remove stale siblings, wait for canonical Remove, then perform
a separate Add with a fresh KeyPackage. An admin may clean up an account only after it has no current leaf. V1 has no
cross-group tombstone or recovery when neither a sibling nor active admin survives.

## Initial invitation and exclusions

When an account has no group leaf, an admin admits exactly one initial leaf using the ordinary path. Public KeyPackage
slot tags are not device identifiers and discovery MUST NOT fan out across all valid packages.

This feature never copies an MLS state store, epoch secrets, sender ratchets, KeyPackage private keys, or pending
operations. Continuous journals, CRDT merges, public device identifiers, cross-group atomicity, and shared virtual-leaf
secrets are out of scope.

## Migration from the withdrawn draft

The withdrawn draft used an External Commit, join PSK, externally provisioned GroupInfo, administrator proof, and
transferred group keys. None shipped. Its released ids remain invalid and MUST NOT be interpreted as this feature.
