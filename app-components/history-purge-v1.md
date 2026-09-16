# marmot.group.history-purge.v1

Status: adopted.

`marmot.group.history-purge.v1` carries one bounded consensual request from an application event into temporary canonical
GroupContext state, records each member's single decision, and carries the terminal authorization in `AppEphemeral`. The
accepted terminal transition may authorize removal of application plaintext from before a new retention policy takes
effect. It does not authorize deleting protocol recovery material or copies outside a conforming member's controlled
stores.

## Registry and locations

- Component id: `0x800d`
- Name: `marmot.group.history-purge.v1`
- Purge control app-event kind: `453`
- Member decision proof kind: `454`
- Request proof kind: `455`
- Cancellation proof kind: `456`
- Terminal proof kind: `457`
- Valid locations: a temporary GroupContext entry while one request is open, and one terminal `AppEphemeral` value in
  the Commit that removes that entry
- Default requirement: optional

A group supports this feature only when every nonblank leaf advertises `app_ephemeral`, `app_data_update`, and component
`0x800d`. An open request requires `0x800d` in the GroupContext required-component list. A terminal Commit atomically
removes both the entry and that temporary requirement.

## Request bytes

```text
struct {
  opaque account_pubkey[32];
} MarmotHistoryPurgeMemberV1;

struct {
  uint32 leaf_index;
  opaque account_pubkey[32];
  uint8 app_ephemeral_supported;
  uint8 app_data_update_supported;
  uint8 history_purge_supported;
} MarmotHistoryPurgeCapabilityLeafV1;

struct {
  MarmotHistoryPurgeCapabilityLeafV1 leaves<39..39936>;
} MarmotHistoryPurgeCapabilityStateV1;

struct {
  opaque group_id<1..255>;
  uint64 parent_epoch;
  opaque parent_group_context_hash[32];
  opaque proposer_pubkey[32];
  uint64 created_at;
  uint64 expires_at;
  uint8 prior_retention_present;
  uint64 prior_retention_secs;
  uint64 target_retention_secs;
  MarmotHistoryPurgeMemberV1 members<32..32768>;
  opaque capability_state_hash[32];
} MarmotHistoryPurgeRequestCoreV1;

struct {
  MarmotHistoryPurgeRequestCoreV1 core;
  MarmotAuthorizationProof proposer_proof;
} MarmotHistoryPurgeRequestV1;
```

These structures use the Marmot binary profile in
[../foundation/canonical-encoding.md](../foundation/canonical-encoding.md). `members` contains between one and 1024
entries, sorted by `account_pubkey` bytes without duplicates. It MUST equal the sorted unique set of Marmot account
identities in all nonblank leaves of the candidate parent state. `proposer_pubkey` MUST be in that set.

`parent_group_context_hash` MUST equal `SHA-256(TLS-serialize(candidate_parent_group_context))`. The input is the MLS
TLS serialization of the complete candidate parent GroupContext used directly, without Marmot-specific re-encoding.

`prior_retention_present` is `0` or `1`. When it is `0`, `prior_retention_secs` MUST be zero and the bound parent has no
`marmot.group.message-retention.v1` entry. When it is `1`, `prior_retention_secs` MUST equal the exact effective value in
that parent. `target_retention_secs` follows the value bounds in
[message-retention-v1.md](./message-retention-v1.md).

For every nonblank parent leaf, up to 1024 leaves, a validator constructs one
`MarmotHistoryPurgeCapabilityLeafV1` in increasing `leaf_index` order. All three support bytes are `0` or `1` and are
derived from that leaf's authenticated MLS capabilities and Marmot component support. The request is eligible only when
all three bytes are `1` for every entry. The bound digest is:

```text
capability_state_hash = SHA-256(
  "marmot-history-purge-capabilities-v1" ||
  0x00 ||
  encode(MarmotHistoryPurgeCapabilityStateV1)
)
```

The request interval is absolute Unix time in whole seconds. `created_at` MUST equal
`proposer_proof.created_at`; `expires_at` MUST be greater than `created_at` and no more than `604800` seconds later.
V1 has no caller-selected prompt text and permits at most one open request per group.

The request identity is:

```text
request_id = SHA-256(
  "marmot-history-purge-request-v1" ||
  0x00 ||
  encode(MarmotHistoryPurgeRequestCoreV1)
)
```

