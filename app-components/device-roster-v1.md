# marmot.account.device-roster.v1

Status: draft.

`marmot.account.device-roster.v1` is the roster of an account's device group: the account's linked devices, the
sign-ins and KeyPackages its devices rejected, the key that seals the account's device tags, and account-wide fields
reserved for account sync. A group that requires this component is a device group.
[../features/device-group.md](../features/device-group.md) describes the device group, when it is created, and when a
device trusts a group as its own. Requiring this component never makes a group trusted.

The roster holds nothing about the other groups the account's devices are in. Which leaf in a group belongs to which
device is carried by that leaf's own device tag ([device-tag-v1.md](./device-tag-v1.md)), so joining a group, leaving
one, or replacing a leaf there never changes the roster.

The non-normative direction this component serves is described in [../ideas/multi-device.md](../ideas/multi-device.md)
and [../ideas/account-sync.md](../ideas/account-sync.md).

## Registry

- Component id: `0x800e`
- Name: `marmot.account.device-roster.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: required from creation in a device group ("Requirement" below); never required in any other
  group

A client MUST NOT create an entry under `0x800e` anywhere else. An entry under `0x800e` in a LeafNode, a KeyPackage or
any other location is unknown data ([README.md](./README.md), "Unknown Data"), in a device group as in any other
group.

## State

```text
opaque SlotId[32];
opaque RenameIdV1[16];
opaque KeyPackageRefV1<1..64>;
opaque TagSignatureKeyV1<1..255>;
opaque ReservedKeyV1<1..255>;

enum {
  active(0),
  inactive(1),
  leaving(2),
  (255)
} DeviceStatusV1;

struct {
  SlotId slot;
  opaque label<0..64>;
  optional<RenameIdV1> rename_id;
  opaque client<0..64>;
  opaque platform<0..64>;
  uint64 linked_at;
  optional<SlotId> linked_by;
  uint8 settings;
  DeviceStatusV1 status;
  optional<KeyPackageRefV1> announced_key_package;
  optional<TagSignatureKeyV1> tag_signature_key;
  optional<ReservedKeyV1> history_key;
} DeviceEntryV1;

enum {
  not_me(0),
  removed(1),
  (255)
} RejectionReasonV1;

struct {
  SlotId slot;
  RejectionReasonV1 reason;
  uint64 rejected_at;
  optional<TagSignatureKeyV1> tag_signature_key;
} RejectedSlotV1;

struct {
  KeyPackageRefV1 key_package_ref;
  SlotId slot;
  uint64 rejected_at;
} RejectedKeyPackageV1;

struct {
  optional<SlotId> backup_writer;
  optional<ReservedKeyV1> recovery_public_key;
} AccountEntryV1;

