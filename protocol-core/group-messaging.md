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

The inner app event has an `id` but no `sig`. The active transport binding owns the outer envelope and builds its routing tags — the tags that address, route, or expire it — from canonical group state, never from the inner app event (the Nostr binding's routing tags are defined in [../transports/nostr.md](../transports/nostr.md)). An inner tag therefore carries application content only: it never affects addressing, routing, expiry, or branch selection. The inner event's structural rules are in [../foundation/application-messages.md](../foundation/application-messages.md), "Encoding".

Receiver authentication follows [../foundation/application-messages.md](../foundation/application-messages.md)
("Receiver authentication").
Unsupported app-event kinds do not change group state unless the owning feature says otherwise.

## Commit authorization

An active admin MAY commit a group-state change when its owning rule authorizes that admin.

Non-admin members MUST NOT commit anything except the narrow flows the spec explicitly allows:

- a self-update Commit that updates only the sender's own LeafNode;
- a dedicated SelfRemove-only Commit that processes valid pending SelfRemove proposals by reference.
- when experimental component `marmot.same-account-membership.v1` is required, its exactly-one-Add or one-to-four-
  sibling-Remove inline Commit shape.

Those shapes MUST NOT be combined with each other or with other proposal types. Same-account membership authorization,
candidate-parent checks, and resulting-state limits are defined by
[`marmot.same-account-membership.v1`](../app-components/same-account-membership-v1.md).

All other Commits from non-admins are invalid.

In particular, adopted v1 defines no non-admin `new_member_commit` External Commit path. The optional experimental
multi-device component uses an ordinary member Commit with one inline Add, never an External Commit.

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

When retention is disabled, a sender cannot force retention data onto the group message envelope. The sender removes or
replaces retention data so the on-wire behavior is determined by group state.

## Migration notes

This document is the home for MIP-03 group-message behavior; the [MIP coverage map](../mip-coverage.md) records where
each MIP-03 concern moved. The MIP-era documents are a deprecated version of the protocol (see the
[spec README](../README.md)).
