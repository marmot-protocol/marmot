# Convergence

Status: adopted.

Convergence chooses one canonical branch from unordered group input.

Commits are the consensus log. MLS application messages can witness that members used a branch, but they do not create
epochs and they do not replace MLS commit validation.

## Guarantees and assumptions

Convergence has separate safety and liveness guarantees.

For safety, clients that start from the same retained anchor, use the same convergence policy, and resolve the same
frozen authenticated input batch with the same retained dependencies MUST select the same canonical branch and assign
the same convergence dispositions. Transport arrival order, local scheduling, and device speed do not weaken this
requirement.

For liveness across more than one pass, the relevant input must eventually close. Relevant input is closed for a group
when there is a finite set of valid selection-relevant input and authenticated dependencies, no later valid input can
extend or change that set, and every compared client has acquired the same set while it remains inside the applicable
retention and rollback horizons. Given that closure, clients using the same convergence policy that continue executing,
retain the required state, revisit deferred work, and have sufficient local resources MUST eventually reach equivalent
canonical protocol state as defined in
[../foundation/conformance.md](../foundation/conformance.md).

This liveness guarantee does not apply during permanent delivery suppression, an unbounded stream of valid
selection-relevant input, loss beyond the retained-history limits, incompatible convergence policies, or local resource
exhaustion. A client affected by one of those conditions still follows the fail-closed safety rules below.

`Settled` is a local fixed point over the protocol input currently retained and admitted by that client. It is not
global finality, proof that every transport has finished synchronization, or a promise that later valid input cannot
open another pass.

