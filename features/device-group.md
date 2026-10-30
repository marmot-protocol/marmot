# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how a device is linked
into it, how clients keep it out of sight, and how the account's devices notice a new sign-in. The messages devices
exchange in the group, private KeyPackages, and removal are not specified yet.

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
- Foundation: [../foundation/key-packages.md](../foundation/key-packages.md), whose publications are the evidence of a
  new sign-in ([New sign-ins](#new-sign-ins)).

## What a device group is

A device group is a group whose GroupContext `app_components` required list contains `0x800e`. Its members are the
devices of one account and no others ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
"Requirement").

An account has no device group while it has one device. A device that trusts no device group creates one when it
approves a link ("Creating the device group").

The marker never makes a group trusted. Anyone holding the account's signing key can create a group that requires
`0x800e` and send a Welcome for it to the account. A device acts on a group as its device group only under the trust
rule below.

## Creating the device group

The device that approves a link creates the device group if it trusts none yet ("Trust"), and adds the newly linked
device in the founding Add:

- The founding state, the group's state at epoch 0, requires `0x800e` and carries a roster that lists only the creating
  device, with the rejections it already holds ("Answers"), which never name the linked device's slot ("Before
  answering"). The founding Add sets the linked device's roster entry, as every later Add sets the entry of the device
  it adds. The creating device's entry has the "add to all my chats" and "bring chat history" settings on, as a new
  device's are unless its user turns them off ("Approving").
- The group runs under the ordinary group rules. The creating device's account is its only admin: the creator passes
  no other initial admin. Whether the founding state requires `0x800d` follows the ordinary creation rule
  ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)).
- The founding Add contains exactly one KeyPackage: the one the link confirmed, identified by its `KeyPackageRef`. A
  client MUST NOT found a device group with any other KeyPackage, and MUST NOT select one from the account's
  publications. This is narrower than the founding exemption in
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) ("Sender rules"), which lets a
  creator add its own account's published KeyPackages to a new group. A device group never relies on that exemption.

A Commit that adds a device to the device group or removes one, the founding Add included, also writes that device's
roster entry, so each change of membership and its record are one decision. Such a Commit carries an AppDataUpdate, so
it is `privileged` in branch selection ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate
branches").

These are sender rules. A receiver cannot tell where a KeyPackage came from, so it does not reject a Commit or a
Welcome for breaking them.

## Trust

A device treats a group as its device group only if:

