# Changes

Status: adopted.

This log lists changes to the specification that implementers need to know about, newest first. Each entry says what
changed, every document whose rules it changed, what an implementation has to do differently, and which pull request
made the change. Index-only edits to surface `README.md` files and `layout.md` are not named; the pull request has the
full file list. Idea documents, editorial fixes, and repository housekeeping are not listed.

The specification has no version number, and this log does not version the protocol. An interop-visible breaking change
still needs an explicit versioning hook, as [layout.md](./layout.md#features) requires.

The log starts at the 2026-07-05 baseline, the oldest commit on `master`. Earlier MIP-era changes are mapped in
[mip-coverage.md](./mip-coverage.md).

## 2026-10-30: Sibling Welcomes (draft)

[#471](https://github.com/marmot-protocol/marmot/pull/471) changes
[features/device-group.md](./features/device-group.md),
[app-components/account-devices-v1.md](./app-components/account-devices-v1.md),
[protocol-core/joining.md](./protocol-core/joining.md),
[transports/nostr.md](./transports/nostr.md) and
[foundation/registries.md](./foundation/registries.md).

- A Welcome that consumes a private KeyPackage travels as a sibling Welcome (kind `461`, new), an app event in the
  device group carrying the Welcome, the consumed KeyPackage's `KeyPackageRef` and the chat's relays. A device MUST NOT
  deliver such a Welcome through the transport binding's Welcome delivery.
- A device joins through a Welcome that consumes a private KeyPackage it issued only when it arrived as a sibling
  Welcome in its trusted device group, from a leaf whose device tag reads as the sender's slot, for a KeyPackage it
  recorded as handed to that slot and still keeps. Every other Welcome that consumes one is still rejected. The join
  stands if branch selection later withdraws the sibling Welcome.
- A sibling Welcome's relay list holds one to 16 entries, none repeated, each valid under the binding's relay rules.
- A transport binding carries Welcomes only for published KeyPackages, and the Nostr binding sends no kind `444` rumor
  for a never-published one. A sibling Welcome names its consumed KeyPackage by `KeyPackageRef`.
- When a device adds a sibling to a chat, and when it sends a sibling Welcome again, are not specified yet.

## 2026-10-30: Resending small state after a withdrawn device-group message (draft)

[#470](https://github.com/marmot-protocol/marmot/pull/470) changes
[features/account-sync.md](./features/account-sync.md).

- A device that does not keep which items a withdrawn update carried may send every item it holds again instead of only
  those items. A device that cannot tell whether a withdrawn device-group message was an update or a broadcast request
  may treat it as both. Receivers change nothing: each resent item keeps its version and change id, and merging a value
  it already holds changes nothing.

## 2026-10-30: Rejected KeyPackages, the compromise warning and leaves tied to a rejection (draft)

[#469](https://github.com/marmot-protocol/marmot/pull/469) changes
[features/device-group.md](./features/device-group.md),
[app-components/device-roster-v1.md](./app-components/device-roster-v1.md),
[app-components/device-tag-v1.md](./app-components/device-tag-v1.md),
[app-components/account-devices-v1.md](./app-components/account-devices-v1.md) and
[foundation/registries.md](./foundation/registries.md).

- A device that finds a valid KeyPackage it did not make in its own slot now also records it as a rejected KeyPackage in
  its device group's roster, besides replacing it. `RejectedKeyPackageV1` gains `leaf_signature_key`, the raw
  `signature_key` of the KeyPackage's LeafNode, and the roster's test vectors gain one. This changes the roster's
  encoding under the same id `0x800e`: while the component is a draft, its encoding can change, with no promise that
  revisions work together. A sibling that finds a valid KeyPackage, fresh or not, that no roster announced in a linked
  device's slot catches up on the device group, sends that device an anomaly alert (kind `462`, new), and rejects the
  KeyPackage itself if, a day later and caught up again, no roster has announced or rejected it, even when the slot no
  longer serves it or is no longer a device's. Catching up counts only after a fetch of the device group that succeeded.
  A device keeps each announcement it has seen for the longest time a KeyPackage can be valid. The slot's device answers
  an alert by announcing a KeyPackage it made again, even one it has since replaced, or, while its slot still serves one
  it did not make, by rejecting it; it never announces a current publication it did not make. Each device keeps the
  `KeyPackageRef` of every KeyPackage it publishes for that. No device rejects a KeyPackage any roster it held
  announced, or one whose LeafNode carries a device tag that reads as a device's, and each rejection is decided while
  the device holds the KeyPackage, so that it can read that tag: a sibling reads it before it alerts. A device keeps
  each rejected KeyPackage it records until the record lapses, committing it again when a branch selection drops the
  update that recorded it, and a device with no device group brings the ones it keeps, its own slot's included, into the
  device group it creates or joins.
- A device whose check is complete rejects each valid KeyPackage it finds as the current publication of a `not_me` slot,
  unless the same check finds it in another slot or a roster announced it. Answering This wasn't me starts a check. Each
  rejected KeyPackage is dropped 30 days after it was recorded, and a roster, a founding one included, and the
  rejections a device keeps each hold at most eight for one slot, the newest, so the roster stays bounded whatever the
  key holder publishes.
- A device warns its user whenever it rejects a sign-in or a KeyPackage, whenever its roster gains such a rejection,
  whenever it removes a leaf tied to one, and whenever it finds such a leaf in a group it cannot clean up. One warning
  stays open per account, it never claims the key holder was stopped, and dismissing it marks what it gathers as seen on
  that device only.
- Each device records the `KeyPackageRef` each of its account's leaves joined with, and removes, where it can, the
  leaves that no device claims and that joined with a KeyPackage its roster rejects or it has rejected itself: by a
  same-account Remove, now allowed for this by the sender rules of `marmot.group.account-devices.v1`, or as an admin. A
  leaf that no device claims is not evidence by itself and is never removed or warned about for that alone.
- A client that lets a new device start without the sign-ins its first check found answers Not now for every slot that
  check returned, never This wasn't me.

## 2026-10-30: Deleting a far-future publication in a device's own slot (draft)

[#468](https://github.com/marmot-protocol/marmot/pull/468) changes
[foundation/key-packages.md](./foundation/key-packages.md) and [transports/nostr.md](./transports/nostr.md).

- A device whose own slot serves a publication it did not make, dated further ahead than the device would date its own,
  cannot outrank it. The device may ask relays to delete that publication by id and then publish into its slot again.
  On Nostr the request is a kind `5` event at the current time with exactly one `e` tag naming the event and one `k`
  tag, `30443`. Receivers selecting KeyPackages still ignore `e` tags.

## 2026-10-30: Slot announcements, the own-slot check and private KeyPackages (draft)

[#459](https://github.com/marmot-protocol/marmot/pull/459) changes
[features/device-group.md](./features/device-group.md),
[app-components/device-roster-v1.md](./app-components/device-roster-v1.md),
[foundation/key-packages.md](./foundation/key-packages.md) and [foundation/registries.md](./foundation/registries.md).

- A device in a device group names each KeyPackage in its own roster entry (`announced_key_package`) before that
  KeyPackage reaches its slot, publishes only once the Commit carrying the announcement is in its group state, and
  never publishes an unannounced KeyPackage. The creating device's founding entry announces the KeyPackage it last
  published, as the founding Add announces the linked one. A client should tell its user while a refresh is held back
  for want of an announcement.
- Every device, in a device group or not, now reads its own slot at start and about daily. A current publication
  there other than its own latest, valid or not, is replaced by a newer KeyPackage of its own.
- Siblings in a device group hand each other private KeyPackages: single-use, never published, consumed only by a
  sibling's add; until sibling adds are specified, a device rejects any Welcome that consumes one. A device tops a
  sibling's stock up to 10 when it falls below 5. A request (kind `459`) and a hand-off (kind `460`), both new, travel
  only in the device group. A receiver keeps a hand-off only if every KeyPackage in it is its own account's, not
  last-resort and unexpired, and carries a device tag that reads as the sender's. It reads either message only when the
  sending leaf's device tag reads as the `from` slot the message names. A device may cap what it keeps for a sibling, at
  no fewer than 300, and never deletes a private KeyPackage early; at the cap it may hand over unconsumed ones again,
  without renewing them, and a holder never keeps one it has already used.
- Devices without a device group publish as before.

## 2026-10-30: Small-state sync between an account's devices (draft)

[#466](https://github.com/marmot-protocol/marmot/pull/466) adds [features/account-sync.md](./features/account-sync.md)
and registers kinds `475` and `476` in [foundation/registries.md](./foundation/registries.md). An account's devices keep
each chat's read position, pin, mute and archive state the same by exchanging items in their device group: an update
when the user changes one, and a broadcast of every item a device holds. Each item names its chat by raw MLS group id.
Only chats whose MLS group id is at most 256 bytes have small state. The furthest read position wins, in chat order by
epoch, `created_at` and `id`, a device's own position is the furthest message a position may name that its user has read
there, and a receiver judges a position by its encoding alone; for the other items the highest version wins, then the
lowest random change id, then the lowest value. A version stops at 9007199254740991, and no user can change an item held
there. Each device broadcasts when it starts, at least every 24 hours, and whenever the device group's tip moves past
the app-payload window since its last broadcast began. A starting device also sends a broadcast request, which each
sibling answers with one broadcast, at most once an hour. No device asks a particular sibling or tracks what its
siblings hold. A device reads these kinds only in its trusted device group, from any member, drops a message with a
repeated member name or item, skips item names it does not know, and keeps what a withdrawn message set. It resends the
items of every withdrawn update it sent or merged, and a new broadcast request for every withdrawn one it sent or read.
[features/device-group.md](./features/device-group.md) now says small-state messages name other groups and leaves them
to the new document, and [ideas/account-sync.md](./ideas/account-sync.md) and
[ideas/multi-device.md](./ideas/multi-device.md) point to the feature for these rules. Clients that do not support
device groups change nothing.

## 2026-10-29: Linking a device into the device group (draft)

[#456](https://github.com/marmot-protocol/marmot/pull/456) adds "Linking a device" to
[features/device-group.md](./features/device-group.md). An existing device answers a pairing request only if it is not
itself a new device in a session or waiting for its Welcome, and would link the named KeyPackage: its slot is not
already a device or rejected, by the roster or by the device itself, it supports everything the device group requires,
and the roster has room for another device. When the KeyPackage lacks something or the roster is full, it sends Cancel
`cannot_link` instead. The existing device's Confirm names the device group it trusts, or a fresh 16-byte random id for
the one it will create, and the signature key of its own leaf there, which it keeps through the Commit that adds the new
device so that key signs the Welcome. Once the link is confirmed it adds exactly the confirmed KeyPackage, in one Commit
that sets the new device's roster entry. A device that trusts no device group creates one first, and that Commit is the
founding Add. Another device of the account may already have one it cannot see; merging two is not specified yet. The
founding roster lists only the creating device, with the rejections it already holds, where #452's listed the linked
device too. The creating device's own entry has the "add to all my chats" and "bring chat history" settings on, as a new
device's are by default. Any Commit a device makes in the device group that adds a member, the founding Add included,
adds exactly one, by value, with that device's roster entry for a new slot: a same-account Add with the roster update,
committed as the group's admin, never a same-account Commit. It never adds a KeyPackage no confirmed link named,
including when re-inviting after a founding Welcome that could not be delivered. A device that cannot commit the link at
once may retry, but not after the new device stops waiting, counted from when the new device's Confirm arrived. Before
it sends its Confirm, the new device records the link with the pairing session's id, and keeps it across restarts until
it joins through the link's Welcome, 600 seconds have passed since that Confirm, a Cancel for that session arrives, or
it confirms a newer link, which replaces it; each pairing session uses a KeyPackage no earlier link of the device
confirmed. It joins only the Welcome from the named leaf into the named group that adds the confirmed KeyPackage, and
only if that group requires `0x800e`, deciding before it joins; it refuses every other device-group Welcome, and while
the link lasts any Welcome into the group id or that adds the confirmed KeyPackage, so a forged one or an invite to a
chat leaves the KeyPackage and the id for the real one. The approving device treats the link as made only once the new
device's first Commit there, which sets its tag signature key, is on the selected branch with no input for the group
pending; the new device makes it as soon as it can once it has joined. Once made, a link stays made. If that Commit has
not come 3600 seconds after the `linked_at` the approving device wrote in the new device's entry, and is still missing
once it has processed the input it holds for the group, the approving device, and only it, removes the new device's leaf
and roster entry in one Commit and stops delivering the Welcome. A device whose leaf is removed from its device group
stops trusting the group and must discard its copy's active state, keeping at most its history and a removal tombstone,
so a later link's Welcome into the same id is a first join; a new device removed before its first Commit there tells its
user that linking failed. Clients that do not support `0x800e` change nothing.

## 2026-10-29: Device pairing (draft)

[#454](https://github.com/marmot-protocol/marmot/pull/454) adds
[features/device-pairing.md](./features/device-pairing.md), registers kinds `452` to `456` and reserves `457` to `489`
for multi-device accounts in [foundation/registries.md](./foundation/registries.md), adds "Pairing delivery" and its
entry in "Validation before peeling" to [transports/nostr.md](./transports/nostr.md), and makes
[protocol-core/joining.md](./protocol-core/joining.md) run any check a feature requires before a Welcome is joined
inside the tentative validation, so a Welcome that fails one consumes no KeyPackage. The feature is a draft. A new
device, the one whose user asks to link it and which has no device group, and an existing device, any other device of
the same account, compare a code: Matrix's `m.sas.v1` verification, transcribed into Marmot encodings and shown as seven
emoji from Matrix's table. The five messages are rumors gift-wrapped from the account to itself. The new device commits
to its key in its request; the code binds the session, the account, the new device's `KeyPackageRef`, the answering
device's slot and both keys; and the two confirmations cover the `KeyPackageRef`, and the id of the group the new device
joins with the signature key of the existing device's leaf there, the only sender whose Welcome the new device accepts.
While the link lasts, the new device joins no other Welcome into that group or that adds that KeyPackage, and joins the
link's Welcome only if its group requires `0x800e`.
The existing device confirms first, and the new device confirms only after verifying the existing device's confirmation.
An existing device sends at most 10 Answers an hour, and none while more than one request is live. Clients that do not
link devices need no changes.

## 2026-10-29: New sign-ins in the device group (draft)

[#465](https://github.com/marmot-protocol/marmot/pull/465) changes
[features/device-group.md](./features/device-group.md) and
[app-components/device-roster-v1.md](./app-components/device-roster-v1.md). A client that supports `0x800e` reads its
account's KeyPackages as an inviter does, and treats a slot holding a valid, fresh KeyPackage that is not its own, not a
roster device's and not a rejected slot as a sign-in to ask its user about. A Welcome naming a KeyPackage it did not
publish is a reason to fetch and check that KeyPackage, never evidence by itself. Slots its first check returns, fresh
or not, are devices that were signed in before it; others are new sign-ins, and a publication's time never decides
which. "This wasn't me" commits a `not_me` rejected slot, never a rejected KeyPackage, since the KeyPackage may be a
copy of a real device's. A device with no device group keeps its rejections and writes them into the roster it later
creates or joins. A device keeps its rejections until the roster holds the slot as a device, commits one again whenever
the roster has no entry for that slot, and never replaces an entry. A link or rejection on one device ends the question
on all of them while the roster holds it. A device keeps its list of sign-ins and its answers across restarts. A sign-in
whose slot a complete check finds holding no valid KeyPackage that a deletion does not cover stays listed as no longer
signed in, and can be linked again once a complete check finds one; being no longer fresh never on its own signs a
sign-in out. A check is complete only from one unbounded answer per query from every relay in the account's non-empty
KeyPackage relay set, each short of the limit the device asked for; an account past one answer, and a relay capping
below the request without advertising it, are stated limits. Clients that do not support `0x800e` change nothing.

## 2026-10-28: Device roster component and device group (draft)

[#452](https://github.com/marmot-protocol/marmot/pull/452) adds
[app-components/device-roster-v1.md](./app-components/device-roster-v1.md),
[app-components/device-tag-v1.md](./app-components/device-tag-v1.md) and
[features/device-group.md](./features/device-group.md), registers `0x800e` and `0x800f` in
[foundation/registries.md](./foundation/registries.md), and changes
[app-components/README.md](./app-components/README.md) to allow a component to define a diff-style update. All three
new documents are drafts. A group that requires `0x800e` from creation is an account's device group. Its roster holds
devices, rejected slots, rejected KeyPackages and the key that seals device tags; its update is a diff that sets or
removes single entries against the candidate parent's roster, every leaf has the same credential identity, and no Commit
or proposal may start or stop requiring it. A device SHOULD drop a `removed` slot record 30 days after it was recorded.
A client that supports `0x800e` treats its entry and updates as unknown data in a group that does not require it, and
MUST NOT write one there. A device trusts a group as its device group only if it created it or joined it through a
Welcome a confirmed link named, MUST NOT join a group that requires `0x800e` through any other Welcome, and founds it
with only the KeyPackage that link confirmed. A linked device puts a device tag (`0x800f`) in every KeyPackage and
LeafNode it creates, so that its siblings can tell which of the account's leaves belongs to which device. A tag is
verified with the tag signature key of the roster entry it names, or of the `removed` record that keeps that key. A tag
never makes anything invalid, and a Commit or Welcome that requires `0x800f` is invalid. Clients that support neither
component change nothing.

## 2026-10-28: Activation eligibility reasons and lost activations

[#453](https://github.com/marmot-protocol/marmot/pull/453) changes
[app-components/README.md](./app-components/README.md) and
[app-components/account-devices-v1.md](./app-components/account-devices-v1.md). A client does not commit an activation
again on its own after it loses branch selection or fails its checks when regenerated from the queue; it activates only
if its user asks again. A client MAY tell its user why a group cannot activate `marmot.group.account-devices.v1` yet,
as a reason about the whole group that never names the members or devices holding it back.

## 2026-10-27: Fair scheduling covers admin and same-account intents only

[#450](https://github.com/marmot-protocol/marmot/pull/450) changes
[protocol-core/convergence.md](./protocol-core/convergence.md) and
[protocol-core/group-state.md](./protocol-core/group-state.md). The preparation attempt after a bounded pass goes to a
queued admin-authorized intent or a same-account intent, not to every intent the member may commit; a self-update or a
Leave does not receive it. [#443](https://github.com/marmot-protocol/marmot/pull/443) had widened the rule to every
authorized intent. A client that gave a queued self-update or Leave the attempt stops doing so. Admin and same-account
intents keep it.

## 2026-10-26: Push token snapshots, announces, and repair

[#447](https://github.com/marmot-protocol/marmot/pull/447) changes
[features/push-notifications.md](./features/push-notifications.md) and says when members send push-token gossip. It also
adds a non-normative note to [implementation-model.md](./implementation-model.md) on the per-group state a client keeps,
keeping complete removal entries so tombstones can be relayed, and measuring the size budget on the published group
message. A member that commits a Commit adding leaves, including a same-account device add, SHOULD send a snapshot after
merging it: kind `448` lists of every active record it holds and kind `449`s relaying every tombstone it holds. A member
that holds neither sends nothing. Kind `447` gains an optional `have` member, the first 8 bytes of
`SHA-256(SignedRecord)` in standard base64 for every record and tombstone the sender holds, at most 4,096 of them; a
`447` that carries it is an announce. A joined device has a join window lasting T (at least one minute) after its join
completes, which includes fetching the group's messages from its join epoch on; offline time does not count. It sends no
`have` inside the window, and SHOULD announce once when the window ends, whether or not snapshot events arrived. After
the window, or at once for the group's creator, a device SHOULD also announce when its record changes, and with its next
message in a group when it has not announced there within an implementation-defined interval, which a device that has
never announced there has not. Members rank every non-blank leaf except the announcer's sender leaf by `SHA-256(announce
id bytes || leaf_index)`. Only the devices at the top three leaves reply, after staggered waits, with only the missing
records and tombstones. A reply is cancelled once entries carried in the announce's epoch or later cover it. A device
SHOULD NOT send more than one repair reply per announcer's leaf per group in 24 hours, and treats an empty `447` without
`have` as its sender's announce holding nothing. A device whose record is missing from a snapshot SHOULD re-share it,
and while a group may contain clients without these rules, SHOULD re-share it after any Commit that adds leaves. Lists
are split by a byte budget, 65,536 bytes per published message by default; the 32-entry maximums on `tokens` in kinds
`447` and `448` and on `removals` in kind `449` are unchanged. Removal entries can be relayed by any member, and a
winning removal writes its tombstone even when no record for the key is stored. Clients that do not implement these
rules apply what they receive as before, and read an announce as a plain self-update.

## 2026-10-26: Senders pad every push trigger

[#445](https://github.com/marmot-protocol/marmot/pull/445) changes
[features/push-notifications.md](./features/push-notifications.md). A sender must append at least one padding chunk to
every kind `446` trigger: 1084 bytes from a cryptographically secure random generator, fresh for each trigger. A
trigger therefore carries at most 31 `EncryptedToken`s, and padding counts toward any smaller per-trigger chunk limit a
sender applies; a sender that splits its tokens across several triggers pads each one. Without padding, a sender's
triggers that carry the same tokens have identical content, and a server deduplicating by content hash discards real
triggers as replays. Notification servers do not change: the dedup hash covers every chunk, padding included, and a
server must not ignore a structurally valid trigger because it appears to carry no padding.

## 2026-10-26: Devices can add and remove their own account's leaves

[#443](https://github.com/marmot-protocol/marmot/pull/443) adds
[app-components/account-devices-v1.md](./app-components/account-devices-v1.md) and changes
[app-components/README.md](./app-components/README.md),
[app-components/admin-policy-v1.md](./app-components/admin-policy-v1.md),
[foundation/identity.md](./foundation/identity.md), [foundation/registries.md](./foundation/registries.md),
[protocol-core/joining.md](./protocol-core/joining.md),
[protocol-core/member-departure.md](./protocol-core/member-departure.md),
[protocol-core/group-messaging.md](./protocol-core/group-messaging.md),
[protocol-core/group-setup.md](./protocol-core/group-setup.md),
[protocol-core/publish-lifecycle.md](./protocol-core/publish-lifecycle.md),
[protocol-core/convergence.md](./protocol-core/convergence.md), and
[protocol-core/group-state.md](./protocol-core/group-state.md). It registers adopted component `0x800d`,
`marmot.group.account-devices.v1`, which has no data. In a group that requires it, any member may commit a same-account
Commit without admin authority: Add proposals for KeyPackages of its own account and Remove proposals for its account's
other leaves, by value and with no other proposal. An added KeyPackage must advertise everything the resulting group
requires, and no requirement may be dropped so that a device fits; while a group requires the component, every leaf must
advertise it. `tip_priority` is now one test: a Commit is `ordinary` when one rule that permits a non-admin committer
covers all of it, whoever commits it, and `privileged` otherwise. A same-account Commit is therefore `ordinary` even
from an admin. Self-update and SelfRemove-only Commits were already `ordinary` under the earlier wording, an admin's
included, so their scoring does not change. No account may have more than `max_leaves_per_account` leaves, a constant
fixed at 20 that only a new component id can change. A group can never stop requiring the component. A joiner accepts a
Welcome from its own account when the joined state requires the component. A creator whose client supports it must
require it when every founding leaf advertises it; existing groups activate it by an admin Commit. In such a group a
client must not add a KeyPackage of its own account only because it is published under the account's key, except in the
founding Add Commit. A device of an admin account can leave through a Remove by its sibling, so the SelfRemove rule for
admins is unchanged. A component may now have no data location. The fair scheduling rule now covers queued
same-account intents as well as admin ones. Apart from that rule, groups that do not require the component are
unaffected.

## 2026-10-19: Several devices per account

[#442](https://github.com/marmot-protocol/marmot/pull/442) changes [foundation/identity.md](./foundation/identity.md),
[foundation/key-packages.md](./foundation/key-packages.md), [foundation/registries.md](./foundation/registries.md),
[protocol-core/joining.md](./protocol-core/joining.md),
[protocol-core/member-departure.md](./protocol-core/member-departure.md),
[protocol-core/publish-lifecycle.md](./protocol-core/publish-lifecycle.md),
[transports/nostr.md](./transports/nostr.md), and [transports/quic.md](./transports/quic.md). A device is one client
installation, and it must not copy MLS state or KeyPackage private keys to another device. Each device must publish
into exactly one KeyPackage slot for its lifetime; a client that used several keeps one and SHOULD delete the rest.
Devices SHOULD use 30-day KeyPackage lifetimes, refresh their slot at least every 7 days, keep a superseded
KeyPackage's `init_key` through the 24-hour replacement grace period, and delete their slot with a NIP-09 kind `5`
request when they sign out. Inviters SHOULD add every KeyPackage an account published in the last 30 days, must not
add more than 20 for one account in one Commit, must not select one covered by a deletion request they hold, and must
not select one that lacks any capability the resulting group requires. The Nostr KeyPackageRef tie-break now only
orders equal candidates and drops one only when selection has to cut. An inviter makes one Welcome delivery for each
KeyPackage it adds; a device that receives a delivery naming a sibling's KeyPackage does not treat it as a failed join.
Removing an account means removing all of its leaves in one Commit. KeyPackage events MAY carry a one-value `client`
tag, which no other Nostr event shape in the binding may carry. The QUIC binding states that it carries no KeyPackages
or Welcomes.

## 2026-10-16: Replaced KeyPackage init keys outlive replacement by 24 hours

[#440](https://github.com/marmot-protocol/marmot/pull/440) changes
[foundation/key-packages.md](./foundation/key-packages.md). After a successful Welcome, a last-resort KeyPackage's
`init_key` must now be deleted 24 hours after confirmed publication of its replacement, or at `Lifetime.not_after` if
that is earlier. Before, it had to be deleted at confirmed replacement. Clients SHOULD keep the key for the whole grace
period, so that a Welcome built from the old publication before the replacement reached the inviter can still be
processed.

## 2026-10-15: Existing groups can adopt new app components

[#439](https://github.com/marmot-protocol/marmot/pull/439) changes [app-components/README.md](./app-components/README.md),
[foundation/key-packages.md](./foundation/key-packages.md), and
[app-components/group-lifecycle-v1.md](./app-components/group-lifecycle-v1.md). A client SHOULD replace its published
KeyPackages when the set of component ids it supports changes, and keep advertising every id it still supports. It
refreshes a stale own leaf after a randomized delay. Once every leaf advertises an id, an authorized member can activate
the component in one Commit. Activation is always an explicit decision. Lifecycle-v1 enablement follows this process.

## 2026-10-05: Nostr KeyPackage discovery without kind 10051

[#422](https://github.com/marmot-protocol/marmot/pull/422) adds a migration subsection to
[transports/nostr.md](./transports/nostr.md). It changes no requirement. It spells out that the kind `10002`
write-capable relay set is where kind `30443` KeyPackages are published and fetched, with no kind `10051` step, and that
kind `10050` stays the source of Welcome inbox relays. Relays where metadata was found are lookup locations, not
advertised destinations.

## 2026-09-20: Encrypted NIP-88 polls

[#425](https://github.com/marmot-protocol/marmot/pull/425) changes
[foundation/application-messages.md](./foundation/application-messages.md) and
[foundation/registries.md](./foundation/registries.md). NIP-88 poll kinds `1068` and `1018` are ordinary Marmot app
events inside MLS. Inner `relay` tags do not select relays; authenticated group routing does. Supporting polls is
optional, and polls are neither anonymous nor fit for elections.

## 2026-09-16: Group reports, dismissal labels, and admin deletion

[#423](https://github.com/marmot-protocol/marmot/pull/423) adds
[features/content-moderation.md](./features/content-moderation.md) and changes
[foundation/application-messages.md](./foundation/application-messages.md) and
[foundation/registries.md](./foundation/registries.md). It registers three app-event kinds: `1984` for
NIP-56 reports of messages in the same group, `1985` for NIP-32 `marmot.report-review.v1` / `dismissed` labels on
reports, and `4891` for an admin's deletion of any member's chat message with its edits and attachments. Admin
authority is checked against the event's authenticated source-epoch state, and a dismissal does not override a deletion.

## 2026-08-13: Durability and restart contract

[#416](https://github.com/marmot-protocol/marmot/pull/416) adds [protocol-core/durability.md](./protocol-core/durability.md)
and changes [protocol-core/convergence.md](./protocol-core/convergence.md),
[protocol-core/group-state.md](./protocol-core/group-state.md),
[protocol-core/inbound-processing.md](./protocol-core/inbound-processing.md),
[protocol-core/publish-lifecycle.md](./protocol-core/publish-lifecycle.md),
[protocol-core/retained-history.md](./protocol-core/retained-history.md),
[foundation/conformance.md](./foundation/conformance.md), and [foundation/errors.md](./foundation/errors.md). A restart must
not change canonical branch selection, input dispositions, unresolved outbound gates, or the application-visible
projection. Possible external acceptance without a recoverable acknowledgement remains `PendingPublish`. There are no
wire, component, or registry changes.

## 2026-07-30: Convergence assurance and deferred input

[#410](https://github.com/marmot-protocol/marmot/pull/410) adds [foundation/conformance.md](./foundation/conformance.md)
and changes [protocol-core/convergence.md](./protocol-core/convergence.md),
[protocol-core/group-state.md](./protocol-core/group-state.md),
[protocol-core/inbound-processing.md](./protocol-core/inbound-processing.md),
[protocol-core/retained-history.md](./protocol-core/retained-history.md),
[foundation/errors.md](./foundation/errors.md), [foundation/registries.md](./foundation/registries.md), and
[transports/nostr.md](./transports/nostr.md). Transport-deferred and resource-refused input is now distinct
from stale, invalid, or deduplicated input. It must stay refetch-eligible instead of being discarded when a local retry
or storage limit is reached, and the affected range must not be reported as synchronized. A change to state-selecting
convergence policy needs an explicit capability or component. The conformance projection is test-only.

## 2026-07-28: Group disbanding

[#409](https://github.com/marmot-protocol/marmot/pull/409) adds
[app-components/group-lifecycle-v1.md](./app-components/group-lifecycle-v1.md) and changes
[app-components/README.md](./app-components/README.md),
[app-components/admin-policy-v1.md](./app-components/admin-policy-v1.md),
[foundation/application-messages.md](./foundation/application-messages.md),
[foundation/registries.md](./foundation/registries.md),
[protocol-core/convergence.md](./protocol-core/convergence.md),
[protocol-core/group-setup.md](./protocol-core/group-setup.md),
[protocol-core/group-state.md](./protocol-core/group-state.md),
[protocol-core/inbound-processing.md](./protocol-core/inbound-processing.md), and
[protocol-core/member-departure.md](./protocol-core/member-departure.md). It registers required app component `0x800c`,
`marmot.group.lifecycle.v1`, with an irreversible `Active` to `Disbanded` transition made by an authenticated admin
Commit. `Disbanded` becomes the sixth
canonical group lifecycle state. New groups require the component and start `Active`. An existing group can disband only
after an admin enables the component in one Commit and every current leaf advertises support.

## 2026-07-23: Push owner proofs signed as unpublished Nostr events

Commit [`dedeaf4`](https://github.com/marmot-protocol/marmot/commit/dedeaf4) changes
[features/push-notifications.md](./features/push-notifications.md) and
[foundation/registries.md](./foundation/registries.md), plus two multi-device documents that
[#427](https://github.com/marmot-protocol/marmot/pull/427) later replaced with an idea document. A push token or removal entry's `owner_sig` is now a BIP-340
signature over the id of an exact, unpublished kind `451` Nostr event. `SHA-256(SignedRecord)` remains only the ordering
tie-breaker, and the legacy signature preimage is not reinterpreted.

## 2026-07-23: Specification issue sweep

[#408](https://github.com/marmot-protocol/marmot/pull/408) resolves 200 specification issues, one commit each, across
[53 files](https://github.com/marmot-protocol/marmot/pull/408/files). The changes implementers most often need:

- Membership and admin authority is checked against candidate parent state. A group has a non-empty admin policy from
  creation, and losing every admin freezes governance.
- Convergence is bounded and deterministic, with defined retained-history behavior and canonical-state-derived
  self-removal.
- Welcome, KeyPackage, publish-before-apply, rollback, Nostr routing, fetch, and acknowledgement rules are aligned. This
  set the KeyPackage `init_key` deletion bound that #440 later relaxed.
- Push v1 is stateless and best-effort. Service revocation, storage, and rate policy are outside the wire protocol.
- Encrypted-media, group-image, retention, component, registry, identity-proof, and inner sender-binding rules are
  repaired.
- Endpoint reachability, DNS and SSRF policy, remote-fetch consent, storage, and application-event ordering are not
  part of protocol validity.
- The QUIC preview documents are corrected and are not required for Marmot operation.

## 2026-07-05: Adopted baseline

The oldest commit on `master` contains the adopted specification as it stood after
[#236](https://github.com/marmot-protocol/marmot/pull/236) tightened the wire-boundary validation rules in
[foundation/canonical-encoding.md](./foundation/canonical-encoding.md),
[foundation/key-packages.md](./foundation/key-packages.md), and [transports/nostr.md](./transports/nostr.md). That
specification was imported in [#71](https://github.com/marmot-protocol/marmot/pull/71), marked adopted in
[#170](https://github.com/marmot-protocol/marmot/pull/170), and had its admin-policy, membership, and role-change rules
aligned in [#171](https://github.com/marmot-protocol/marmot/pull/171). Later entries are relative to this baseline.
