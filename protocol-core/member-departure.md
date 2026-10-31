# Member departure

Status: adopted.

Member departure covers three paths: a member leaving on its own through SelfRemove, an admin removing another
member, and, in a group that requires `marmot.group.account-devices.v1`, another device of the same account removing a
device's leaf. This document specifies the SelfRemove path in full. Ordinary admin-initiated removal is an admin-gated
group-state change whose authorization is owned by
[../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) ("remove another member"); it otherwise
follows the normal commit, publish-lifecycle, and convergence rules. Removal by another device of the same account is
described in "Removal by another device of the same account" below. Every path ends with the removed member realizing
its own removal; that flow is "Realizing removal" below.

SelfRemove lets a current member leave a group without asking an admin to remove them. It uses the MLS SelfRemove
proposal from the MLS extensions work and does not define a Marmot custom proposal type.

## Surfaces

- MLS proposal: SelfRemove.
- Protocol core: proposal ingest, opportunistic SelfRemove commits, convergence, retained history.
- App components: `marmot.group.admin-policy.v1` for admin leave constraints, and `marmot.group.account-devices.v1`
  for removal by another device of the same account.
- Transport: whichever transport carries the proposal and commit.

## Accounts with several devices

An account can have several leaves in one group, one for each of its devices
([../foundation/identity.md](../foundation/identity.md), "Devices"). Departure is leaf-scoped, and removing an account
means removing all of its leaves:

- A client that removes an account from a group MUST include a Remove for every current leaf with that account identity
  in one Commit, so the account is never left partly removed. If the account is an admin, the same Commit removes it
  from the admin list under the coupling rule in
  [../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) ("Active admins"). This rule binds the
  committer. A Remove does not say whether the committer meant to remove an account or one device, so a receiver cannot
  check it and MUST NOT reject a Commit for removing only some of an account's leaves; such a Commit is a device
  removal under the next point.
- A Remove that targets one leaf removes only that device. The account stays a member while it has another current
  leaf.
