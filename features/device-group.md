# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how clients keep it out of
sight, and how each device shows its siblings to its user. Linking, the other messages devices exchange in the group,
private KeyPackages, and removal are not specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule.
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).
- Marmot app event: kind `457` (heartbeat), sent only in a device group ([Heartbeats](#heartbeats)) and registered in
  [../foundation/registries.md](../foundation/registries.md).

## What a device group is

A device group is a group whose GroupContext `app_components` required list contains `0x800e`. Its members are the
devices of one account and no others ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
"Requirement").

An account has no device group while it has one device. The device group is created when a second device is linked.

The marker never makes a group trusted. Anyone holding the account's signing key can create a group that requires
`0x800e` and send a Welcome for it to the account. A device acts on a group as its device group only under the trust
rule below.

## Creating the device group

The device that approves a link creates the device group, if its account has none, and adds the newly linked device in
the founding Add:

- The founding state requires `0x800e` and carries a roster with an entry for the creating device and one for the
  linked device.
- The group runs under the ordinary group rules. The creating device's account is its only admin: the creator passes
  no other initial admin. Whether the founding state requires `0x800d` follows the ordinary creation rule
  ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)).
- The founding Add contains exactly one KeyPackage: the one the link confirmed, identified by its `KeyPackageRef`. A
  client MUST NOT found a device group with any other KeyPackage, and MUST NOT select one from the account's
  publications. This is narrower than the founding exemption in
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) ("Sender rules"), which lets a
  creator add its own account's published KeyPackages to a new group. A device group never relies on that exemption.

A Commit that adds a device to the device group or removes one also writes that device's roster entry, so each change of
membership and its record are one decision. Such a Commit carries an AppDataUpdate, so it is `privileged` in branch
selection ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate branches").

These are sender rules. A receiver cannot tell where a KeyPackage came from, so it does not reject a Commit or a
Welcome for breaking them.

## Trust

A device treats a group as its device group only if:

- it created the group itself, as above; or
- it joined the group through a Welcome for the group that a confirmed link named.

A device MUST NOT join a group that requires `0x800e` through any other Welcome, and decides that before it joins.

A device records which group it trusts as its device group when it creates or joins it, and does not infer it later
from group state.

## Keeping it out of sight

A device group is not a chat:

- Clients MUST NOT show a device group, or any group that requires `0x800e`, in chat lists, chat counts, unread counts,
  or notifications, and MUST NOT offer it as a destination for messages.
- A client shows the roster of its own device group only to its own user, for example on a Devices screen. It never
  shows another account's devices.

## Matching leaves to devices

Every leaf of the account in a group carries the same credential identity, so the group alone does not say which leaf
belongs to which device. Each linked device tags its leaves instead
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md)), and a device that holds the roster reads
those tags in the groups it is in. Nothing about other groups is written to the device group, so joining a group,
leaving one, or replacing a leaf there never commits to it.

- Each device makes its own tag signature key pair and keeps the private key to itself.
- The device that creates the device group chooses the roster's `leaf_tag_key`, and its founding entry carries its
  `tag_signature_key` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)).
- A device that joins the device group sets the `tag_signature_key` in its own roster entry with its first Commit
  there, its post-join self-update ([../protocol-core/joining.md](../protocol-core/joining.md), receiving flow, step
  14), which it SHOULD make as soon as it has joined. That Commit also replaces its leaf in the device group with one
  tagged under that key ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags").
  Until then its leaf there is unclaimed, like any untagged leaf. A group where it made its post-join self-update
  before then gets a tagged leaf later.

What the devices do with what they find (adding a sibling to a group it is missing from, removing a removed device's
leaves, warning about a leaf no device claims) is not specified yet.

## Devices

