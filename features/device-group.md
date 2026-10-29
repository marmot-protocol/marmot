# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how a device is linked
into it, and how clients keep it out of sight. The messages devices exchange in the group, private KeyPackages, and
removal are not specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule.
- Feature: [device-pairing.md](./device-pairing.md), the exchange that authenticates a new device before it is
  linked.
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).

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
- it joined the group through the Welcome a confirmed link named: into the group the link named, from the leaf whose
  signature key the link named ([device-pairing.md](./device-pairing.md), "New device", step 5).

A device MUST NOT join a group that requires `0x800e` through any other Welcome, and decides that before it joins, so
a refused Welcome uses up neither the KeyPackage nor the group id ("Joining"). The group id alone proves nothing:
anyone holding the account's signing key can read it in the existing device's Confirm and found a group under it.

A device records which group it trusts as its device group when it creates or joins it, and does not infer it later
from group state.

## Linking a device

A device is linked through [device pairing](./device-pairing.md), which ends in a confirmed link: the new device's exact
`KeyPackageRef`, the id of the group the existing device adds it to, and the signature key of the existing device's
leaf in that group. This section covers what each device does around that exchange.

### Before answering

An existing device answers a pairing request only if it is not running a session as a new device itself, and only if it
would link the KeyPackage the request names ([device-pairing.md](./device-pairing.md), "Existing device", step 2). It
answers whether it trusts a device group or has none yet. It would not link the KeyPackage when:

- the KeyPackage's slot is already a device in its roster, or the roster rejects that slot or that KeyPackage;
- the KeyPackage does not support everything its device group requires, or, when it has no device group, everything
  the device group it would create will require;
- its roster already lists `max_leaves_per_account` devices, the most a roster holds
  ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Validation").

A device that would not link the KeyPackage does not offer Link, and tells its user why: what the new device's client
lacks, or that the account has as many devices as it can, so the user removes one first. In those two cases it sends
Cancel `cannot_link`, so the new device stops waiting. When the slot or KeyPackage is rejected, it MAY send it.

### Approving

On the existing device, the user who confirms the link also names the new device and sets its "add to all my chats"
and "bring chat history" settings ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
"State"). Both settings are on unless the user turns them off. The device's Confirm names:

- the device group it trusts, if it has one, with the signature key of its own leaf there;
- otherwise a fresh group id of 16 random bytes, for the device group it will create, with the signature key it will
  create the group with.

Once the link is confirmed, the device adds the new device:

- to the device group it trusts, by one Commit that adds exactly the confirmed KeyPackage and sets the new device's
  roster entry; or
- with no device group, by creating it under the group id its Confirm named ("Creating the device group").

The new device's entry carries the label and settings the user chose, `linked_at`, `linked_by` set to the approving
device's slot, and `announced_key_package` set to the confirmed `KeyPackageRef`. It carries no `tag_signature_key`: the
new device sets that itself ("Matching leaves to devices"). That Commit, or the founding Add, is the approval. Its Welcome is sent as for any other Add.

The approving device treats the link as settled once the approving Commit's publication is confirmed, its state for the
device group is at or past that Commit's epoch with the Commit on the selected branch, and it holds no unprocessed input
for the group. Anything that acts on the new device as a member of the account waits until then.

A device adds a device to its device group only under a confirmed link. A Commit it makes in the device group that adds
a member MUST add exactly one, by value, and MUST set that device's roster entry in the same Commit, for a slot the
roster does not list yet, with `announced_key_package` naming the added KeyPackage. So it never adds its own account's
KeyPackages there by an invite or a same-account Add
([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)), and never commits an Add
proposal by reference there.

A device that cannot commit the link at once, because the device group has a Commit still settling, MAY try again, but
not once the new device has stopped waiting for its Welcome ("Joining"). It does not hold the link for later, so it
never adds a device that will not join.

Approval by any one device of the account is enough. Another device that showed the same request stops offering Link
once the new device's entry is in its roster, and shows the labels of the new device and of the device that added it.

### Joining

By the time it sends its Confirm, the new device has recorded what the link expects: the group id, the signature key
of the sender's leaf, and when the wait ends. It then waits for a Welcome into that group from that leaf, joins only
through it, and on joining records the group as its device group ("Trust"). While it waits, the group id is reserved:
the device joins no other Welcome into it, whether or not that group requires `0x800e`. A Welcome it refuses leaves the
KeyPackage and the group id for the real one, so a forged Welcome that arrives first does not make the link fail.

It stops waiting, and accepts no Welcome under the link, once:

- 600 seconds have passed since it sent its Confirm; or
- a Cancel withdraws the link ([device-pairing.md](./device-pairing.md), "Every session").

It decides before joining. After that, a Welcome into the group is one no link expects, refused if the group requires
`0x800e`, and linking again starts a new pairing session.

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

## Security considerations

- Every device in the device group is the same account, and that account is the group's only admin, so any device can
  add or remove another and edit any roster entry. A stolen linked device can do the same until it is removed.
- The trust rule is what keeps someone holding the account's signing key from pulling a device into a device group they
  control. They can read the group id in the existing device's Confirm, but cannot sign as the leaf it names. Requiring
  `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
- Between the existing device's Confirm and the new device's own, the group id is readable but not yet reserved. A
  Welcome under that id in that window, into a group that does not require `0x800e`, joins as an ordinary group, and
  the link then fails because the id is taken. This is denial of service only, like a forged Cancel
  ([device-pairing.md](./device-pairing.md), "Security considerations").
- Holding the account's signing key never authenticates a device. A device enters the device group only under a link
  whose code both users compared ([device-pairing.md](./device-pairing.md), "Threat model"); a KeyPackage published
  under the account is not enough.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