struct {
  opaque leaf_tag_key[32];
  DeviceEntryV1 devices<V>;
  RejectedSlotV1 rejected_slots<V>;
  RejectedKeyPackageV1 rejected_key_packages<V>;
  AccountEntryV1 account;
} DeviceRosterV1;
```

The structures use the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)). `optional<T>` is one presence byte,
`0x00` for absent or `0x01` followed by `T`, as in MLS; any other presence byte is invalid. Enumerations are one byte,
and a value the enumeration does not list is invalid.

`leaf_tag_key` is the key that seals the device tags of the account's devices
([device-tag-v1.md](./device-tag-v1.md)). The device that creates the device group sets it to 32 bytes from a
cryptographically secure random source. No update changes it in this version.

Each device the account has linked has one `DeviceEntryV1`:

- `slot` is the device's KeyPackage publication slot id ([../foundation/key-packages.md](../foundation/key-packages.md),
  "Devices and publication slots"). On the Nostr binding it is the 32 bytes of the KeyPackage event's `d` value
  ([../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"). The slot identifies the device in the
  roster.
- `label` is the name the user gave the device, `client` its client name, and `platform` its platform. Each is UTF-8,
  compared and stored as bytes and never normalized; a decoder rejects bytes that are not UTF-8.
- `rename_id` is 16 random bytes. Every entry is created with a fresh one, every rename writes a new one, and no other
  update changes it, so a device can tell its own rename from another after a fork
  ([../features/device-group.md](../features/device-group.md), "Labels, clients and platforms").
- `linked_at` is when the device was linked, in seconds since the Unix epoch, as the linking device wrote it.
  `linked_by` is the slot of the device that linked it, absent for the device that created the group.
- `settings` holds one flag per bit: bit 0 (`0x01`) "add to all my chats", bit 1 (`0x02`) "bring chat history", and
  bit 2 (`0x04`) "keep while inactive". The other bits MUST be zero.
- `status` is `active`, `inactive` (the device's siblings marked it inactive), or `leaving` (the device recorded that it
  is signing out).
- `announced_key_package` is the `KeyPackageRef` ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420), section 5.2) of
  the KeyPackage the device announced for its slot, if it announced one. A `KeyPackageRefV1` holds the raw output of
  `MakeKeyPackageRef` under the KeyPackage's ciphersuite, without the length prefix MLS gives a `HashReference`: 32
  bytes under ciphersuite `0x0001`. See [../features/device-group.md](../features/device-group.md), "Slot
  announcements".
- `tag_signature_key` is the public key the device signs its device tags with, under the signature scheme of the device
  group's ciphersuite ([device-tag-v1.md](./device-tag-v1.md)). It is absent until the device sets it.
- `history_key` is reserved for account sync and has no meaning in this version.

`RejectedSlotV1` records a slot whose sign-in the user rejected (`not_me`) or whose device was removed (`removed`).
`RejectedKeyPackageV1` records a rejected KeyPackage by its `KeyPackageRef`, with the slot it appeared in. `rejected_at`
is when the rejection was recorded, as the recording device wrote it. A `removed` record keeps the `tag_signature_key`
the device's entry had, if it had one, so that the account's devices can still recognize that device's tags
([device-tag-v1.md](./device-tag-v1.md), "Reading tags"). A `not_me` record has none: a rejected sign-in never had an
entry. When a device writes a `not_me` record, and what it then stops asking about, is in
[../features/device-group.md](../features/device-group.md) ("New sign-ins").

A `removed` record lets the account's devices recognize the removed installation if it publishes into its old slot
again or turns up in a group. A device SHOULD remove a `removed` record once 30 days have passed since its
`rejected_at`, by the device's own clock, so that the roster does not keep every device the account has ever removed.
The record is a bounded recognition aid, not a guarantee. A KeyPackage can stay valid for up to 84 days, and an inviter
MAY select a stale one when an account has no fresh candidate
([../foundation/key-packages.md](../foundation/key-packages.md), "Selection and lifecycle"), so the removed
installation can still join a group after its record is gone. Its leaf then reads as unclaimed rather than as the
removed device's ([device-tag-v1.md](./device-tag-v1.md), "Reading tags").

`AccountEntryV1` is reserved for account sync: `backup_writer` names a device by slot, and `recovery_public_key` is the
public half of the recovery key. Neither has a meaning in this version.

Receivers never compare `linked_at` or `rejected_at` with their own clocks. The fields reserved for account sync are
opaque hints in the sense of [../foundation/canonical-encoding.md](../foundation/canonical-encoding.md) ("Canonical
decoding"): a receiver checks only their stated bounds, and the document that gives them a meaning MUST NOT make
bytes within those bounds invalid.

## Validation

A `DeviceRosterV1` is valid when all of these hold:

- it decodes canonically, with no trailing bytes;
- `devices` and `rejected_slots` are each sorted by `slot` and unique by `slot`, and `rejected_key_packages` is sorted
  and unique by `key_package_ref`, in the default order of
  [../foundation/canonical-encoding.md](../foundation/canonical-encoding.md) ("Sorting and duplicates");
- `devices` holds at most `max_leaves_per_account` entries, the constant of
  [account-devices-v1.md](./account-devices-v1.md) ("Leaf limit");
- every `settings` value has bits 3 to 7 clear;
- no two entries in `devices` carry the same `tag_signature_key`. This compares present keys only: any number of entries
  may have none;
- no `not_me` record in `rejected_slots` carries a `tag_signature_key`;
- no slot appears both in `devices` and in `rejected_slots`.

A device can appear once only, so a slot that is rejected is never also a linked device.

## Update

The roster's update is a diff, not a full replacement state. This is the explicit exception that
[README.md](./README.md) ("GroupContext Update Processing") allows: an AppDataUpdate sets or removes individual entries,
and the members apply it to the candidate parent's roster.

```text
enum {
  set_device(0),
  remove_device(1),
  set_rejected_slot(2),
  remove_rejected_slot(3),
  set_rejected_key_package(4),
  remove_rejected_key_package(5),
  set_account(6),
  (255)
} RosterOperationType;

