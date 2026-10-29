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
