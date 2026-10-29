# marmot.member.device-tag.v1

Status: draft.

`marmot.member.device-tag.v1` lets an account's linked devices tell which of the account's leaves in a group belongs to
which device. Every leaf of one account carries the same credential identity, so nothing else in a group says which
device holds a leaf. A device tag names the device's slot, is signed by that device, and is sealed so that only the
account's linked devices can read it. Other members see opaque bytes that differ in every KeyPackage.

The device group, its roster and the keys a tag uses are described in
[../features/device-group.md](../features/device-group.md) and [device-roster-v1.md](./device-roster-v1.md).

## Registry

- Component id: `0x800f`
- Name: `marmot.member.device-tag.v1`
- Location: the `app_data_dictionary` in an MLS LeafNode, including the LeafNode embedded in a KeyPackage
- Default requirement: never required. A group MUST NOT list `0x800f` in its required list, because an account with
  one device has no tag to carry.

A client MUST NOT create an entry under `0x800f` anywhere else. An entry under `0x800f` in any other location is
unknown data ([README.md](./README.md), "Unknown Data").

## Component data

```text
struct {
  opaque nonce[12];
  opaque sealed<1..255>;
} DeviceTagV1;

struct {
  opaque slot[32];
  opaque signature<1..255>;
} DeviceTagContentV1;

struct {
  opaque slot[32];
  opaque leaf_signature_key<V>;
} DeviceTagSignedContentV1;
```

The structures use the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)).

`sealed` is a `DeviceTagContentV1` sealed with ChaCha20-Poly1305
([RFC 8439](https://www.rfc-editor.org/rfc/rfc8439)):

```text
sealed = ChaCha20-Poly1305.encrypt(leaf_tag_key, nonce, DeviceTagContentV1, aad = leaf_signature_key)
```

- `leaf_tag_key` is the device group roster's ([device-roster-v1.md](./device-roster-v1.md)).
- `nonce` is 12 bytes from a cryptographically secure random source, chosen afresh for every tag.
- `leaf_signature_key` is the exact contents of the LeafNode's `signature_key` vector, without its length prefix.
- `slot` is the device's slot id, as in its roster entry.
- `signature` is `SignWithLabel(tag signature private key, "Marmot DeviceTag", DeviceTagSignedContentV1)`
  ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420), section 5.1.2), under the signature scheme of the device
  group's ciphersuite. Its `slot` and `leaf_signature_key` are the same values as above. The public key is the device's
  `tag_signature_key` in the roster.

Under ciphersuite `0x0001` a tag is 127 bytes.

## Producing tags

A device can tag once it holds its device group's `leaf_tag_key` and its own roster entry carries its
`tag_signature_key` ([../features/device-group.md](../features/device-group.md), "Matching leaves to devices"). From
then on:

- it MUST put a tag in the LeafNode of every KeyPackage it creates, whether it publishes the KeyPackage or hands it to a
  sibling;
- it MUST put a tag in every LeafNode it creates for its own leaf in any group, including the device group: in an
  Update, or in the UpdatePath of its own Commit. A replacement LeafNode whose signature key is unchanged MAY carry the
  same tag; one with a new signature key needs a new tag;
- every LeafNode that carries a tag MUST advertise `0x800f` in its `app_components` support list.

A device whose own leaf in a group carries no tag that reads as its own, because it joined through a KeyPackage created
before it could tag or because the leaf predates the link, SHOULD replace that leaf with a tagged one. When it joined
that way, it does so with its post-join self-update ([../protocol-core/joining.md](../protocol-core/joining.md),
receiving flow, step 14). Otherwise it waits a random delay first, as for a leaf that advertises too few components
([README.md](./README.md), "Advertising support"), so that linking a device does not make it commit in every group at
once.

## Reading tags

Only a device that holds `leaf_tag_key` can read a tag. For a leaf whose credential identity is its own account's, it:

1. decodes the leaf's `0x800f` entry as a `DeviceTagV1`, opens `sealed` with `leaf_tag_key`, `nonce` and the leaf's
   signature key as `aad`, and decodes the result as a `DeviceTagContentV1`;
2. if `slot` names a device in the roster that has a `tag_signature_key`, verifies `signature` with that key. If it
   verifies, the leaf belongs to that device;
3. if `slot` names a slot in the roster's `rejected_slots`, takes the leaf to belong to that rejected slot. A rejected
   slot has no key to verify with, and a tag can only make such a leaf look less trusted, so the signature is not
   checked;
4. otherwise the leaf is unclaimed. This covers a leaf with no entry, an entry that does not decode or open, a
   signature that does not verify, and a slot the roster does not hold.

A device has at most one leaf in a group. Two leaves in one group that both belong to the same device show that
device's keys were misused.

What the account's devices do about an unclaimed leaf, a rejected slot's leaf, or a sibling missing from a group is
not specified yet.

## Validity

A device tag never makes a KeyPackage, LeafNode, proposal, Commit or Welcome invalid, and a receiver checks nothing
about the entry. Most members cannot open a tag, so a rule that rejected one would split the members who can from
those who cannot. To a device that can read tags, an entry that does not decode, open or verify is the same as no tag.

## Lifecycle

The entry belongs to its LeafNode. It changes only when the device creates a new or replacement LeafNode, and it MUST
NOT be created, replaced or removed with `AppDataUpdate` ([README.md](./README.md), "Placement").

## Security considerations

- Members outside the account see a tag as bytes that differ with every KeyPackage and reveal nothing without
  `leaf_tag_key`. They learn nothing new: an account's leaf count is already visible. A KeyPackage used in several
  groups, such as a last-resort one, shows the same tag in each, as it already shows the same leaf signature key.
- A tag is bound to its leaf's signature key both as `aad` and inside the signature. Copying a tag from a published
  KeyPackage into another leaf gives a leaf whose tag does not open, so that leaf is unclaimed.
- Holding the account's signing key gives neither `leaf_tag_key` nor any device's tag signature key, so a leaf added
  that way is unclaimed.
- A removed device still holds `leaf_tag_key` ([device-roster-v1.md](./device-roster-v1.md), "Security
  considerations"). It can tag a leaf only with its own slot, which its siblings recorded as `removed`.

## Test vectors

Not yet defined.

## Migration

This is the first version. A breaking change gets a new component id and document.
