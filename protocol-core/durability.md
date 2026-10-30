# Durability and restart

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#t7-crash-incomplete-recovery-and-rollback-of-externally-visible-work).

This document defines the implementation-neutral durability contract for Marmot group processing. It specifies which
protocol facts and effects survive process interruption, and the safe behavior when recovery is incomplete. It does
not define a database, snapshot format, transaction mechanism, scheduler, or serialization beyond existing Marmot and
MLS wire encodings.

`Retain` in this document means retain or be able to reconstruct from authenticated bytes and dependencies before the
affected group resumes processing. An implementation MAY persist, derive, replay, or otherwise recover a fact. The
observable requirement is the same protocol result after restart.

The **protocol observer projection** is the complete per-group conformance view in
[../foundation/conformance.md](../foundation/conformance.md): canonical state and lifecycle, convergence status, local
protocol gates, unresolved publication, input outcomes, and effective application-visible outputs. It excludes the
physical representation of those facts.

## Recoverable protocol facts

For each retained group, a client MUST retain or be able to reconstruct every fact still needed to continue the
protocol without changing its result:

- the last complete canonical group state, lifecycle state, and convergence status;
- retained candidate-parent states and the cryptographic material required by
  [retained-history.md](./retained-history.md);
- each admitted protocol input's exact bytes, stable message identity, authenticated dependencies, and current
  disposition while that disposition can still change, under
  [inbound-processing.md](./inbound-processing.md);
- enough identity, outcome, and effect information for terminally classified or already-accounted-for input to prevent
  duplicate state application or duplicate application-visible output when the same bytes are encountered again;
- every unresolved publish obligation, including the four protocol-relevant parts in
  [publish-lifecycle.md](./publish-lifecycle.md), whether an external publish attempt might have occurred, and whether
  the required acknowledgement is known to have succeeded;
- local protocol gates and terminal local conditions that restrict legal actions, including `Leaving`, `Disbanding`,
  local-leaf removal, `Unrecoverable`, and `Disbanded`; and
- application-visible delivery, state-notification, withdrawal, and invalidation effects that have not yet been made
  reconstructible to the application.

An implementation MAY release a fact when no current or future protocol decision inside the applicable retention
horizon, retry obligation, local gate, or application effect depends on it. Restart does not shorten any owning
document's retention or release condition.

## Restart equivalence

A restart MUST NOT, by itself, change the canonical protocol-state projection defined in
[../foundation/conformance.md](../foundation/conformance.md), change an input disposition, clear a local protocol gate,
make unresolved outbound work successful, or make an application effect disappear.

For convergence, given the same retained authenticated inputs and dependencies, a restarted client that continues
executing MUST reach the same canonical protocol-state projection and dispositions as uninterrupted execution under
the guarantees and assumptions in [convergence.md](./convergence.md) ("Guarantees and assumptions"). This requirement
includes restart that changes local timer deadlines, pass partitioning, work ordering, or device speed. Those
differences MAY delay an outcome or cause a different safe intermediate pass, but they MUST NOT change the eventual
result after relevant input closes.

If the client cannot yet reconstruct a required fact, it MUST keep the affected transition unapplied and outbound work
blocked. For convergence work, temporary unavailability has the `Blocked` status; publish work remains in its current
lifecycle state. Permanent loss or corruption follows "Missing or corrupt material" below.

## Publish interruption boundaries

Publication and canonical application remain separate protocol steps. Recovery follows the last boundary the client
can establish from retained or reconstructed facts:

1. **Prepared with no possible external publish.** Canonical state remains the prior state. The client MAY abandon the
   preparation and return to `Stable`, or retry the exact obligation. It MUST NOT expose the pending state as canonical.
2. **External acceptance possible, but acknowledgement unavailable after restart.** This includes bytes accepted by an
   endpoint when confirmation was not retained or reconstructed. The client MUST treat the obligation as unresolved,
   remain in `PendingPublish`, and MUST NOT assume either success or failure. It MAY republish the byte-identical
   obligation to obtain a new acknowledgement satisfying the active transport rule. It MUST NOT replace the uncertain
   obligation with newly generated Commit bytes.
3. **Publication confirmed, canonical apply incomplete.** The client resumes `Merging` and applies the exact confirmed
   pending transition once. Replaying its deterministic application from the last complete prior state is allowed. The
   client MUST NOT generate a replacement Commit or expose a partially advanced canonical state.
4. **Canonical apply complete, derived work incomplete.** The client keeps the applied canonical state and reconstructs
   its dispositions, gates, notifications, deliveries, withdrawals, and invalidations. It MUST NOT reapply the Commit
   or reopen `PendingPublish` merely to finish derived work.

Before any publish attempt can make bytes externally observable, the exact obligation and the prior and pending states
needed by cases 2 and 3 MUST be recoverable. Byte-identical republication is a retry of one obligation, not a new
group-state change; duplicate handling still applies.

If possible external acceptance cannot be excluded, the exact obligation or state needed to resolve it is permanently
missing or corrupt, and no verified repair path is available, the client enters `Unrecoverable`. It MUST NOT discard
the uncertainty, prepare another group-state change, or select the only locally complete branch merely because the
possibly published branch is absent.

## Convergence interruption boundaries

A crash during convergence does not make admitted input invalid, stale, or unadmitted.

- **Collection.** The client MAY resume the same collection window when its boundaries are reconstructible, or start a
  new bounded pass over the still-eligible retained input. It MAY restart local collection timers. It MUST NOT omit an
  admitted input merely because volatile pass membership or elapsed monotonic time was lost.
