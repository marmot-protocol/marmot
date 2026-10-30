# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how clients keep it out
of sight, how the account's devices notice a new sign-in, how each device announces the KeyPackages it publishes, what
the devices do when someone else publishes under the account's key where they did not expect it, and how devices hand
each other private KeyPackages. Linking, adding a sibling to a chat, the group's other messages, and removal are not
specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule, and whose same-account Remove takes leaves tied to a rejection out
  of other groups ([Leaves tied to a rejection](#leaves-tied-to-a-rejection)).
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).
- Foundation: [../foundation/key-packages.md](../foundation/key-packages.md), whose publication slots each device's
  roster entry announces into, and whose publications are the evidence of a new sign-in ([New sign-ins](#new-sign-ins)).
- Marmot app events: kind `462` (anomaly alert, [Anomaly alerts](#anomaly-alerts)), kind `459` (private KeyPackage
  request) and kind `460` (private KeyPackage hand-off, [Private KeyPackages](#private-keypackages)), each sent only in
  a device group. Their kinds are registered in [../foundation/registries.md](../foundation/registries.md).

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
- The founding roster announces a KeyPackage for both devices ([Slot announcements](#slot-announcements)): the linked
  device's entry sets `announced_key_package` to the `KeyPackageRef` of the KeyPackage the link confirmed, and the
  creating device's entry sets it to the `KeyPackageRef` of the KeyPackage it currently publishes in its own slot, if
  any.

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
linked device's slot that holds a KeyPackage the device did not publish ([A KeyPackage the roster does not
announce](#a-keypackage-the-roster-does-not-announce)).

A device keeps its own rejections, across restarts, until the roster holds the slot as a device. While it keeps one, it
commits it again whenever the roster has no entry for the slot: when its Commit fails, and when branch selection drops
the update that recorded it, whichever device made that update.

If the roster holds the slot as a device, the user confirmed linking it, on this device or another: the device commits
nothing for the slot, forgets its rejection, and stops asking about it. If branch selection later drops that link, the
device asks about the slot again ([Any one device's answer](#any-one-devices-answer)) rather than restore an answer the
user's link overrode. What a rejection does beyond its record, warning the user and removing leaves from groups, is in
[Rejections](#rejections).

A device with no device group keeps its rejections itself and never asks about those slots again. When it creates a
device group, the founding roster carries them. When it joins one, it commits them once it trusts that group. Either way
it leaves out, and forgets, a rejection of a slot the roster holds as a device, such as the one just linked, and keeps
the others as above.

A client MAY let a device whose first check found sign-ins ([Already signed in, or new](#already-signed-in-or-new))
start without them, in groups it is invited to from then on. Starting that way answers Not now for each of those
sign-ins. It MUST NOT reject them: one of them may be a device the user still has somewhere, which can link this one
later, and a rejection would block that link and warn the user about a device they only lost.

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

A leaf that no device claims is not evidence of anything by itself ([Leaves tied to a
rejection](#leaves-tied-to-a-rejection)). What the devices do with a leaf tied to a rejection is in that section. Adding
a sibling to a group it is missing from, and removing a removed device's leaves, are not specified yet.

## Slot announcements

A device in a device group names each KeyPackage in its own roster entry before that KeyPackage reaches its slot
([../foundation/key-packages.md](../foundation/key-packages.md), "Devices and publication slots"). The entry's
`announced_key_package` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)) holds the
`KeyPackageRef` of the KeyPackage the device publishes there. Its siblings can then tell a refresh, which the roster
names, from a publication in the slot that the device did not make.

- Before a device publishes a KeyPackage to its slot, whether a new one or the current one again, it MUST check that its
  own entry in its device group's current roster names that KeyPackage. If the entry names another or none, the device
  first commits an AppDataUpdate that sets its own entry, with every other field unchanged and `announced_key_package`
  naming the KeyPackage.
- The device publishes only once that Commit is part of the group state it holds. A Commit that fails, or that a
  branch selection drops, leaves the entry as it was, so the device announces again before it publishes.
- A device that cannot announce, for example because the device group's relays are unreachable, does not publish. It
  MUST NOT publish an unannounced KeyPackage after a timeout; its slot ages instead
  ([../foundation/key-packages.md](../foundation/key-packages.md), "Refreshing a slot"). While a refresh that section
  calls for, or a replacement its "A publication the device did not make" calls for, is held back this way, a client
  SHOULD tell its user, so that a device whose device group stays unwritable does not quietly become one that new
  chats cannot add.
- The founding roster announces the KeyPackage the link confirmed and the creating device's current one, if any
  ([Creating the device group](#creating-the-device-group)), so neither device owes a Commit before it publishes one of
  those KeyPackages again. Any other KeyPackage, including every refresh, is announced as above.
- A device with no device group publishes as before.

The roster keeps one announcement per device. Between an announcement and its publication, while some relays still serve
the previous publication, and after branch selection drops an announcement whose KeyPackage the device had already
published, a sibling can find a KeyPackage in a device's slot that the roster does not name. In the last case the device
announces again before it next publishes, whether the same KeyPackage or a new one. What a sibling does then is in
[A KeyPackage the roster does not announce](#a-keypackage-the-roster-does-not-announce).

A device that finds a publication in its own slot that it did not make replaces it
([../foundation/key-packages.md](../foundation/key-packages.md), "A publication the device did not make"), announcing
the replacement first as above.

### A KeyPackage the roster does not announce

To a device, a KeyPackage is announced for a slot when the entry of the device in that slot named it, as
`announced_key_package`, in any roster of its trusted device group that the device has held. The device keeps each
`KeyPackageRef` it has seen announced, by slot, until that KeyPackage's `Lifetime.not_after`, so a sibling's earlier
KeyPackage that some relays still serve stays announced. A KeyPackage is unannounced in a slot of a device in the
roster when it is the slot's current publication, counts as evidence ([Evidence](#evidence)), is not announced for
that slot, and is not a rejected KeyPackage in the roster.

Only the slot's own device knows whether it made a KeyPackage. A sibling cannot tell a publication someone else made
from one whose announcement it has not processed yet, or whose announcement a branch selection dropped after the
KeyPackage was published. So the slot's device decides, and a sibling decides by itself only after giving that device
a day.

**The slot's own device.** A device that finds, in its own slot, a publication that it did not make replaces it, as
above. When that publication is a valid KeyPackage of the account, the device also rejects it: in its trusted device
group it commits a roster update that sets a rejected KeyPackage with the KeyPackage's `KeyPackageRef`, its own slot,
and the time ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Update"), unless the
roster already rejects that KeyPackage. It keeps the rejection, across restarts, until the roster holds it, and commits
it again when its Commit fails or a branch selection drops the update that recorded it. A device with no device group
keeps the rejection itself, like its rejected sign-ins ([Answers](#answers)), and the roster of the device group it
later creates or joins gets it the same way.

**A sibling.** A device that finds a KeyPackage unannounced in a sibling's slot:

1. brings its trusted device group up to date first: it processes every Commit for the group that it can fetch, until
   it holds no unprocessed input for the group. If the KeyPackage is then announced for that slot, rejected, or no
   longer the slot's current publication, it does nothing more;
2. sends the slot's device an anomaly alert naming the KeyPackage ([Anomaly alerts](#anomaly-alerts)). It sends one
   alert for each KeyPackage;
3. rejects the KeyPackage itself, as the slot's own device would, if a check made 24 hours or more after it sent the
   alert, by its own clock, finds that KeyPackage still unannounced in the slot.

**On an alert.** A device that receives an anomaly alert naming a KeyPackage reads its own slot as
[../foundation/key-packages.md](../foundation/key-packages.md) ("A publication the device did not make") describes,
which replaces and rejects a publication it did not make as above. If it made the KeyPackage the alert names and that
KeyPackage is still its slot's current publication, it announces it again ([Slot announcements](#slot-announcements)),
which also repairs an announcement a branch selection dropped. If it did not make that KeyPackage, it rejects it,
whether or not its slot still holds it.

A device MUST NOT reject a KeyPackage that any roster of its trusted device group announced for any device. Whoever
holds the account's signing key can copy one device's KeyPackage into another device's slot, and rejecting the copy
would reject the KeyPackage of the device that made it. The slot's device replaces the copy like any other publication
it did not make.

A device that rejects a KeyPackage, or whose roster gains a rejected KeyPackage, warns its user
([Rejections](#rejections)).

### Anomaly alerts

An anomaly alert is a Marmot app event of kind `462`
([../foundation/application-messages.md](../foundation/application-messages.md)), sent as an MLS application message in
the device group. Its content is one UTF-8 JSON object with exactly these members, written in this order without
whitespace. Slots are JSON strings of lowercase hexadecimal, 64 characters, as in a request
([Messages](#messages)). `v` is a JSON number, written as a decimal integer without leading zeros.

| Member            | Value |
| ----------------- | ----- |
| `v`               | `1` |
| `from`            | the alerting device's slot |
| `to`              | the slot that holds the KeyPackage, and so the device the alert is for |
| `key_package_ref` | the KeyPackage's `KeyPackageRef`, as a JSON string of lowercase hexadecimal, 2 to 128 characters |

A device reads an alert only from the device group it trusts ([Trust](#trust)), and ignores the kind in any other
group. It drops an alert unless its content decodes exactly as above with `v` `1`, `to` is its own slot, `from` is
another device in its current roster, and the leaf that sent it carries a device tag that reads as `from`'s, as for a
request ([Receiving](#receiving)). It acts on each KeyPackage that alerts name once.

## Rejections

A `not_me` rejected slot and a rejected KeyPackage each record that someone holding the account's signing key published
where the account's devices did not: a sign-in the user rejected ([Answers](#answers)), or a KeyPackage in a linked
device's slot that the device did not make ([A KeyPackage the roster does not
announce](#a-keypackage-the-roster-does-not-announce)). Neither stops them. Other accounts' inviters read only published
KeyPackages, never the roster, so they can still add whoever holds the key to new groups; and whoever holds it can still
send as the account, remove the account's devices, and publish more KeyPackages. A rejection does two things: it warns
the user, and it takes leaves tied to it out of the groups the account's devices can clean up. A `removed` rejected slot
is not a rejection in this sense.

### The warning

A device warns its user when it rejects a sign-in or a KeyPackage itself; when the roster of its trusted device group
gains a `not_me` rejected slot or a rejected KeyPackage, whichever device recorded it; and when it removes a leaf tied to
a rejection ([Leaves tied to a rejection](#leaves-tied-to-a-rejection)).

- The warning says that the account's signing access may be in someone else's hands: the account's signing key, or a
  session with a remote signer. It MUST NOT claim that the account's devices stopped whoever holds it, or that removing
  leaves made the account safe. For a signing key, the only complete fix is moving to a new account.
- A device keeps at most one warning open for the account, which gathers every rejection and removal its user has not
  yet seen, so a run of rejections does not become a run of warnings. It records, across restarts, each rejection and
  removal its user has seen, and does not warn about one again when a branch selection drops and restores it.
- Dismissing the warning on one device dismisses it there only.
- Like the roster, the warning is shown only to the account's own user.

### Leaves tied to a rejection

A KeyPackage is tied to a rejection, for a device, when no roster of its trusted device group has announced it for any
device, and:

- the roster of its trusted device group rejects it; or
- the device saw it as the current publication of a slot rejected as `not_me`, in that roster or among its own
  rejections, and never saw it as the current publication of a slot that is not rejected. Whoever holds the account's
  signing key can copy a real device's KeyPackage into a slot the user then rejects, and the copy shows the same
  `KeyPackageRef` in the real device's slot.

Each device records, for each leaf of its own account in each group it is in, other than its own, the `KeyPackageRef`
of the KeyPackage that leaf joined with, from the Add proposal that added it, which carries the whole KeyPackage. It
keeps the record while that leaf is in the group. Such a leaf is tied to a rejection when the KeyPackage it joined with
is. In a group the device joined after the leaf was added, it has no such record: there the leaf is tied to a rejection
when its signature key is the leaf signature key of a KeyPackage tied to a rejection that the device has seen.

A device SHOULD remove, from each group it is in, every leaf of its account that is tied to a rejection and does not
read as a device's or a removed slot's ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md),
"Reading tags"):

- by a same-account Remove ([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)), in a
  group whose current state requires `0x800d`;
- otherwise by an ordinary Remove, in a group where its account is an active admin.

It lists for its user, with the warning, each group where it found such a leaf and can do neither. Several of the
account's devices may remove the same leaf; branch selection keeps one of their Commits.

A leaf that no device claims is not evidence of anything by itself. A device's leaves from before it was linked stay
unclaimed until it replaces them ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing
tags"), and so do the leaves that other accounts' inviters gave a sign-in the user has not answered, or answered Not
now. A device MUST NOT warn about a leaf, or remove one, only because no device claims it.

This has limits:

- In a group a device joined after the leaf was added, a leaf whose signature key has changed since it was added is
  not tied to a rejection, so whoever holds the account's signing key can keep a leaf there by replacing it before such
  a device joins.
- A KeyPackage published and replaced between two of a device's checks is tied to a rejection only if the roster
  rejects it.
- A device cleans up only groups it is in.

## Private KeyPackages

Devices in a device group add each other to chats only with private KeyPackages: single-use KeyPackages that one device
hands to one sibling inside the device group. A private KeyPackage never reaches a slot or any other publication. How a
sibling uses one to add a device to a chat is not specified yet.

### Issuing

A private KeyPackage is a KeyPackage of the device that issues it
([../foundation/key-packages.md](../foundation/key-packages.md)), with the lifetime and capabilities that device gives
the KeyPackages it publishes. It MUST NOT be last-resort, so a Welcome consumes it once. It carries the issuer's device
tag ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags"), so a device issues
private KeyPackages only once it can tag.

- The issuer records which sibling, by slot, it handed each one to. It keeps the private key material until a Welcome
  consumes the KeyPackage or until its `Lifetime.not_after`, whichever comes first.
- Only a sibling's add may consume a private KeyPackage, and how one does is not specified yet. Until it is, a device
  MUST reject every Welcome that consumes a private KeyPackage it issued, within the tentative validation of
  [../protocol-core/joining.md](../protocol-core/joining.md) (steps 4 through 9), so the KeyPackage and its `init_key`
  stay.
- Halfway is `not_before + (not_after - not_before) / 2` in integer seconds, from the KeyPackage's `Lifetime`.
- A device's stock with a sibling is the private KeyPackages it handed that sibling that no Welcome has consumed, that
  have not reached halfway, and that it has not stopped counting on answering a later request from that sibling
  ([Sending](#sending)). When the stock falls below 5, the device issues enough new ones to bring it to 10 and hands
  them over.
- A device tops up its siblings before it asks for its own, so a device back after a long gap serves the others first.
- A device MAY cap how many unexpired private KeyPackages it keeps for one sibling. Once it reaches that cap it issues
  fewer than a top-up or a request calls for, and a top-up waits for room. It MUST NOT delete one before `not_after` to
  make room. At the cap it MAY make up the rest of an answer to a request by handing over again private KeyPackages it
  already handed that sibling that no Welcome has consumed, the most recently issued first, so a sibling whose hand-offs
  were all lost still gets some. Handing one over again does not change its `Lifetime`: it counts toward the stock again
  only until it reaches halfway.
- At `not_after`, the issuer deletes the private key material and the holder deletes the KeyPackage.

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
  hour.
- A device answers a request by issuing `want` new private KeyPackages to the requester and handing them over. The ones
  it handed the requester before stop counting toward the stock, since they may have been lost, but keep their key
  material until a Welcome consumes them or they expire. A device at its cap answers as [Issuing](#issuing) allows. A
  device answers each request, by its Marmot app event `id`, once.
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

- is a valid MLS KeyPackage with a current `Lifetime`, whose credential is its own account's Marmot account identity
  with a valid account identity proof ([../foundation/key-packages.md](../foundation/key-packages.md)). The checks
  there on a publication's transport author, transport encoding and KeyPackageRef hint do not apply, and capabilities
  are checked when the KeyPackage is used;
- is not last-resort;
- has not reached its `Lifetime.not_after`;
- carries a device tag that reads as `from`'s, as above.

The tag checks are the device group's rules for accepting a request or a hand-off, not validity rules: a KeyPackage or
leaf without a tag stays valid everywhere else
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Validity"). The receiver keeps the
KeyPackages it accepts by `from` until it uses one, discards them, or they expire. A device MUST NOT keep a private
KeyPackage it has already used, even when a sibling hands it over again. It remembers each one it used until that
KeyPackage's `not_after`, and keeps the rest of such a hand-off.

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
- An announcement is evidence only among devices that trust the same device group. Someone holding the account's
  signing key can publish into any slot, but cannot write the roster of a device group they are not in.
- Private KeyPackages are why holding the account's signing key never lets someone join a chat as a sibling: siblings
  add each other only with KeyPackages handed over inside a device group that person is not in.
- Device tags tie a request or hand-off, and each handed-over KeyPackage, to its `from` slot as the roster records
  it. One device in the device group therefore cannot file its KeyPackages under a sibling's slot, or make a request
  in a sibling's name that resets what was handed that sibling, without first rewriting that sibling's roster entry,
  which the roster lets any device do ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
  "Security considerations"). Someone holding only the account's signing key has neither `leaf_tag_key` nor a tag
  signature key. A removed device can tag only with its own old slot, which is no longer a roster device.
- A rejection warns the user and cleans up; it does not stop whoever holds the account's signing key
  ([Rejections](#rejections)). Clients say so, and do not present a rejection as protection.
- Whoever holds the account's signing key can replace the KeyPackage in the slot of a linked device that is rarely
  opened. Other accounts' inviters can add that KeyPackage until the device next runs and replaces it, rejected or
  not. Once it is rejected, the account's devices remove its leaves from the groups they are in. When the slot's device
  does not answer an alert, its siblings reject it after a day.
- An anomaly alert and a rejected KeyPackage come only from a device in the device group. A linked device can send
  false alerts or reject a sibling's KeyPackage against the rules above, as it can rewrite any roster entry
  ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "Security considerations").
