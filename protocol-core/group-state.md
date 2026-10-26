# Group state

Status: adopted.

Each Marmot group has one canonical MLS state at a time. A client MAY temporarily hold candidate or pending state, but
only one state is visible as the group's canonical state.

## Lifecycle states

The group lifecycle has six states:

- `Stable`: the group has a canonical MLS epoch. Normal inbound processing and outbound work MAY proceed.
- `PendingPublish`: the client has prepared a local group-state commit, but has not confirmed that the required bytes
  were published.
- `Merging`: publication was confirmed, and the client is applying the staged commit to its local canonical state.
- `Recovering`: the client is selecting a safe branch from retained state after detecting a fork-shaped conflict or
  admitting a valid disband candidate that requires terminal convergence.
- `Unrecoverable`: required retained material is permanently missing or corrupt, no verified repair path is available,
  and the client therefore cannot safely establish canonical state or resolve an in-flight transition.
- `Disbanded`: an authenticated disband Commit was selected by a bounded convergence pass. The group is terminal,
  read-only, and cannot resume or rejoin under the same group id.

`Unrecoverable` is local to one client. It does not mean the Marmot group is dead. It means that this client MUST repair
its group state, restore retained material, rejoin, or discard the local group copy before it can safely send or apply
more group traffic.

`Disbanded` is authenticated canonical group state backed by
`marmot.group.lifecycle.v1`. It is absorbing and has no repair or rejoin
transition. A replacement conversation creates a new group.

`Stable` is the only state where a client MAY prepare a new local group-state commit. Outbound app payloads are also
held while convergence input is unresolved, because they MUST be encrypted against the selected canonical state.

A member that has sent a SelfRemove proposal also enters the local `Leaving` gate defined in
[member-departure.md](./member-departure.md). `Leaving` is not a canonical group lifecycle state: the MLS group state
still contains the member until a commit removes it. It is a durable outbound restriction on the leaving client and may
span multiple epoch-bound SelfRemove proposals.

An admin whose irreversible disband request is unresolved enters the durable
local `Disbanding` gate defined in
[../app-components/group-lifecycle-v1.md](../app-components/group-lifecycle-v1.md).
Like `Leaving`, `Disbanding` is not a canonical lifecycle state. It blocks all
new outbound work while the request is prepared, published, retried, or
evaluated by convergence.

A member whose own removal has been realized holds the group as a removed, inactive copy per
[member-departure.md](./member-departure.md) ("Realizing removal"). Like `Leaving`, this is not a canonical lifecycle
state. It is locally inactive and does not resume without an explicit rejoin.

The optional "unverified" presentation described in [joining.md](./joining.md) ("Welcome-bootstrap trust") is neither
a lifecycle state nor a protocol condition. It is an application-defined activity heuristic and does not change the
legal transitions below.

## Legal transitions

```text
Stable
  -> PendingPublish      local group-state commit prepared
PendingPublish
  -> Merging             publish obligation confirmed
PendingPublish
  -> Stable              publish obligation failed or was abandoned
PendingPublish
  -> Unrecoverable       possibly published transition is permanently missing or corrupt with no verified repair path
Merging
  -> Stable              staged commit applied
Merging
  -> Unrecoverable       confirmed transition material is permanently missing or corrupt with no verified repair path
Stable
  -> Recovering          fork detected, or valid disband candidate admitted
Stable
  -> Unrecoverable       required state is permanently missing or corrupt with no verified repair path
Recovering
  -> Stable              a canonical branch was selected and applied
Recovering
  -> Disbanded           a selected branch terminates the group
Recovering
  -> Unrecoverable       required branch material is permanently missing or corrupt with no verified repair path
Unrecoverable
  -> Stable              state was repaired, restored, or replaced by a verified join
Disbanded
  -> (none)              terminal
```

Fork detection runs only from `Stable`, against settled canonical state, using the operational rule in
[convergence.md](./convergence.md) ("Fork detection"). Ordinary linear advancement does not enter `Recovering`. A valid
Commit that changes `marmot.group.lifecycle.v1` to `disbanded` is the exception: admitting that candidate into its
mandatory bounded pass changes `Stable -> Recovering` even when no divergent edge exists. This exception does not
classify the candidate set as forked or change branch scoring.

There is no `Merging -> Recovering` edge: a competing branch or locally published disband Commit observed while the
client is applying its own confirmed commit is retained, the merge completes to `Stable`, and admission into the
bounded pass then triggers the applicable `Stable -> Recovering` rule. `Recovering` re-entry is implicit:
convergence-relevant input that arrives while the group is already in `Recovering` and before the bounded pass cutoff is
folded into that recovery pass. Input retained after the cutoff belongs to a later pass. The group stays in `Recovering`
until a branch is selected and applied (`-> Stable` or `-> Disbanded`) or required branch material is permanently
missing or corrupt and no verified repair path is available (`-> Unrecoverable`).

The direct `Stable -> Unrecoverable` transition applies when normal linear processing discovers that required retained
history or authenticated state inside the rollback horizon is permanently unavailable or corrupt and no defined
authenticated repair path can restore it. A client does not enter `Recovering` merely to pass through to
`Unrecoverable` when no fork recovery is possible.

A client MUST reject a local group-state commit while the group is in `PendingPublish`, `Merging`, `Recovering`, or
`Unrecoverable`. A `Disbanded` client rejects all local and inbound group
traffic.

