# Account state synchronization

Status: exploratory. Non-normative.

This document explores how one account's accepted content and private application state can be synchronized across
its devices. It is a design exploration, not an interoperability specification. Nothing here is adopted; if any of it
becomes protocol behavior, the owning surface documents change and this document either becomes the feature flow or
is split.

Device enrollment — how a device joins groups in the first place — is owned by [multi-device.md](./multi-device.md).
This document covers what happens after enrollment: replicating logical, accepted application data between devices of
one account.

## Core boundary

Content sync replicates logical, accepted application data. It does not transfer live cryptographic state, local MLS
group state, KeyPackage private material, or unpublished local input. The canonical identity, MLS-state, and key
lifecycle rules are defined in [identity.md](../foundation/identity.md), [key-packages.md](../foundation/key-packages.md),
and [mls-protocol.md](../foundation/mls-protocol.md).

A newly admitted device generally cannot independently revalidate old application messages after the relevant MLS
secrets are deleted. Transferred history is therefore an authorized account archive, not fresh MLS verification, and
must be presented as such.

## Data classes

The sync model distinguishes at least:

**Accepted group history** — stable message identifiers and accepted plaintext; edits, deletions, reactions, and
replies; media references and provenance; relevant application metadata; enough ordering information for deterministic
presentation.

**Private account or presentation state** — read positions; archive, mute, and pin state; drafts; notification
preferences; user-assigned device labels.

**Binary objects** — media and thumbnails; draft attachments; encrypted snapshot chunks.

**Live cryptographic state** — explicitly excluded (see above).

Users may eventually need policies such as full retained history, active groups only, selected groups, or from-now-on
only. The default scope is an open question.

## Layered design direction

The proposed layering keeps the logical data model independent of any carrier. This document owns only the exploration;
before interoperability, the first four layers require a versioned account-sync feature document with exact bytes and
merge rules, while each selected delivery binding belongs in `transports/` or a separately registered feature carrier:

1. a canonical, typed account-sync record format;
2. narrow deterministic merge rules per record type;
3. an append-only journal plus periodic encrypted snapshots;
4. versioned sync encryption keys and per-device signing identities authorized by the account's device control plane;
5. interchangeable carriers for direct, relay, object-store, or peer-to-peer delivery.

### Narrow merge semantics

Many fields need CRDT-like behavior without a general collaborative-document model. Candidate starting points:

| State              | Candidate merge rule                                            |
| ------------------ | --------------------------------------------------------------- |
| Accepted message   | Set union by stable message identifier                          |
| Edit               | Latest authenticated logical revision by deterministic ordering |
| Delete             | Tombstone wins over retained content                            |
| Reaction           | Add/remove operation scoped by author and reaction               |
| Read position      | Monotonic high-water mark where the timeline permits            |
| Archived / muted   | Last-writer-wins register                                       |
| Draft              | Last-writer-wins or multi-value register                        |
| Pin ordering       | Explicit ordering merge, or device-local in the first version   |

These rules need adversarial treatment of clocks, replay, duplicate records, malicious same-account devices, and late
arrival. "Last writer" cannot mean an untrusted wall-clock timestamp alone.

### Sync keys and device authority

Any adopted design SHOULD encrypt content under random, versioned account-sync keys rather than directly under the
long-term Nostr account key. Each device would also need a synchronization signing identity authorized by an explicitly
specified account-device control plane. No current Marmot document assigns that record format, key schedule, signing
proof, or control plane; implementations MUST NOT treat this exploration as an interoperable wire protocol.
Removing a device can rotate keys for future records and checkpoints but cannot revoke content already downloaded;
adding a device needs an explicit policy for which historical key versions it receives.

## Carrier options

**Direct pairing transfer** — encrypted snapshot plus journal tail over the carrier-independent pairing channel from
[multi-device.md](./multi-device.md). Best first milestone: private, fast, simple. Requires both devices online
together and provides no ongoing sync.

**Encrypted relay journal** — typed encrypted records published through the existing transport stack. Asynchronous,
but subject to retention limits, event-size limits, metadata leakage, weak deletion, and gap detection burden.

**Private account-device control group** — an MLS group containing the account's devices could carry sync-key
distribution, manifests, and small control records. A control plane, not a historical archive on its own.

**Encrypted object-store checkpoints** — compressed chunked encrypted snapshots with a signed manifest naming chunks
and journal position. Good for bootstrap and backup; composed best as "checkpoint in object storage, deltas
elsewhere."

**Replicated-log libraries** — a signed append-only operation log with causal ordering could implement the journal
layer instead of ad hoc encrypted events. Promising but unproven here; adoption is contingent on a prototype covering
direct pairing, offline writers, deletion, snapshot bootstrap, device removal, and long-history compaction.

A dedicated synchronization service and user-owned cloud storage remain possible optional carriers; neither is a good
interoperable baseline.

## Suggested incremental path

1. Optional direct history bootstrap during pairing (see [multi-device.md](./multi-device.md)), using a typed record
   envelope shaped so the same records embed verbatim into later journal carriers.
2. Encrypted deltas over a relay journal or account-device control group, with checkpoints, gap detection,
   compaction, retention, and key rotation.
3. Presentation-state sync (read positions, pins, drafts) behind the same record format.

## Things to avoid

- treating relay replay as a complete archive;
- encrypting the archive solely to the long-term Nostr account key;
- letting synchronized application records override canonical current MLS group state;
- trusting exporter attestation as cryptographic proof of history: a compromised exporting device can fabricate
  history that no receiving device can detect, so imported content carries a labeled trust level distinct from
  normally verified traffic;
- adopting a general-purpose CRDT document model as the entire archive before authorization rules are defined.

## Open questions

- Default history scope: all retained, active groups, selected groups, or from-now-on?
- Exact proof binding an MLS credential and a device sync key to the same account.
- Which private presentation fields synchronize versus stay device-local.
- Deterministic merge rules for edits, tombstones, drafts, pins, and read state under adversarial inputs.
- Archive attestation beyond the exporter's own signature, and what trust claims receivers display.
- Which historical sync-key versions a newly authorized or recovered device receives.
- Media retention, cache eviction, and representation of missing encrypted objects.
- Availability promise when no existing device is online.
- Snapshot compaction, garbage collection, and recovery after partial upload.
