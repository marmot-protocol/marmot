# Ratchet tree reference

Status: draft.

Security context: [protocol threat model](../security-considerations.md#t3-invitation-abuse-stale-packages-and-first-contact-group-substitution)
and [external media](../security-considerations.md#t8-external-media-shared-credentials-and-deletion-limits).

A Marmot Welcome normally carries the group's ratchet tree inline, in the GroupInfo `ratchet_tree` extension. The tree
grows by about one leaf per member, so in a large group the Welcome outgrows what transports carry, and every invitee
receives its own copy. A ratchet tree reference lets the inviter upload the tree once, as an encrypted blob, and send
each invitee a small Welcome whose delivery names the blob, its key, its hash and how long it stays available. The
joiner fetches the blob, checks it, and supplies the tree to MLS out of band
([RFC 9420 §12.4.3.1](https://www.rfc-editor.org/rfc/rfc9420#section-12.4.3.1)).

This is the only out-of-band tree distribution Marmot defines. An inviter uses it only when every invitee of the Commit
advertises support, so a client that cannot follow a reference never receives one
([../protocol-core/joining.md](../protocol-core/joining.md), "Ratchet tree source").

## Surfaces

- Foundation KeyPackages: the capability marker `marmot.feature.ratchet_tree_reference.v1`
  ([../foundation/registries.md](../foundation/registries.md)).
- Protocol-core joining: the tree-source rule, the receiving flow and Welcome failures
  ([../protocol-core/joining.md](../protocol-core/joining.md)).
- The active transport binding: how a Welcome delivery carries the reference
  ([../transports/nostr.md](../transports/nostr.md), "Welcome delivery").
- Blob storage: the locator kinds of [encrypted-media.md](./encrypted-media.md#locator-kinds). `blossom-v1` is the
  first.

The reference never chooses group state. MLS binds the tree to the GroupInfo the Welcome carries; the reference only
says where to find the bytes.

## Capability

A client that can join from a reference lists extension type `0xf2e1` (`marmot.feature.ratchet_tree_reference.v1`) in
its KeyPackage LeafNode `capabilities.extensions`. The marker carries no extension data and is never emitted as a
LeafNode, GroupContext or GroupInfo extension body. An inviter reads it from the decoded KeyPackage. A client that adds
support replaces its published KeyPackages ([../foundation/key-packages.md](../foundation/key-packages.md),
"Capability advertising").

The marker is a property of one KeyPackage, not of a group. No group requires it, and existing members never process
Welcomes, so a group whose members run different versions needs no change. An inviter that does not implement this
feature keeps sending inline trees.

## Choosing the tree source

One Commit has one GroupInfo, so the inviter chooses one tree source for every Welcome of a Commit.

The inviter MUST use the inline source unless every KeyPackage the Commit adds advertises the marker. When every one
does, it MAY use a reference, and SHOULD when an inline Welcome would exceed a known event-size limit of a delivery
target that an invitee needs. The binding names those limits ([../transports/nostr.md](../transports/nostr.md),
"Welcome delivery"). Below them the choice is the inviter's policy: an inline Welcome is self-contained and needs no
blob host, while a reference costs one blob upload per Commit instead of one copy of the tree per invitee per
delivery target, and each joiner fetches only its own copy.

The choice applies to one Commit. It does not change the tree source of any later Commit's Welcomes, and a client
MUST NOT stop including the tree in inline Welcomes because it once sent a reference.

When an invite into an existing group has invitees that need different sources, the inviter adds them in separate
Commits, one source per Commit. It SHOULD commit the inline ones first, while the tree is smallest.

A founding creation has exactly one founding Commit, which is never published
([../protocol-core/joining.md](../protocol-core/joining.md), "Behavior"). The creator adds every initial invitee in it
with one tree source, or leaves out the invitees that cannot use the chosen source. It MAY add those afterward with
ordinary published Commits, and otherwise reports each of them as not invited. It MUST NOT add them with a second Commit
that is not published: the members the founding Commit added would never receive it. The founding Commit's automatic
requirements follow the KeyPackages in it ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)). A
left-out invitee whose KeyPackage lacks one of them, such as `marmot.group.account-devices.v1`, cannot be added
afterward, and the creator reports it as not invited for that reason.

A reference Welcome still carries the GroupInfo, whose GroupContext component state can grow with the group (for
example the admin list). The size limits that apply to any Welcome apply to it too.

## Reference

A reference has these fields:

| Field | Value |
| --- | --- |
| `version` | `1` |
| `locators` | 1 to 4 locators, each a locator kind and value, in the order the joiner tries them |
| `blob_sha256` | SHA-256 of the blob, the exact bytes stored and served, 32 bytes |
| `key` | the blob key, 32 bytes |
| `blob_size` | the blob's length in bytes, at least 64 and less than 2^32 |
| `available_until` | Unix time in seconds until which the inviter keeps the blob available |

Locator kinds and their validation are those of [encrypted-media.md](./encrypted-media.md#locator-kinds). A
`blossom-v1` locator in a reference MUST be the BUD-01 fetch URL `server_root || "/" || hash_hex`, with no extension,
query or fragment, where `server_root` is the endpoint's base URL without trailing `/` and `hash_hex` is the lowercase
hex `blob_sha256`: the form of encrypted media's fallback fetch URL. The inviter builds it from the endpoint rather
than storing a URL the server returned. A joiner skips, without contacting it, a locator whose kind it does not
support, a `blossom-v1` locator of another form, and one that names another hash. A reference with no usable locator
is discarded without a validity claim and without a fetch.

The reference is secret: its key opens the tree. It travels only inside the encrypted Welcome delivery.

## Blob

```text
tree_bytes = the extension_data of the MLS ratchet_tree extension for the Commit's resulting epoch
             (optional<Node> ratchet_tree<V>, RFC 9420 §12.4.3.3), exactly as the inline extension would carry it
L          = len(tree_bytes)
plain      = uint32(L) || tree_bytes || zero bytes, padded_len(L) - L of them
key        = random(32)
nonce      = random(12)
aad        = "marmot-ratchet-tree-v1"
blob       = nonce || ChaCha20-Poly1305.encrypt(key, nonce, plain, aad)
```

`uint32` is big-endian. The AAD is the ASCII bytes shown, with no terminator. `blob_sha256` is the SHA-256 of `blob`,
nonce included, and `blob_size` is its length, `12 + 4 + padded_len(L) + 16`.

`padded_len(L)` is 32 if `L` ≤ 32, and otherwise the smallest multiple of `chunk` that is at least `L`, where `chunk`
is 32 if the smallest power of two at least `L` is 256 or less, and otherwise one eighth of that power of two. This is
NIP-44's `calc_padded_len` without its 65,535-byte cap. For a tree over 256 bytes, padding adds less than 25% and
reveals the tree's length only to within one chunk.

The inviter MUST generate `key` and `nonce` with a cryptographically secure random generator and MUST use a fresh key
for every blob. One blob serves every Welcome of one Commit. A re-upload sends the identical blob bytes; it never
re-encrypts.

## Upload

The inviting device uploads the blob. It tries the group's `marmot.group.encrypted-media.v2` `default_blob_endpoints`
in order, then its own configured media servers, and stores it at one or two endpoints. A group with no endpoint and an
inviter with no server cannot use a reference.

The inviter MUST authorize each blob's upload and deletion with a fresh ephemeral key used for no other blob and no
other purpose, and keeps that key until it deletes the blob. Each operation (upload, re-upload, deletion) signs its
own short-lived authorization with it, under the locator kind's rules. The inviter MUST NOT authorize a blob operation
with its account identity. A `blossom-v1` blob is served without authorization, so a joiner fetches it with a plain
request.

Before the inviter starts the Commit's publish obligation
([../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md)), at least one endpoint MUST have stored
the blob and confirmed its hash. If none does, the inviter abandons the Commit without publishing it, and either adds
the invitees with the inline source in a new Commit, when its Welcomes fit, or reports the invite as failed. A founding
creation completes the upload before its canonical write; if none succeeds, it uses the inline source when that fits,
and otherwise refuses the creation. An inviter that abandons a Commit, for this or any other reason, including after a
restart, deletes its blob. A Welcome naming a blob therefore never goes out unless the blob was stored. This does not
guarantee that the blob stays available; "Availability and lifetime" below bounds that.

## Availability and lifetime

The inviter sets `available_until` when it releases a delivery: the release time plus 30 days. A delivery prepared
before its Commit's publish obligation succeeded gets its deadline at release, not before. The inviter MUST NOT
publish or republish a delivery after its `available_until`.

The inviting device keeps the blob available:

- with no deadline yet, while the Commit's publish obligation is unresolved or its Welcomes are held for an undecided
  branch;
- after release, until the latest `available_until` among the deliveries that name it. In that time it SHOULD check
  that each locator still serves the blob when it republishes a delivery and periodically, and SHOULD upload the
  identical bytes again where a locator has lost it.

It SHOULD delete the blob from every endpoint, with the blob's ephemeral key, after that latest deadline. It SHOULD
NOT delete it earlier because the invitees joined: the host would learn which fetchers joined. Completion evidence for
a leaf is an MLS-authenticated Commit or application message on the canonical branch whose sender is that leaf, sent
after the Add and before any removal or replacement of that leaf. A relay acknowledgement or the leaf's presence in
the roster is not completion evidence. If the Commit's
publish obligation is abandoned, or its branch is terminally invalidated, the inviter withdraws its Welcomes and
deletes the blob.

Deletion depends on the endpoint honoring it. A blob that stays stored is ciphertext under a key held only by the
Commit's invitees and its inviter.

When a delivery's `available_until` passes without completion evidence for its leaf, the inviter knows only that the
tree is no longer available and that it has seen no sign of the invitee joining. The invitee may have joined and
stayed silent. If the invitee did not join, its leaf stays in the roster; an admin can remove it and invite again,
with a new Commit and blob.

## Fetching and verification

A joiner fetches the blob only for a delivery it would otherwise process: the delivery passed transport
authentication and its reference is well formed; `available_until` has not passed, allowing a small clock skew; it
names a KeyPackage this device
holds; it is not from a sender the client refuses and has not been declined; and the Welcome, inspected without any
durable change, has a GroupInfo that lacks the `ratchet_tree` extension and a group id the client would accept. That
inspection MUST NOT consume, rotate or delete KeyPackage material; the KeyPackage-consuming join runs only once the
tree is in hand, as the tentative operation of the receiving flow. A device MUST NOT fetch for a delivery that names
another device's KeyPackage. The join itself repeats every check.

The joiner tries the locators in order. It MUST NOT read more than `blob_size` bytes, and MAY refuse a reference
whose `blob_size` exceeds a local resource limit. It accepts bytes from a locator only when their length equals
`blob_size` and their SHA-256 equals `blob_sha256`. A joiner that keeps a fetched blob for later use MUST check its
hash again before using it. With those bytes it MUST:

1. decrypt them under `key` with the AAD above;
2. check that the length prefix `L` is at most `len(plain) - 4`, that `plain` has exactly `4 + padded_len(L)` bytes,
   and that every byte after `tree_bytes` is zero;
3. decode `tree_bytes` as `optional<Node> ratchet_tree<V>` with no trailing bytes;
4. supply that tree to MLS Welcome processing as the out-of-band tree.

MLS then verifies the tree's parent hashes and leaves, the GroupInfo signature against the signer's leaf in that tree,
the tree hash against the GroupContext `tree_hash`, and the confirmation tag (RFC 9420 §12.4.3.1). The rest of the
receiving flow in [../protocol-core/joining.md](../protocol-core/joining.md) applies unchanged.

Network contact follows the client's network-destination policy for media locators.

## Failures

A delivery's sender authenticates the reference it carries, not the Welcome inside it: anyone who holds a recipient's
Welcome bytes can carry them under another reference. Every outcome that involves the reference therefore depends on
the delivery, and under [../protocol-core/joining.md](../protocol-core/joining.md) ("Failure behavior") none of them
stops the receiver from processing another delivery of the same Welcome.

- **Unavailable.** No locator served bytes of the declared length and hash: not found, refused, timed out, too large,
  or a hash mismatch. The joiner keeps the delivery, changes no KeyPackage state, records no duplicate marker, and
  retries with backoff until `available_until`. It then discards the delivery without a validity claim.
- **Reference invalid.** Bytes matched the hash, and decryption, padding, decoding, or MLS's verification of the tree
  failed; or the delivery offers both tree sources or neither, or its Welcome carries more than one
  `EncryptedGroupSecrets` entry. The joiner rejects this delivery only. The same Welcome bytes remain eligible in
  another delivery, and the KeyPackage is untouched. Until MLS accepts a tree, a wrong tree and a bad GroupInfo look
  alike, so the joiner treats both as this delivery's failure.
- **Other refusals.** MLS accepted the tree and a later check of the receiving flow failed. The joiner refuses the
  delivery as it would an inline one, under [../protocol-core/joining.md](../protocol-core/joining.md) ("Failure
  behavior").

A local failure that is not about the delivery, such as a storage error, is retried as it would be for an inline
Welcome.

A joiner MUST bound the deliveries it holds as unavailable, per account and per sender, the fetches it runs at once,
the bytes it downloads and caches, its retries, and how long it holds a delivery whatever its `available_until`. A
delivery a bound refuses is discarded without a validity claim, oldest first, with the KeyPackage untouched.

An inviter cannot observe a joiner's fetch, as it cannot observe Welcome processing.

## Privacy

- The delivery carries the reference inside its encryption. Nothing about the blob appears in an outer transport
  object.
- A reference Welcome does not grow with the tree, so its delivery targets do not learn the group's size from it.
- The blob host is a party an invitee contacts before joining. It learns the blob's padded size, which tracks the
  group's size closely, the upload's time and network origin, and each fetch's time and network origin. For a founding
  creation, whose Commit is never published, the blob host is the one party that learns the new group's size. Fetches
  happen before an invitee accepts, so the host learns which addresses were invited, not which joined. Co-invitees of
  one Commit fetch the same blob, so the host can link them, and repeated fetches link one device's retries. An
  operator that also runs the group's relays can correlate the upload and the fetches with the Commit and with later
  subscriptions to the group. The ephemeral key does not identify the inviter.
- The fetch precedes GroupInfo signature verification, because the GroupInfo's signer leaf is in the tree. Anyone
  holding a published KeyPackage can send a Welcome-shaped delivery and so make a client contact a host of the sender's
  choosing and download up to its local limit, even for a Welcome that then fails. The fetch rules and bounds above
  confine that to deliveries the client would otherwise process, to usable locators that name the declared hash. A
  client MAY wait to fetch until its user opens the invite.

## Interaction with other flows

- **Convergence.** A reference names the tree of one epoch. Joining from it is a first join at that epoch, followed by
  catch-up, as for an inline Welcome. A Welcome for a losing branch is handled as any such Welcome.
- **Redelivery.** A redelivered delivery carries the same reference and deadline; the blob does not change.
- **Sibling Welcomes.** A sibling Welcome inside the device group carries its tree inline
  ([device-group.md](./device-group.md), "Sibling Welcomes").