A device shows its user the account's devices from its device group's roster, for example on a Devices screen. It never
shows them to anyone else ([Keeping it out of sight](#keeping-it-out-of-sight)).

### Labels, clients and platforms

A device entry's `label`, `client` and `platform`
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State") are what a user reads to tell
the devices apart.

- Any device MAY change any device entry's `label`, its own included. A rename is a roster update that sets that entry
  with only `label` changed.
- A device SHOULD keep its own entry's `client` and `platform` current. `client` is the client name it puts in its
  KeyPackages' `client` tag ([../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"); `platform`
  is a short name for the platform it runs on, such as `iOS`. Either is empty when the device has none. It SHOULD write
  them in a roster update it is already making to its own entry, rather than in one of their own. A device does not
  write another device's `client` or `platform`.
- A device SHOULD build a roster update from the roster of the state it commits to, and SHOULD NOT send one while an
  earlier Commit of its own in the device group is unresolved. An update sets whole entries, so one built from an
  older roster puts back whatever changed in that entry since.

A rename can lose a fork ([../protocol-core/convergence.md](../protocol-core/convergence.md)) to a sibling's Commit. A
device that renamed a device keeps the rename, and the label it replaced, while the Commit carrying it can still be
superseded. When a Commit of its own in the device group is superseded, it checks each such rename against the
winning roster:

- If that entry's `label` is still the label the rename replaced, it renames the device again.
- Otherwise another rename of that device won, and that one stands: the device drops its own.

Either way, a device shows its user the label its roster holds.

### Heartbeats

| Kind  | Message   | Sent by                   |
| ----- | --------- | ------------------------- |
| `457` | Heartbeat | every device in the group |

A heartbeat is a Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
sent as an MLS application message in the device group. Its content is `{"v":1}`, written without whitespace, and its
`created_at` is when it was sent. It says that the device that sent it is running.

**Sending.** While it runs, a device sends a heartbeat in the device group it trusts ([Trust](#trust)) whenever its
last heartbeat there is at least one hour old, whether it has just started or has been running for a while. It keeps
the time of its last heartbeat across restarts. It sends one only while the roster lists it and its own entry carries
its `tag_signature_key`, so that its leaf in the device group is tagged
([Matching leaves to devices](#matching-leaves-to-devices)). A heartbeat never asks for a push notification and never
wakes a sibling.

**Receiving.** A device reads heartbeats only in the device group it trusts, and ignores kind `457` in any other group.
A heartbeat counts for a sibling only when the leaf that sent it, in the tree of the epoch the device holds when it
reads it, carries a device tag that reads as that sibling's
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Reading tags"): it opens under the
roster's `leaf_tag_key`, names a slot that is a device in the roster, and verifies under that entry's
`tag_signature_key`. A heartbeat from an earlier epoch, from an unclaimed leaf, or from a leaf whose tag names a
`removed` slot counts for no device; that sibling's next heartbeat counts instead. A receiver enforces no rate: every
heartbeat that meets these rules counts.

A receiver does not read a heartbeat's content, so that a later version can add to it without older devices dropping
its heartbeats and judging its sender inactive.

**Last activity.** A device keeps, for each sibling, the time of the newest heartbeat that counted for it: the
heartbeat's `created_at`, or the time the device read it if that is earlier. A heartbeat delivered late never makes a
sibling look active later than it was, and a sender's clock never dates activity after it was read. Each device keeps
its own; nothing about it is written to the roster.

### Inactive devices

A device treats a sibling as inactive once 30 days have passed, by its own clock, since that sibling's last activity or
since the device first found that sibling in its roster, whichever is later. A device that has just joined the device
group, or a sibling that was just linked, therefore gets 30 days before it shows as inactive. A device never treats
itself as inactive. A device SHOULD show its user which siblings are inactive.

A device that comes back after a long absence sees every sibling as inactive until the heartbeats sent meanwhile
arrive. It MUST NOT record a sibling as inactive in the roster on that view alone. Recording the roster's `inactive`
status, and removing a device after a longer absence, are not specified yet.

## Security considerations

- Every device in the device group is the same account, and that account is the group's only admin, so any device can
  add or remove another and edit any roster entry. A stolen linked device can do the same until it is removed.
- The trust rule is what keeps someone holding the account's signing key from pulling a device into a device group they
  control. Requiring `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
