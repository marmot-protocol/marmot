# Group messaging

Status: adopted.

This document describes group control messages and encrypted app payloads.

## Surfaces

- Foundation application payloads.
- MLS protocol: Proposals, Commits, PublicMessage, PrivateMessage, application messages, and epochs.
- Protocol-core publish lifecycle, inbound processing, retained history, and convergence.
- Active transport binding for group message delivery.
- App components for admin policy, routing, and message retention.
- SelfRemove as the member-departure flow.

## Behavior

Marmot group traffic carries three kinds of MLS work:

- Proposals that ask the group to change state later.
- Commits that advance group state.
- MLS application messages that carry Marmot app payloads.

All three are delivered through the active transport binding. The transport owns the outer envelope. Protocol core owns
which peeled MLS bytes become canonical group state.

## App payloads

Marmot app payloads use an unsigned Nostr event shape inside MLS.

Marmot-defined app-payload kinds and their owning documents are listed in
[../foundation/registries.md](../foundation/registries.md) ("Nostr event kinds used by Marmot").

The [inner app event](../foundation/application-messages.md) is distinct from its transport envelope. Delivery
addressing and routing derive from canonical group state, never from inner application tags. A validated
[per-message expiry](../features/message-expiry.md) cap may shorten an application's transport deletion hint as the
active binding defines. It does not change delivery addressing, group state, or branch selection.

Receiver authentication follows [../foundation/application-messages.md](../foundation/application-messages.md)
("Receiver authentication").
Unsupported app-event kinds do not change group state unless the owning feature says otherwise.

## Commit authorization

An active admin MAY commit a group-state change when its owning rule authorizes that admin.

Non-admin members MUST NOT commit anything except the narrow flows the spec explicitly allows:

- a self-update Commit that updates only the sender's own LeafNode;
- a dedicated SelfRemove-only Commit that processes valid pending SelfRemove proposals by reference;
- in a group whose candidate parent state requires `marmot.group.account-devices.v1`, a same-account Commit: one whose
  proposals are only Add proposals for KeyPackages of the committer's own account and Remove proposals for other leaves
  of that account, carried by value, as
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) defines.

These non-admin commit shapes MUST NOT be combined with each other or with other proposal types.

All other Commits from non-admins are invalid.

In particular, adopted v1 defines no non-admin `new_member_commit` External Commit path.

Non-admin members MAY send standalone MLS proposals only where the spec explicitly allows them. In v1 protocol core,
that proposal flow is SelfRemove. A request for an admin-gated group-state change is an application payload or
feature-owned request flow, not a standalone MLS proposal.

## Publish before apply

A locally generated Commit MUST NOT become the sender's canonical local state until its publish obligation succeeds.

The sender publishes the transport envelope required by the active transport binding and waits for the transport publish
success required by the publish lifecycle.

If the Commit adds members, the associated Welcomes are sent only after the Commit publish obligation succeeds.

## Race handling

Convergence uses authenticated commit ordering, retained MLS states, and the pinned convergence policy. Transport
evidence MUST NOT choose the winning branch, and digest ordering is only the final same-committer fallback.

## Message retention

When message retention is enabled, the active transport binding applies its own retention hint if it has one.

A sender may select a stricter per-message lifetime through [per-message expiry](../features/message-expiry.md),
including when group retention is disabled. The active binding derives its hint from the pinned group decision and
validated per-message cap, never from arbitrary unvalidated application metadata. Local expiry does not release
protocol evidence before [retained-history](./retained-history.md) rules allow it.

## Migration notes

This document is the home for MIP-03 group-message behavior; the [MIP coverage map](../mip-coverage.md) records where
each MIP-03 concern moved. The MIP-era documents are a deprecated version of the protocol (see the
[spec README](../README.md)).