- **Frozen-batch resolution.** The client MAY resume deterministic resolution of the exact frozen batch, or abandon the
  wholly unapplied pass and admit all of its still-eligible inputs and authenticated dependencies to a later pass under
  the restart exception in [convergence.md](./convergence.md) ("Convergence policy"). It MUST NOT resolve or apply an
  accidental subset of the frozen batch. Later-retained input remains outside that batch unless a new pass is started.
- **Selected-branch application.** The client MUST recover either the complete observer projection from before the
  application or the complete projection after it, then finish or replay deterministic work from that boundary. It
  MUST NOT expose a canonical state from one side with dispositions, gates, or application effects from the other.

Loss of timer state or pass-membership metadata alone is not missing retained history when all admitted inputs and
authenticated dependencies remain available. Loss or corruption of an admitted input, candidate-parent state, or
dependency that could change selection is handled under "Missing or corrupt material" and MUST NOT be hidden by
resolving the locally remaining branch.

## Observer-atomic transitions

The following multi-part changes MUST be atomic from the protocol observer's perspective:

- preparing a local Commit makes both the pending state and its complete publish obligation available while leaving
  canonical state unchanged;
- selected-branch application changes canonical state, current dispositions, protocol gates or terminal conditions,
  and the effective application output to one self-consistent projection;
- realizing local-leaf removal changes the local condition and its application effect together; and
- terminal disbanding establishes `Disbanded`, its authenticated tombstone, its single effective presentation effect,
  and the prohibition on further group processing together.

The lifecycle MAY expose `PendingPublish`, `Merging`, or `Recovering` while work is incomplete. During those states the
last complete canonical projection remains authoritative. A client MUST NOT expose a partially applied transition.
Physical writes MAY occur in any number and in any order that preserves this observer-visible rule.

Safe replay reuses the same authenticated input or byte-identical publish obligation and is idempotent with respect to
the effective projection. Regenerating a Commit with new randomness is a new protocol action, not replay, and is allowed
only after the prior obligation is conclusively resolved and the lifecycle again permits preparation.

## Missing or corrupt material

On restart, a client first validates or reconstructs the facts required for the next affected transition. It then
follows these outcomes:

- If authenticated retained inputs and dependencies reproduce the fact, processing MAY continue from the reproduced
  fact.
- If the unavailable fact is temporary and no partial transition is exposed, the affected operation remains blocked;
  convergence work has the `Blocked` status.
- If material is outside its owning retention horizon and no unresolved work depends on it, ordinary pruning and stale
  rules apply; its absence is not `Unrecoverable`.
- If canonical state, a possibly published transition, or selection-relevant material inside the rollback horizon is
  permanently missing or corrupt and no verified repair path is available, the group enters `Unrecoverable`.
  Associated admitted input remains deferred with `missing_history` as specified in
  [../foundation/errors.md](../foundation/errors.md).

Partial recovery is not evidence for branch selection. A client in the last case MUST NOT select the only locally
available branch, shorten the rollback horizon, discard an uncertain published branch, or convert affected input to a
terminal disposition merely to resume operation. A verified repair, restore, explicit rejoin, or future specified
recovery path is required.

Loss of only derived disposition or application-effect records does not require `Unrecoverable` when the client can
reconstruct them exactly from intact canonical state and admitted inputs. Until that reconstruction completes, the
client MUST NOT claim `Settled` or expose a guessed projection.

## Application effects after restart

Application callbacks and acknowledgement APIs are implementation-defined. Their effective protocol view is not:

- an accepted MLS application message has one effective delivered payload, keyed by its stable protocol message
  identity;
- a state notification derived from a Commit remains attributable to that Commit's `commit_digest`;
- duplicate replay MUST NOT create a second effective delivery or state change;
- an invalidated app payload or superseded state change remains withdrawn, and any required invalidation remains
  observable until the application can reconstruct the selected-branch view; and
- `group_disbanded` remains one effective presentation effect, while the leaf-scoped removal outcome remains
  reconstructible under the suppression rule in [member-departure.md](./member-departure.md).

Each effect has a stable effect identity. For a delivered or invalidated app payload, it is the effect kind plus the
stable protocol message identity. For a state notification derived from a Commit, it is the effect kind plus that
Commit's `commit_digest` and, when the Commit produces more than one effect of that kind, the canonical protocol
identity of the affected leaf, component, or other subject. A state-change withdrawal uses the effect kind plus the
identity of the notification it withdraws. A group-state invalidation uses the effect kind plus the superseded Commit's
`commit_digest`. Distinct effect kinds remain distinct when they refer to the same input or Commit. A branch-recovery
notification that is not attributed to one Commit uses the effect kind plus the optional superseded canonical tip
Commit digest and the selected tip Commit digest; absence of a superseded tip digest is part of the identity. Any
future effect not covered here MUST define an equivalent deterministic identity from the accepted protocol inputs and
selected state that produce it; it MUST NOT use local receipt order, scheduling order, or a local storage identifier.

An effect's observation boundary is established only when the client can recover its stable effect identity together
with either:

- an application acknowledgement for that identity; or
- an equivalent recoverable selected-branch projection through which the application reconstructs the current
  effective outputs.

The acknowledgement shape and projection-access mechanism are implementation-defined. A client that relies on the
second option MUST re-expose the recovered projection after restart before suppressing re-emission. Merely invoking a
callback, attempting delivery, or recording the effect without one of these two conditions does not establish
observation.

After restart, a client MUST re-emit an effect whose observation boundary was not established, or re-expose the
equivalent reconstructible current projection. Re-emission uses the same stable effect identity so repeated delivery
can be deduplicated. A crash between canonical application and application observation does not cancel the effect, and
a crash between prior observation and a later branch change does not cancel the required withdrawal or invalidation.
