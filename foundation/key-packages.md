# KeyPackages

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#t4-device-account-key-and-reusable-keypackage-compromise).

This document defines KeyPackage meaning, discovery requirements, and lifecycle.

KeyPackages are how Marmot supports asynchronous invites. Each of a user's devices publishes a usable KeyPackage before
an inviter is online. Later, an inviter fetches them, adds a leaf for each KeyPackage it selects ("Selection and
lifecycle" below), and sends each selected device a Welcome.

## Surfaces

- Foundation identity and capability negotiation.
- MLS protocol: `BasicCredential`, KeyPackage, KeyPackageRef, capabilities, and `last_resort_key_package`.
- Transport binding for KeyPackage publication and discovery.
- Protocol-core joining flow for consuming a KeyPackage through a Welcome.
- Registries for app component ids, MLS proposal ids, and transport kinds.

This document does not define new group state. It defines account/device readiness for future group joins.

## Behavior

Each Marmot account is identified by a Nostr public key. The MLS credential identity is the raw 32-byte x-only public
key, not hex text and not an `npub`.

Each MLS leaf has its own MLS signing key. That signing key proves the leaf. It is separate from the Nostr account
identity in the credential.

A KeyPackage belongs to the account named by its credential identity and to the device that generated it
([identity.md](./identity.md), "Devices").

Every Marmot KeyPackage MUST carry `marmot.member.account-identity-proof.v2` in the
`app_data_dictionary` of its embedded LeafNode. The proof binds the credential identity to that LeafNode's MLS
signature public key. A KeyPackage without a valid proof is malformed.

When a KeyPackage is published through a transport object, the transport binding defines how the outer author or sender
is checked against the credential identity.

Only the public KeyPackage bytes are published. Private `init_key` material is never published. If implementation APIs
expose a `KeyPackageBundle` type, only the public KeyPackage bytes belong in a transport publication. Those public
KeyPackage bytes are carried inside an `MLSMessage` with `wire_format = mls_key_package` (RFC 9420 §6), so a transport
publication is unambiguously the framed `MLSMessage`, not a bare `KeyPackage` struct. The `KeyPackageRef` is computed
over the inner `KeyPackage` (RFC 9420 `MakeKeyPackageRef`), not over the `MLSMessage` envelope.

## Capability advertising

KeyPackages advertise what that client/device can support. Group creation and member addition use these capabilities to
avoid creating a group that some member cannot process.

Every Marmot KeyPackage MUST carry `marmot.member.account-identity-proof.v2` in its embedded LeafNode and advertise
component id `0x8009` in that LeafNode's `app_components` support list as required by
[../app-components/account-identity-proof-v2.md](../app-components/account-identity-proof-v2.md). The remaining
current-profile capabilities are listed by namespace in [registries.md](./registries.md): the LeafNode advertises the
`app_data_dictionary` extension and the relevant proposal types in MLS capabilities, including `app_data_update`
(`0x0008`), and its `app_components` entry advertises the Marmot component ids the client supports.

When the set of component ids a client supports changes, the client SHOULD replace the KeyPackage in its publication
slot ("Devices and publication slots" below) with one that advertises the new set. A replacement keeps advertising
every component id the client still supports, so the client can still be added to groups that do not yet require a
newly added id. Leaves in groups the client has already joined change separately (see
[../app-components/README.md](../app-components/README.md), "Enabling a Component in an Existing Group").

Last-resort status is not an MLS capability or extension type. A last-resort KeyPackage carries an
`app_data_dictionary` in its KeyPackage extensions, separate from the dictionary in its embedded LeafNode, with an
empty-data `last_resort_key_package` component entry. A KeyPackage that is not last-resort MUST NOT contain that entry.

A member can join only if its KeyPackage advertises support for every MLS primitive, app component, and component-owned
role capability the group requires. For example, an agent-stream-ready group may require the agent text stream `receive`
role, whose fallback behavior is defined by the owning feature and component documents.

## Devices and publication slots

An account MAY be signed in on several devices ([identity.md](./identity.md), "Devices"). Each device publishes its own
KeyPackages, and an inviter adds each device it selects as its own leaf, so one account can have several leaves in a
group.

A publication slot is the place where a newer KeyPackage publication from an account replaces an older one. The active
transport binding defines what a slot is, how its id is generated, and how a publication in it is replaced or deleted.
A slot id MUST NOT be derived from the account key, an MLS leaf key, a KeyPackageRef, a device label, or other identity
material.

Each device publishes into exactly one slot:

- a device creates its slot once and keeps it for the device's lifetime;
- a device MUST NOT publish KeyPackages into a second slot;
- a device MUST NOT publish into, replace, or delete a slot it did not create, unless a feature document explicitly
  allows it.

Another device of the same account creates its own slot. That includes a different Marmot client on the same hardware
and a reinstall of the same client. Each of an account's current slots therefore stands for one device, and inviters
select per slot ("Selection and lifecycle" below).

### Refreshing a slot

A device SHOULD give each KeyPackage it publishes a `Lifetime` range of no more than 2,595,600 seconds: 30 days plus a
one-hour clock-skew margin. This is a publishing target. The validity limit in "Selection and lifecycle" below is
unchanged, so a receiver MUST NOT reject a longer range that is within that limit.

A device SHOULD publish a new KeyPackage into its slot:

- after a Welcome consumes the current one ("Selection and lifecycle" below);
- when the capabilities it advertises change ("Capability advertising" above);
- at least every 7 days while the client runs, even when nothing else has changed;
- before the current KeyPackage's `Lifetime.not_after`.

Each of these publications carries a newly generated KeyPackage and is a replacement under the deletion bound in
"Selection and lifecycle" below.

An inviter can fetch the superseded KeyPackage just before the replacement reaches it. A device SHOULD therefore keep
the `init_key` of a superseded KeyPackage that no Welcome has consumed until the replacement grace period in
"Selection and lifecycle" ends, or until that KeyPackage's `Lifetime.not_after` when that is earlier. Publishing a
replacement is not, by itself, a reason to stop accepting the superseded KeyPackage. A consumed KeyPackage follows the
deletion bound instead, and a device that signs out MAY delete at once ("Stopping publication" below).

The weekly refresh keeps the slot's publication time recent, which is how an inviter tells a device that still exists
from one that has been uninstalled. A client can refresh only while it runs, so a device that is rarely opened looks
older than it is.

### A publication the device did not make

Anyone holding the account's signing key can publish into any of its slots. A device SHOULD read its own slot when it
starts and then about once a day, from every place the active transport binding lets it read the slot's current
publication. If any of them serves, as the current publication, anything other than the device's own latest publication,
the device SHOULD publish a new KeyPackage of its own into the slot, with a later publication time than every such
publication. That includes an earlier KeyPackage of the device's own that someone published again: the device may no
longer hold its `init_key`. The publication's transport authentication is enough to count it: one whose content is not a
valid KeyPackage still occupies the slot. The device reads the slot itself, not a page of the account's publications, so
that the account's other slots cannot crowd its own out.

A publication dated further ahead of the device's clock than the device would date its own cannot be outranked: a later
publication time would put the device's own just as far ahead. The device does not try. It MAY instead ask the transport
to delete that one publication by its identifier, using the active transport binding's mechanism for that
([../transports/nostr.md](../transports/nostr.md), "Deleting one publication"), and then publish a new KeyPackage of
its own into the slot, later than every other publication it found there. It deletes publications this way only in its
own slot. A transport that ignores the request keeps serving the publication, and the device's next read of the slot
finds it again. A transport that honors it serves nothing in the slot until the new KeyPackage reaches it. When a read
of a place that accepted the device's latest publication reaches the end of what that place serves and finds nothing in
the slot, the device SHOULD publish a new KeyPackage of its own into the slot, not the latest one again: a deletion of
the whole slot also covers the latest publication. It SHOULD NOT publish one this way before its latest publication is a
day old, so that a place that accepts publications and keeps none costs one KeyPackage a day. A device its device group
removed SHOULD NOT publish one this way at all: the device that decided the removal deleted the slot
([../features/device-group.md](../features/device-group.md), "The removed device's slot"). A read that failed or
stopped short shows nothing.

A device in a device group announces that KeyPackage first, like any other
([../features/device-group.md](../features/device-group.md), "Slot announcements").

### Stopping publication

When a device signs out, it SHOULD delete the publication in its own slot using the active transport binding's
deletion mechanism. It deletes only its own slot.

Deletion asks the transport to stop serving the KeyPackage. It does not revoke it: a copy that a transport keeps serving
remains a valid candidate until its `Lifetime.not_after`. A device that has signed out no longer accepts Welcomes, so it
MAY delete the private key material of its KeyPackages at once under the early-deletion rule below.

## Selection and lifecycle

An inviter usually sees several current KeyPackages for one account, one in each of the account's slots. When it adds an
account to a group, including at founding creation, it adds one leaf for each KeyPackage it selects for that account.

Before ranking candidates, an inviter MUST perform the validation listed below and any additional checks required by the
active transport binding. It MUST reject malformed or incompatible candidates before selecting any.

A candidate is compatible only when it advertises support for every MLS primitive, app component, and component-owned
role capability that the group requires once the Commit is applied ("Capability advertising" above). At founding
creation, that is the set the creator will require. Freshness never overrides this: an inviter MUST NOT select an
incompatible candidate, even when it is the account's only one. The group's requirements come from what the group
needs, not from the candidates found, so an inviter SHOULD NOT leave a requirement out of a new group only so that more
of an account's devices qualify.

The active transport binding keeps at most one current publication per slot and defines a candidate's publication
time. A candidate is fresh when its publication time is no more than 2,592,000 seconds (30 days) before the selection
time.

When an inviter adds an account to a group, it SHOULD select every valid, fresh candidate for that account. It MUST NOT
select more than 20 KeyPackages for one account in one Commit; when more than 20 fresh candidates remain, it selects the
20 highest-ranked. This limit binds the inviter, and a receiver does not check it. When the account has no fresh
candidate, the inviter MAY select the single highest-ranked valid candidate, so that an account whose devices are
rarely opened can still be invited.

The ranking carried forward from the MIP-era documents (the prior Marmot Improvement Proposals; see
[../mip-coverage.md](../mip-coverage.md)) prefers valid non-last-resort candidates, then the most recently published
candidates. Candidates that are still equivalent are ordered by the deterministic content-derived tie-breaker defined
by the transport binding. A transport binding owns any transport-specific replacement, address, and tie-breaking rules.

An inviter that selects only one KeyPackage for an account still produces a valid group. The account's other devices
are then not members of that group until they are added separately.

Candidate freshness is only a KeyPackage selection input. It MUST NOT create group state and MUST NOT override decoded
KeyPackage validity, account identity proof validity, capability compatibility, or transport author binding.

The MLS `Lifetime` extension is part of KeyPackage validity. A Marmot KeyPackage candidate MUST carry a `Lifetime`
extension, MUST be current at validation time (the validation time is not before `not_before` and not after `not_after`),
and MUST have `not_after - not_before <= 7,261,200` seconds. The range is 84 days plus a one-hour clock-skew margin. A
last-resort KeyPackage does not relax this limit.

After a client successfully processes a Welcome that consumed a published KeyPackage, it SHOULD publish a fresh
replacement into its slot according to the active transport binding.

The private `init_key` material for a consumed non-last-resort KeyPackage MUST be deleted after successful Welcome
processing. A last-resort KeyPackage MAY keep its `init_key` after a successful Welcome so that the published package
remains usable, but it MUST delete that material at the earlier of:

- the end of the replacement grace period, 24 hours (86,400 seconds) after confirmed publication of a replacement under
  the active transport binding;
- the KeyPackage `Lifetime.not_after` time.

A confirmed replacement is any successfully published KeyPackage that supersedes the old publication under the active
transport's authenticated slot or replacement rule. The replacement does not itself need to carry the
`last_resort_key_package` component.

An asynchronous transport cannot prove that every Welcome already encrypted to the superseded last-resort KeyPackage
has arrived. An inviter can fetch the old publication just before the replacement reaches it, so a Welcome built from
the old KeyPackage can arrive after the replacement is confirmed. A client SHOULD keep the old `init_key` until the
replacement grace period ends so that such a Welcome can still be processed. A Welcome that arrives after the material
is deleted is undecryptable; this is the deliberate confidentiality-versus-availability trade-off of the deletion bound.
The inviter can retry with a currently published KeyPackage.

A client MAY delete the material earlier after it stops accepting that KeyPackage. Local retention policy MUST NOT
extend either bound.

Welcome confidentiality depends on the referenced KeyPackage's private `init_key` remaining secret. Compromise of that
key before deletion lets an attacker decrypt every recorded Welcome encrypted to that KeyPackage and recover the join
secrets carried by those Welcomes. Reuse makes this exposure apply to multiple joins for a last-resort KeyPackage, and
the replacement grace period extends the exposure by at most 24 hours after the replacement is confirmed.
Possession of the `init_key` alone does not let the attacker advance through later commits after the joined leaf's other
private state has changed or been erased.

## Failure behavior

A client MUST NOT rotate or delete the consumed KeyPackage if Welcome processing fails. The existing KeyPackage remains
available so the inviter can retry or choose another candidate.

A client MUST reject a published KeyPackage when:

- the decoded content is not a valid MLS KeyPackage;
- the KeyPackage `Lifetime` extension is missing, the validation time is before `not_before` or after `not_after`, or
  the total range is longer than 7,261,200 seconds;
- the credential identity is not a valid Marmot account identity;
- the account identity proof component is missing or invalid;
- the transport author or sender does not match the credential identity under the active transport binding;
- the transport publication encoding is invalid;
- required capability tags are missing or incompatible;
- a publication carries a KeyPackageRef hint and it does not match the decoded KeyPackageRef.

Transport-specific KeyPackage publication details live in [../transports/nostr.md](../transports/nostr.md).
