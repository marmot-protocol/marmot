# Group construction and settings

Status: adopted.

This document describes group creation and the signed settings every member MUST agree on.

A Marmot group is an MLS group plus Marmot group state. The exact byte formats for Marmot group state live in app
component docs.

## Surfaces

- Foundation MLS protocol and capability negotiation.
- Protocol-core publish lifecycle and convergence.
- App components for profile, avatar, admin policy, routing, image, encrypted-media policy, and message-retention
  state (see [../app-components/README.md](../app-components/README.md) for the full set).
- The active transport binding, if the group needs transport-owned routing state.
- Canonical encoding for every component state and update payload.

## Behavior

Every Marmot group has an MLS group id. That id is private group security state and MUST NOT be published through a
transport envelope unless a future document explicitly changes that rule.

Before creating a group or adding a member, clients check that the target KeyPackages support the capabilities required
by the group. A group MUST NOT be created with features that the initial members cannot process.

Group settings are authenticated group state. A client MUST NOT treat local UI preferences, locally observed delivery
data, or cached transport data as group settings.

At creation, the GroupContext MUST include the `required_capabilities` and `app_data_dictionary` extensions. The
`app_data_dictionary` MUST contain `marmot.group.admin-policy.v1` and the other required GroupContext component entries
selected by the feature set. The GroupContext `app_components` list MUST require
`marmot.member.account-identity-proof.v2`, `marmot.group.admin-policy.v1`, and every other component required by the
selected feature set, including any required component whose data appears only in member LeafNodes rather than in the
GroupContext dictionary.

Newly created groups MUST also require component id `0x800c` and contain
`marmot.group.lifecycle.v1 = active`. Groups created before adoption of that
component remain valid without it and cannot disband until an active admin
completes its explicit negotiated enablement.

A creator whose client supports `marmot.group.account-devices.v1` (`0x800d`) MUST require it in a new group when the
creator's own leaf, and every KeyPackage in the founding Add Commit if there is one, advertise it. Each member's devices
can then add and remove leaves of their own account from the start, and the founding Add Commit has to respect the
component's leaf limit. This rule binds the creator. A group that does not require the component is valid, so a joiner
MUST NOT reject a Welcome because the group omits it. A group created without it can activate it later
([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)).

The account-proof and admin-policy requirements are lifetime invariants, not creation defaults. Every resulting epoch
MUST require component ids `0x8009` and `0x8003` in the GroupContext `app_components` list, every member leaf MUST
advertise and carry a valid `0x8009` proof, and the GroupContext MUST retain the `marmot.group.admin-policy.v1` entry.
A Commit that violates any of those invariants, including a Commit that changes `app_components`, is invalid under
[../app-components/account-identity-proof-v2.md](../app-components/account-identity-proof-v2.md) and
[../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md).

Every current-profile group MUST list the `app_data_update` proposal type (`0x0008`) in
`required_capabilities.proposals`, and every member KeyPackage and LeafNode capability list MUST advertise it. This
requirement is lifetime-wide because every current-profile group carries mutable GroupContext component state.

Separately, `ratchet_tree` is a per-Welcome GroupInfo extension, not a GroupContext extension. The GroupInfo encrypted
in every Marmot Welcome carries the ratchet tree inline, as [joining.md](./joining.md) requires.

## Creation flow

When creating a group, the creator chooses the initial required feature set, initial members, transport routing state,
and optional profile settings. The initial admin policy MUST contain the creator's Marmot account identity and MAY
contain other initial members. This requirement applies even when the creator is the group's only initial member.
It is therefore not conditional on enabling an admin feature or on adding invitees: every founding group includes the
same required admin-policy component, and any founding Welcome is evaluated against it.

If the selected transport requires signed group routing state, creation MUST include that transport's routing component.

If the group has a human-visible profile, creation MUST include `marmot.group.profile.v1`.

If the group has a Blossom-backed group image, creation MUST include `marmot.group.blossom.image.v1`; a group that
references an avatar by plain URL instead MUST include `marmot.group.avatar-url.v1`.

If the group has disappearing messages, creation MUST include `marmot.group.message-retention.v1`.

If the application profile supports encrypted media, creation MUST include `marmot.group.encrypted-media.v2`. This is
an application-profile choice: the encrypted-media component is required for new app groups created under a
media-capable profile, not by the bare protocol. A non-media group MAY omit it.

If an experimental application profile enables raw QUIC agent previews, creation MUST include
`marmot.group.agent-text-stream.quic.v1` and MUST require the `receive` role. This is an application-profile choice that
makes groups agent-stream-ready without exposing a user-facing enable switch. The component and feature documents own
the exact role semantics and fallback behavior.

The component documents in [../app-components/](../app-components/) own the exact bytes, authorization, and removal
rules for each component named here.

## Updates

Group settings change through MLS group-state updates. The client prepares the update, publishes the required bytes,
and applies the pending state only after the publish obligation succeeds.

Settings updates are admin-gated by default. A component MAY define a looser rule, but it MUST say so explicitly.

Self-update Commits, dedicated SelfRemove-only Commits, and same-account Commits in a group that requires
`marmot.group.account-devices.v1` do not change group settings and do not require admin authorization
([group-messaging.md](./group-messaging.md), "Commit authorization").

## Required capability changes

A change to the GroupContext `required_capabilities` extension uses the MLS `GroupContextExtensions` proposal and a
Commit. Only an active admin MAY send that proposal as a standalone proposal, and only an active admin MAY commit the
change. Proposal-sender and commit authorization use the source-epoch and candidate-parent rules in
[../app-components/README.md](../app-components/README.md) ("Authorization Evaluation").

The resulting epoch is valid only if every current member LeafNode advertises every extension type, proposal type, and
credential type named by `required_capabilities` in the corresponding MLS capability list. This check runs for every
Commit that changes `required_capabilities` or the member leaf set. A Commit therefore cannot make a capability
required while retaining a member that does not advertise it. Removing a requirement uses the same authorized flow.

The Commit follows [publish-lifecycle.md](./publish-lifecycle.md) like any other local group-state change. A client MUST
NOT apply the changed GroupContext before the publication obligation succeeds.

## Admin policy

Admin authority is based on Marmot account identity, not on MLS leaf id. If an account has multiple leaves in a group,
the admin policy applies to each current leaf with that account identity.

A settings update that would leave the group with no active admin (defined in
[../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md)) is invalid.

Admins who want to use SelfRemove MUST first leave the admin list through an admin-policy update. The member-departure
doc owns the detailed leave flow.

## Message retention

When message retention is enabled, the transport binding applies its own retention hint, if it has one. The owning
component [../app-components/message-retention-v1.md](../app-components/message-retention-v1.md) defines the pinned
source-epoch state, exact expiry calculation, overflow behavior, and sender-timestamp caveat.

Retention is group state, not a sender preference. A sender-supplied expiration tag is replaced or removed according to
the message's source-epoch retention component.
