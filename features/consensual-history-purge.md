# Consensual history purge

Status: draft.

This feature is a separate, high-consequence group action for changing prospective message retention and, only after
unanimous consent, hiding and best-effort deleting application plaintext from before the request opened. It is not implied by enabling
or changing disappearing messages.

The exact request, proof, temporary state, terminal finalization, receipt, TTL, and identity bytes are owned by
[`marmot.group.history-purge.v1`](../app-components/history-purge-v1.md). Prospective retention state remains owned by
[`marmot.group.message-retention.v1`](../app-components/message-retention-v1.md). Canonical branch selection and the
rollback horizon remain owned by [convergence](../protocol-core/convergence.md) and
[durability](../protocol-core/durability.md).

## Eligibility and capability gate

The rich action is available only when every nonblank active leaf advertises the required MLS proposal support,
`AppEphemeral`, and component `0x800d`. A client MUST NOT emit a request when any active leaf is unsupported or when a
request is already open. An old or unsupported client is never counted as consenting.

Any active member may create a request, including a non-admin. The member signs the versioned request proof and sends
the feature-owned kind `453` app event. Only an active admin may propose and commit canonical opening, after the
component's local admission, cooldown and recovery-priority checks. This replaces unrestricted member opening while
preserving non-admin request creation. Acceptance and the retention update remain admin-only.

The request binds the group and parent state, proposer, prior and target retention values, exact active-account cohort,
capability-state digest, creation time, and deadline. Membership, account identity, capability, admin policy, or
retention changes while it is open supersede it; the client requires a new request id rather than silently removing a
voter or binding a newcomer.

## Consent flow

The request UI MUST show:

- the proposed retention duration;
- the complete active-member cohort;
- the fixed history boundary from before the request opened, excluding messages written during voting and protocol recovery state;
- the absolute response deadline, the consequences of Yes and No, and that an existing Yes can authorize later
  acceptance until a canonical terminal outcome closes the request;
- that any cohort member can close voting as expired without an online admin, and a malicious member can abort voting
  early with a false timestamp, which cannot authorize a purge;
- that cleanup is cooperative and cannot guarantee removal from former, hostile, unsupported, or offline
  non-conforming clients, relays, exports, screenshots, backups, or other external copies.

Yes and No are explicit accessible actions. Dismissal, Back, process death, silence, and timeout are not decisions and
never imply consent. No control is preselected, and V1 carries no custom prompt text.

A member's Yes becomes canonical through the component's one-record state update. A No is submitted as the rejected
terminal Commit rather than as an advisory event. The selected No transition removes the open component, so later Yes
material cannot replace it. A conforming signer durably refuses to sign two decisions for one request. Competing
same-parent terminal Commits are resolved only by canonical convergence; relay arrival order and locally observed proof
order never choose group state.

The proposer may cancel only while open, using the versioned cancellation proof and terminal Commit. Expiry is bounded
to at most seven days by request bytes. At the local deadline a client stops offering responses and persists a
provisional expired projection across restart, but expiry never means consent. Canonical accepted, rejected, cancelled,
expired, and superseded outcomes are the versioned terminal finalizations defined by the component owner. Rejected,
cancelled, expired, and superseded requests require a new request id.

Capable online cohort clients automatically attempt canonical expiry within the component's bounded interval, including
for an unusably future-dated window. The durable obligation survives restart and failed publication. Admins honor the
group-wide cooldown and prioritize pending recovery before another opening. These rules do not guarantee progress with
all members offline, unavailable signers, malicious admins or adversarial delivery.

## Atomic finalization

Acceptance requires one canonical Yes from every account in the bound cohort. The active-admin Commit atomically:

1. sets the exact requested prospective retention value;
2. removes the temporary request state and requirement;
3. carries the accepted finalization bytes; and
4. installs suppression for the immutable request-bound history range.

The component owner's exact proposal-set rule rejects missing, duplicate, or unrelated proposals. No client starts
suppression or deletion from a request, an individual Yes, an uncommitted No proof, local expiry, or receipt. The
accepted Commit is the linearization point.

The target is application plaintext whose MLS source epoch precedes the request's opening epoch, as derived by the
component owner. Acceptance does not expand that range. Messages written during voting retain their original retention
semantics; the requested prospective policy starts at acceptance. This replaces the tracker proposal's acceptance-relative
range so delayed or backdated acceptance cannot authorize deleting later messages. The target excludes
MLS Commits and proposals, retained recovery anchors, candidate state, pending publication obligations, required audit
or security material, and content already governed by an independent delete action. This one-shot flow does not change
the prospective retention invariant for ordinary timer changes.

## Crash-safe application and late arrivals

After accepted finalization, each conforming member installs a reversible suppression boundary before rendering the
target again. The boundary covers timeline, search, notifications, exports, reply previews, TTS, and media caches.
Late, replayed, or newly recovered pre-boundary app payloads are suppressed before presentation.

A client checkpoints the effect before exposing progress, applies cleanup idempotently by request id and activation
epoch, resumes at every restart boundary, and emits no applied receipt before all stores it controls have finished.
Suppression follows canonical branch selection. If convergence supersedes the authorization while its parent is still
inside the rollback horizon, suppression is withdrawn and destructive cleanup has not begun. Best-effort deletion starts
only after the accepted Commit's parent is outside that horizon, while authorization remains on the settled selected branch.

Logical removal is not a physical-overwrite claim. Storage encryption, filesystem behavior, platform backups, exports,
and non-conforming copies limit secure-erasure guarantees.

## Results and privacy

The versioned finalization and receipt identities are defined by the component owner. User-visible status separates:

- `accepted`: canonical consent and authorization exist;
- `applying`: this account is suppressing and cleaning its controlled stores;
- `local_applied`: this account completed durable cleanup and emitted its applied receipt;
- `group_complete`: one applied receipt is known for every account in the bound cohort;
- `partially_completed`: receipt evidence exists but is not all-applied, or a member emitted a coarse failed receipt.

Only `accepted` is a canonical wire outcome. Application and completion values are local projections over durable local
state and authenticated receipts; clients may learn them at different times. Missing, offline, unsupported, or failed
members MUST NOT be shown as complete.

The UI MUST expose only the privacy-minimizing aggregate result. It MUST NOT show a member/device cleanup table, message
ids, deleted-content hashes, filenames, per-message counts, device inventory, precise cleanup timing, or detailed
failure reasons. The protocol still authenticates each receipt sender so duplicate and forged receipts can be rejected.

## Boundaries

This feature does not grant or modify authority for sender retraction, admin moderation, delete-for-me, general group
disbanding, arbitrary historical ranges, or physical remote wipe. Those actions require their own scopes and identities.
Normal prospective retention remains the default when no accepted purge finalization exists.

## Conformance

The normative matrix is in [foundation conformance](../foundation/conformance.md). It covers non-admin request creation,
unanimous acceptance, explicit No, cancellation, expiry and restart, duplicate/conflicting decisions, terminal races,
request replay, membership/admin/capability changes, unsupported clients, rollback-horizon behavior, crash recovery,
late target messages, privacy-minimizing receipts, and complete versus partial result projection.