## Request proof and non-admin route

The proposer proof uses the common envelope in
[../foundation/authorization-proofs.md](../foundation/authorization-proofs.md). A verifier reconstructs this local-only
Nostr event:

```text
pubkey     = lowercase-hex(proposer_proof.signer_pubkey)
created_at = proposer_proof.created_at
kind       = 455
tags       = [
  ["d", "marmot-history-purge-request-v1"],
  ["component", "0x800d"],
  ["group_id", group_id_hex],
  ["parent_epoch", parent_epoch_decimal],
  ["request", request_id_hex]
]
content    = lowercase-hex(SHA-256(encode(MarmotHistoryPurgeRequestCoreV1)))
```

The proof signer MUST equal `proposer_pubkey` and be an active member in the bound parent. Kind `455` is a signing
template and MUST NOT be published to relays.

Any active member, including a non-admin, MAY create and send the request app event below. Any active member MAY relay a
valid request into an `AppDataUpdate` that adds the temporary GroupContext entry; the proposer proof, not relay identity,
authenticates creation. This explicit feature-owned app route does not loosen the active-admin requirement for the
retention update or accepted finalization.

The member that relays a valid request is authorized to commit only the exact paired addition of the `0x800d`
GroupContext entry and `0x800d` required-component listing. For every terminal transition, the actor authorized below is
also authorized to commit only the exact paired removal of that entry and listing. These feature-owned exceptions to
the default GroupContext authorization do not permit changing any other required component or unrelated GroupContext
state.

## Open state and decision updates

```text
uint8 MarmotHistoryPurgeDecisionV1; // 1 = yes, 2 = no

struct {
  MarmotHistoryPurgeDecisionV1 decision;
  MarmotAuthorizationProof proof;
} MarmotHistoryPurgeDecisionRecordV1;

struct {
  MarmotHistoryPurgeRequestV1 request;
  MarmotHistoryPurgeDecisionRecordV1 yes_decisions<0..107520>;
} MarmotHistoryPurgeOpenStateV1;
```

The GroupContext component data is exactly one encoded `MarmotHistoryPurgeOpenStateV1`. `yes_decisions` contains at
most one record per account, sorted by `proof.signer_pubkey`, and every record MUST have decision `1`. A state update is
a full replacement. From an existing state it may add exactly one previously absent Yes record and may change no other
byte. The proposal sender MUST equal that record's signer, and both sender and committer MUST be active members in the
bound cohort. A member's own Yes is the only decision that may remain in open state.

A No is not an advisory app event and is never stored as an open-state value. It is a terminal response carried in the
rejected finalization Commit below. The No signer MAY commit that response directly. Consequently, after a valid No is
on the selected canonical branch, the component entry is gone and no later Yes can replace it. Competing same-parent
terminal Commits remain ordinary candidate branches; canonical convergence chooses one transition, and off-branch
proof delivery cannot mutate the selected state.

A decision proof reconstructs the kind `454` event:

```text
pubkey     = lowercase-hex(proof.signer_pubkey)
created_at = proof.created_at
kind       = 454
tags       = [
  ["d", "marmot-history-purge-decision-v1"],
  ["component", "0x800d"],
  ["group_id", group_id_hex],
  ["parent_epoch", parent_epoch_decimal],
  ["request", request_id_hex],
  ["decision", decision]
]
content    = ""
```

`decision` in the event is exactly `yes` or `no`. The signer MUST occur in `members`. The proof timestamp MUST be from
`created_at` through `expires_at`, inclusive. These byte comparisons, rather than a verifier's wall clock, determine
Commit validity. A conforming signer MUST durably remember the first decision it signed for a request through expiry
and MUST refuse a second or conflicting decision. The response identity is:

```text
response_id = SHA-256(
  "marmot-history-purge-response-v1" ||
  0x00 || request_id || decision || encode(proof)
)
```

## Cancellation

The proposer may cancel only while the request is open. The cancellation proof uses kind `456` with the exact tags
below and empty content:

```text
[
  ["d", "marmot-history-purge-cancellation-v1"],
  ["component", "0x800d"],
  ["group_id", group_id_hex],
  ["parent_epoch", parent_epoch_decimal],
  ["request", request_id_hex]
]
```