Inbound group messages MAY be retained in any non-`Stable` state. Whether retained inbound may change canonical group
state depends on the state:

- during `PendingPublish` and `Merging`, retained inbound MUST NOT be applied to canonical group state;
- during `Recovering`, retained inbound is replayed only as candidate material for convergence; canonical group state
  changes only when a selected branch is applied (see below);
- during `Unrecoverable`, retained inbound MUST NOT be applied to canonical group state until a verified repair path
  restores, repairs, or replaces the local group state.
- during `Disbanded`, inbound is not retained or applied and receives the
  `unknown_group` pre-convergence category.

While a group is in `Recovering`, a client MAY process or reprocess retained input to build candidate branches, score
them, and select a canonical branch. That processing MUST NOT release outbound work or emit delivered app payloads until
the selected branch has been applied and the lifecycle returns to `Stable`.

## Unrecoverable cases

A client enters `Unrecoverable` when it cannot safely establish canonical protocol state or complete an unresolved
state transition because required material is permanently missing or corrupt and no verified repair path is available.

Examples include:

- a retained state inside the rollback horizon is permanently missing;
- required material is missing or corrupt, so the client cannot validate any candidate branch from the retained anchor;
- local group state is corrupt and cannot validate the retained commit path;
- a possibly published local transition is permanently unavailable and cannot be reconstructed; or
- required material for an interrupted selected-branch application is permanently unavailable, so the application
  can be neither completed nor restored to its prior complete projection.

A client in `Unrecoverable` MUST NOT choose the current local state merely because it is the only state available. It
MUST stop applying group-state changes until it has a verified repair path.

After restart, the complete classification in [durability.md](./durability.md) ("Missing or corrupt material") applies.
Temporary unavailability keeps the current lifecycle and blocks the affected work. A wholly unapplied frozen batch MAY
instead be abandoned and recollected only under the all-input restart exception in that document. Permanent loss or
corruption changes the lifecycle to `Unrecoverable` only when no verified repair path is available.

A repair path MAY restore retained state, rejoin through MLS, or use another recovery method defined by a future
protocol-core document.

## Convergence status

Convergence has a separate derived status:

- `Syncing`: a bounded convergence pass is collecting selection-relevant input and neither the quiescence window nor the
  absolute collection deadline defined in [convergence.md](./convergence.md) has elapsed.
- `Resolving`: the pass input batch is frozen and the client is computing a deterministic fixed point over state already
  retained in that batch. It does not wait for fetches or admit later input; unresolved children remain deferred to a
  later pass.
- `Settled`: candidate processing reached a fixed point and the selected branch, if any, has been applied.
- `Blocked`: candidate processing cannot safely continue without a repair path, missing retained material, or sufficient
  local resources to finish the immutable admitted batch.

Convergence status is derived from stored input and policy. It is not a claim made by the transport.
`Settled` is therefore local to the input retained and admitted by the client. Transport synchronization is a separate
availability condition and MUST NOT be inferred from `Settled`.

The lifecycle state is authoritative; convergence status is a derived view of how convergence is progressing within it.
The legal combinations are:

| Convergence status | Lifecycle states it can appear in       | Notes                                                          |
| ------------------ | --------------------------------------- | -------------------------------------------------------------- |
| `Syncing`          | `Stable`, `Recovering`                  | bounded pass still collecting selection-relevant input         |
| `Resolving`        | `Stable`, `Recovering`                  | frozen-batch fixed-point work; no waiting or new input         |
| `Settled`          | `Stable`, `Disbanded`                   | fixed point reached and any selected branch applied            |
| `Blocked`          | `Stable`, `Recovering`, `Unrecoverable` | needs retained material, a repair path, or local resources     |

Two couplings follow from this table. A group leaves `Recovering` for `Stable` only after convergence reaches
`Settled` (a selected branch was applied). A resource-caused `Blocked` status does not by itself change the lifecycle:
the immutable admitted batch remains unapplied and processing resumes when sufficient resources become available. Only
a `Blocked` status caused by required retained state that is permanently missing or corrupt is the `Unrecoverable`
condition: when recovery has no safe branch and no repair path, the lifecycle moves to `Unrecoverable`.
`PendingPublish` and `Merging` are local-publish states, not convergence passes, so convergence status is not meaningful
while the group is in them.

A disband Commit is the exception to ordinary linear advancement. When a valid
disband candidate is admitted from `Stable`, the client enters `Recovering`
even without a detected fork and runs the mandatory bounded convergence pass.
Publication may pass internally through `Merging` and `Stable`, but terminal
application occurs only through `Recovering -> Disbanded`. Selection of an
active branch instead returns the lifecycle to `Stable`.

## Local actions during convergence

When convergence status is `Syncing`, `Resolving`, or `Blocked`, a client MUST NOT prepare a group-state change or
encrypt an app payload against the unresolved state. It MAY queue the local intent until the group settles or reject it
as locally unavailable; the queue representation and user-visible behavior are application concerns.

Queued app-payload sends are encrypted after convergence status reaches `Settled` and the lifecycle state allows
outbound work.

Queued group-state changes are regenerated after convergence status reaches `Settled` and the lifecycle state allows
outbound work. A staged commit created before branch selection MUST NOT be reused after convergence changes the
canonical state. After a bounded pass, the fair scheduling rule in [convergence.md](./convergence.md) gives one
already-queued authorized group-state intent a preparation opportunity before queued inbound input alone starts
another pass.
