# KeyPackages

Status: adopted.

This document defines KeyPackage meaning, discovery requirements, and lifecycle.

KeyPackages are how Marmot supports asynchronous invites. A user can publish one or more usable KeyPackages before an
inviter is online. Later, an inviter fetches one, adds that user to a group, and sends a Welcome.

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

A KeyPackage belongs to the account named by its credential identity.

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

When the set of component ids a client supports changes, the client SHOULD replace its published KeyPackages with
KeyPackages that advertise the new set. A replacement keeps advertising every component id the client still supports,
so the client can still be added to groups that do not yet require a newly added id. Leaves in groups the client has
already joined change separately (see [../app-components/README.md](../app-components/README.md), "Enabling a Component
in an Existing Group").

Last-resort status is not an MLS capability or extension type. A last-resort KeyPackage carries an
`app_data_dictionary` in its KeyPackage extensions, separate from the dictionary in its embedded LeafNode, with an
empty-data `last_resort_key_package` component entry. A KeyPackage that is not last-resort MUST NOT contain that entry.

A member can join only if its KeyPackage advertises support for every MLS primitive, app component, and component-owned
role capability the group requires. For example, an agent-stream-ready group may require the agent text stream `receive`
role, whose fallback behavior is defined by the owning feature and component documents.

## Selection and lifecycle

An inviter MAY see several current KeyPackages for one account. It MUST reject malformed or incompatible candidates
before selecting one.

The selection policy carried forward from the MIP-era documents (the prior Marmot Improvement Proposals; see
[../mip-coverage.md](../mip-coverage.md)) prefers valid non-last-resort candidates when available, then prefers the
freshest valid candidate. A transport binding owns any transport-specific replacement, address, and tie-breaking rules.

Before ranking candidates, an inviter MUST perform the validation listed below and any additional checks required by the
active transport binding. Candidate freshness is only a KeyPackage selection input. It MUST NOT create group state and
MUST NOT override decoded KeyPackage validity, account identity proof validity, capability compatibility, or transport
author binding.

The MLS `Lifetime` extension is part of KeyPackage validity. A Marmot KeyPackage candidate MUST carry a `Lifetime`
extension, MUST be current at validation time (the validation time is not before `not_before` and not after `not_after`),
and MUST have `not_after - not_before <= 7,261,200` seconds. The range is 84 days plus a one-hour clock-skew margin. A
last-resort KeyPackage does not relax this limit.

When a transport exposes a publication timestamp or replacement rule, clients SHOULD use it to avoid consuming stale
single-use KeyPackages. If two otherwise equivalent candidates remain, clients SHOULD use a deterministic
content-derived tie-breaker defined by the transport binding.

After a client successfully processes a Welcome that consumed a published KeyPackage, it SHOULD publish a fresh
replacement according to the active transport binding.

The private `init_key` material for a consumed non-last-resort KeyPackage MUST be deleted after successful Welcome
processing. A last-resort KeyPackage MAY keep its `init_key` after a successful Welcome so that the published package
remains usable, but it MUST delete that material at the earlier of:

- confirmed publication of a replacement under the active transport binding;
- the KeyPackage `Lifetime.not_after` time.

A confirmed replacement is any successfully published KeyPackage that supersedes the old publication under the active
transport's authenticated slot or replacement rule. The replacement does not itself need to carry the
`last_resort_key_package` component.

An asynchronous transport cannot prove that every Welcome already encrypted to the superseded last-resort KeyPackage
has arrived. Deletion after confirmed replacement publication can therefore make such a delayed Welcome undecryptable.
This is the deliberate confidentiality-versus-availability trade-off of the deletion bound, not a reason to retain the
old `init_key` for an unprovable drain period. The inviter can retry with a currently published KeyPackage.

A client MAY delete the material earlier after it stops publishing or accepting that KeyPackage. Local retention policy
MUST NOT extend either bound.

Welcome confidentiality depends on the referenced KeyPackage's private `init_key` remaining secret. Compromise of that
key before deletion lets an attacker decrypt every recorded Welcome encrypted to that KeyPackage and recover the join
secrets carried by those Welcomes. Reuse makes this exposure apply to multiple joins for a last-resort KeyPackage.
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
