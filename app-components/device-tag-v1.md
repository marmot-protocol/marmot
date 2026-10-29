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

Under ciphersuite `0x0001` a `DeviceTagContentV1` is 98 bytes: the slot, a 2-byte length prefix and a 64-byte Ed25519
signature. Sealing adds a 16-byte authentication tag, so a `DeviceTagV1` is 128 bytes: the nonce, a 2-byte length
prefix and 114 sealed bytes.

## Producing tags

A device can tag once it holds its device group's `leaf_tag_key` and its own roster entry carries its
`tag_signature_key`, or the Commit it is creating sets that key
([../features/device-group.md](../features/device-group.md), "Matching leaves to devices"). From then on:

- it MUST put a tag in the LeafNode of every KeyPackage it creates, whether it publishes the KeyPackage or hands it to a
  sibling;
- it MUST put a tag in every LeafNode it creates for its own leaf in any group, including the device group: in an
  Update, or in the UpdatePath of its own Commit. A replacement LeafNode whose signature key is unchanged MAY carry the
  same tag; one with a new signature key needs a new tag;
- every LeafNode that carries a tag MUST advertise `0x800f` in its `app_components` support list.

A device whose own leaf in a group carries no tag that reads as its own SHOULD replace that leaf with a tagged one. This
happens when it joined through a KeyPackage created before it could tag, or when the leaf predates the link. If it can
tag when it makes its post-join self-update in that group ([../protocol-core/joining.md](../protocol-core/joining.md),
receiving flow, step 14), that update is the replacement. Otherwise it replaces the leaf once it can tag, after a random
delay as for a leaf that advertises too few components ([README.md](./README.md), "Advertising support"), so that
linking a device does not make it commit in every group at once.

## Reading tags

Only a device that holds `leaf_tag_key` can read a tag. It reads against its device group's current roster, so a tag
signed with a key that the same Commit sets reads as its device's once that Commit is applied. For a leaf whose
credential identity is its own account's, it:

1. decodes the leaf's `0x800f` entry as a `DeviceTagV1`, opens `sealed` with `leaf_tag_key`, `nonce` and the leaf's
   signature key as `aad`, and decodes the result as a `DeviceTagContentV1`;
2. if `slot` names a device in the roster that has a `tag_signature_key`, verifies `signature` with that key. If it
   verifies, the leaf belongs to that device;
3. if `slot` names a `removed` record in the roster's `rejected_slots` that keeps a `tag_signature_key`, verifies
   `signature` with that key. If it verifies, the leaf belongs to that removed slot;
4. otherwise the leaf is unclaimed. This covers a leaf with no entry, an entry that does not decode or open, a
   signature that does not verify, a slot the roster holds no key for, and a slot the roster does not hold.

A device has at most one leaf in a group. Two leaves in one group that both belong to the same device show that
device's keys were misused.

What the account's devices do about an unclaimed leaf, a removed slot's leaf, or a sibling missing from a group is
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
  `leaf_tag_key`. The entry's presence is not hidden: it shows other members, and anyone who fetches the account's
  KeyPackages, that the account has linked devices. The account's KeyPackage publications already show that, one slot
  per device ([../foundation/key-packages.md](../foundation/key-packages.md)). A KeyPackage used in several groups,
  such as a last-resort one, shows the same tag in each, as it already shows the same leaf signature key.
- A tag is bound to its leaf's signature key both as `aad` and inside the signature. Copying a tag from a published
  KeyPackage into another leaf gives a leaf whose tag does not open, so that leaf is unclaimed.
- Holding the account's signing key gives neither `leaf_tag_key` nor any device's tag signature key, so a leaf added
  that way is unclaimed.
- A removed device still holds `leaf_tag_key` ([device-roster-v1.md](./device-roster-v1.md), "Security
  considerations"). It can tag a leaf only with its own slot, which its siblings recognize as `removed` while they keep
  that slot's record.

## Test vectors

Under ciphersuite `0x0001`, with leaf tag key `0x33` repeated 32 times, slot `0x11` repeated 32 times, a leaf signature
key of `0x66` repeated 32 times, nonce `0x77` repeated 12 times, and an Ed25519 tag signature private key
([RFC 8032](https://www.rfc-editor.org/rfc/rfc8032)) of `0x55` repeated 32 times, whose public key is
`c6822637c7d310ec57627be00ba259d253749f4aaf644470cffbe53a35f73242`.

The `SignContent` ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420), section 5.1.2) that is signed, 92 bytes:

```text
18                                                               label<V>, 24 bytes
4d4c5320312e30204d61726d6f7420446576696365546167                 "MLS 1.0 Marmot DeviceTag"
4041                                                             content<V>, 65 bytes
1111111111111111111111111111111111111111111111111111111111111111 slot
20 6666666666666666666666666666666666666666666666666666666666666666 leaf_signature_key
```

The `DeviceTagContentV1`, 98 bytes:

```text
1111111111111111111111111111111111111111111111111111111111111111 slot
4040                                                             signature<1..255>, 64 bytes
601cd5e2a4fc4fc0871cac3ce66a8f2376b199110700f92abb693460bb282849
695ff8afe6da3432ca7a60a1b409195e9cac96b3ed1ff25a31ab138f8c455e01
```

The `DeviceTagV1`, 128 bytes, whose `sealed` ends with the 16-byte authentication tag:

```text
777777777777777777777777                                         nonce
4072                                                             sealed<1..255>, 114 bytes
711af2f06f38f0f04032cfdf0f23a8ea57773ecac4fde7f4b8e7d4789c38ba13
4a727afee6b3858640acf81557466cdb6abd9251bafa8de2c6cb69d4e15993fe
39ed1ca968e78f4b4e804bf74ed76d782a2ba3d3a3ac51afda04f00318e3a2a5
7e181129d2430033adf59c6160510eae4782
```

## Migration

This is the first version. A breaking change gets a new component id and document.