Process interruption does not weaken the safety guarantee. After interruption, liveness applies only after the client
has recovered the required authenticated inputs and dependencies and resumed execution, with the same input-closure,
retention, convergence-policy, and resource conditions above. The recoverable-input, pass-restart, and observer-atomic
apply rules are defined in [durability.md](./durability.md) ("Restart equivalence" and "Convergence interruption
boundaries").

## Convergence policy

The convergence policy tells clients how to run convergence. The v1 convergence policy is a set of protocol constants:
every client MUST use exactly the values below. The policy is not carried in group state and is not a local preference;
every convergence pass, and every branch scored within it, uses the same values.

The convergence policy contains:

- `max_rewind_commits`: how far back from the current tip a branch MAY fork and still be eligible.
- `app_payload_past_epoch_limit`: how many past MLS epochs MAY still produce delivered app payloads or app-payload
  witnesses (the exact window formula is in [retained-history.md](./retained-history.md), "App-payload retention").
- `settlement_quiescence_ms`: the minimum time without new selection-relevant input before a client MAY treat a
  convergence pass as settled and release queued outbound work.
- `max_convergence_pass_ms`: the maximum duration of one convergence input-collection window. This deadline is measured
  from the start of collection and MUST NOT be extended by later input.
- `witness_quorum_senders_per_epoch`: the number of distinct senders needed for one branch epoch to count toward witness
  quorum.
- `witness_quorum_epochs`: the number of branch epochs that MUST meet sender quorum.
- `max_witness_override_depth`: the maximum commit-depth boost a branch MAY receive from witness quorum.

The Marmot convergence policy, version 1, is:

| Field                               | Value   |
| ----------------------------------- | ------- |
| `max_rewind_commits`                | `5`     |
| `app_payload_past_epoch_limit`      | `5`     |
| `settlement_quiescence_ms`          | `1000`  |
| `max_convergence_pass_ms`           | `5000`  |
| `witness_quorum_senders_per_epoch`  | `2`     |
| `witness_quorum_epochs`             | `1`     |
| `max_witness_override_depth`        | `1`     |

The table above is convergence policy v1. It does not define or encode a policy-version wire field.

`max_witness_override_depth` MUST NOT exceed `max_rewind_commits`. The witness-quorum boost is bounded so it can never
push a branch past the rollback horizon; allowing it to would let app-payload traffic beat an arbitrarily longer valid
commit branch, violating the invariant below. The version-1 values satisfy this bound, and any future policy component
MUST satisfy it.

`settlement_quiescence_ms` and `max_convergence_pass_ms` bound one convergence input-collection window. A pass starts
when the convergence scheduler admits eligible retained input into a new collection batch; receipt or durable retention
alone does not start a pass. Both intervals are measured with the client's local monotonic clock.

Selection-relevant input is newly retained or reclassified input that can still change deterministic resolution of the
current batch, for example by adding or invalidating an eligible candidate edge, changing a bounded witness score,
supplying a missing parent, or making deferred input processable. Selection-relevant input restarts quiescence. Ordinary
app-payload delivery that cannot change branch selection does not restart it. Neither do duplicate, invalid, stale,
already-dominated, or already-fully-counted witness inputs.

While the lifecycle is `PendingPublish` or `Merging`, inbound input is retained but the scheduler MUST NOT admit it into
a new pass. After the lifecycle returns to `Stable`, the fair scheduling rule below runs before queued inbound input
alone can start another pass.

A valid Commit that linearly advances the canonical tip starts or joins this bounded pass when the scheduler admits it,
even when no divergent edge is yet known. The canonical tip does not advance while the pass is `Syncing`; the linear
Commit is applied only when the collection window reaches its cutoff and resolves the frozen batch. If an eligible
divergent edge becomes available before that cutoff, the same pass changes the group lifecycle from `Stable` to
`Recovering`. It MUST NOT restart either timer, resnapshot `pass_base_epoch`, or briefly apply the formerly linear edge
as canonical state.

A valid candidate edge that changes `marmot.group.lifecycle.v1` to `disbanded` also changes the lifecycle from `Stable`
to `Recovering` when it is admitted, even when it is a linear edge and no divergent edge exists. This forced transition
does not assert that the candidate set is forked, restart either timer, resnapshot `pass_base_epoch`, or give the
disband candidate special branch-scoring priority.

The absolute pass deadline starts when the pass starts and MUST NOT restart. A client closes the pass at the earlier of:

1. `settlement_quiescence_ms` elapsing without selection-relevant input; or
2. `max_convergence_pass_ms` elapsing.

At that cutoff, the client freezes the exact batch: every candidate Commit, proposal, application-message witness,
candidate-parent state, and other authenticated dependency admitted to the pass. It reaches a deterministic fixed point
using only that batch. This `Resolving` phase MUST NOT wait for a fetch, admit newly retained input, or restart either
collection timer. A Commit whose parent is absent from the frozen batch remains deferred to a later pass; the missing
parent does not keep this pass open.

Fixed-point resolution is not subject to a protocol wall-clock deadline: device speed MUST NOT make clients resolve the
same frozen batch differently. An implementation MAY yield and resume the work locally, but it MUST complete
deterministic resolution of that immutable batch before starting another pass. The only exception is process
interruption under [durability.md](./durability.md) ("Convergence interruption boundaries"): a wholly unapplied frozen
batch MAY instead be abandoned, after which every still-eligible input and authenticated dependency from that batch is
admitted to a later pass. This exception MUST NOT discard an input, resolve an accidental subset, or apply any result
from the abandoned batch.

A recovering client returns to `Stable` only after successfully selecting and applying a non-terminal canonical
branch. If the selected branch ends in `disbanded`, recovery instead enters the terminal `Disbanded` state, releases
live MLS and convergence state, and does not allow a later branch to supersede it, as defined in "Applying the selected
branch." A linear pass that began in `Stable` remains `Stable` after applying its selected advancement. If required
retained state, including the retained anchor, is permanently missing or corrupt and no verified repair path is
available, the client does not mutate canonical group state and enters `Unrecoverable` as required below. Temporary
unavailability instead leaves the immutable work unapplied and `Blocked`. Input retained after the cutoff is not
discarded; it belongs to a later pass. The local cutoff controls scheduling and batch membership only. Input arrival
time, cutoff time, and pass membership MUST NOT enter candidate validity or the branch score.

After relevant input closes under the assumptions above, dividing that same retained input across different bounded
passes MUST NOT change the eventual canonical result. Input excluded by one cutoff remains eligible for a later pass
until the protocol assigns it a terminal disposition. Implementations MUST NOT use timer tuning or pass partitioning to
resolve a difference that the deterministic selection rules leave open.

After a bounded pass settles in `Stable`, the client MUST give one already-queued local group-state intent one
preparation attempt against the selected canonical state before it begins another convergence pass solely because more
inbound input is queued. The intent is either admin-authorized or a same-account Commit that the same-account authority
in [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) permits in that state. A
self-update or a Leave does not receive this attempt, although any member may commit one. Inbound input remains durably
retained during that attempt. If the attempt cannot proceed with currently available authorization, prerequisites, or
signing capability, the scheduler proceeds rather than waiting indefinitely. A prepared Commit then follows the normal
publication and convergence rules; this scheduling guarantee does not make it valid, accepted, or canonical.

The preparation opportunity is bounded anti-starvation behavior, not an unconditional administrative-progress
guarantee. Marmot does not guarantee that a privileged transition becomes canonical while valid selection-relevant
input, including ordinary self-updates, continues without bound.

Convergence parameters are deliberately not group-tunable: a bad policy choice can fork a group. A future protocol
version that changes convergence behavior MUST ship the new policy as a new app component behind a required capability.
This includes changes to eligibility, retention horizons, comparison order, witness scoring, admissible input, or any
other rule that can change the selected branch. Clients MUST NOT infer the active policy from software version. Until
such a component exists, there is no mechanism to change the active policy.

## Fork detection

While the lifecycle is `Stable`, a fork-shaped conflict is detected when retained input produces a valid, eligible
candidate edge that diverges from the currently selected canonical commit path. The retained canonical suffix and the
divergent edge then provide at least two candidate branches from a shared `fork_epoch`. The client MUST enter
`Recovering` and open a bounded convergence pass before convergence selects and applies a branch.

A valid Commit that advances the current canonical tip, with no divergent eligible edge, is linear advancement and does
not by itself enter `Recovering`; it still follows the bounded-pass apply timing above. The exception is a valid
Commit that changes `marmot.group.lifecycle.v1` to `disbanded`: admission of that candidate forces
`Stable -> Recovering` so terminalization can occur only after selection, whether or not a divergent edge exists. A
Commit with an unavailable parent remains deferred and does not trigger recovery until replay against retained state
produces a valid divergent edge or validates it as the disband exception. Invalid, stale, duplicate, or outside-horizon
input does not trigger recovery. Fork detection derives parentage from validated MLS bytes and retained states, never
from transport metadata.

## Candidate branches

A client builds candidate branches by replaying MLS commit bytes from retained group states.

A candidate parent is the retained group state at the Commit's authenticated source epoch against which the Commit's
parent-dependent MLS authentication succeeds. It is the prior state used for commit authorization and resulting-state
validation; transport metadata never identifies it. Marmot's handshake messages are MLS `PublicMessage` values, so the
membership tag and sender signature cryptographically bind the Commit to that source-epoch state. Merely sharing an
epoch number does not make another retained state an alternate candidate parent.

A commit creates a candidate edge only when it validates against a candidate parent state. Validation here is full
commit validity: MLS validation; authorization of the authenticated committer against that parent state; and Marmot
component validation of the resulting state, including cross-component resulting-epoch checks such as the admin/leaf
coupling in [../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md) ("Validation").

Authorization is parent-relative: the client first identifies the candidate parent through MLS authentication, then
evaluates the committer against that state's policy. Failure against a retained state whose MLS authentication does not
match is not an authorization failure and cannot reject the Commit. The Commit creates an edge only from its candidate
parent when all checks succeed. A candidate edge whose resulting state fails Marmot component invariants MUST NOT be
created, so convergence can never select that invalid transition.

A valid Commit that changes `marmot.group.lifecycle.v1` to `disbanded` is
always admitted through a bounded convergence pass, even when it would
otherwise be a linear edge. This mandatory pass is a terminalization boundary,
not a new branch-scoring rule.

If no retained state passes the Commit's parent-dependent MLS authentication, the Commit remains deferred while its
authenticated source epoch is inside or ahead of the rollback horizon. Once authentication identifies its candidate
parent, a failed authorization check is terminal `authorization_failed`. An implementation MUST NOT infer terminal
authorization failure merely from the current absence of that parent.

A commit whose parent is not available remains deferred while its authenticated MLS source epoch is inside or ahead of
the rollback horizon. Deferred Commit expiry is epoch-based, not a local wall-clock policy:

```text
canonical_tip_epoch - commit_source_epoch > max_rewind_commits
```

Here `canonical_tip_epoch` is the epoch of the client's current canonical group state when it performs the check, and
`commit_source_epoch` is the epoch authenticated by the deferred MLS handshake message.

Deferred expiry deliberately uses the live canonical tip so obsolete input can age out as canonical state advances
across completed passes. Branch eligibility uses the frozen `pass_base_epoch` instead so an open pass cannot change its
rollback horizon while comparing candidates.

When that condition becomes true, the client reclassifies the Commit as stale and MAY release its retained bytes. If
the parent arrives first, the client replays the Commit and applies the normal candidate validity and `fork_epoch`
eligibility checks; a newly discovered fork outside the horizon is stale even when the child Commit's own source epoch
was more recent.

A client MUST NOT trust transport-provided parent metadata when building a branch. Parentage is derived by replaying MLS
bytes against retained candidate states.

Each candidate branch has:

- `fork_epoch`: the epoch where the branch diverged from retained canonical state;
- `tip_epoch`: the epoch reached after replaying the branch's valid commits;
- `tip_priority`: the authenticated ordering class of the branch's tip Commit. A Commit is `ordinary` when one Marmot
  authorization rule that permits a committer without admin authority covers the whole Commit in its candidate parent
  state, and `privileged` otherwise. The ordinary cases are a self-update Commit, a SelfRemove-only Commit, a
  same-account Commit under [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md), and a
  component change whose owning document explicitly permits a non-admin committer. The class depends only on the Commit
  and its candidate parent state: a Commit that one such rule covers is `ordinary` even when its committer is also an
  active admin, and a Commit that combines shapes no single such rule covers is `privileged`. The operation's category
  does not override its actual authorization rule.
- `tip_committer`: the authenticated Marmot account identity of the branch's tip commit sender, derived from the MLS
  credential/leaf that authenticated the commit, not from transport metadata.
- `tip_digest`: `SHA-256` of the serialized MLS message bytes of the branch's tip commit (the same Commit
  `MLSMessage` bytes the branch replayed to reach `tip_epoch`). These bytes are deterministic because Marmot pins one
  handshake wire format, so the same authenticated commit cannot yield two different digests (see
  [../foundation/mls-protocol.md](../foundation/mls-protocol.md), "Handshake wire format"). It is exactly 32 bytes and is
  always byte-for-byte the tip Commit's own `commit_digest`, regardless of how many earlier Commits the branch contains;
  both are `SHA-256` over that tip Commit's MLS bytes. `tip_digest` is only a final tie-breaker after fixed authenticated
  metadata.
