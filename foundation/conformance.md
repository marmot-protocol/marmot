# Conformance state equivalence

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#formalization-and-review-boundary).

This document defines the protocol-state projection used to compare Marmot clients in deterministic conformance tests.
It defines equality over protocol meaning, not equality over implementation storage.

## Canonical snapshot

A conformance snapshot for one group contains:

- the raw MLS group id;
- the MLS epoch;
- `SHA256` of the TLS-serialized MLS `GroupContext`;
- the exporter commitment defined below;
- every nonblank leaf in leaf-index order, including its leaf index, Marmot account identity, MLS signature public key,
  and advertised capabilities;
- the group-required capabilities;
- every `GroupContext.extensions.app_data_dictionary` entry in ascending component-id order, including the exact
  component value bytes;
- the canonical group lifecycle and current convergence status;
- every local protocol gate or terminal local condition that restricts legal group actions;
- the protocol-relevant meaning of every unresolved required publication: exact outbound bytes, recipient scope,
  whether an external publish attempt may have occurred, whether the required acknowledgement is known to have
  succeeded, and the conformance projections of its prior and pending group states from
  [../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md);
- the current convergence disposition of every scenario input known to the client, keyed by a stable synthetic
  scenario name rather than transport metadata; and
- application-visible outputs, state changes, and invalidations produced for the scenario, keyed by their stable
  effect identities, including whether each effect's observation boundary is established under
  [../protocol-core/durability.md](../protocol-core/durability.md) ("Application effects after restart").

Two clients have equivalent canonical protocol state when every applicable field above is equal. Full scenario
quiescence additionally requires that neither client has an unresolved convergence pass or required publication.

Local queue layout, transport cursors, retry counters, database row ids, storage encoding, pruned secrets, and private
ratchet state are not part of canonical protocol-state equality. A test MAY compare those as separate availability,
resource, or implementation assertions.

This projection is a conformance-test interface. It defines no wire message, group extension, or interoperable
serialization.

## Crash and restart scenarios

Durability conformance compares a restarted client with an uninterrupted reference given the same subsequent local
actions and transport outcomes, at complete observer boundaries. The restarted client MAY expose a longer
`PendingPublish`, `Merging`, `Recovering`, or `Blocked` interval, but after required work completes its snapshot MUST
equal the reference snapshot. Conformance tests for this contract MUST cover at least these boundaries:

1. **Prepared, not published:** interrupt after preparation but before any external attempt. Recovery either abandons
   the preparation with the prior canonical state intact or retries the same obligation; pending state is never
   canonical before acknowledgement.
2. **Acknowledgement uncertain:** externally accept the bytes, interrupt before the acknowledgement is recoverable,
   and redeliver or retry. Recovery keeps one unresolved obligation, never generates replacement Commit bytes, and
   reaches one effective application of the original Commit after a conforming acknowledgement.
3. **Confirmed, not applied:** interrupt after confirmation and at several points during canonical application.
   Recovery produces exactly the confirmed resulting state and does not expose a mixed epoch, component, disposition,
   or output projection.
4. **Applied, derived work incomplete:** interrupt after canonical state changes but before each disposition,
   notification, delivery, withdrawal, or invalidation crosses its observation boundary. Recovery re-emits each
   unobserved effect with its stable effect identity or re-exposes an equivalent reconstructible projection, preserves
   one effective output per identity, and completes every required inverse effect. Repeat after an acknowledgement or
   equivalent projection has established observation and verify that restart does not create a second effective output.
5. **Collecting:** interrupt with eligible admitted input collected and more input retained near each timer boundary.
   Resetting local timers or changing pass partitioning may delay settlement but, after relevant input closes, produces
   the same canonical snapshot and dispositions as uninterrupted execution.
6. **Frozen resolving batch:** interrupt while fixed-point work is incomplete. Recovery either resolves the identical
   batch or wholly recollects its still-eligible input; it never selects from an accidental subset or admits later
   input into the old frozen batch.
7. **Selected branch applying:** interrupt after selection at each multi-part apply boundary, including a branch that
   supersedes previously delivered payloads or state notifications and a branch that disbands the group. Recovery
   exposes either the complete prior projection or the complete selected projection, never a mixture.
8. **Missing or corrupt material:** remove one selection-relevant candidate parent, admitted input, frozen dependency,
   or acknowledgement-uncertain pending transition inside its active horizon. If exact reconstruction is permanently
   impossible and no verified repair path is available, recovery enters `Unrecoverable`, leaves any associated admitted
   input deferred with `missing_history`, and does not select the only remaining local branch. Temporary unavailability
   instead blocks the affected work without changing the lifecycle solely for that reason.
9. **Local gates and terminal effects:** interrupt while `Leaving` or `Disbanding`, while realizing local-leaf removal,
   and while terminalizing disband. Recovery preserves the outbound gate and reconstructs the required effective
   notification or tombstone without a duplicate presentation effect.

These tests compare behavior and the projection above. They MUST NOT require a database schema, transaction API,
snapshot encoding, process scheduler, or one snapshot per epoch. The owning normative rules are in
[../protocol-core/durability.md](../protocol-core/durability.md).

## Exporter commitment

The conformance exporter secret is:

```text
MLS-Exporter("marmot", "convergence-conformance-v1", 32)
```

The snapshot contains only this commitment:

```text
SHA256(
  "marmot-convergence-conformance-v1" ||
  0x00 ||
  conformance_exporter_secret
)
```

The domain string before `0x00` is exactly 33 ASCII bytes. The raw exporter secret MUST NOT appear in logs, reports, or
test artifacts. The commitment is limited to synthetic conformance tests and local forensic comparison; production
telemetry MUST NOT export it.
