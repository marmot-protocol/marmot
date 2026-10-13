# Protocol core

Status: adopted.

Protocol core describes what Marmot clients do with MLS group state.

These docs are the tour for implementers who do not already live inside MLS. Foundation docs define the stable
building blocks. Protocol core explains the flow: create a group, invite members, process incoming bytes, publish local
changes, resolve competing branches, and keep enough history to recover safely.

Transport documents say how bytes arrive. App component documents say how component bytes change. Protocol core says
when those bytes become canonical group state.

## Big picture

```text
create group
  -> publish or retain initial state
  -> add member KeyPackage
  -> publish add Commit
  -> deliver Welcome through the active transport
  -> new member processes Welcome
  -> group traffic advances through proposals, commits, and app payloads
```

Marmot uses MLS for group security. A Marmot client does not invent group membership or epochs locally. It feeds valid
MLS inputs into the group, checks Marmot policy around those inputs, and applies one canonical branch.

## Main flows

```text
Local group-state change:

prepare MLS commit
  -> hold pending state
  -> publish required transport bytes
  -> apply pending state only after publish succeeds
```

```text
Inbound group traffic:

receive transport envelope
  -> peel transport
  -> retain protocol bytes
  -> classify as proposal, commit, or app payload
  -> run validation and convergence
  -> emit state notifications or delivered app payloads
```

```text
Member join:

find compatible KeyPackage
  -> commit Add
  -> publish Add commit
  -> deliver MLS Welcome
  -> new member validates group state
  -> new member rotates consumed KeyPackage and self-updates
```

## Files

- [group-setup.md](./group-setup.md) - group creation and signed group settings.
- [joining.md](./joining.md) - member add flow, MLS Welcomes, and post-join behavior.
- [group-messaging.md](./group-messaging.md) - proposals, commits, and MLS application messages.
- [member-departure.md](./member-departure.md) - SelfRemove and member departure rules.
- [group-state.md](./group-state.md) - the per-group lifecycle states and legal transitions.
- [../app-components/group-lifecycle-v1.md](../app-components/group-lifecycle-v1.md) - authenticated terminal group
  disbanding and legacy-group enablement.
- [publish-lifecycle.md](./publish-lifecycle.md) - publish-before-apply for local group-state changes.
- [inbound-processing.md](./inbound-processing.md) - how incoming bytes are stored, classified, and retried.
- [convergence.md](./convergence.md) - how candidate branches are built, scored, selected, and applied.
- [retained-history.md](./retained-history.md) - retained state, rollback horizon, and late input rules.
- [durability.md](./durability.md) - recoverable protocol facts, crash boundaries, and restart equivalence.

## Core rule

Marmot clients choose group state from MLS-valid protocol bytes and the convergence policy that group state selects.

They MUST NOT choose group state from transport arrival order, transport envelope timestamps, outer event ids, local
receive order, or which transport source delivered a message first.
