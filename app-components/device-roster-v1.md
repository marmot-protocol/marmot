# marmot.account.device-roster.v1

Status: draft.

`marmot.account.device-roster.v1` is the roster of an account's device group: the account's linked devices, the leaf
each device holds in each group it joined, the sign-ins and KeyPackages its devices rejected, and account-wide fields
reserved for account sync. A group that requires
this component is a device group. [../features/device-group.md](../features/device-group.md) describes the device group,
when it is created, and when a device trusts a group as its own. Requiring this component never makes a group trusted.

The non-normative direction this component serves is described in [../ideas/multi-device.md](../ideas/multi-device.md)
and [../ideas/account-sync.md](../ideas/account-sync.md).

## Registry

- Component id: `0x800e`
- Name: `marmot.account.device-roster.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: required from creation in a device group ("Requirement" below); never required in any other
  group

## State

```text
opaque SlotId[32];
opaque KeyPackageRefV1<1..64>;
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
  opaque client<0..64>;
  opaque platform<0..64>;
  uint64 linked_at;
  optional<SlotId> linked_by;
  uint8 settings;
  DeviceStatusV1 status;
  optional<KeyPackageRefV1> announced_key_package;
  optional<ReservedKeyV1> history_key;
} DeviceEntryV1;

struct {
  SlotId slot;
  opaque group_id<1..255>;
} LeafMapKeyV1;

struct {
  LeafMapKeyV1 key;
  opaque leaf_signature_key<1..255>;
} LeafMapEntryV1;

enum {
  not_me(0),
  removed(1),
  (255)
} RejectionReasonV1;

struct {
  SlotId slot;
  RejectionReasonV1 reason;
  uint64 rejected_at;
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
  DeviceEntryV1 devices<V>;
  LeafMapEntryV1 leaf_map<V>;
  RejectedSlotV1 rejected_slots<V>;
  RejectedKeyPackageV1 rejected_key_packages<V>;
  AccountEntryV1 account;
} DeviceRosterV1;
```

The structures use the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)). `optional<T>` is one presence byte,
`0x00` for absent or `0x01` followed by `T`, as in MLS; any other presence byte is invalid. Enumerations are one byte,
and a value the enumeration does not list is invalid.

Each device the account has linked has one `DeviceEntryV1`:

- `slot` is the device's KeyPackage publication slot id ([../foundation/key-packages.md](../foundation/key-packages.md),
  "Devices and publication slots"). On the Nostr binding it is the 32 bytes of the KeyPackage event's `d` value
  ([../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"). The slot identifies the device in the
  roster.
- `label` is the name the user gave the device, `client` its client name, and `platform` its platform. Each is UTF-8,
  compared and stored as bytes and never normalized; a decoder rejects bytes that are not UTF-8.
- `linked_at` is when the device was linked, in seconds since the Unix epoch, as the linking device wrote it.
  `linked_by` is the slot of the device that linked it, absent for the device that created the group.
- `settings` holds one flag per bit: bit 0 (`0x01`) "add to all my chats", bit 1 (`0x02`) "bring chat history", and
  bit 2 (`0x04`) "keep while inactive". The other bits MUST be zero.
- `status` is `active`, `inactive` (the device's siblings marked it inactive), or `leaving` (the device recorded that it
  is signing out).
- `announced_key_package` is the `KeyPackageRef` ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420), section 5.2) of
  the KeyPackage the device announced for its slot, if it announced one.
- `history_key` is reserved for account sync and has no meaning in this version.

Each group a device has joined has one `LeafMapEntryV1`, keyed by the device's slot and the group's MLS group id. The
group id is the MLS group id, not a transport routing id. `leaf_signature_key` is the signature key of the device's
leaf in that group. It identifies the leaf rather than its position, because positions are reused after a removal, and
the device sets the entry again when it rotates that key. A device that joins a group writes one entry, and one that
leaves a group removes its entry.

`RejectedSlotV1` records a slot whose sign-in the user rejected (`not_me`) or whose device was removed (`removed`).
`RejectedKeyPackageV1` records a rejected KeyPackage by its `KeyPackageRef`, with the slot it appeared in. `rejected_at`
is when the rejection was recorded, as the recording device wrote it.

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
- `leaf_map` is sorted by `slot`, then by the content bytes of `group_id` in lexicographic order, and is unique by the
  pair (`slot`, `group_id`). This overrides the default order;
- `devices` holds at most `max_leaves_per_account` entries, the constant of
  [account-devices-v1.md](./account-devices-v1.md) ("Leaf limit");
- no slot appears both in `devices` and in `rejected_slots`;
- the slot of every `leaf_map` entry is the slot of an entry in `devices`, or of an entry in `rejected_slots` whose
  reason is `removed`.

A device can appear once only, so a slot that is rejected is never also a linked device.

A removed device's leaf-map entries may outlive its device entry. Its siblings remove its leaves from the groups they
are members of, but a group none of them is in keeps the removed device's leaf until an admin there removes it. While
the slot is recorded as `removed`, its entries still say which groups those are. A Commit that removes a device entry
without recording its slot as `removed`, or that removes a `removed` slot's record, removes that slot's leaf-map
entries too, or the resulting roster is invalid.

## Update

The roster's update is a diff, not a full replacement state. This is the explicit exception that
[README.md](./README.md) ("GroupContext Update Processing") allows: an AppDataUpdate sets or removes individual entries,
and the members apply it to the candidate parent's roster.

```text
enum {
  set_device(0),
  remove_device(1),
  set_leaf_map_entry(2),
  remove_leaf_map_entry(3),
  set_rejected_slot(4),
  remove_rejected_slot(5),
  set_rejected_key_package(6),
  remove_rejected_key_package(7),
  set_account(8),
  (255)
} RosterOperationType;

