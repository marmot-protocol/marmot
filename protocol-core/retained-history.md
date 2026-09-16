# Retained history

Status: adopted.

Marmot clients need retained group state so they can recover from forks and late delivery.

Retention is a protocol tradeoff. Keeping more history improves recovery from delayed or withheld commits. Keeping less
history limits how far a client can be forced to replay old state and improves forward secrecy guarantees.

## Retained anchor

The retained anchor is the oldest group state from which a client can rebuild a candidate branch.

A client MUST retain enough state to replay candidate branches inside the group's rollback horizon. The storage format
is implementation-defined.

At minimum, a client needs retained state for:

- the current canonical tip;
- each epoch inside `max_rewind_commits` from the current tip;
- any staged local commit waiting for publish confirmation;
- any candidate parent state still needed by deferred input inside the rollback horizon.

These candidate-replay requirements are part of the broader restart contract in
[durability.md](./durability.md). That document also owns recoverability of admitted input, unresolved publication,
local protocol gates, and application effects; it does not extend the cryptographic release conditions below.

## Retained cryptographic material

Retained group state is functional state, not an instruction to snapshot every secret an MLS implementation exposes.
The material retained for each function is:

| Function | Material that remains available | Release condition |
| --- | --- | --- |
| Candidate authentication and advancement | The MLS member state needed to verify the retained epoch's member `PublicMessage` membership tags and to process a valid Commit path from that candidate parent, including private ratchet-tree or path material required by the active ciphersuite | The candidate parent is outside the rollback horizon and is not needed by staged, deferred, or recovery work |
| App-payload decryption and witness counting | The MLS application secret-tree state needed to decrypt messages for an eligible candidate epoch | The epoch is outside the retained app-payload window and is not needed by active convergence work |
| Transport or feature exporters | A derived exporter value only while its owning transport or feature still has an in-window protocol use for it; clients MAY instead derive it from retained MLS state when needed | The owning use expires, or the MLS state from which it can be derived is released |

The first row cannot generally be replaced with only the public ratchet tree, GroupContext, and Commit bytes. Marmot's
member handshake messages are MLS `PublicMessage` values whose membership tags require the source epoch's
`membership_key`, and advancing a branch can require private path material from the candidate parent.

Cryptographic material with no remaining function in this table MUST NOT remain available to protocol processing merely
because an implementation stores a whole-state snapshot. Pruning makes the released material unavailable for future
Marmot processing; physical overwrite guarantees, device backups, and storage-encryption mechanisms are implementation
and platform concerns.

## Late commits

Late commits are judged by their source epoch:

- If the source epoch is at or after the retained anchor, the commit MAY be replayed during convergence.
- If the source epoch is older than the retained anchor, the commit MUST receive a stale disposition, reported as
  `BeyondAnchor`.
- If the source epoch is inside the rollback horizon but the required retained state is missing, convergence MUST report
  `MissingRetainedAnchor`, leave canonical group state unchanged, and move the local group to `Unrecoverable`.

The third case is storage loss, not a transport gap. A commit whose parent state has not yet been replayed — because the
parent commit has not arrived — is **deferred**, not `Unrecoverable`: it waits for the parent under
[convergence.md](./convergence.md) ("Candidate branches") and [inbound-processing.md](./inbound-processing.md#deferred-input)
("Deferred input"). `MissingRetainedAnchor` and the move to `Unrecoverable` apply only when retained state that a candidate
branch requires inside the rollback horizon has been *lost from storage* (see [convergence.md](./convergence.md): "the
client enters `Unrecoverable` until it has a verified repair path").

## App-payload retention

MLS application messages have their own retained decryption window for app payloads. The width of that window is the
pinned convergence-policy constant `app_payload_past_epoch_limit` (see [convergence.md](./convergence.md)).

An MLS application message at `message_epoch` is inside the retained app-payload window iff:

```text
reference_tip_epoch - message_epoch <= app_payload_past_epoch_limit
```

For delivery decisions, `reference_tip_epoch` is the canonical tip epoch. For witness counting, `reference_tip_epoch`
is the `tip_epoch` of the candidate branch being evaluated.

An MLS application message outside the retained app-payload window MUST expire (a stale disposition).

An MLS application message for a future candidate epoch MAY remain deferred until convergence selects a branch that can
decrypt its Marmot app payload or until the message expires.

The retained app-payload window is not a complete offline-message-history guarantee. A client that returns after more
than `app_payload_past_epoch_limit` canonical epoch advances can conformantly lose application payloads from older
epochs even when their transport objects remain available. Applications that require complete long-term history need a
separate protocol mechanism; transport retention alone does not extend the MLS decryption window.

## Authorized application plaintext purge

A selected Commit carrying a valid [`marmot.group.history-purge.v1`](../app-components/history-purge-v1.md)
authorization establishes one reversible local suppression boundary at its resulting activation epoch. The client MUST
suppress every delivered Marmot app payload whose MLS source epoch is less than that boundary before any application
surface can render or emit it. If a later convergence pass supersedes the Commit while its parent remains inside the
rollback horizon, the client withdraws the suppression with the Commit's other application effects and performs no
destructive deletion.

Idempotent local best-effort deletion becomes eligible only after convergence is settled, the selected branch still
contains the authorization, and the request's parent epoch is outside the current canonical tip's rollback horizon. The
client then deletes application-controlled plaintext and resumes unfinished cleanup after restart, as defined by
[consensual-history-purge.md](../features/consensual-history-purge.md).

The suppression boundary does not move the retained anchor or the app-payload decryption window. It MUST NOT release
candidate-authentication state, application secret-tree state, pending publication data, replay markers, or any other
protocol recovery material before that material's release condition in this document is reached. Receiving a No,
silence, an unsupported member, or expiry of a request creates no suppression boundary.

## Pruning

After convergence reaches a settled selected branch, a client SHOULD prune retained states older than the group's
rollback horizon.

Pruning MUST NOT remove retained state that is still needed to resolve an active `PendingPublish`, `Merging`,
`Recovering`, or `Unrecoverable` state.

When a retained state or app-payload epoch is pruned, the client MUST also release the cryptographic material whose
release condition has been reached in the table above.
