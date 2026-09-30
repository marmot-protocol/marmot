# marmot.group.lifecycle.v1

Status: adopted.

## Registry

- Component id: `0x800c`
- Name: `marmot.group.lifecycle.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: required for newly created groups

## State

```text
enum {
  active(0),
  disbanded(1)
} MarmotGroupLifecycleV1;
```

The encoded state is exactly one byte. `0x00` is `active` and `0x01` is
`disbanded`. Every other value and every encoding with trailing bytes is
invalid.

`active` means the authenticated group has not terminated. The client's local
protocol lifecycle can still be `Stable`, `PendingPublish`, `Merging`,
`Recovering`, or `Unrecoverable`.

`disbanded` is the terminal sixth group lifecycle state. It is absorbing:
clients do not process later group traffic, select a later branch, or rejoin
the same group id after accepting a selected disband Commit. A replacement
conversation uses a newly created MLS group.

## Enablement for existing groups

A group that predates this component MAY omit it and MAY omit `0x800c` from its
required `app_components` list. Such a group remains valid but cannot be
disbanded.

An active admin MAY enable disbanding in one Commit that:

- adds the `active` state if it is absent; and
- adds `0x800c` to the required `app_components` list.

The resulting state is valid only when every resulting member leaf advertises
support for `0x800c`. Enablement does not disband the group and produces no
group-system row.

Once required, this component MUST remain present and required for the
remainder of the group's lifetime.

## Disband update and Commit shape

The only state transition is `active -> disbanded`. A disband update MUST be
inline in the Commit that realizes it; a standalone or by-reference disband
proposal is invalid.

A Commit carrying the transition is valid only when:

- the candidate parent has no open [history-purge request](./history-purge-v1.md); a group using that draft component
  must first close the request in a prior canonical Commit because disband cannot carry its terminal `AppEphemeral`;
- the authenticated committer is an active admin in the candidate parent;
- `0x800c` is already required in the candidate parent;
- the resulting lifecycle state is `disbanded`;
- the resulting admin-policy list contains exactly the committer's Marmot
  account identity;
- every candidate-parent leaf except the exact committing leaf is removed,
  including other leaves for the committer's account;
- it contains no Add, Update, PreSharedKey, ReInit, ExternalInit,
  GroupContextExtensions, AppEphemeral, Custom, unrelated AppDataUpdate, or
  other proposal; and
- the resulting state satisfies normal MLS and Marmot validation.

The Commit carries a full admin-policy replacement even when the committer was
already the sole admin. A single-leaf group therefore produces a valid disband
Commit with no Remove proposals.

## Convergence and realization

A valid disband Commit is never terminalized through ordinary linear
advancement. After publication, or after inbound validation, the client retains
it as candidate material and opens a bounded convergence pass. Admission of the
valid disband candidate changes the lifecycle from `Stable` to `Recovering`
even when no divergent edge exists. This forced transition does not assert that
a fork exists and does not change normal branch selection; disband receives no
special ordering priority.

While a local irreversible disband request is unresolved, the client holds a
durable `Disbanding` gate. `Disbanding` is not a canonical lifecycle state. It
blocks new outbound work and survives publication failure, restart, and a
losing branch. If an active branch is selected, an authorized client
regenerates the Commit against that selected state. If any valid disband branch
is selected, the request succeeds regardless of which admin authored the
selected Commit.

Only a selected disband Commit moves the lifecycle from `Recovering` to
`Disbanded`. The client then:

- emits one actor-attributed `group_disbanded` state notification;
- does not emit member/admin removal presentation rows for the same Commit;
- retains a read-only authenticated tombstone and MAY retain delivered
  application history; and
- deletes live MLS state and stops routing, sending, maintenance, and
  convergence for the group.

The final committer leaf is a mechanical MLS requirement and is not an active
Marmot participant after terminalization.

## Authorization failure

A durable local request that becomes impossible because the requester is no
longer an admin or no longer a member ends with a local typed failure. Transport
failure and `Unrecoverable` do not cancel the request; they leave it pending
until publication can resume or a verified repair restores state.

## Removal

This component cannot be removed while present. An AppDataUpdate `remove`
operation targeting it is invalid.

## Migration

This is the first versioned lifecycle component. A breaking wire or validation
change receives a new component id and document.