struct {
  RosterOperationType type;
  select (RosterOperationV1.type) {
    case set_device:                  DeviceEntryV1 device;
    case remove_device:               SlotId slot;
    case set_leaf_map_entry:          LeafMapEntryV1 leaf_map_entry;
    case remove_leaf_map_entry:       LeafMapKeyV1 key;
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

Each operation names one entry. A device entry and a rejected slot are keyed by their slot, a leaf-map entry by its
`LeafMapKeyV1`, a rejected KeyPackage by its `key_package_ref`, and the account entry is a single entry with no key.
An update is valid only when:

- it decodes canonically and holds at least one operation;
- it holds at most one operation per entry;
- its operations are sorted by entry: device entries first, then leaf-map entries, then rejected slots, then rejected
  KeyPackages, then the account entry. Within each kind they follow that kind's order in `DeviceRosterV1`
  ("Validation" above).

The resulting roster is the candidate parent's roster with every operation applied:

- `set_device`, `set_leaf_map_entry`, `set_rejected_slot` and `set_rejected_key_package` insert the entry, or replace
  the entry with the same key;
- `remove_device`, `remove_leaf_map_entry`, `remove_rejected_slot` and `remove_rejected_key_package` remove the entry
  with that key. Removing an
  entry the parent's roster does not hold makes the update invalid;
- `set_account` replaces the account entry.

Because no two operations name the same entry, the result does not depend on the order in which they are applied. The
resulting roster MUST be valid ("Validation" above); otherwise the update, and the Commit that carries it, is invalid.

An update replaces whole the entries it names. A device that changes one field of an entry, such as its label, sends
the whole entry with that field changed. Other entries are untouched.

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

- Any device of the account can rewrite any entry, including another device's settings and the rejections. A stolen
  linked device can do the same until it is removed. The roster records decisions; it does not protect them from a
  linked device.
- Only the account's own devices are members of a device group, so the roster, its labels, platforms and leaf map are
  never visible to other accounts. A client MUST NOT copy them into any other group or show another account's roster.
- The roster grows with the number of devices and, through the leaf map, with the number of groups each device has
  joined. A Welcome into the device group carries the whole roster. An update carries every entry it names in full,
  so joining a group costs one leaf-map entry.
- Holding the account's signing key does not by itself let anyone into the device group or let anyone write the
  roster. Only a member of the device group can write it, and a device becomes a member only through a link the user
  confirmed ([../features/device-group.md](../features/device-group.md), "Trust").

## Test vectors

A roster with one device in slot `0x11` repeated 32 times, labelled `Phone`, client `wn`, no platform, linked at
`0x6553f100`, with no linker, settings `0x05` ("add to all my chats" and "keep while inactive"), status `active`, no
announced KeyPackage and no history key, and with no leaf-map entries, no rejections and an empty account entry:

```text
37                                                               devices<V>, 55 bytes
1111111111111111111111111111111111111111111111111111111111111111 slot
0550686f6e65                                                     label "Phone"
02776e                                                           client "wn"
00                                                               platform ""
000000006553f100                                                 linked_at
00                                                               linked_by absent
05                                                               settings
00                                                               status active
00                                                               announced_key_package absent
00                                                               history_key absent
00                                                               leaf_map<V>
00                                                               rejected_slots<V>
00                                                               rejected_key_packages<V>
00                                                               backup_writer absent
00                                                               recovery_public_key absent
```

An update that removes that device:

```text
21                                                               operations<V>, 33 bytes
01                                                               remove_device
1111111111111111111111111111111111111111111111111111111111111111 slot
```

An update that records that device's leaf in the group with MLS group id `0x01` repeated 16 times, with signature key
`0x02` repeated 32 times:

```text
4053                                                             operations<V>, 83 bytes
02                                                               set_leaf_map_entry
1111111111111111111111111111111111111111111111111111111111111111 slot
10 01010101010101010101010101010101                              group_id
20 0202020202020202020202020202020202020202020202020202020202020202 leaf_signature_key
```

The empty roster is `000000000000`.

## Migration

This is the first version. A breaking change gets a new component id and document.