Its signer MUST equal `proposer_pubkey`, and its timestamp MUST be from `created_at` through `expires_at`, inclusive.
The cancellation identity is:

```text
cancellation_id = SHA-256(
  "marmot-history-purge-cancellation-v1" ||
  0x00 || request_id || encode(cancellation_proof)
)
```

A cancellation app event may distribute this proof, but cancellation becomes authoritative only in the selected
terminal Commit. A cancelled, rejected, expired, or superseded request cannot reopen and requires a new request id.

## Terminal finalization bytes

```text
uint8 MarmotHistoryPurgeTerminalV1;
// 1 = accepted, 2 = rejected, 3 = cancelled, 4 = expired, 5 = superseded

struct {
  opaque request_id[32];
  MarmotHistoryPurgeTerminalV1 terminal;
} MarmotHistoryPurgeFinalizationCoreV1;

struct {
  MarmotHistoryPurgeFinalizationCoreV1 core;
  MarmotAuthorizationProof authorization;
} MarmotHistoryPurgeFinalizationV1;
```

The finalization is the only component `0x800d` value in one inline `AppEphemeral` proposal in the terminal Commit. Its
identity is:

```text
finalization_id = SHA-256(
  "marmot-history-purge-finalization-v1" ||
  0x00 || encode(MarmotHistoryPurgeFinalizationV1)
)
```

The authorization envelope is interpreted by terminal value:

- `accepted`: kind `457`, signed by the active-admin committer, with a timestamp from `created_at` through `expires_at`,
  inclusive; the parent open state contains exactly one valid Yes for every `members` account;
- `rejected`: the kind `454` No decision proof; its signer is an active cohort member, MUST equal the Commit sender, and
  MUST NOT already occur in the parent open state's `yes_decisions`;
- `cancelled`: the kind `456` cancellation proof; its signer is the proposer and MUST equal the Commit sender;
- `expired`: kind `457`, signed by the active-admin committer, with a timestamp greater than `expires_at`;
- `superseded`: kind `457`, signed by the committer of the canonical membership, identity, capability, admin-policy, or
  retention change that invalidates a request binding; the signer MUST equal the terminal Commit sender.

For kind `457`, the local signing event has exact tags:

```text
[
  ["d", "marmot-history-purge-terminal-v1"],
  ["component", "0x800d"],
  ["group_id", group_id_hex],
  ["parent_epoch", parent_epoch_decimal],
  ["request", request_id_hex],
  ["terminal", terminal]
]
```

Its content is lowercase hex of `SHA-256(encode(MarmotHistoryPurgeFinalizationCoreV1))`. For kind `457`, `terminal` is
exactly `accepted`, `expired`, or `superseded`, corresponding to terminal values 1, 4, and 5. Rejected and cancelled
finalizations use kinds `454` and `456`, respectively; they do not use kind `457`. Kind `457` is local-only and MUST
NOT be relayed.

Every terminal Commit removes the GroupContext `0x800d` entry and its temporary required-component listing. An accepted
Commit additionally contains exactly one full-replacement update for `marmot.group.message-retention.v1` with
`target_retention_secs`. Other terminal Commits contain no retention update. Except for the exact canonical-state change
that causes `superseded`, a terminal Commit contains no proposal beyond the history-purge removal, required-component
removal, the terminal `AppEphemeral`, and the accepted retention update when applicable. Any missing, duplicate, or
extra proposal makes the terminal transition invalid.

The accepted Commit is the sole purge linearization point. Neither a request, a Yes, a No proof that has not reached a
selected Commit, nor local expiry starts suppression or deletion. The first terminal transition on the selected
canonical branch wins; later replayed finalizations are inert because no matching open component remains.

## Request, cancellation, and receipt app events

All control messages are MLS-protected Marmot app payloads of kind `453`; they are not relay-level Nostr events.

A request event has exact tags:

```text
[
  ["v", "marmot-history-purge-v1"],
  ["type", "request"],
  ["request", request_id_hex]
]
```

Its content is standard padded base64 of the exact `MarmotHistoryPurgeRequestV1` bytes. The MLS-authenticated sender MUST
equal `proposer_pubkey`.

A cancellation event has the same `v` and `request` tags, `type` equal to `cancellation`, and content equal to padded
base64 of the exact cancellation proof. The authenticated sender MUST be the proposer.