- A SelfRemove removes only its sender's leaf. Other devices of the same account stay members.
- Admin status belongs to the account. A device whose account is an active admin cannot use SelfRemove, even when
  another device of that account stays in the group. In a group that requires `marmot.group.account-devices.v1`, such a
  device can leave through a Remove committed by another device of its account ("Removal by another device of the same
  account" below).
- A device whose own leaf is removed realizes its removal even when another device of the same account stays in the
  group ("Realizing removal" below).

## Behavior

A current member MAY create a SelfRemove proposal for itself.

A non-admin member MAY self-remove if the MLS proposal is valid. A SelfRemove proposal whose sender is an active admin
in its authenticated source-epoch state is invalid (see
[../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) for the definition of an active admin).

A departing admin MUST first complete an accepted admin-policy update that removes its account from the admin list
before creating a SelfRemove proposal. The admin-policy update is an admin-gated group-state change and is valid only
if at least one other active admin remains, so the last active admin MUST designate another admin before leaving.

This two-step flow applies to voluntary departure through SelfRemove only. An admin removed by another admin does not
use it: the removing commit drops the account's last leaf and its `admins` key together, under the coupling rule in
[../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) ("Active admins").

The leaving member MUST NOT commit its own SelfRemove proposal. A remaining authorized member commits it.

After handing the SelfRemove proposal to the active transport, the leaving member enters a local `Leaving` state for
that group. While `Leaving`, the member MUST NOT send MLS application messages, group-state commits, or non-SelfRemove
MLS proposals in that group; it MAY publish a fresh SelfRemove proposal for a newer source epoch when the prior
SelfRemove becomes stale. Transport-level retries of the same serialized SelfRemove proposal MAY continue, but the
client MUST NOT generate fresh SelfRemove proposal bytes for the same source epoch. The `Leaving` state is backed by a
durable leave request. While canonical state contains the local leaf, it ends only if the member repairs or rejoins
through a future specified recovery flow, a future explicit cancel flow clears the request, or the client discards the
local group copy. An accepted removing Commit moves the copy to the removed condition described below.

Applying an accepted removing Commit ends `Leaving` and puts the local copy in the terminal removed condition below.
The client MAY release the durable leave request after it durably records that condition.

If an accepted commit advances the group to a later epoch without removing the leaving member, the prior SelfRemove is
stale because MLS proposals are epoch-bound. The client remains in `Leaving`, MUST NOT reuse the old SelfRemove
proposal bytes, and SHOULD publish a fresh SelfRemove proposal for the new source epoch once local group-state commits
are allowed.

## SelfRemove commits

A SelfRemove-only Commit MAY reference one or more valid retained SelfRemove proposals and MUST NOT contain another
proposal type. Each referenced SelfRemove proposal is validated independently, and one invalid proposal makes the whole
Commit invalid.

Any remaining member whose authenticated account is authorized in the candidate-parent state MAY commit the retained
SelfRemove proposals, provided the complete resulting state satisfies every Marmot invariant. Marmot does not elect one
deterministic SelfRemove committer.

A client that observes a valid peer SelfRemove proposal SHOULD schedule a SelfRemove-only Commit after a short
randomized jitter while the group lifecycle permits local group-state commits. Before preparing the commit, the client
SHOULD re-check whether an accepted commit already consumed that SelfRemove. If the group lifecycle or convergence
status does not allow local group-state commits when the jitter expires, the client waits until local group-state
commits are allowed and then re-checks the retained SelfRemove.

The jitter is local scheduling only. It MUST NOT enter branch scoring, same-epoch commit ordering, message identity,
duplicate handling, or validation. If several members publish SelfRemove-only commits for the same proposal, ordinary
convergence chooses the canonical branch from their MLS-valid commit bytes.

A client whose own SelfRemove-only commit publish fails MUST follow the normal publish-before-apply failure rule:
discard the pending state and keep the SelfRemove available if it is still valid and unconsumed.

A client that receives multiple distinct valid SelfRemove proposals from the same leaving leaf for the same source
epoch before one is consumed MUST retain all of them for MLS proposal-reference resolution. For local Commit
preparation, it selects the proposal with the lexicographically lowest `self_remove_proposal_digest`, where:

```text
self_remove_proposal_digest = SHA-256(serialized_proposal_mls_message)
```

`serialized_proposal_mls_message` is the complete serialized handshake `MLSMessage` carrying the SelfRemove proposal,
under Marmot's pinned [handshake wire format](../foundation/mls-protocol.md#handshake-wire-format). The lowest digest is
only the deterministic choice for a new local SelfRemove-only Commit. A valid Commit that references any retained valid
alternative remains processable; non-selected alternatives are not stale merely because the client would prepare a
different Commit. Byte-identical repeats are duplicates under [inbound-processing.md](./inbound-processing.md).

The client MAY release the alternatives after one SelfRemove for that leaf is accepted on the selected branch, after
the source epoch is outside the rollback horizon and no staged or retained Commit can still reference them, or when
another ordinary MLS proposal-release rule applies. Local arrival order MUST NOT choose the proposal used for local
Commit preparation.

## Removal by another device of the same account

In a group whose candidate parent state requires `marmot.group.account-devices.v1`, any current leaf MAY commit a
Remove of another current leaf of its own account, whether or not the account is an active admin. That component owns
the authorization, the allowed Commit shape, and the sender rules
([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md)). Such a Remove is how a device
leaves a group while another device of its account stays, for example when it signs out:

- The departing device does not commit its own removal. Another device of the same account commits an ordinary Remove
  of the departing leaf. How the departing device asks for this is outside this document; receivers see only the
  Remove.
- The departing device MAY instead use SelfRemove where the rules above allow it. Both paths end in the same removed
  condition.
- The Remove counts as removing another member, not as a self-leave, because the committer is a different leaf. The
  restriction on SelfRemove by an active admin therefore does not apply to it and does not relax.
- The account stays a member through its remaining leaves, including the committer's, so the Remove never triggers the
  admin coupling rule in [../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) ("Active admins").
  An admin account keeps its `admins` entry.
- The removed device realizes its removal as described in "Realizing removal" below.

A device whose account has no other leaf in the group cannot be removed this way. It leaves through SelfRemove, after
first leaving the admin list if its account is an active admin ("Behavior" above).

## Realizing removal

Every departure path ends the same way for the removed member: its client realizes that its membership ended, tells
the application, and stops treating the group as active.

The authenticated evidence of removal is always the same bytes: an accepted commit on the selected canonical branch
that removes this local client's own MLS leaf — a Remove committed by an admin or by another device of the same
account, or a committed SelfRemove — recorded in retained canonical state. This evidence is leaf-scoped: other current
leaves with the same Marmot account identity do not prevent this local leaf from realizing its removal. When the client
applies such a commit, it MUST emit a self-removed state notification (see
[inbound-processing.md](./inbound-processing.md), "Application-visible output") and mark the local group copy removed.

`SelfEvicted` names this state-derived realization, not an input disposition. Whenever retained canonical group state
records the local member's removal and the local group copy is not yet marked removed, the client MUST perform the
realization above. It MUST check this obligation when it applies or restores canonical state and whenever it loads or
attempts to process the retained group copy. A client MAY have recorded the removing commit without the application
ever observing the resulting notification; the obligation stands until the group copy is marked removed.

Later group input can therefore cause the client to notice an outstanding realization, but the input does not receive
a `SelfEvicted` outcome and need not be trusted as evidence. If the client classifies that input at all, it does so
under the ordinary validation and disposition rules. The client MUST NOT continue to present the group as active merely
because the later bytes could not be decrypted or authenticated.

Failure to decrypt group traffic is not, by itself, evidence of removal. Without authenticated evidence that the local
member's own leaf was removed, undecryptable input is a missing-history or repair condition (see
[retained-history.md](./retained-history.md) and [group-state.md](./group-state.md), "Unrecoverable cases"), and the
client MUST NOT present the group as removed.

