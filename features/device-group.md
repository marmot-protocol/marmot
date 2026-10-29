# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how clients keep it out of
sight, and how the account's devices notice a new sign-in. Linking, the messages devices exchange in the group, private
KeyPackages, and removal are not specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule.
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).
- Foundation: [../foundation/key-packages.md](../foundation/key-packages.md), whose publications are the evidence of a
  new sign-in ([New sign-ins](#new-sign-ins)).

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

## New sign-ins

Each device publishes its KeyPackages into a slot of its own
([../foundation/key-packages.md](../foundation/key-packages.md), "Devices and publication slots"), so a slot that none
of the account's devices accounts for is the account signed in somewhere new. That is how linking starts, and it is
also what someone holding the account's signing key does. Only the user can tell the two apart, so a device asks and
never decides. These rules apply to every device whose client supports `0x800e`, whether or not its account has a
device group yet.

### Evidence

A device checks for sign-ins by reading its account's KeyPackage publications as an inviter reads them
([../foundation/key-packages.md](../foundation/key-packages.md), "Selection and lifecycle"), under the transport
binding's fetch, replacement and deletion rules. A slot counts only if its current publication is a valid, fresh
KeyPackage of the account. Nothing else raises a sign-in: not a publication that fails validation, not a `client` tag,
and not a Welcome on its own.

A check is complete when every relay it read from answered in full: none failed or timed out, and none cut its answer
off at a limit that could hide a publication.

A slot that counts is an unrecognized sign-in unless it is:

- the device's own slot;
- the slot of a device in the roster of its trusted device group ([Trust](#trust));
- rejected: a rejected slot in that roster or among the rejections the device keeps itself ([Answers](#answers)), or a
  slot whose current KeyPackage is rejected there
  ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State").

A device with no device group has no roster, so it recognizes only its own slot and its own rejections.

A Welcome that names a KeyPackage of the account that this device did not publish
([../protocol-core/joining.md](../protocol-core/joining.md), "Delivery") is a reason to look. The device SHOULD fetch
the KeyPackage it names (on the Nostr binding, the KeyPackage event in the Welcome rumor's `e` tag) and classify that
KeyPackage's slot as above. A fetch that fails, or a KeyPackage that is not valid and fresh, raises nothing: anyone can
send a Welcome naming any KeyPackage.

A device SHOULD check when its client starts, so that opening Marmot on a device already signed in is enough to see a
new sign-in, and periodically while it runs. It MAY also check when a new publication of its account reaches it, for
example on a live subscription; the check's read is the evidence, not the publication that prompted it.

### Already signed in, or new

Nothing published says which of two devices signed in first. A slot's only public time is its latest publication, and
whoever holds the account's signing key chooses that time.

- Every unrecognized slot that a device's first check finds belongs to a device that was signed in before it. The first
  check is the first one that reads from any relay after the device signs in, or after its client gains these rules.
  The device tells its user that the account is already signed in elsewhere, with when that slot last published, and
  asks whether they still have that device.
- Every unrecognized slot it finds after its first check is a new sign-in, and the device asks its user whether it was
  them.
- A device MUST NOT use a publication's time to decide which of the two a slot is. When a sign-in appeared and when it
  last published are for display only.

A slot the first check missed, for example because a relay did not answer, is a new sign-in when a later check finds
it. That errs toward asking.

### Answers

A device keeps each unrecognized sign-in listed for its user, with the `client` tag of its publication if it has one,
when it appeared, and when it last published, until the user links or rejects it. Like the roster, the list is shown
only to the account's own user. The answers are:

- **Link:** starts linking that slot's device, which is not specified yet.
- **Not now:** the sign-in stays listed, without asking again. Nothing is written to the roster.
- **This wasn't me:** the device rejects the sign-in. In its trusted device group, it commits one roster update that
  sets a `not_me` rejected slot for the slot and a rejected KeyPackage for the KeyPackage it found there
  ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Update"). It keeps the rejection
  until the roster records it, and commits again if the Commit fails or branch selection drops it.

A device MUST NOT record as rejected a KeyPackage it made itself or that the roster announces for a device, even when
it finds that KeyPackage in a rejected slot. Whoever holds the account's signing key can copy a published KeyPackage
into a new slot. A rejection that conflicts with the roster, such as one for a slot another device linked meanwhile, is
not specified yet. What else a rejection does, such as warning the user and removing the slot's leaves from chats, is
not specified yet.

A device with no device group keeps its rejections itself and never asks about those slots or KeyPackages again. When
it creates a device group, the founding roster carries them. When it joins one, it commits them once it trusts that
group. Either way it leaves out a slot the roster holds as a device, such as the one just linked. After that, the roster
is the only record.

### Any one device's answer

A link or a rejection is written to the roster, so one device's answer reaches all of them. A device that finds the
slot of a sign-in it lists among the roster's devices or rejected slots stops asking about it: the user answered on
another device. It MAY keep telling its user so, and which device linked it, until the user dismisses it. Not now is
each device's own and is not shared.

### A sign-in that goes away

When a complete check finds that the slot of a listed sign-in no longer holds a valid, fresh KeyPackage, for example
because a deletion covers it, the device keeps the sign-in listed and marks it as no longer signed in. It can no longer
be linked, but it can still be rejected. Otherwise someone holding the account's signing key could publish, wait for the
user to be asked, and delete the publication before the user saw it. A device decides that a slot is empty only from a
complete check, never from one that failed.

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
  control. Requiring `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
- A new sign-in is only ever a question. Holding the account's signing key lets anyone publish into a new slot, but a
  sign-in never links itself: only a link the user confirms adds a device.
- A device that gains these rules while someone holding the account's signing key is already signed in finds that
  sign-in on its first check, and asks about it as a device that was there before, not as a new sign-in. The user still
  sees it listed.
- Someone holding the account's signing key can publish into many new slots, and each is a sign-in to answer.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
