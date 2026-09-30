# marmot.group.history-purge.v1

Status: draft.

`marmot.group.history-purge.v1` carries one bounded consensual request from an application event into temporary canonical
GroupContext state, records each member's single decision, and carries the terminal authorization in `AppEphemeral`. The
accepted terminal transition may authorize removal of application plaintext from before the request opened. The
prospective retention policy takes effect at acceptance. It does not authorize deleting protocol recovery material or
copies outside a conforming member's controlled stores.

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

The exclusive purge boundary is `purge_before_epoch = parent_epoch + 1`, computed with checked unsigned arithmetic.
A request with `parent_epoch = 2^64 - 1` is invalid. Opening MUST consume the exact bound candidate parent and therefore
produces epoch `purge_before_epoch`. The boundary never advances with voting, acceptance, expiry, replay, or delivery.
Application payloads from the opening epoch onward are outside this purge, even if acceptance is delayed.

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
request app event, but only active admins may propose and commit the opening `AppDataUpdate`. The proposer proof
authenticates request creation; the opening proposal sender and Commit sender must each satisfy active-admin authority
under the normal source-epoch and candidate-parent rules. Opening carries an empty decision list and exactly the paired
component/requirement addition. This admin-mediated opening replaces unrestricted member opening; it preserves any-member
request creation without granting a non-admin the ability to repeatedly gate group recovery.

Immediately before opening, a conforming admin MUST require `abs(local_now - created_at) <= 300` seconds and
`local_now < expires_at`. It MUST also honor the cooldown and recovery priority below. These are local producer
obligations, never receiver-clock-dependent Commit validation rules. Request timestamps follow the common proof bounds.

The admin that opens a valid request is authorized to commit only the exact paired addition of the `0x800d`
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

A conforming client MUST offer and sign a decision only after the bound request has opened canonically. A decision
update requires that exact request in the candidate parent; an uncommitted request event cannot collect canonical votes.

A No is not an advisory app event and is never stored as an open-state value. It is a terminal response carried in the
rejected finalization Commit below. Only the No signer may commit that rejected finalization. Consequently, after a valid No is
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
Commit validity. These self-asserted timestamps do not prove an adversarial signer's wall-clock time. A conforming
signer MUST durably remember the first decision it signed for a request and MUST refuse a second or conflicting
decision. Local expiry does not release that protection; it may be released only after canonical closure is beyond
the rollback horizon and no pending replay or recovery work needs the request. Canonical validation uses only proofs
carried by the candidate state or transition, never conflicting material observed solely off-branch. The response
identity is:

