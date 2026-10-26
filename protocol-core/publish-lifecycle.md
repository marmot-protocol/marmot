# Publish lifecycle

Status: adopted.

This document states the publish-before-apply rule for locally generated group-state changes.

## Rule

A locally generated group-state change MUST NOT become local canonical state until the client has confirmed that its
publish obligation succeeded.

This rule applies to:

- group creation (see "Group creation" below — the obligation shape differs from all other operations)
- invite
- member removal by an admin, or by another device of the same account
  ([member-departure.md](./member-departure.md), "Removal by another device of the same account")
- group profile update
- required-capability change
- admin policy update
- self-update Commit
- SelfRemove-only commits prepared by remaining members

A member's own departure is a SelfRemove *proposal*, not a local commit. The leaver publishes the proposal and does not
apply any pending state, because another authorized member commits it (see
[member-departure.md](./member-departure.md)). Publish-before-apply binds any remaining member that prepares a
SelfRemove-only Commit, not the leaver. If the leaver's durable leave request later requires a fresh SelfRemove proposal
for a newer epoch, that proposal is another standalone proposal publish and still has no pending state.

## Shape

```text
prepare local commit
  -> retain pending state
  -> produce publish obligation
  -> publish required bytes
  -> confirm or fail publication
  -> apply or discard pending state
```

## Publish obligation

A publish obligation has four protocol-relevant parts:

- outbound MLS or Marmot bytes;
- the recipient scope for those bytes;
- the prior canonical state they were generated from;
- the pending state they would make canonical after publication.

The exact local representation is implementation-defined.

A publish obligation succeeds when the active transport binding reports an acknowledged accept for the obligation's
bytes from at least one endpoint in the obligation's recipient scope. Each transport binding MUST define its
acknowledgement signal. A transport binding or client MAY apply a stricter success rule, but at least one acknowledged
accept is the minimum, and a client MUST NOT treat anything weaker (such as a queued or sent-without-acknowledgement
state) as success.

A transport MAY require attempts to additional targets after its acknowledgement rule has been satisfied. The
acknowledgement that satisfies that rule releases publish-before-apply; outstanding transport fanout MUST NOT keep the
group in `PendingPublish`, reopen that state after apply, undo the applied state, or require the Commit to be re-staged.
The active transport document defines which remaining targets require an attempt and whether later retries are
required.

Group creation is special because there is no existing group recipient set before the group exists.

The one-member epoch-0 group creation has an empty outbound byte set and an empty recipient scope. The creator MUST
treat that empty obligation as immediately satisfied and make epoch 0 canonical without publishing group-message bytes.

When founding creation includes initial invitees, the creator next prepares and locally merges one founding Add Commit
from epoch 0 to epoch 1. That Commit also has an empty group-message publication obligation: the creator is the only
pre-existing member, so no peer can be forked by failure to publish it. Each resulting epoch-1 Welcome is a separate
retryable per-invitee delivery obligation after the Add Commit becomes canonical. A Welcome delivery succeeds or fails
independently and does not affect canonical group state.
Consumed KeyPackage material for founding invitees cannot be restored on Welcome delivery failure; if a Welcome
cannot be delivered, the founding creator MAY re-invite the unreachable member using a new Add commit against
the now-canonical group with a fresh KeyPackage.

The empty-obligation exception is limited to the epoch-0 creation and, when applicable, its immediately following
founding Add Commit. Every subsequent Commit follows the normal publish-before-apply rule.

## Proposal-driven commits

Commits prepared in response to retained proposals produce publish obligations too.

When a client prepares a commit that consumes a retained proposal, the client retains pending state and exposes a publish
obligation. The pending state does not become canonical until publication is confirmed.

For SelfRemove, [member-departure.md](./member-departure.md) defines which remaining members may attempt a
SelfRemove-only Commit and the local jitter before they do. That scheduling does not weaken publish-before-apply and
does not decide canonical group state.

## Failure

If publication fails, the client discards the pending state and keeps the inbound proposal or local action available if
retry is valid.

For a SelfRemove-only commit, publication failure leaves the SelfRemove proposal available for another attempt by any
eligible remaining member, as long as the proposal has not been consumed by an accepted commit and remains inside
retained history.

If another member publishes an equivalent or conflicting commit first, ordinary convergence decides the result.

## Restart

A process interruption does not resolve a publish obligation. Recovery of prepared, acknowledgement-uncertain,
confirmed-but-unapplied, and applied-but-underived transitions follows
[durability.md](./durability.md) ("Publish interruption boundaries"). In particular, possible external acceptance
without a recoverable acknowledgement is still `PendingPublish`, and safe retry republishes the byte-identical
obligation rather than generating a replacement Commit.
