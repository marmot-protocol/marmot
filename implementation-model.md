# Marmot Implementation Model

Status: non-normative.

This document describes one way to implement the Marmot protocol. It is not a wire contract.

The normative rules live in the protocol documents. A compliant client can use different module names, queues, database
tables, and API shapes.

## Boundary

A Marmot client needs one local component that owns group-state transitions. That component may be an engine, state
machine, actor, service, library, or process.

Other local code can ask it to create local actions, feed it inbound protocol bytes, publish its outbound bytes, and
confirm or fail pending publication.

## Local State Owner

For each group, an implementation will usually track:

- the current canonical state;
- one unresolved local publish obligation, if any;
- retained prior states or anchors within the active retention policy;
- received protocol bytes and their classified outcomes;
- local actions that must be regenerated after convergence changes the canonical state.

These are local mechanics. They are not wire types.

## Publish Obligations

A useful local API can return a publish obligation with:

- the outbound bytes to publish;
- the group or recipient class those bytes target;
- the source epoch and target epoch;
- a local pending reference.

After transport publication succeeds, the caller confirms the pending reference. After transport publication fails, the
caller fails the pending reference.

The pending reference is local. Marmot protocol bytes do not carry it.

## Replay And Convergence

Implementations need enough retained material to replay candidate state transitions during the policy window. This often
means storing raw MLS message bytes, welcome bytes, prior state snapshots, and local classification metadata.

The protocol defines what must be reproducible. It does not define table names, cache keys, or snapshot formats.

## Durability Boundary

The normative restart contract is [protocol-core/durability.md](./protocol-core/durability.md). An implementation may
satisfy it with transactions, journals, snapshots, replay, derived indexes, or another strategy. It need not keep one
physical snapshot per epoch, and protocol-state atomicity does not require one physical write.

The useful design boundary is logical: before outbound bytes can escape, their exact publish obligation and recovery
states are reproducible; before a selected branch is exposed, canonical state, dispositions, gates, and application
effects form one complete observer projection. Restart recovery can resume work or replay deterministic work from a
verified boundary. It cannot invent a success, silently omit admitted input, or expose a mixed projection.

Local application delivery APIs may use acknowledgements, cursors, an effective-state query, or idempotent callbacks.
Those shapes are implementation-defined. They need to preserve the protocol requirement that restart neither loses a
required effect nor creates a second effective delivery.

## Convergence Policy Overrides

The normative pinned-policy rule lives in [protocol-core/convergence.md](./protocol-core/convergence.md) ("Convergence
policy"). Implementations and simulators can expose local convergence-policy overrides for testing, such as shrinking
the quiescence window or widening the rollback horizon in a harness. Those overrides are development tooling; a product
using non-default values is non-conformant under the owning protocol rule.

## Outcomes

Local APIs should expose classified outcomes for inputs that do not produce application content.

The API names can vary. Their categories should map to the complete Marmot classification surface in
[foundation/errors.md](./foundation/errors.md) ("Input categories") rather than maintaining a separate list here.

## Post-join rotation window

`protocol-core/joining.md` requires a new member to perform a post-join self-update as a `SHOULD`, before sending
application payloads when feasible. The concrete operational target carried forward from MIP-02 is to complete that
self-update within 24 hours of joining. This window is local operational guidance — it is not interop-visible and no
other client can observe or enforce it — so it lives here rather than in the protocol document. An implementation may
schedule the rotation sooner.

## Same-account pairing carriers

The normative multi-device feature treats the pairing carrier as untrusted and replaceable. Platform adapters can use
Apple peer-to-peer networking, Wi-Fi Direct or Wi-Fi Aware where available, a temporary hotspot, a local-network
socket, or another rendezvous mechanism. Carrier discovery, permissions, lifecycle, and fallback UI are implementation
details; the feature's signed descriptor, encryption, bounds, and timeouts still apply.

Enrollment may publish per-group Adds sequentially. An implementation that parallelizes them should limit one pairing
session to about four concurrently publishing Adds to bound retained candidate states and reduce avoidable convergence
races. This is scheduling guidance, not an observable protocol limit.

After Welcome delivery, a sponsor should retry the byte-identical Welcome after approximately 1, 2, 4, and 8 minutes,
with jitter, and stop automatic retransmission after 30 minutes. Absence of an acknowledgement then becomes a local
published-but-unacknowledged result, not a terminal enrollment failure. The sponsor retains the exact Welcome and
correlation record until later acknowledgement recovery, pairing reconciliation, canonical branch loss, group
deletion, or removal of the enrolled leaf.

## Network destination safety

A URL or endpoint carried in authenticated Marmot state or an authenticated app payload proves only that a
protocol-authenticated author selected those bytes. It does not authorize a client to contact that destination from its
own network environment.

Before automatically fetching from or uploading to such a destination, implementations should apply
platform-appropriate server-side request forgery protections to the initial destination, every redirect, and every
address selected for connection after name resolution. By default, this should refuse loopback, link-local, private or
unique-local, multicast, unspecified, platform-metadata, and other non-public special-purpose destinations unless
explicit local application or deployment configuration permits an intended private service. Implementations should
account for DNS rebinding and should not treat a check of the URL string alone as sufficient.

This is local availability and network-safety policy. Refusal makes the resource unavailable on that client; it does not
change the decoded bytes, invalidate a component, message, or Commit, alter canonical group state, or participate in
convergence. The
[IANA IPv4 and IPv6 special-purpose address registries](https://www.iana.org/numbers/registries) and
[OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
are useful operational references, not fixed Marmot protocol data.

## Diagnostics

Logs, errors, metrics, and traces should avoid account ids, group ids, message ids, relay URLs, pubkeys, payloads,
ciphertext, plaintext, and key material.

Use aggregate counts, method names, local enum names, and redacted or hashed values when a diagnostic needs correlation.

## Deferred implementation surfaces

A normative surface may land in this specification before every implementation supports it. That implementation status
does not weaken the owning protocol rule.

Implementation repositories track their own deferred work, such as per-group agent-stream `replay_ttl_secs` /
`max_plaintext_frame_len` enforcement and exposing the MLS own-leaf index needed for push `leaf_index`. This
specification does not assign implementation-work issue numbers.

## Darkmatter Mapping

This repository maps the model above to code using names such as:

- `CgkaEngine`;
- `PendingStateRef`;
- `drain_auto_publish`;
- `drain_auto_proposals`;
- `confirm_published`;
- `publish_failed`;
- retained snapshots;
- the convergence simulator.

Those names are darkmatter implementation details. They are not part of the Marmot wire spec.