- it created the group itself, as above; or
- it joined the group through the Welcome a confirmed link named: into the group the link named, from the leaf whose
  signature key the link named, for the KeyPackage the link confirmed ([device-pairing.md](./device-pairing.md), "New
  device", step 5), and the group requires `0x800e`.

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

An existing device answers a pairing request only if it is not running a session as a new device itself or keeping a
link that waits for its Welcome ("Joining"), and only if it would link the KeyPackage the request names
([device-pairing.md](./device-pairing.md), "Existing device", step 2). It answers whether it trusts a device group or
has none yet. It would not link the KeyPackage when:

- the KeyPackage's slot is already a device in its roster, the roster rejects that slot or that KeyPackage, or the
  device rejected that slot itself ("Answers");
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

The new device accepts only a Welcome whose `GroupInfo` that key signs ("Joining"). So that key MUST still be the
signature key of the device's own leaf in the epoch the Welcome joins: the device does not change it there until the
Commit that adds the new device, founding Add included, and that Commit's UpdatePath keeps it.

Once the link is confirmed, the device adds the new device:

- to the device group it trusts, by one Commit that adds exactly the confirmed KeyPackage and sets the new device's
  roster entry; or
- with no device group, by creating it under the group id its Confirm named ("Creating the device group").

The new device's entry carries the label and settings the user chose, `linked_at`, `linked_by` set to the approving
device's slot, and `announced_key_package` set to the confirmed `KeyPackageRef`. It carries no `tag_signature_key`: the
new device sets that itself ("Matching leaves to devices"). That Commit, or the founding Add, is the approval. Its
Welcome is sent as for any other Add.

The approving device treats the link as made once the new device's first Commit in the device group, which sets the
`tag_signature_key` in its roster entry ("Matching leaves to devices"), is on the selected branch of its state for the
group, and it holds no unprocessed input for the group. Neither the approving Commit's publication nor its Welcome's
delivery shows that the new device joined; only a Commit from the new device's own leaf does. Once made, a link stays
made. Until then, anything that acts on the new device as a member of the account waits, and the link can still fail
("A link that is not taken up").

A device adds a device to its device group only under a confirmed link. A Commit it makes in the device group that adds
a member, the founding Add included, MUST add exactly one, by value, and MUST set that device's roster entry in the
same Commit, for a slot the roster does not list yet, with `announced_key_package` naming the added KeyPackage. That
Commit is a same-account Add with the roster update, which the account commits as the group's only admin
([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md), "Authorization"); it is never a
same-account Commit, whose shape cannot carry the roster update. A device never adds a KeyPackage there that no
confirmed link named, by an invite or otherwise, and so never re-invites a member whose founding Welcome could not be
delivered with a fresh KeyPackage ([../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md),
"Publish obligation"). It never commits an Add proposal by reference there.

A device that cannot commit the link at once, because the device group has a Commit still settling, MAY try again, but
not once the new device has stopped waiting for its Welcome ("Joining"). It counts that wait from when the new device's
Confirm arrived. A Confirm delayed on its way can still lead to an Add the new device refuses; that link is then not
taken up ("A link that is not taken up"). It does not hold the link for later.

Approval by any one device of the account is enough. Another device that showed the same request stops offering Link
once the new device's entry is in its roster, and shows the labels of the new device and of the device that added it.

### Joining

By the time it sends its Confirm, the new device has recorded the link: the pairing session's id, the confirmed
`KeyPackageRef`, the group id, the signature key of the sender's leaf, and when its wait ends. It keeps that record
across restarts until the link ends, so that after a restart has erased the session's secrets it can still check a
Welcome and act on a Cancel. It then waits for a Welcome into that group from that leaf for that KeyPackage, the one
whose `KeyPackageRef` the Welcome's secrets for this device name. It joins only through that Welcome and only if the
group requires `0x800e`, and on joining records the group as its device group ("Trust"). While it waits, the group id is
reserved: the device joins no other Welcome into it, whether or not that group requires `0x800e`. The confirmed
KeyPackage is reserved too: the device joins no other Welcome that adds it, into any group, such as an invite to a chat
built from its publication, so no other join uses it up. A Welcome it refuses leaves the KeyPackage and the group id for
the real one, so a forged Welcome that arrives first does not make the link fail.

A new device keeps at most one link, and starts each pairing session with a KeyPackage that no earlier link of its own
confirmed, so a Welcome sent under an earlier link never matches a later one. The link ends, and the device accepts no
Welcome under it, once:

- it joins through the link's Welcome;
- its wait ends, 600 seconds after it sent its Confirm;
- a Cancel for the link's session arrives, whether or not the device still holds that session
  ([device-pairing.md](./device-pairing.md), "Every session"); or
- it confirms a newer link, which replaces this one. Starting a new pairing session does not end the link; confirming
  one does.

This is the only limit on how long a new device waits for its Welcome. It decides before joining. A Cancel after it has
joined changes nothing: it keeps its device group and its leaf there. Once the link has ended, a Welcome into its group
is one no link expects, refused if the group requires `0x800e`, and linking again starts a new pairing session. A device
that has a device group does not run a pairing session as a new device: joining a second device group, which merging
two device groups would need, is not specified yet.

### A link that is not taken up

The approving device, the one the new device's entry names in `linked_by`, waits for the new device's first Commit until
3600 seconds after the `linked_at` it wrote in that entry, so the deadline survives its restarts. That leaves the new
device time to commit after the holds that can delay a device that has joined, such as a Commit still settling in the
device group or one of its own still unconfirmed, and after a short suspension right after it joined. The new device
makes that Commit as soon as it can once it has joined: this deadline, not the general post-join guidance
([../protocol-core/joining.md](../protocol-core/joining.md), "Receiving flow"), bounds it. Until the deadline the slot
is a device in the roster, so a new request from it is not answered ("Before answering").

If the link is not made by then, the approving device first processes the input it holds for the group. If the new
device's first Commit is still not on the selected branch after that, the link has failed. Only the approving device
acts on that: it makes one Commit that removes the new device's leaf and, with `remove_device`, its roster entry
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Update"), and stops delivering the
link's Welcome. The slot is then a sign-in again ("Any one device's answer"), and the user can link it again. If branch
selection keeps the new device's first Commit and drops that removal, the link is made after all.

A device whose leaf a Commit removes from its device group, whenever that Commit reaches it, no longer has a device
group. It stops trusting the group and MUST discard the active state of its copy, which a removed member may do
([../protocol-core/member-departure.md](../protocol-core/member-departure.md), "Realizing removal"); it MAY keep the
group's history and a removal tombstone. A later link's Welcome into the same group id is then a first join
([../protocol-core/joining.md](../protocol-core/joining.md), "Receiving flow"), which a retained copy would make it
refuse. If its first Commit there was never on the selected branch, it was not linked: it tells its user that linking
failed, and links again only through a new pairing session.

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

- **Link:** starts linking that slot's device ([Linking a device](#linking-a-device)).
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
it leaves out, and forgets, a rejection of a slot the roster holds as a device, and keeps the others as above.

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
- A device that joins the device group sets the `tag_signature_key` in its own roster entry with its first Commit there,
  its post-join self-update ([../protocol-core/joining.md](../protocol-core/joining.md), receiving flow, step 14), which
  it makes as soon as it can once it has joined. The device that approved its link takes that Commit as the sign that it
  joined, and removes it if it has not made it in time ("A link that is not taken up"). That Commit also replaces its
  leaf in the device group with one tagged under that key
  ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags"). Until then its leaf
  there is unclaimed, like any untagged leaf. A group where it made its post-join self-update before then gets a tagged
  leaf later.

What the devices do with what they find (adding a sibling to a group it is missing from, removing a removed device's
leaves, warning about a leaf no device claims) is not specified yet.

## Security considerations

- Every device in the device group is the same account, and that account is the group's only admin, so any device can
  add or remove another and edit any roster entry. A stolen linked device can do the same until it is removed.
- The trust rule is what keeps someone holding the account's signing key from pulling a device into a device group they
  control. They can read the group id in the existing device's Confirm, but cannot sign as the leaf it names. Requiring
  `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
- Between the existing device's Confirm and the new device's own, neither the group id nor the KeyPackage is reserved
  yet. A Welcome in that window into a group that does not require `0x800e`, under that id or adding the KeyPackage,
  joins as an ordinary group, and the link then fails because the id is taken or the KeyPackage used up. A Welcome into
  a group that requires `0x800e` is still refused, since no link names it yet, and uses up neither. This is denial of
  service only, like a forged Cancel ([device-pairing.md](./device-pairing.md), "Security considerations").
- A device that trusts no device group cannot see one that another device of the account already has, such as one linked
  from another sign-in. When it approves a link it founds a second device group. Merging two device groups is not
  specified yet ("Joining").
- Holding the account's signing key never authenticates a device. A device enters the device group only under a link
  whose code both users compared ([device-pairing.md](./device-pairing.md), "Threat model"); a KeyPackage published
  under the account is not enough.
- A new sign-in is only ever a question. Holding the account's signing key lets anyone publish into a new slot, but a
  sign-in never links itself: only a link the user confirms adds a device.
- A device that gains these rules while someone holding the account's signing key is already signed in finds that
  sign-in on its first check, and asks about it as a device that was there before, not as a new sign-in. The user still
  sees it listed.
- Someone holding the account's signing key can publish into many new slots, and each is a sign-in to answer.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
