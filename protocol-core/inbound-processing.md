# Inbound processing

Status: adopted.

Inbound processing accepts bytes from a transport, turns them into Marmot protocol input, and gives each input a
protocol outcome: either a rejection category or, for input that enters convergence, a convergence disposition.

Transport delivery is evidence that bytes exist. It is not evidence that those bytes define the canonical group state.

## Processing shape

```text
transport message
  -> peel or decode transport envelope
  -> retain protocol bytes
  -> classify welcome, commit, proposal, or MLS application message
  -> produce one protocol outcome:
     -> reject before convergence with a rejection category; or
     -> feed processable group-state input into convergence
        -> emit accepted, stale, deferred, or invalidated disposition
        -> emit application-visible output when canonical state or delivered payloads change
```

The exact local API is implementation-defined. The protocol-visible outcome is either a rejection category or a
convergence disposition. The category and disposition vocabularies, including the four dispositions (`accepted`,
`deferred`, `stale`, `invalidated`), are pinned in [../foundation/errors.md](../foundation/errors.md).

## Message identity

Each inbound message has a message id used for deduplication. A client MUST deduplicate before applying state changes.

The message id used for deduplication MUST be stable for the carried protocol bytes. It MUST NOT depend on local receive
order, transport source order, subscription id, or any local storage identifier.

Duplicate input maps to the `duplicate` category in [../foundation/errors.md](../foundation/errors.md) and MUST NOT be
applied twice. Convergence outcomes named in `PascalCase` below, such as `BeyondAnchor`, map to a disposition and a
shared `snake_case` category in the "Named convergence outcomes" table in `errors.md`.

## Classification

After transport peeling, a group message is one of:

- a commit;
- a proposal;
- an MLS application message carrying a Marmot app payload;
- malformed or unsupported input.

A welcome is addressed to one member and creates or joins a group according to the MLS welcome rules and Marmot identity
rules.

Malformed input MUST fail closed. Unsupported input MUST fail closed when the active group policy requires support for
that input (e.g. a welcome requires capabilities the client does not support).

Encoding, branch-independent required-signature, and required-feature checks run before convergence. Required MLS
authentication that needs retained source-epoch or candidate-parent state — including membership-tag or sender-signature
validation — instead runs while replaying the input against retained source-epoch states. If no state authenticates the
membership tag, the input remains deferred while its parent may still arrive. Once MLS authentication identifies the
candidate parent, a failed sender-signature or authorization check is terminal for that input. The candidate-edge and
terminal-rejection rules are defined in [convergence.md](./convergence.md), "Candidate branches."

When the candidate parent has an open [history-purge request](../app-components/history-purge-v1.md), an external join
or resync Commit is invalid until the request closes canonically. Such external Commits cannot carry its required
terminal proposal set. Any active cohort member may commit expiry after the response deadline under the component's
proof rules, so closure does not require an online admin. Member-driven binding changes instead require atomic
supersession with the normal authority for that change. A disband Commit requires closure in a prior canonical Commit.

Input naming a group for which the client has no processable group state receives the `unknown_group` category before
convergence and no convergence disposition. The client cannot authenticate or classify a branch without that state.

## Transport-deferred input

A received transport object is not yet Marmot protocol input when the client cannot recover its inner MLS bytes with
the currently available transport decryption keys. When a later canonical epoch, retained candidate state, staged
state, or verified repair could make the object decryptable, the current category is `transport_deferred`, not
`stale_epoch` or `invalid_encoding`, and the object receives no convergence disposition.

The active transport binding defines how a client retains, retries, refetches, or backfills such an object. A retained
object MUST be retried whenever the transport decryption context changes in a way that could change the result.
Implementations MAY suppress retries while that context is unchanged.

A client MAY refuse to retain an unclassified transport object under a local resource bound. That outcome is
`resource_refused`: it makes no claim that the object is invalid or permanently unreadable. A refused object MUST NOT
be recorded as a terminal duplicate, and the client MUST NOT claim that the affected transport history is synchronized
until the binding's recovery rule has given the object another delivery opportunity.

## Deferred input

A client MAY defer recovered Marmot protocol input when it cannot yet be processed but could become processable after
more protocol bytes arrive.

Common deferred cases:

- an MLS application message for a future candidate epoch;
- a child commit whose parent branch is unavailable;
- input received while the group is in `PendingPublish` or `Merging`.

Deferred input MUST be retried when the missing state becomes available or when convergence advances the canonical
branch.

## Stale input

Input that cannot affect the group MUST receive a stale disposition. This includes:

- commits older than the retained anchor (`BeyondAnchor` -> `stale_epoch`, per
  [retained-history.md](./retained-history.md));
- MLS application messages older than the retained app-payload window (`stale_epoch`; the window is
  `app_payload_past_epoch_limit` past epochs, see [convergence.md](./convergence.md));
- commits that fork from outside the rollback horizon: these are ineligible for branch selection (see
  [convergence.md](./convergence.md), "Eligibility") and receive the `stale_epoch` category; when their source epoch is
  also older than the retained anchor, the named outcome is `BeyondAnchor`.

The `snake_case` names in parentheses are the shared categories in [../foundation/errors.md](../foundation/errors.md);
`BeyondAnchor` is a named convergence outcome that maps to the `stale` disposition and the `stale_epoch` category.

Stale input MUST NOT mutate canonical group state.

## Application-visible output

Inbound processing can produce two kinds of output for the application:

- state notifications, when canonical group state changes or a retained decision becomes visible;
- delivered app payloads, when an MLS application message is accepted on the selected branch.

State notifications include events such as:

- group joined;
- epoch advanced;
- member added or removed, including the local member's own removal (see
  [member-departure.md](./member-departure.md), "Realizing removal");
- component state changed;
- group disbanded by an authenticated admin;
- branch recovered;
- app payload invalidated because its MLS application message belonged only to a losing branch;
- group-state change invalidated because the commit it was derived from was superseded by branch selection.

A state notification is not a delivered app payload. It tells the application what changed in the group state.

Realizing the local member's own removal is derived from retained canonical state, independently of any later input's
validity or disposition. The required check and notification are defined in
[member-departure.md](./member-departure.md), "Realizing removal."

State notifications track the selected canonical branch. When convergence supersedes a commit the client previously
applied, the client MUST emit a group-state-change invalidation naming the superseded commit, and state notifications
attributed to that commit are withdrawn from application output (see [convergence.md](./convergence.md), "Applying the
selected branch"), so the application never keeps rendering a group-state change that the canonical state contradicts.

The selected disband notification is terminal and is not withdrawn: after
terminalization the local copy no longer participates in convergence.

## Delivered app payloads

An MLS application message is an input to convergence. A delivered app payload is the output handed to the application
after that input is accepted.

A Marmot app payload is delivered only if its MLS application message decrypts on the selected branch and remains inside
the retained app-payload window.

A Marmot app payload whose MLS application message decrypts only on a losing branch MUST be reported as invalidated, not
delivered as accepted application output.

Restart does not cancel a delivery, notification, withdrawal, or invalidation effect. Re-emission, deduplication, and
reconstruction follow [durability.md](./durability.md) ("Application effects after restart").