- `raw_commit_depth`: the number of valid commits from `fork_epoch` to `tip_epoch`;
- fully validated app-payload witnesses at the branch epochs defined below.

The branch epochs of a candidate are the epochs strictly greater than `fork_epoch` and at most `tip_epoch`.

## Eligibility

A convergence pass snapshots `pass_base_epoch`, the epoch of the canonical group state when that pass starts. It stays
fixed until the pass selects and applies one branch; candidate replay during the pass does not advance it.

Only branches inside the rollback horizon relative to that fixed base are eligible:

```text
pass_base_epoch - fork_epoch <= max_rewind_commits
```

Branches outside that horizon MUST NOT be selected.

A branch that needs a retained state older than the retained anchor MUST NOT be selected.

A losing branch remains eligible for a later pass while its `fork_epoch` is inside the rollback horizon measured from
the live canonical tip and all state needed to replay it remains at or after the retained anchor. It becomes permanently
ineligible, and its retained-only inputs become stale, when the live canonical tip moves it outside that horizon, its
required state is older than the retained anchor, or it has a terminal validity failure. Losing one pass is not by
itself permanent ineligibility.

## App-payload witnesses

An app-payload witness is an MLS application message whose Marmot app payload decrypts against a candidate branch state
at one of that branch's branch epochs and passes the complete payload checks in
[../foundation/application-messages.md](../foundation/application-messages.md), including canonical structural
decoding and receiver authentication requiring the inner author identity to equal the Marmot account identity
authenticated by the MLS sender leaf. Decryption alone is not a witness. An MLS application message at `fork_epoch` or
earlier is not an app-payload witness for any candidate. A witness MUST also be inside the retained app-payload window,
evaluated with the candidate's `tip_epoch` as the reference tip (the window formula is in
[retained-history.md](./retained-history.md), "App-payload retention").

