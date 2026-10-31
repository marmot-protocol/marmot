# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how a device is linked
into it, how clients keep it out of sight, how the account's devices notice a new sign-in, how each device announces
the KeyPackages it publishes, what a device does when its own slot holds a KeyPackage it did not make, how devices hand
each other private KeyPackages, how the Welcome for an add that uses one reaches its sibling, how the user removes a
device, and how each device shows its siblings to its user.
[account-sync.md](./account-sync.md) specifies the small-state messages devices exchange in the group. When a device
adds a sibling to a chat, the group's other messages, what a device removed from its device group does next, and
signing out through a sibling are not specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule, and whose same-account Remove takes a removed device's leaves out of
  other groups ([Removing it from chats](#removing-it-from-chats)).
- Feature: [device-pairing.md](./device-pairing.md), the exchange that authenticates a new device before it is
  linked.
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).
- Foundation: [../foundation/key-packages.md](../foundation/key-packages.md), whose publication slots each device's
  roster entry announces into, and whose publications are the evidence of a new sign-in ([New sign-ins](#new-sign-ins)).
- Marmot app events: kind `457` (heartbeat, [Heartbeats](#heartbeats)), kind `459` (private KeyPackage request), kind
  `460` (private KeyPackage hand-off, [Private KeyPackages](#private-keypackages)) and kind `461` (sibling Welcome,
  [Sibling Welcomes](#sibling-welcomes)), each sent only in a device group. Their kinds are registered in
  [../foundation/registries.md](../foundation/registries.md).

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
  device, with the rejected sign-ins it already keeps ("Answers"), which never name the linked device's slot ("Before
  answering"). The founding Add sets the linked device's roster entry, as every later Add sets the entry of the device
  it adds. The creating device's entry has the "add to all my chats" and
  "bring chat history" settings on, as a new device's are unless its user turns them off ("Approving").
- The group runs under the ordinary group rules. The creating device's account is its only admin: the creator passes
  no other initial admin. Whether the founding state requires `0x800d` follows the ordinary creation rule
  ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)).
- The founding Add contains exactly one KeyPackage: the one the link confirmed, identified by its `KeyPackageRef`. A
  client MUST NOT found a device group with any other KeyPackage, and MUST NOT select one from the account's
  publications. This is narrower than the founding exemption in
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) ("Sender rules"), which lets a
  creator add its own account's published KeyPackages to a new group. A device group never relies on that exemption.
- The creating device's entry in the founding state sets `announced_key_package` to the `KeyPackageRef` of the
  KeyPackage the creating device generated and last published to its own slot, if any, whatever the slot serves now
  ([Slot announcements](#slot-announcements)). The founding Add sets the linked device's to the KeyPackage the link
  confirmed ("Approving").

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

- the KeyPackage's slot is already a device in its roster, the roster rejects that slot, or the device rejected that
  slot itself ("Answers");
- the KeyPackage does not support everything its device group requires, or, when it has no device group, everything
  the device group it would create will require;
- its roster already lists `max_leaves_per_account` devices, the most a roster holds
  ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Validation").

A device that would not link the KeyPackage does not offer Link, and tells its user why: what the new device's client
lacks, or that the account has as many devices as it can, so the user removes one first. In those two cases it sends
Cancel `cannot_link`, so the new device stops waiting. When the slot is rejected, it MAY send it.

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
new device sets that itself ("Matching leaves to devices"). Like every new entry, it carries a fresh `rename_id`
([Labels, clients and platforms](#labels-clients-and-platforms)). That Commit, or the founding Add, is the approval.
Its Welcome is sent as for any other Add.

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

A device with no device group has no roster, so it recognizes only its own slot and its own rejected slots.

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
can copy a real device's KeyPackage into a slot the user then rejects.

A device keeps its own rejections, across restarts, until the roster holds the slot as a device. While it keeps one, it
commits it again whenever the roster has no entry for the slot: when its Commit fails, and when branch selection drops
the update that recorded it, whichever device made that update.

If the roster holds the slot as a device, the user confirmed linking it, on this device or another: the device commits
nothing for the slot, forgets its rejection, and stops asking about it. If branch selection later drops that link, the
device asks about the slot again ([Any one device's answer](#any-one-devices-answer)) rather than restore an answer the
user's link overrode. What a rejection does beyond its record, warning the user, is in [Rejections](#rejections).

A device with no device group keeps its rejections itself and never asks about those slots again. When it creates a
device group, the founding roster carries them. When it joins one, it commits them once it trusts that group. Either way
it leaves out, and forgets, a rejected sign-in whose slot the roster holds as a device, and keeps the others as above.

A client MAY let a device whose first check found sign-ins ([Already signed in, or new](#already-signed-in-or-new))
start without them, in groups it is invited to from then on. Starting that way answers Not now for every slot that first
check returned, including one that does not count then and is listed only when it counts later. It MUST NOT reject them:
one of them may be a device the user still has somewhere, which can link this one later, and a rejection would block
that link and warn the user about a device they only lost.

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
those tags in the groups it is in. No roster commit records anything about other groups, so joining a group, leaving
one, or replacing a leaf there never commits to the device group. Small-state messages
([account-sync.md](./account-sync.md)) do name other groups, by MLS group id; that document's security considerations
cover what this discloses.

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

A leaf that no device claims is not evidence of anything by itself. A device's leaves from before it was linked stay
unclaimed until it replaces them ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing
tags"), and so do the leaves that other accounts' inviters gave a sign-in the user has not answered, or answered Not
now. A device MUST NOT warn about a leaf, or remove one, only because no device claims it. Removing a removed device's
leaves is under [Removing a device](#removing-a-device). Adding a sibling to a group it is missing from is not specified
yet.

## Removing a device

The user removes a linked device from any other device of the account. A device never removes itself this way: a
device the user is done with signs out.

### The removal Commit

A device removes a sibling with one Commit in its trusted device group. The Commit removes the sibling's leaf, the one
whose device tag reads as the sibling's slot ([Matching leaves to devices](#matching-leaves-to-devices)), and carries a
roster update ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Update") with two
operations for that slot, in this order:

1. `remove_device`;
2. `set_rejected_slot` with reason `removed`, `rejected_at` the time the user decided, and the `tag_signature_key` the
   entry had.

If no leaf's tag reads as the slot, the Commit carries the same roster update and removes no leaf. A client MUST NOT
remove a device whose entry has no `tag_signature_key` yet: its link may still fail, and the approving device undoes a
failed link with `remove_device` alone ("A link that is not taken up").

A device keeps each removal it decided, across restarts, until it discards its copy of the device group ([A link that is
not taken up](#a-link-that-is-not-taken-up)), and removes the device again whenever the roster lists its slot. It
records the decision before it commits. While its copy of the group is terminal or cannot be read, and it has not
discarded it, the removal waits. It commits only while it can commit in the device group, so a Commit there still in
flight or settling only delays the removal. It also waits while the entry has no `tag_signature_key`, which branch
selection can drop after the user decided. The decision is for the slot: if the approving device then removes the entry
as a failed link, the decision stands. A device does the cleanup in [Removing it from chats](#removing-it-from-chats)
and [Its private KeyPackages](#its-private-keypackages) only while its trusted roster records the slot as `removed`, so
it does none when the entry went as a failed link, which writes no such record, or when the record was dropped before
the device acted on it; the slot's leaves then read as unclaimed. When the removal's Commit fails, or branch selection
drops the removal, even after the `removed` record has been dropped, the roster lists the slot again and the device
commits the removal again. A removed device comes back only as a new slot. A removal committed again keeps the
decision's time as `rejected_at`, so once that is 30 days past, the record goes at the next pass that drops old
`removed` records ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State").

### The removed device's slot

The device that decided the removal deletes the removed device's publication slot, with the transport's slot deletion
(for Nostr, [../transports/nostr.md](../transports/nostr.md), "Slot deletion"). This is the one case in which a device
deletes a slot it did not create ([../foundation/key-packages.md](../foundation/key-packages.md), "Devices and
publication slots"):

- it sends the deletion once its state for the device group is settled and no longer lists the slot as a device,
  whether it records the slot as `removed`, that record has since been dropped, or the entry went as a failed link
  after the user decided;
- the deletion covers only publications stamped at or before its own time, so the device stamps it as far ahead of its
  clock as it would date a publication of its own ([../foundation/key-packages.md](../foundation/key-packages.md), "A
  publication the device did not make"), since the removed device's clock may run ahead;
- it sends it again until the transport accepts it;
- when branch selection drops the removal after that, it commits the removal again and, once its state is settled and
  no longer lists the slot as a device, deletes the slot again, since the removed device may have published to it in
  between;
- no other device deletes the slot, and nothing else lets a device delete another device's slot.

The deletion stops inviters from selecting the KeyPackages the removed device published up to the deletion's time. It
does not cover a later publication: what the account's devices do about a removed device that publishes again is not
specified yet. It is cleanup, not revocation: a KeyPackage a relay keeps serving, or one an inviter already holds, can
still be used until its `Lifetime` ends.

### Removing it from chats

While a device's trusted roster records a slot as `removed`, the device removes from each group it is in, other than
the device group, every leaf of its account whose device tag reads as that slot ([Matching leaves to
devices](#matching-leaves-to-devices)). Every device that trusts the device group does this, whichever device decided
the removal.

- In a group that requires `0x800d`, it removes those leaves with one same-account Commit
  ([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md), "Same-account operations"). It
  makes that Commit only while it can commit in the group, and otherwise tries again later. Two devices may both make
  one; branch selection keeps one, and the other then finds nothing left to remove.
- In a group that does not require `0x800d`, only an admin can remove one leaf of an account. The device leaves the leaf
  in place, even where it is an admin, and SHOULD tell its user that an admin of that group can remove it.
- A leaf with no tag reads as unclaimed and is left alone. A leaf in a group none of the remaining devices is in stays
  there: no device of the account can see it.

The removed device realizes each such removal in that group. The account stays a member there through the device that
committed it, so the removed device does not tell its user the account was removed from the group
([../protocol-core/member-departure.md](../protocol-core/member-departure.md), "Realizing removal").

The removed device's leaves stay readable as its old slot until the roster drops the `removed` record
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State"). A leaf left in a group after
that reads as unclaimed.

### Its private KeyPackages

While its trusted roster records a slot as `removed`, every device of the account deletes the private KeyPackages it
exchanged with that slot ([Private KeyPackages](#private-keypackages)):

- those it issued to the slot, with their private keys, so that a Welcome the removed device makes from one cannot add
  this device to a group;
- those the slot handed it, so that it never adds the removed device with one.

## Slot announcements

A device in a device group names each KeyPackage in its own roster entry before that KeyPackage reaches its slot
([../foundation/key-packages.md](../foundation/key-packages.md), "Devices and publication slots"). The entry's
`announced_key_package` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)) holds the
`KeyPackageRef` of the KeyPackage the device publishes there. Its siblings can then tell a refresh, which the roster
names, from a publication in the slot that the device did not make.

- Before a device publishes a KeyPackage to its slot, whether a new one or the current one again, it MUST check that its
  own entry in its device group's current roster names that KeyPackage. If the entry names another or none, the device
  first commits an AppDataUpdate that sets its own entry, with every other field unchanged and `announced_key_package`
  naming the KeyPackage. The one exception: that update MAY also bring the device's own `client` and `platform`
  current ([Labels, clients and platforms](#labels-clients-and-platforms)).
- The device publishes only once that Commit is part of the group state it holds. A Commit that fails, or that a
  branch selection drops, leaves the entry as it was, so the device announces again before it publishes.
- A device that cannot announce, for example because the device group's relays are unreachable, does not publish. It
  MUST NOT publish an unannounced KeyPackage after a timeout; its slot ages instead
  ([../foundation/key-packages.md](../foundation/key-packages.md), "Refreshing a slot"). While a refresh that section
  calls for, or a replacement its "A publication the device did not make" calls for, is held back this way, a client
  SHOULD tell its user, so that a device whose device group stays unwritable does not quietly become one that new
  chats cannot add.
- The founding state announces the KeyPackage the creating device last published, if any, and the founding Add the one
  the link confirmed ([Creating the device group](#creating-the-device-group)), so neither device owes a Commit before
  it publishes one of those KeyPackages again. Any other KeyPackage, including every refresh, is announced as above.
- A device with no device group publishes as before.

The roster keeps one announcement per device. Between an announcement and its publication, while some relays still serve
the previous publication, and after branch selection drops an announcement whose KeyPackage the device had already
published, a sibling can find a KeyPackage in a device's slot that the roster does not name. In the last case the device
announces again before it next publishes, whether the same KeyPackage or a new one. A sibling does nothing about such a
KeyPackage: only the slot's own device acts on what its slot serves ([A KeyPackage the device did not
make](#a-keypackage-the-device-did-not-make)).

### A KeyPackage the device did not make

A device made a KeyPackage when the signature key of the KeyPackage's LeafNode is one the device holds, or has held, as
its own. A valid KeyPackage is signed under its LeafNode's signature key, so only the device can produce one that
carries its key: the test needs no record of what the device published, and it holds for KeyPackages the device
published before it had a device group and after it restores older local state that holds the same key. A device that
changes the signature key it puts in its KeyPackages still made the older ones. The test has one gap: whoever holds the
account's signing key can republish a copy of one of the device's own KeyPackages without a warning, which gains them
nothing, since only the device can open a Welcome to it.

A device that finds a publication in its own slot that it did not make replaces it
([../foundation/key-packages.md](../foundation/key-packages.md), "A publication the device did not make"), announcing
the replacement first as in [Slot announcements](#slot-announcements). When that publication holds a valid
current-profile KeyPackage of the account ([../foundation/key-packages.md](../foundation/key-packages.md)), fresh or
not, that the device did not make, the device also warns its user ([The warning](#the-warning)), on that device only: it
records nothing in the roster and tells no sibling. Anything else it replaces without a warning: a publication that is
not such a KeyPackage, such as an invalid or legacy one, and a copy of one of the device's own KeyPackages. This applies
whether or not the device has a device group.

## Rejections

A `not_me` rejected slot records that someone holding the account's signing key may have published where the account's
devices did not: a sign-in the user rejected ([Answers](#answers)). A KeyPackage a device finds in its own slot that it
did not make shows the same ([A KeyPackage the device did not make](#a-keypackage-the-device-did-not-make)). Neither the
rejection nor the device's replacement stops them. Other accounts' inviters read only published KeyPackages, never the
roster, so they can still add whoever holds the key to new groups; and whoever holds it can still send as the account,
remove the account's devices, and publish more KeyPackages. A stolen account signing key is out of scope: Marmot builds
nothing to evict whoever holds it, and the warning only tells the user. A `removed` rejected slot is not a rejection in
this sense.

### The warning

A device warns its user when it rejects a sign-in itself ([Answers](#answers)); when the roster of its trusted device
group gains a `not_me` rejected slot, whichever device recorded it; and when it finds in its own slot a KeyPackage it
did not make ([A KeyPackage the device did not make](#a-keypackage-the-device-did-not-make)).

- The warning says that the account's signing access may be in someone else's hands: the account's signing key, or a
  session with a remote signer. It MUST NOT claim that the account's devices stopped whoever holds it. For a signing
  key, the only complete fix is moving to a new account.
- A device keeps at most one warning open for the account, which gathers every rejection and every such KeyPackage that
  its user has not yet seen, so a run of them does not become a run of warnings. It records, across restarts, each of
  them its user has seen, and does not warn about one again when a branch selection drops and restores it. It keeps a
  seen KeyPackage from its own slot, by its `KeyPackageRef`, for 7,261,200 seconds after it found it, the longest a
  KeyPackage can be valid, so that one its slot serves again does not warn again either.
- Dismissing the warning on a device marks every rejection and KeyPackage the warning then gathers as seen on that
  device, so the warning stays closed there until something it has not seen arrives. It dismisses it there only: another
  device's warning is unchanged.
- Like the roster, the warning is shown only to the account's own user.

## Private KeyPackages

Devices in a device group are to add each other to chats only with private KeyPackages: single-use KeyPackages that one
device hands to one sibling inside the device group. A private KeyPackage never reaches a slot or any other publication.
The Welcome for an add that uses one reaches its sibling only inside the device group ([Sibling
Welcomes](#sibling-welcomes)). When a device adds a sibling to a chat is not specified yet; until it is, the founding
exemption still applies ([Security considerations](#security-considerations)).

### Issuing

A private KeyPackage is a KeyPackage of the device that issues it
([../foundation/key-packages.md](../foundation/key-packages.md)), with the lifetime and capabilities that device gives
the KeyPackages it publishes. It MUST NOT be last-resort, so a Welcome consumes it once. It carries the issuer's device
tag ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags"), so a device issues
private KeyPackages only once it can tag.

- The issuer records which sibling, by slot, it handed each one to. It keeps the private key material until a Welcome
  consumes the KeyPackage, until its `Lifetime.not_after`, or until its trusted roster records that sibling's slot as
  `removed` ([Its private KeyPackages](#its-private-keypackages)), whichever comes first.
- Only a sibling's add may consume a private KeyPackage. A device MUST reject every Welcome that consumes a private
  KeyPackage it issued unless it arrived as a sibling Welcome that passes [Receiving a sibling
  Welcome](#receiving-a-sibling-welcome). It decides that within the tentative validation of
  [../protocol-core/joining.md](../protocol-core/joining.md) (steps 4 through 9), so a refused Welcome leaves the
  KeyPackage and its `init_key` in place.
- Halfway is `not_before + (not_after - not_before) / 2` in integer seconds, from the KeyPackage's `Lifetime`.
- A device's stock with a sibling is the private KeyPackages it handed that sibling that no Welcome has consumed and
  that have not reached halfway, counting, once that sibling has sent a request, only those it handed over in its answer
  to that sibling's latest request or after it ([Sending](#sending)). When the stock falls below 5, the device issues
  enough new ones to bring it to 10 and hands them over.
- A device tops up its siblings before it asks for its own, so a device back after a long gap serves the others first.
- A device MAY cap how many unexpired private KeyPackages it keeps for one sibling, but the cap MUST be at least 300:
  that leaves room for a full answer of 100 beside the ones a device at the default stock keeps until `not_after`. Once
  it reaches that cap it issues fewer than a top-up or a request calls for, and a top-up waits for room. It MUST NOT
  delete one before `not_after` to make room. At the cap it MAY make up the rest of an answer to a request by handing
  over again private KeyPackages it already handed that sibling that no Welcome has consumed, the most recently issued
  first, so a sibling whose hand-offs were all lost still gets some. Handing one over again does not change its
  `Lifetime`: it counts toward the stock again only until it reaches halfway.
- At `not_after`, the issuer deletes the private key material and the holder deletes the KeyPackage. A `removed` slot
  ends both sooner ([Its private KeyPackages](#its-private-keypackages)).

### Messages

| Kind  | Message  | Sent by                                   |
| ----- | -------- | ----------------------------------------- |
| `459` | Request  | a device that wants private KeyPackages   |
| `460` | Hand-off | the device that issued them               |

Both are Marmot app events ([../foundation/application-messages.md](../foundation/application-messages.md)) sent as MLS
application messages in the device group. Both name the sender's slot (`from`) and the addressee's slot (`to`), each a
`SlotId` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State").

A request's content is one UTF-8 JSON object with exactly these members, written in this order without whitespace.
Slots are JSON strings of lowercase hexadecimal, 64 characters. `v` and `want` are JSON numbers, written as decimal
integers without leading zeros.

| Member | Value |
| ------ | ----- |
| `v`    | `1` |
| `from` | the requesting device's slot |
| `to`   | the slot of the device asked |
| `want` | how many new private KeyPackages it asks for, from 1 to 100 |

A hand-off's content is the standard base64 encoding, with padding
([RFC 4648, section 4](https://www.rfc-editor.org/rfc/rfc4648#section-4)), of:

```text
struct {
  uint8 version;
  SlotId from;
  SlotId to;
  MLSMessage key_packages<V>;
} PrivateKeyPackageHandOffV1;
```

The structure uses the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)). Each MLSMessage is encoded as MLS defines
it, and `key_packages<V>` is the byte length of their concatenation followed by that concatenation. `version` is `1`.
`key_packages` holds 1 to 20 MLSMessages, each with `wire_format` `mls_key_package`. An answer of more than 20 goes out
as several hand-offs.

### Sending

- A device asks a sibling for private KeyPackages when it holds no usable one from that sibling, or when it needs more
  than it holds. A usable one has not reached halfway. While the need lasts, it sends the request again at most once an
  hour. Each request, first or repeated, is a new Marmot app event with a later `created_at` than the one before, so its
  `id` differs and the sibling answers it.
- A device answers a request by issuing `want` new private KeyPackages to the requester and handing them over. The ones
  it handed the requester before stop counting toward the stock, since they may have been lost, but keep their key
  material until one of the ends in [Issuing](#issuing): a Welcome consumes them, they expire, or its trusted roster
  records the requester's slot as `removed`. A device at its cap answers as [Issuing](#issuing) allows. A device answers
  each request, by its Marmot app event `id`, once.
- There are no receipts. A lost hand-off is repaired by the requester's next request.

### Receiving

A device reads a request or a hand-off only from the device group it trusts ([Trust](#trust)), and ignores both kinds
in any other group. It drops one unless:

- its content decodes exactly as [Messages](#messages) gives it: a request with `v` `1` and `want` from 1 to 100, or a
  hand-off with `version` `1` and 1 to 20 `mls_key_package` MLSMessages, with no bytes left over;
- `to` is its own slot;
- `from` is another device in its current roster;
- the leaf that sent it carries a device tag that reads as `from`'s
  ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Reading tags"): it opens under the
  roster's `leaf_tag_key`, names `from`, and verifies under the `tag_signature_key` in `from`'s roster entry.

A device whose leaf in the device group carries no tag yet, such as a new device before its post-join self-update, has
its requests and hand-offs dropped and not counted. It sends them again once it has tagged its leaf.

A removed device still holds `leaf_tag_key`, and its `removed` record keeps its `tag_signature_key`, so its tags still
read as its old slot ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Security
considerations"). That slot is no longer a device in the roster, so the receiver drops whatever it sends.

It drops a whole hand-off unless every KeyPackage in it:

- is a valid MLS KeyPackage whose `Lifetime` is current and no longer than a published KeyPackage's may be, and whose
  credential is its own account's Marmot account identity with a valid account identity proof
  ([../foundation/key-packages.md](../foundation/key-packages.md)). The checks there on a publication's transport
  author, transport encoding and KeyPackageRef hint do not apply, and capabilities are checked when the KeyPackage is
  used;
- is not last-resort;
- has not reached its `Lifetime.not_after`;
- carries a device tag that reads as `from`'s, as above.

The tag checks are the device group's rules for accepting a request or a hand-off, not validity rules: a KeyPackage or
leaf without a tag stays valid everywhere else
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Validity"). The receiver keeps the
KeyPackages it accepts by `from` until it uses one, discards them, or they expire. A device MUST NOT keep a private
KeyPackage it has already used, even when a sibling hands it over again. It remembers each one it used until that
KeyPackage's `not_after`, and keeps the rest of such a hand-off.

## Sibling Welcomes

A device that adds a sibling to a chat with a private KeyPackage that sibling handed it sends the Welcome inside the
device group, as a sibling Welcome. A private KeyPackage has no publication for a transport binding's Welcome delivery
to name, and only the device group can show the receiver that a sibling sent it.

### Message

| Kind  | Message         | Sent by                                                   |
| ----- | --------------- | --------------------------------------------------------- |
| `461` | Sibling Welcome | the device that added a sibling with its private KeyPackage |

A sibling Welcome is a Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
sent as an MLS application message in the device group. Its content is the standard base64 encoding, with padding
([RFC 4648, section 4](https://www.rfc-editor.org/rfc/rfc4648#section-4)), of:

```text
struct {
  opaque url<1..512>;
} SiblingWelcomeRelayV1;

struct {
  uint8 version;
  SlotId from;
  SlotId to;
  KeyPackageRefV1 key_package_ref;
  MLSMessage welcome;
  SiblingWelcomeRelayV1 relays<V>;
} SiblingWelcomeV1;
```

The structure uses the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)). `SlotId` and `KeyPackageRefV1` are as the
roster defines them
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State").

- `version` is `1`.
- `from` is the sender's slot and `to` the slot of the sibling it added.
- `key_package_ref` is the `KeyPackageRef` of the private KeyPackage the Commit consumed, computed as
  [../foundation/key-packages.md](../foundation/key-packages.md) gives it.
- `welcome` is one MLSMessage with `wire_format` `mls_welcome`, encoded as MLS defines it.
- `relays` lists, in order, where the new member SHOULD fetch the chat's group messages, as the active transport
  binding names them: one to 16 entries, none repeated. On Nostr each entry is a relay URL under the relay URL profile
  ([../transports/nostr.md](../transports/nostr.md), "Relay URL profile"), as in a kind `444` rumor's `relays` tag. The
  list is a fetch hint, not group state: the chat's routing component inside the Welcome stays authoritative.

### Sending a sibling Welcome

- A device sends one sibling Welcome for each private KeyPackage its Commit added, each naming its own KeyPackage
  ([../protocol-core/joining.md](../protocol-core/joining.md), "Delivery"), and sends it when an inviter sends a
  Welcome: after the Commit's publish obligation succeeds ([../protocol-core/joining.md](../protocol-core/joining.md),
  "Behavior").
- It MUST NOT deliver a Welcome that consumes a private KeyPackage through the transport binding's Welcome delivery.
  Members of other accounts that the same Commit added get their Welcomes through the binding as usual.
- When a device sends a sibling Welcome again is not specified yet.

### Receiving a sibling Welcome

A device reads a sibling Welcome only from the device group it trusts ([Trust](#trust)), and ignores the kind in any
other group. It drops one unless:

- its content decodes exactly as [Message](#message) gives it: `version` `1`, a `welcome` whose `wire_format` is
  `mls_welcome`, and no bytes left over;
- `relays` holds one to 16 entries, none repeated after validation, each valid under the active binding's rules;
- `to` is its own slot;
- `from` is another device in its current roster;
- the leaf that sent it, as that leaf was in the epoch the message was sent in, carries a device tag that reads as
  `from`'s, as for a request or a hand-off ([Receiving](#receiving));
- `key_package_ref` names a private KeyPackage this device issued and recorded as handed to `from`
  ([Issuing](#issuing)), whose private key material it still keeps.

A device that passes these checks joins through the receiving flow of
[../protocol-core/joining.md](../protocol-core/joining.md), with the sibling Welcome as the delivery. The device
group's authenticated sender, a device of this account, addresses it to this account (step 1), and `to` to this device
within it. `key_package_ref` names the KeyPackage step 2 checks, and step 3 decodes the `welcome` field. A sibling
Welcome dropped for its `to` or its `key_package_ref` consumes no KeyPackage. Joining consumes that KeyPackage: the
issuer deletes its private key material and its record of the hand-off along with the other consumed KeyPackage state
(steps 11 and 12).

A device joins only from a sibling Welcome whose app payload was delivered to it
([../protocol-core/convergence.md](../protocol-core/convergence.md), "Applying the selected branch"). Once joining has
consumed the KeyPackage, the join stands: a branch selection that later withdraws that payload does not undo it, as a
withdrawn update does not undo small state ([account-sync.md](account-sync.md), "Convergence and retained history").

A KeyPackage handed over again at the cap ([Issuing](#issuing)) goes to the same sibling, so the record still names the
slot that holds it.

## Devices

A device shows its user the account's devices from its device group's roster, for example on a Devices screen. It never
shows them to anyone else ([Keeping it out of sight](#keeping-it-out-of-sight)).

### Labels, clients and platforms

A device entry's `label`, `client` and `platform`
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State") are what a user reads to tell
the devices apart.

- Every device entry MUST be created with a `rename_id` of 16 bytes the creating device draws from a cryptographically
  secure random source: the creating device's entry in the founding state, and the entry of every device added, by the
  founding Add ("Creating the device group") or a later link ("Approving").
  Only a rename changes it afterwards, so no two entries share one, and an id a device kept can show up in the roster
  again only when a fork brings back an earlier state, which is what rename recovery below reads.
- Any device MAY change any device entry's `label`, its own included. An update that changes an entry's `label` is a
  rename: it sets that entry with only `label` and `rename_id` changed, and MUST write a fresh `rename_id` drawn the
  same way, one that clears `label` included. Every other update to an entry MUST keep its `label` and its
  `rename_id`.
- A device SHOULD keep its own entry's `client` and `platform` current. `client` is the client name it puts in its
  KeyPackages' `client` tag ([../transports/nostr.md](../transports/nostr.md), "KeyPackage publication"); `platform`
  is a short name for the platform it runs on, such as `iOS`. Either is empty when the device has none. It SHOULD
  write them in the update that announces its next KeyPackage ([Slot announcements](#slot-announcements)) rather than
  in an update of their own, so a changed value reaches the roster with that announcement. Publishing a KeyPackage its
  entry already names makes no announcement. A rename never carries them. A device does not write another device's
  `client` or `platform`.
- A device SHOULD build a roster update from the roster of the state it commits to, and SHOULD NOT send one while an
  earlier Commit of its own in the device group is unresolved. An update sets whole entries, so one built from an
  older roster puts back whatever changed in that entry since.

A rename can lose a fork ([../protocol-core/convergence.md](../protocol-core/convergence.md)) to a sibling's Commit.
The entry's `rename_id` tells the renaming device where its rename stands; labels and Commits do not, since two renames
can set the same label and a lost Commit can be sent again as a different Commit. From before it sends a rename's
Commit, a device keeps, for the device it renames:

- as written, the `rename_id` the rename writes, and each one it writes when it makes the rename again;
- as replaced, the `rename_id` the entry held when the device built the rename. If the device still keeps an earlier
  rename of that device, and the entry held an id that earlier rename kept, as written or as replaced, it also keeps as
  replaced every id the earlier rename kept, both kinds. The new rename takes the earlier one's place.

It keeps them until another rename of that device stands or the device leaves the roster. It reads where a rename
stands only while its device group is `Stable` ([../protocol-core/group-state.md](../protocol-core/group-state.md)) and
no Commit of its own there is unresolved, and only from that entry's `rename_id` in the roster of its canonical state,
taking the first of these that matches:

- One kept as written: the rename applied.
- One kept as replaced: the rename lost and nothing renamed the device since. It renames the device again with a
  fresh `rename_id`, unless the entry already shows the label it set.
- Any other: another rename won and stands, and the device drops its own.

A device MAY forget the oldest `rename_id`s it keeps for one device, but never the newest it keeps as written, nor the
`rename_id` the entry held when the device last built the rename or made it again: while the rename has not applied and
nothing renamed the device since, the roster holds that one. A roster holding a forgotten one reads as another rename's,
so the device drops its rename rather than make it again over one it cannot place. Either way, a device shows its user
the label its roster holds.

### Heartbeats

| Kind  | Message   | Sent by                   |
| ----- | --------- | ------------------------- |
| `457` | Heartbeat | every device in the group |

A heartbeat is a Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
sent as an MLS application message in the device group. Its content is `{"v":1}`, written without whitespace, and its
`created_at` is when it was sent. It says that the device that sent it is running.

**Sending.** While it runs, a device sends a heartbeat in the device group it trusts ([Trust](#trust)) whenever it has
sent none there or its last heartbeat there is at least one hour old, whether it has just started or has been running
for a while. It keeps the time of its last heartbeat across restarts. A heartbeat that no relay accepted is not its last
one, so the device sends again at its next chance. It sends one only while the roster lists it and its own leaf in the
device group carries a device tag that reads as its slot ([Matching leaves to devices](#matching-leaves-to-devices)),
since its siblings count no heartbeat from an untagged leaf. A heartbeat never asks for a push notification and never
wakes a sibling.

**Receiving.** A device reads heartbeats only in the device group it trusts, and ignores kind `457` in any other group.
A heartbeat counts for a sibling only when the leaf that sent it, in the tree of the epoch the device holds when it
reads it, carries a device tag that reads as that sibling's
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Reading tags"): it opens under the
roster's `leaf_tag_key`, names a slot that is a device in the roster, and verifies under that entry's
`tag_signature_key`. A heartbeat from an earlier epoch, from an unclaimed leaf, or from a leaf whose tag names a
`removed` slot counts for no device; that sibling's next heartbeat counts instead. A device that reads a sibling's
heartbeats only after it has applied a later Commit, as when it catches up after an absence, therefore counts none of
them, and can show that sibling as inactive until it sends again ([Inactive devices](#inactive-devices)). A receiver
enforces no rate: every heartbeat that meets these rules counts.

A receiver does not read a heartbeat's content, so that a later version can add to it without older devices dropping
its heartbeats and judging its sender inactive.

**Last activity.** A sibling's last activity is the latest, over the heartbeats that counted for it, of each
heartbeat's `created_at` or the time the device read it, whichever is earlier, in seconds since the Unix epoch. A
heartbeat only ever moves it later. A heartbeat never dates activity after the device read it, and one delivered late
counts at its `created_at`, not when it arrived. Neither holds the sender's clock to the truth: a sender whose clock
runs behind looks less recently active than it is, which errs toward showing it inactive, and a sender whose clock
runs ahead, read late, can look active as late as the read, which errs toward hiding a sibling that stopped. A device
keeps each sibling's last activity, and when it first found that sibling in its roster, across restarts, for that
sibling's roster entry: its slot together with the entry's `linked_at`. A device MUST NOT carry either from one entry to
another: once its roster lists the slot with a different `linked_at`, the device first finds that sibling then, even if
it never held a roster without the slot. A device MAY forget both once its roster no longer lists the entry. A fork that
brings back an entry the device saw removed brings back the same sibling, so if the device kept that entry's times,
they still apply. Each device keeps its own; nothing about it is written to the roster.

### Inactive devices

A device treats a sibling as inactive once 30 days have passed, by its own clock, since the later of that sibling's last
activity and when the device first found that sibling in its roster, or, while no heartbeat of the sibling has
counted, since it first found it. A device that has just joined the device group, or a sibling that was just linked,
therefore gets 30 days before it shows as inactive. A device never treats itself as inactive. A device SHOULD show its
user which siblings are inactive.

This judgment only decides what a device shows. A device that comes back after a long absence during which a Commit
moved its device group on counts none of the heartbeats sent before that Commit ([Heartbeats](#heartbeats)), so it sees
siblings as inactive until they send heartbeats it counts, and its view says little about who is still running. A
device MUST NOT set a device entry's status to `inactive`
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)) from it. When a device records that
status, and removing a device after a longer absence, are not specified yet.

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
- An announcement is evidence only among devices that trust the same device group. Someone holding the account's
  signing key can publish into any slot, but cannot write the roster of a device group they are not in.
- Private KeyPackages are why holding the account's signing key never lets someone join a chat as a sibling: a device
  joins through one of its private KeyPackages only from a sibling Welcome sent inside its device group, by the tagged
  sibling it handed that KeyPackage to. Someone holding only the account's signing key is in neither. Until when a
  device adds a sibling is specified, a device that creates a group may still add its account's published KeyPackages
  under the founding exemption in [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)
  ("Sender rules"), including one that someone holding that key published.
- A sibling Welcome is accepted only for a KeyPackage recorded as handed to its sender, so one sibling cannot spend
  another sibling's allocation, even though any sibling could otherwise read the Welcome bytes in the device group.
- Device tags tie a request or hand-off, and each handed-over KeyPackage, to its `from` slot as the roster records
  it. One device in the device group therefore cannot file its KeyPackages under a sibling's slot, or make a request
  in a sibling's name that resets what was handed that sibling, without first rewriting that sibling's roster entry,
  which the roster lets any device do ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
  "Security considerations"). Someone holding only the account's signing key has neither `leaf_tag_key` nor a tag
  signature key. A removed device can tag only with its own old slot, which is no longer a roster device.
- A rejection, like a KeyPackage a device finds in its own slot that it did not make, only warns the user; it does not
  stop whoever holds the account's signing key ([Rejections](#rejections)). Clients say so, and do not present the
  warning as protection.
- Whoever holds the account's signing key can replace the KeyPackage in the slot of a device that is rarely opened.
  Other accounts' inviters can add that KeyPackage until the device next runs, replaces it and warns its user, and the
  leaves that joined with it stay in their groups. Only that device warns: its siblings do not act on a KeyPackage in
  its slot.
