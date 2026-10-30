# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how clients keep it out of
sight, how the account's devices notice a new sign-in, and how each device shows its siblings to its user. Linking, the
other messages devices exchange in the group, private KeyPackages, and removal are not specified yet.

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

A check is complete when the device found the relays the account publishes its KeyPackages to (on the Nostr binding, its
write-capable relay set, [../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"), that set is not
empty, and it read every relay in it with no time bound, each of them ending both of its answers, the one for the
KeyPackages and the one for the deletion requests, without failing or timing out and with fewer events than the device
asked for in that query, counting every event the relay sent. When the device cannot find that set, or it is empty, the
device MAY read other relays, but no check is complete. An answer that holds as many events as the device asked for may
have more behind it, so the check is not complete, and reading further back does not make it so. A relay that cuts its
answer at a lower limit of its own looks whole, so a device SHOULD ask a relay for no more events than the limit it
advertises (on the Nostr binding, the `max_limit` in its NIP-11 relay information document). A read with a time bound,
such as one resumed with `since`, and what a live subscription delivers may show slots, but never complete a check. A
check that is not complete still shows what it found, but proves nothing missing.

This has two limits. An account with more KeyPackage publications or deletion requests than one answer holds never has a
complete check: its sign-ins stay listed and can be answered, but none is marked as no longer signed in. And a relay
that cuts its answer at a lower limit it does not advertise makes a check look complete when it is not: a listed sign-in
whose slot that answer left out is marked as no longer signed in, and cannot be linked, until a complete check finds it
again.

A slot that counts is an unrecognized sign-in unless it is:

- the device's own slot;
- the slot of a device in the roster of its trusted device group ([Trust](#trust));
- a rejected slot in that roster ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
  "State") or among the rejections the device keeps itself ([Answers](#answers)).

A device with no device group has no roster, so it recognizes only its own slot and its own rejected slots. A rejected
KeyPackage does not make another slot rejected: whoever holds the account's signing key can copy any published
KeyPackage into a slot the user then rejects, so a slot is rejected only by its own id.

A Welcome that names a KeyPackage of the account that this device did not publish
([../protocol-core/joining.md](../protocol-core/joining.md), "Delivery") is a reason to look. The device SHOULD fetch
the KeyPackage it names ([../transports/nostr.md](../transports/nostr.md), "Welcome delivery") and classify that
KeyPackage's slot as above, once its first check ([Already signed in, or new](#already-signed-in-or-new)) has happened;
before that, the Welcome waits for it. A fetch that fails, or a KeyPackage that is not valid and fresh, raises nothing:
anyone can send a Welcome naming any KeyPackage.

A device SHOULD check when its client starts, so that opening Marmot on a device already signed in is enough to see a
new sign-in, and periodically while it runs. It MAY also check when a new publication of its account reaches it, for
example on a live subscription; the check's read is the evidence, not the publication that prompted it.

### Already signed in, or new

Nothing published says which of two devices signed in first. A slot's only public time is its latest publication, and
whoever holds the account's signing key chooses that time.

- Every slot that a device's first check returns belongs to a device that was signed in before it, whether or not the
  slot counts then. The first check is the first read of all the account's KeyPackages with no time bound, after the
  device signs in or after its client gains these rules, that ends with at least one relay having answered. Like any
  check, it ends only when every relay in it has ended its answers, failed or timed out. It covers every slot that one
  read returns, from every relay that answered: the `d` of every KeyPackage publication in those answers, including one
  that is not fresh, not valid, or covered by a deletion request. Fetching the one KeyPackage a Welcome names, a read
  with a time bound and a live subscription are never the first check, and until the first check has happened the device
  lists no sign-in. The device keeps, across restarts, that its first check happened and the id of every slot it
  returned, so a later check is never taken for it and those slots keep their class. The first time such a slot is an
  unrecognized sign-in, at the first check or later, the device lists it: it tells its user that the account is already
  signed in elsewhere, with when that slot last published, and asks whether they still have that device.
- Every unrecognized slot that the first check did not return is a new sign-in. The first time it is one, the device
  lists it and asks its user whether it was them.
- A device MUST NOT use a publication's time, freshness included, to decide which of the two a slot is. Freshness
  decides only whether a slot counts. When a sign-in appeared and when it last published are for display only.

A slot the first check missed, for example because a relay did not answer or an answer was full, is a new sign-in when a
later check finds it. That errs toward asking.

Once a sign-in is listed, a later check that finds it again does not ask about it again: only the user's answers and the
roster change how it is listed ([Answers](#answers), [Any one device's answer](#any-one-devices-answer)).

### Answers

A device keeps each unrecognized sign-in listed for its user, with the `client` tag of its publication if it has one,
when it appeared, and when it last published, until the user links or rejects it. It keeps that list across restarts,
with each sign-in's answer and whether it is still signed in, so a restart neither drops a sign-in nor asks again about
one the user put off. Like the roster, the list is shown only to the account's own user. The answers are:

- **Link:** starts linking that slot's device, which is not specified yet.
- **Not now:** the sign-in stays listed, without asking again. Nothing is written to the roster.
- **This wasn't me:** the device rejects the sign-in. In its trusted device group, it commits a roster update that sets
  a `not_me` rejected slot for the slot ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
  "Update"). It commits that update only while the roster has no entry for the slot, neither a device nor a rejected
  slot, and never replaces an entry the roster has.

A rejection names the slot alone, never the KeyPackage the device found there: whoever holds the account's signing key
can copy a real device's KeyPackage into a slot the user then rejects. Rejected KeyPackages in the roster are for a
linked device's slot that holds a KeyPackage the device did not publish, which is not specified yet.

A device keeps its own rejections, across restarts, until the roster holds the slot as a device. While it keeps one, it
commits it again whenever the roster has no entry for the slot: when its Commit fails, and when branch selection drops
the update that recorded it, whichever device made that update.

If the roster holds the slot as a device, the user confirmed linking it, on this device or another: the device commits
nothing for the slot, forgets its rejection, and stops asking about it. If branch selection later drops that link, the
device asks about the slot again ([Any one device's answer](#any-one-devices-answer)) rather than restore an answer the
user's link overrode. What the user is then told, and what else a rejection does, such as warning the user and removing
the slot's leaves from chats, are not specified yet.

A device with no device group keeps its rejections itself and never asks about those slots again. When it creates a
device group, the founding roster carries them. When it joins one, it commits them once it trusts that group. Either way
it leaves out, and forgets, a rejection of a slot the roster holds as a device, such as the one just linked, and keeps
the others as above.

### Any one device's answer

A link or a rejection is written to the roster, so one device's answer reaches all of them. A device that finds the slot
of a sign-in it lists among the roster's devices or rejected slots stops asking about it: the user answered on another
device. It MAY keep telling its user so, and which device linked it, until the user dismisses it. That answer holds only
while the roster does: when the slot is no longer among the roster's devices or rejected slots, a device with no
rejection of its own for it lists it again as it did before, even if the user dismissed it. Not now is each device's own
and is not shared.

### A sign-in that goes away

A slot holds a KeyPackage, fresh or not, when its current publication is a valid KeyPackage of the account and no
deletion request the check found covers it. When a complete check finds that the slot of a listed sign-in no longer
holds a KeyPackage, the device keeps the sign-in listed and marks it as no longer signed in. While it is, it cannot be
linked, but it can still be rejected. Otherwise someone holding the account's signing key could publish, wait for the
user to be asked, and delete the publication before the user saw it. Freshness plays no part in whether a slot holds a
KeyPackage: a valid publication that no deletion request covers holds a KeyPackage however old it is. Freshness decides
which KeyPackage an inviter picks and whether a slot raises a sign-in, but a device that has not been opened for a while
has not signed out. When a later complete check finds that the slot holds a KeyPackage again, the sign-in is signed in
again and can be linked; any answer the user gave it stands. A check that is not complete changes neither: only a
complete check decides whether a slot holds a KeyPackage.

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
  with only `label` and `rename_id` changed. Every rename, one that clears `label` included, MUST write a `rename_id`
  of 16 bytes the device draws from a cryptographically secure random source. Any other update to an entry MUST keep
  its `rename_id`.
- A device SHOULD keep its own entry's `client` and `platform` current. `client` is the client name it puts in its
  KeyPackages' `client` tag ([../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"); `platform`
  is a short name for the platform it runs on, such as `iOS`. Either is empty when the device has none. It SHOULD write
  them in a roster update it is already making to its own entry, rather than in one of their own. A device does not
  write another device's `client` or `platform`.
- A device SHOULD build a roster update from the roster of the state it commits to, and SHOULD NOT send one while an
  earlier Commit of its own in the device group is unresolved. An update sets whole entries, so one built from an
  older roster puts back whatever changed in that entry since.

A rename can lose a fork ([../protocol-core/convergence.md](../protocol-core/convergence.md)) to a sibling's Commit.
The entry's `rename_id` tells the renaming device where its rename stands; labels and Commits do not, since two renames
can set the same label and a lost Commit can be sent again as a different Commit. From before it sends a rename's
Commit, a device keeps:

- as written, the `rename_id` the rename writes, and each one it writes when it makes the rename again;
- as replaced, the `rename_id` the entry held, absent for an entry never renamed, and every id its previous rename of
  that device kept, unless another rename had replaced that one.

It keeps them until another rename of that device stands or the device leaves the roster. Whenever no Commit of its own
in the device group is unresolved, it reads that entry's `rename_id` in the roster of the state it follows:

- One kept as written: the rename applied.
- One kept as replaced: the rename lost and nothing renamed the device since. It renames the device again with a
  fresh `rename_id`, unless the entry already shows the label it set.
- Any other: another rename won and stands, and the device drops its own.

A device MAY forget the oldest `rename_id`s it keeps for one device; a roster holding a forgotten one reads as another
rename's. Either way, a device shows its user the label its roster holds.

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
- A new sign-in is only ever a question. Holding the account's signing key lets anyone publish into a new slot, but a
  sign-in never links itself: only a link the user confirms adds a device.
- A device that gains these rules while someone holding the account's signing key is already signed in finds that
  sign-in on its first check, and asks about it as a device that was there before, not as a new sign-in. The user still
  sees it listed.
- Someone holding the account's signing key can publish into many new slots, and each is a sign-in to answer.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