Witnesses are counted by distinct Marmot sender identity per branch epoch. The sender identity is the account identity
authenticated by the MLS leaf credential for the application message, not an outer transport public key, Nostr event
author, relay, local device id, or transient leaf index.

One sender identity cannot increase a branch score by sending many messages in the same epoch. In a multi-device group,
multiple MLS leaves for the same Marmot account count as one sender identity for witness quorum.

For each branch epoch:

```text
epoch_witness_score =
  min(distinct_valid_app_senders_at_epoch,
      witness_quorum_senders_per_epoch)
```

For the candidate branch as a whole, sum that per-epoch score:

```text
app_witness_score =
  sum over branch epochs of epoch_witness_score
```

`witness_quorum_met` is the boolean used below. It is true when at least `witness_quorum_senders_per_epoch` distinct
senders witnessed each of at least `witness_quorum_epochs` branch epochs, and false otherwise. Each epoch is evaluated
independently; the qualifying sender set MAY differ from epoch to epoch, and no single cohort is required to span all
quorum-counted epochs.

When `witness_quorum_met` is true, the branch receives a bounded depth boost:

```text
effective_commit_depth =
  raw_commit_depth
  + (witness_quorum_met ? max_witness_override_depth : 0)
```

The boost is capped by the pinned policy. App payload traffic MUST NOT let a branch beat an arbitrarily longer valid
commit branch.