A receipt event has exact tags:

```text
[
  ["v", "marmot-history-purge-v1"],
  ["type", "receipt"],
  ["finalization", finalization_id_hex],
  ["outcome", outcome]
]
```

Its content is empty. `outcome` is exactly `applied` or `failed`. A receipt is valid only when `finalization_id` identifies
the accepted finalization on the selected canonical branch. A receipt that identifies a rejected, cancelled, expired,
superseded, or non-canonical finalization is invalid and MUST NOT contribute to a completion projection. The
authenticated sender MUST be one member account in the accepted request cohort. A sender emits at most one receipt for
a finalization. `applied` may be emitted only after all of that account's controlled conforming stores complete the
required idempotent cleanup; `failed` is a terminal coarse result when they cannot. The receipt identity is:

```text
receipt_id = SHA-256(
  "marmot-history-purge-receipt-v1" ||
  0x00 || finalization_id || sender_account_pubkey || outcome
)
```

Receipts expose no message id, content hash, filename, per-message count, device inventory, failure reason, or cleanup
timestamp. Although MLS authenticates each sender, the user-visible group projection MUST expose only the aggregate
outcome, not a member-by-member or device-by-device table.

## Expiry and restart

A client uses `expires_at` for its local open-request UI and MUST retain or reconstruct the request id, deadline, first
signed decision, canonical open state, accepted suppression boundary, cleanup progress, and emitted receipt across
restart. At or after its local `expires_at`, it stops offering Yes/No and treats timeout only as a provisional local
`expired` projection. Expiry is never consent. Canonical expiry requires the terminal Commit above, so Commit validation
never depends on receiver clock skew. A valid accepted finalization signed inside the response interval remains valid
when delivered late unless another terminal transition already won canonically.

## Application and completion projections

An accepted finalization produces these stable projections:

- `accepted`: the accepted finalization is canonical; cleanup has not yet finished locally;
- `applying`: the target range is hidden locally and idempotent cleanup is in progress;
- `local_applied`: local cleanup is durable and the account's `applied` receipt has been emitted;
- `group_complete`: one valid `applied` receipt has been observed for every account in the request cohort;
- `partially_completed`: at least one valid receipt has been observed, but the set is not all-`applied`, or any valid
  `failed` receipt has been observed.

`accepted` is wire-authoritative. The other four are local projections from durable cleanup state and the valid receipt
set; different clients may learn receipts at different times. Missing, offline, unsupported, or failed application MUST
NOT be presented as `group_complete`.

## Target boundary and deletion gate

The target is application plaintext whose MLS source epoch is less than the accepted Commit's resulting epoch. It
excludes MLS Commits and proposals, retained recovery anchors, candidate state, pending publication obligations,
audit/security material required for protocol correctness, and messages already governed by another independent delete
action.

A client MUST durably install one reversible suppression boundary before exposing the accepted effect. Target payloads,
including late or replayed arrivals, are suppressed before timeline, search, notification, export, reply-preview, TTS,
or media-cache presentation. Suppression follows the selected branch and is withdrawn if convergence supersedes the
authorizing Commit while its parent remains inside the rollback horizon.

Best-effort destructive cleanup begins only after the authorization remains selected and its parent is outside the
rollback horizon. Cleanup is idempotent by `(request_id, activation_epoch)`, checkpoints before exposing
`local_applied`, resumes after restart, and never deletes required protocol recovery material. Logical removal is not a
physical-overwrite guarantee. Former members, hostile or non-conforming clients, relays, exports, screenshots, backups,
and external copies are outside enforceable scope.

## Validation, removal, and migration

A decoder rejects noncanonical bytes, unknown enum values, invalid keys or proofs, malformed bounds, duplicate members
or decisions, a mismatched parent/request/capability/retention binding, and any update that is not one permitted
transition above. A membership, identity, capability, admin-policy, or retention change while open MUST atomically
supersede and remove the request; it cannot silently drop a voter or bind a newcomer.

No valid persistent state may be removed without the matching terminal `AppEphemeral`. The component cannot be enabled
for a group containing an unsupported leaf. Legacy groups continue without it. A future incompatible request, state,
proof, finalization, receipt, or authorization rule requires a new component id and new proof kinds; V1 bytes MUST NOT
be reinterpreted.
