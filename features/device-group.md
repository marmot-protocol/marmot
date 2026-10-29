# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, and how clients keep it
out of sight. Linking, the messages devices exchange in the group, private KeyPackages, and removal are not specified
yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule.
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

## Security considerations

- Every device in the device group is the same account, and that account is the group's only admin, so any device can
  add or remove another and edit any roster entry. A stolen linked device can do the same until it is removed.
- The trust rule is what keeps someone holding the account's signing key from pulling a device into a device group they
  control. Requiring `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