## Branch selection

Eligible branches are compared in this order:

1. Higher `effective_commit_depth`.
2. Witness quorum beats no quorum.
3. Higher `app_witness_score`.
4. Lower `tip_priority` (`privileged` before `ordinary`).
5. Lower `tip_committer`.
6. Lower `tip_digest`.

`raw_commit_depth` has no separate comparison step. It is already part of `effective_commit_depth`; if effective depth
and witness-quorum status are both tied, a further raw-depth comparison is necessarily tied as well.

Lower `tip_committer` means lexicographic order over the authenticated account identity's raw 32-byte x-only
secp256k1 public key, as defined in [../foundation/identity.md](../foundation/identity.md). Lower digest means
lexicographic order over the 32 digest bytes. Digest ordering is a same-committer fallback, not the primary fork winner.

Every value in this comparison MUST come from MLS-valid bytes, retained state, decrypted app payloads, or the pinned
convergence policy.

Transport arrival order, transport timestamps, outer transport event ids, and local receive order MUST NOT participate
in branch selection.

## Same-epoch races

Two commits that advance the same candidate parent create competing one-commit branches. They use the branch-selection
algorithm above; same-epoch ordering is not a second algorithm that bypasses depth or witness criteria.

Only after `effective_commit_depth`, `witness_quorum_met`, and `app_witness_score` are tied does branch selection compare
the authenticated tip metadata:

```text
CommitOrderingSuffix {
  priority,       // privileged < ordinary
  committer,      // authenticated Marmot account id
  commit_digest = SHA-256(mls_bytes)
}
```