```text
response_id = SHA-256(
  "marmot-history-purge-response-v1" ||
  0x00 || request_id || encode(MarmotHistoryPurgeDecisionV1) || encode(proof)
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
- `expired`: kind `457`, signed by any active cohort-member committer, with timestamp `t >= expires_at`, or with
  `t < created_at` and `created_at - t > 300`; it closes an elapsed or unusably future-dated response window;
- `superseded`: kind `457`, signed by the committer of the canonical membership, identity, capability, admin-policy, or
  retention change that invalidates a request binding; the signer MUST equal the terminal Commit sender.

Supersession requires an actual change to a bound value: the cohort/account-identity bindings, capability digest,
prior retention value or admin policy from the bound source state. A no-op replacement with the same bound value does
not invalidate the request and cannot authorize `superseded`. The client retains the bound values needed to validate
this comparison while the request remains replayable.

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

In every proof template (kinds `454`, `455`, `456`, and `457`), `group_id` and `parent_epoch` are from the request core.
In particular, `parent_epoch_decimal` is the request's parent epoch, never the parent of a later decision or terminal
Commit. All proof kinds bind the same immutable request identity.

Every terminal Commit removes the GroupContext `0x800d` entry and its temporary required-component listing. An accepted
Commit additionally contains exactly one full-replacement update for `marmot.group.message-retention.v1` with
`target_retention_secs`. Other terminal Commits contain no retention update except the independently authorized retention
change that causes `superseded`; that update remains subject to the retention component's normal authorization. Except
for the exact canonical-state change that causes `superseded`, a terminal Commit contains no proposal beyond the history-purge removal, required-component
removal, the terminal `AppEphemeral`, and the accepted retention update when applicable. Any missing, duplicate, or
extra proposal makes the terminal transition invalid.

When a legitimate superseding change also edits `app_components`, the required-list removal and independently
authorized change MUST be combined in one full-replacement operation for that component. Both proposal sender and
committer must have authority for every delta; a non-admin's exception covers only removing `0x800d`. Duplicate
operations for one component remain invalid, and no other actor's admin authority can be borrowed.

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
a finalization. Receipt emission MUST be coordinated and durably single-use across that account's conforming leaves.
`applied` may be emitted only after all of that account's controlled conforming stores complete the required idempotent
cleanup. Unknown completeness or unavailable coordination MUST withhold `applied`; clients may instead emit one
coarse `failed` result. V1 defines no device-discovery or cross-device coordination protocol, so active-leaf presence
alone never proves account-wide completion. Repeated identical account receipts are idempotent. Conflicting outcomes
for one account prevent `group_complete` and yield a coarse partial result independent of arrival order. The receipt
identity is:

```text
receipt_id = SHA-256(
  "marmot-history-purge-receipt-v1" ||
  0x00 || finalization_id || sender_account_pubkey || outcome
)
```

In the receipt-id preimage, `outcome` is exactly the ASCII bytes `applied` or `failed`, without a length prefix.

Receipts expose no message id, content hash, filename, per-message count, device inventory, failure reason, or cleanup
timestamp. Although MLS authenticates each sender, the user-visible group projection MUST expose only the aggregate
outcome, not a member-by-member or device-by-device table.

## Expiry and restart

A client uses `expires_at` for its local open-request UI and MUST retain or reconstruct the request id, deadline, first
signed decision, canonical open state, accepted suppression boundary, cleanup progress, and emitted receipt across
restart. At or after its local `expires_at`, it stops offering Yes/No and treats timeout only as a provisional local
`expired` projection. Expiry is never consent. Canonical expiry requires the terminal Commit above, so Commit validation
never depends on receiver clock skew. The seven-day limit bounds the honest signer's response window, not an
adversarial admin's acceptance time. A valid accepted finalization whose proof timestamp is inside the response
interval remains valid when committed or delivered late unless another terminal transition already won canonically.
It still targets only source epochs below the immutable `purge_before_epoch`. The UI MUST explain that an existing Yes
can authorize later acceptance until canonical closure; it MUST NOT promise a cryptographically enforced wall-clock
acceptance deadline. A conforming admin uses its current local time and MUST NOT backdate a proof.

Any active cohort member can canonically close the request as `expired`, without an online admin, when its current
time satisfies either expiry condition above. A conforming signer MUST use current local time without backdating or
forward-dating. Self-asserted timestamps cannot prevent a malicious member from aborting voting early; the UI MUST
disclose that this cannot authorize a purge. At the exact deadline, accepted and expired candidates may both validate;
canonical convergence selects the terminal transition.

Every capable active cohort client MUST schedule expiry once either condition becomes locally true. While online with
usable group state and signing capability, it MUST initiate publication within 60 seconds, including any jitter. This
bounds an attempt, not delivery or canonical completion. The closure obligation is durable across restart, publication
failure and branch replacement and retries through the normal publication/convergence rules until closure is selected
or membership authority is lost. Observing an unselected competing candidate does not discharge it.

Opening admins MUST observe a group-wide 300-second local cooldown after any selected terminal transition and prioritize
known pending recovery over a new opening. They retain or reconstruct this cooldown across restart; when unavailable,
they wait a fresh interval. Duplicate terminal delivery MUST NOT extend it. Alternating proposers cannot bypass the
group-wide rule. These are producer obligations, not canonical time validation.

Recovery still requires a capable surviving member and eventual delivery and convergence. All-offline groups,
unavailable signers, malicious admins and adversarial scheduling have no guaranteed liveness. Once closure is selected,
external join or recovery must construct fresh Commit bytes against that closed parent; invalid old bytes do not become
valid retroactively.

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

The target is application plaintext whose MLS source epoch is less than `purge_before_epoch`, derived from the bound
request parent above. The accepted Commit's resulting epoch is `activation_epoch`: authorization, suppression and
prospective retention begin there, but the purge boundary does not move. Messages with source epochs from
`purge_before_epoch` through `activation_epoch - 1` keep their original retention semantics. This V1 choice replaces an
acceptance-relative history range, which would let delayed or backdated acceptance expand the consented target. It
excludes MLS Commits and proposals, retained recovery anchors, candidate state, pending publication obligations,
audit/security material required for protocol correctness, and messages already governed by another independent delete
action.

A client MUST durably install one reversible suppression boundary before exposing the accepted effect. Target payloads,
including late or replayed arrivals, are suppressed before timeline, search, notification, export, reply-preview, TTS,
or media-cache presentation. Suppression follows the selected branch and is withdrawn if convergence supersedes the
authorizing Commit while its parent remains inside the rollback horizon.

Best-effort destructive cleanup begins only after the authorization remains selected, convergence is settled, and the
accepted Commit's parent epoch is outside the rollback horizon. Specifically, require
`canonical_tip_epoch - authorization_parent_epoch > max_rewind_commits`; equality remains protected. Neither the
request parent nor the purge boundary substitutes for `authorization_parent_epoch = activation_epoch - 1`.
The client durably retains the authorizing Commit identity, purge boundary and cleanup progress.
Cleanup is idempotent by `(request_id, activation_epoch)`, checkpoints before exposing `local_applied`, resumes after
restart, and never deletes required protocol recovery material. Logical removal is not a
physical-overwrite guarantee. Former members, hostile or non-conforming clients, relays, exports, screenshots, backups,
and external copies are outside enforceable scope.

## Validation, removal, and migration

A decoder rejects noncanonical bytes, unknown enum values, invalid keys or proofs, malformed bounds, duplicate members
or decisions, a mismatched parent/request/capability/retention binding, and any update that is not one permitted
transition above. A membership, identity, capability, admin-policy, or retention change while open MUST atomically
supersede and remove the request; it cannot silently drop a voter or bind a newcomer.

An external join or resync Commit against a parent with an open request MUST be rejected. Its permitted proposal set
cannot carry this feature's required terminal transition under
[RFC 9420 section 12.2](https://www.rfc-editor.org/rfc/rfc9420.html#section-12.2). The request must first close canonically,
or an authorized member Commit must perform the relevant binding change and atomic supersession. V1 does not relax
the external-Commit proposal rules.

A disband transition MUST first close any open request in a prior canonical Commit. It cannot carry the required
terminal `AppEphemeral` under the lifecycle component's exact proposal-set rule. Required-list edits alone do not
change the three-flag capability digest. Unrelated list changes neither supersede, remove nor reset the request.

No valid persistent state may be removed without the matching terminal `AppEphemeral`. The component cannot be enabled
for a group containing an unsupported leaf. Legacy groups continue without it. A future incompatible request, state,
proof, finalization, receipt, or authorization rule requires a new component id and new proof kinds; V1 bytes MUST NOT
be reinterpreted.

## Non-normative reference checks

[Reference tests and encoding fixtures](../tests/README.md) exercise a limited state model and pin canonical hash
preimages. They do not establish signature validity, MLS convergence, actual store deletion, or full conformance.