struct {
  RosterOperationType type;
  select (RosterOperationV1.type) {
    case set_device:                  DeviceEntryV1 device;
    case remove_device:               SlotId slot;
    case set_rejected_slot:           RejectedSlotV1 rejected_slot;
    case remove_rejected_slot:        SlotId slot;
    case set_rejected_key_package:    RejectedKeyPackageV1 rejected_key_package;
    case remove_rejected_key_package: KeyPackageRefV1 key_package_ref;
    case set_account:                 AccountEntryV1 account;
  };
} RosterOperationV1;

struct {
  RosterOperationV1 operations<V>;
} DeviceRosterUpdateV1;
```

Each operation names one entry. A device entry and a rejected slot are keyed by their slot, a rejected KeyPackage by
its `key_package_ref`, and the account entry is a single entry with no key. No operation names `leaf_tag_key`. An
update is valid only when:

- it decodes canonically and holds at least one operation;
- it holds at most one operation per entry;
- its operations are sorted by entry: device entries first, then rejected slots, then rejected KeyPackages, then the
  account entry. Within each kind they follow that kind's order in `DeviceRosterV1` ("Validation" above).

The resulting roster is the candidate parent's roster with every operation applied:

- `set_device`, `set_rejected_slot` and `set_rejected_key_package` insert the entry, or replace the entry with the same
  key;
- `remove_device`, `remove_rejected_slot` and `remove_rejected_key_package` remove the entry with that key. Removing an
  entry the parent's roster does not hold makes the update invalid;
- `set_account` replaces the account entry.

Because no two operations name the same entry, the result does not depend on the order in which they are applied. The
resulting roster MUST be valid ("Validation" above); otherwise the update, and the Commit that carries it, is invalid.

An update replaces whole the entries it names. A device that changes one field of an entry, such as its `platform`,
sends the whole entry with that field changed; a rename changes `label` and `rename_id` together
([../features/device-group.md](../features/device-group.md), "Labels, clients and platforms"). Other entries are
untouched.

A client that applies the update differently, for example by taking the update's bytes as the new state, computes a
different GroupContext from every other member's, so its Commit does not stage for them and creates no candidate edge
([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate branches").

## Requirement

A group requires this component from its creation or never:

- A device group's founding state lists `0x800e` in its GroupContext `app_components` required list and carries a valid
  roster ([../features/device-group.md](../features/device-group.md), "Creating the device group").
- A Commit whose candidate parent state requires `0x800e` and whose resulting state does not is invalid, and so is a
  Commit whose candidate parent does not require it and whose resulting state does. No member, including an active
  admin, is authorized to commit either. This component defines no activation in an existing group
  ([README.md](./README.md), "Enabling a Component in an Existing Group").
- A standalone proposal that would make either change is invalid.

While a state requires `0x800e`:

- its GroupContext carries a valid roster;
- every current leaf has the same credential identity: a device group holds the devices of one account and no others.
  This is checked against the complete resulting state of every Commit, whoever commits it, and by a joiner against the
  state a Welcome joins ([../protocol-core/joining.md](../protocol-core/joining.md), receiving flow, step 7).

Before a group requires the component, a client that supports it treats an entry under `0x800e`, and an AppDataUpdate
for it, as it treats those of any unknown component ([README.md](./README.md), "Unknown Data"): an update replaces the
bytes whole and nobody parses them. This keeps its validity decisions equal to those of members that do not support the
component. A client MUST NOT create an entry under `0x800e` in a group that does not require it.

## Authorization

This component keeps the default: only an active admin MAY propose or commit a roster update
([README.md](./README.md), "Default GroupContext Authorization"). In a device group every leaf belongs to the account
that created it, and that account is the group's only admin
([../features/device-group.md](../features/device-group.md), "Creating the device group"), so every device of the
account may edit any entry. No device outranks another.

A roster update MAY be inline or standalone. A standalone roster update is validated against its source epoch's
roster when it is received, and against the candidate parent's roster when a Commit carries it.

## Removal

A device group requires this component for its lifetime, so an AppDataUpdate `remove` targeting `0x800e` in it is
invalid ([README.md](./README.md), "GroupContext Removal").

## Security considerations

- Any device of the account can rewrite any entry, including another device's settings, its `tag_signature_key`, and
  the rejections. A stolen linked device can do the same until it is removed. The roster records decisions; it does not
  protect them from a linked device.
- Only the account's own devices are members of a device group, so the roster, its labels, platforms and
  `leaf_tag_key` are never visible to other accounts. A client MUST NOT copy them into any other group or show another
  account's roster.
- Every device that was ever in the device group holds `leaf_tag_key`, including one later removed, because this
  version never changes it. A removed device can still read the device tags in groups it is still in, including those
  of devices linked after it was removed, so it can still tell which of the account's leaves there belongs to which
  device. It cannot make a tag that names another device or another removed slot, because a
  tag is verified with the key of the slot it names ([device-tag-v1.md](./device-tag-v1.md), "Reading tags").
- The roster grows with the number of linked devices, at most `max_leaves_per_account`, and with the rejections. It
  does not grow with the number of groups the devices are in, and activity in those groups never commits to the
  device group. A Welcome into the device group carries the whole roster.
- Holding the account's signing key does not by itself let anyone into the device group or let anyone write the
  roster. Only a member of the device group can write it, and a device becomes a member only through a link the user
  confirmed ([../features/device-group.md](../features/device-group.md), "Trust").

## Test vectors

A roster with leaf tag key `0x33` repeated 32 times and one device in slot `0x11` repeated 32 times, labelled `Phone`
with rename id `0x55` repeated 16 times, client `wn`, no platform, linked at `0x6553f100`, with no linker, settings
`0x05` ("add to all my chats" and "keep while inactive"), status `active`, no announced KeyPackage, tag signature key
`0x44` repeated 32 times and no history key, and with no rejections and an empty account entry:

```text
3333333333333333333333333333333333333333333333333333333333333333 leaf_tag_key
406a                                                             devices<V>, 106 bytes
1111111111111111111111111111111111111111111111111111111111111111 slot
0550686f6e65                                                     label "Phone"
01 55555555555555555555555555555555                              rename_id
02776e                                                           client "wn"
00                                                               platform ""
000000006553f100                                                 linked_at
00                                                               linked_by absent
05                                                               settings
00                                                               status active
00                                                               announced_key_package absent
01                                                               tag_signature_key present
20 4444444444444444444444444444444444444444444444444444444444444444 tag_signature_key
00                                                               history_key absent
00                                                               rejected_slots<V>
00                                                               rejected_key_packages<V>
00                                                               backup_writer absent
00                                                               recovery_public_key absent
```

An update that removes that device and records its slot as `removed` at `0x6553f200`, keeping its tag signature key:

```text
406d                                                             operations<V>, 109 bytes
01                                                               remove_device
1111111111111111111111111111111111111111111111111111111111111111 slot
02                                                               set_rejected_slot
1111111111111111111111111111111111111111111111111111111111111111 slot
01                                                               reason removed
000000006553f200                                                 rejected_at
01                                                               tag_signature_key present
20 4444444444444444444444444444444444444444444444444444444444444444 tag_signature_key
```

A roster with no devices, no rejections and an empty account entry is its `leaf_tag_key` followed by `0000000000`.

## Migration

This is the first version. A breaking change gets a new component id and document.