For a same-epoch race, `source_epoch` is equal by definition and is not another comparison field. When the preceding
branch criteria tie, a valid privileged tip wins over an ordinary tip before byte ordering. This prevents commit-byte
choice alone from making an ordinary self-update beat a tied admin removal; it does not let priority override a branch
that already won on bounded depth or witness evidence. If both tips have the same `priority`, lower `committer`
lexicographically wins. The lower `commit_digest` decides only when the same authenticated committer produced multiple
same-priority commits for the same source epoch.

This rule is for branch choice only. The stored message id used to mark a losing commit is still separate from the
ordering key. Implementations MUST NOT use transport source, relay metadata, or any unauthenticated sender claim in this
key.

## Applying the selected branch

After selecting a branch, a client tentatively replays the selected commit path from the retained parent state to
compute the resulting canonical state. Before exposing any result of that replay, it MUST compute the selected
branch's canonical state, dispositions, protocol gates or terminal conditions, and application effects. The client
then exposes those fields as one complete observer projection. Interrupted application follows
[durability.md](./durability.md) ("Observer-atomic transitions") and MUST NOT expose a partially applied branch.

As part of computing that projection, the client assigns dispositions (the disposition vocabulary is pinned in
[../foundation/errors.md](../foundation/errors.md)):

- commits on the selected path are accepted;
- valid commits retained only on a non-selected eligible branch are deferred while that branch can still participate in
  a later pass, and become stale under the permanent-ineligibility rule in "Eligibility";
- proposals consumed by selected commits are accepted;
- proposals consumed only by a losing branch are deferred while that branch remains eligible for a later pass and
  become stale under the permanent-ineligibility rule in "Eligibility";
- MLS application messages that decrypt on the selected branch are accepted, and their Marmot app payloads are
  delivered to the application;
- MLS application messages that decrypt only on losing branches are invalidated, and their app payloads are withdrawn
  from application output;
- commits and MLS application messages beyond retained history are stale (a commit older than the retained anchor is
  reported as `BeyondAnchor`).

Applying the selected branch also produces application-visible state notifications for changes the application MAY need
to render or act on. Examples include epoch advancement, member additions, member removals, app component changes,
branch recovery, and app payload invalidation.

When the selected branch ends in `disbanded`, the client emits exactly one
actor-attributed `group_disbanded` notification and suppresses presentation
notifications for the member/admin removals carried by that same Commit. The
leaf-scoped removal outcome and self-removal realization still apply for each
local leaf removed by the Commit, but they do not produce another presentation
row. The client then releases live MLS and convergence state. Later branches
cannot supersede a terminalized disband copy.

State notifications are derived only from accepted commits on the selected branch and the canonical resulting state
they produce. A state notification derived from a commit is attributed to that commit's `commit_digest` (the same
`SHA-256` over the commit's MLS bytes defined in "Same-epoch races"). When branch selection supersedes a commit the
client previously applied — including the client's own published and confirmed commit — the client MUST emit a
group-state-change invalidation naming the superseded commit, and every state notification attributed to that commit
is withdrawn: the application treats the changes it announced as not having happened. This is the state-notification
counterpart of app-payload invalidation. The superseded Commit's disposition changes from `accepted` to `deferred` if
its branch remains eligible for a later pass, or to `stale` under the permanent-ineligibility rule in "Eligibility."

Notification objects are local API surface, so their exact shape is implementation-defined; the conformance
requirement is the resulting view. Once convergence is settled, the state notifications still in effect are exactly
those derivable from the accepted commits on the selected branch, and a group-state change that lost branch selection
MUST NOT remain visible to the application as a completed change.

If required retained state is unavailable, the client MUST report the missing retained anchor and MUST NOT mutate
canonical group state. Temporary unavailability leaves convergence `Blocked`. If the state is inside the rollback
horizon, is permanently missing or corrupt, and no verified repair path is available, the client enters
`Unrecoverable`.

After applying the selected branch, retained-state release follows
[retained-history.md](./retained-history.md) ("Pruning"); that document owns the pruning obligation and its exceptions.