A removed group copy is retained inactive, not deleted. The removed member:

- MUST NOT prepare or publish commits, proposals, or MLS application messages for the group;
- MUST NOT present the group to the user as active or sendable;
- MAY retain previously delivered content and group history for local display;
- MAY discard the local group copy at any time.

When a selected disband Commit removes the local leaf, the client MUST still
complete the leaf-scoped realization above: it records the membership outcome,
retains its authenticated evidence, and emits the `self-removed` state
notification. The group-level `Disbanded` state takes presentation precedence,
so that notification MUST NOT synthesize a separate member-removal row. The
single `group_disbanded` row is the only presentation row for the Commit.
Suppressing the duplicate row MUST NOT discard the local membership outcome or
its evidence.

When the state that results from the removing commit still holds a leaf with the local member's account identity, only
this device left the group, and the account stays a member through another of its devices ("Accounts with several
devices" above). The client still completes the leaf-scoped realization above, but MUST NOT present the group to its
user as one the account was removed from: it presents the group as no longer active on this device, with no
member-removal row for the local member.

The removed condition is terminal for that local leaf. The client does not retain old epoch secrets or run convergence
in order to resurrect it if continuing members later select another branch. Rejoining requires explicitly discarding
the old active cryptographic state and processing a fresh valid Welcome under [joining.md](./joining.md). An
implementation MAY preserve local history and a removal tombstone while replacing the active cryptographic state.
Another current leaf with the same Marmot account identity remains independently active unless a Commit removes it too.
Later group traffic presented only to this removed copy has no processable active group state and receives the
`unknown_group` pre-convergence category under [inbound-processing.md](./inbound-processing.md), not a convergence
disposition.

## Validation

A SelfRemove-only Commit is invalid if:

- it references no SelfRemove proposal or includes a proposal of another type;
- any referenced proposal does not target its authenticated sender;
- any referenced proposal sender is an active admin in the proposal's authenticated source-epoch state;
- the committer leaf is the sender and target of any referenced SelfRemove proposal; another current leaf with the same
  Marmot account identity is not excluded by this leaf-scoped rule;
- the committer is not a current member;
- the commit fails the normal MLS and Marmot convergence checks.

## Migration notes

MIP-era Marmot treated SelfRemove as part of group messaging behavior. In this spec it lives in protocol core because
SelfRemove affects the required group-state flow.
