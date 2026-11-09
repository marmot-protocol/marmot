# Structured interactions v1

Status: draft proposal, pending decision in [MDK issue 858](https://github.com/marmot-protocol/mdk/issues/858).
The requirements below describe the proposal, not adopted implementation authorization.

Structured interactions let an agent ask one named account for a single approval or choice in an existing Marmot group.
The response resumes one pending operation through its local owner. A response is never an instruction to a model.

## Scope and owning surfaces

[Structured interaction records v1](../foundation/structured-interactions-v1.md) owns the exact record bytes,
parser bounds, text restrictions, fallback grammar, dispatch interception, author mutations, and fixtures.
Implementations MUST use that contract rather than infer semantics from displayed text.
This feature owns authorization and execution behavior.

[Application payloads](../foundation/application-messages.md) owns inner-event identity and MLS sender authentication.
[Group state](../protocol-core/group-state.md), [convergence](../protocol-core/convergence.md), and
[durability](../protocol-core/durability.md) continue to govern delivery and canonical group state.
The feature adds no GroupContext component, MLS capability, transport envelope, or private delivery channel.

An approval permits or denies one pending operation. Only the fixed allow-once and deny choices are supported.
A choice selects one offered opaque option, or supplies custom text when the request explicitly permits it.
Persistent or session-wide approvals, arbitrary cards, executable option payloads, and agent-specific control objects
are outside this version. Agent-specific local APIs and versioned control DTOs belong in implementation repositories.

## Owner and adapter boundary

Every executable request MUST have one durable authoritative local prompt owner before the request is published.
The owner MUST bind the request to all of the following facts:

- the authenticated local adapter connection and its runtime generation;
- the opaque local pending-operation identity;
- the agent account, group instance, and named responder account;
- the original authenticated input event from that responder;
- the immutable request event, deadline, options, and custom-text permission.

Creation MUST atomically reserve the adapter-connection, runtime-generation, and pending-operation tuple for one
open prompt. Another prompt MUST NOT reserve it while open or after claim, regardless of id, responder, or group.
The adapter MUST NOT reuse a pending-operation identity for a different operation within that generation.
Pre-claim cancellation, expiry, or supersession may release it; claim consumes it until generation end, including
after `resolved` or `indeterminate`. Replacement MUST serialize the unclaimed prompt's terminalization with the
new reservation. An uncertain claimed operation cannot be retried under a fresh prompt id.

Runtime names, local pending identities, and resolver handles MUST NOT appear on the wire.
Receiving a request, restoring a transcript, or importing account history MUST NOT create executable owner state.
Copies of the same identity or owner store running as independent owners are unsupported. This contract supplies no
distributed lock and makes no at-most-once claim across such copies.

Before rich emission, the adapter MUST register the interaction type and typed response path for its live connection
and generation. Agent names, displayed prompts, model output, or a previous connection's registration establish no
support. The owner MUST reject unsupported requests as locally unavailable. They MAY appear as inert readable text,
but MUST NOT become generic model approvals or executable text fallbacks.

Only the owning adapter MAY receive a validated typed decision. It MUST map an option to the already-bound pending
operation, not interpret a label, request body, or answer as executable code. A choice with custom text remains typed
input to that operation and grants no approval. Exact local version dispatch and coexistence of implementation API
versions remain implementation work tracked by issue 858, not a wire or DTO contract in this repository.

## Authorization and current membership

Creation and claim require an active canonical group in `Stable` lifecycle with `Settled` convergence status.
Local gates such as `Leaving`, `Disbanding`, local removal, or disbanding MUST prevent execution.
An eligible active account is represented by at least one currently valid active member leaf in that canonical group.
The agent and responder MUST be distinct eligible active accounts. Multiple leaves for one account count once.
A label, group name, two-leaf count, transport address, or inferred thread identity establishes no authority.

`effectiveDM` means that the complete current canonical membership contains exactly two distinct eligible active
accounts: the request author and the named responder. Approvals and every choice permitting custom text MUST require
`effectiveDM` at creation and immediately before claim. Any observed third account, loss of either account, or
unresolved canonical membership view MUST permanently invalidate an open DM-only prompt. Returning to `effectiveDM`
MUST NOT reopen that prompt. `Settled` describes a local fixed point, not global finality or delivery completeness.

Senders MUST also recheck that exact audience immediately before encrypting or newly publishing any DM-only request
or response, including text fallback and any queued send. The check MUST use the canonical membership of the state
that encrypts those bytes, not the snapshot that composed them. A missing, changed, or unresolved audience MUST discard
the unsent interaction rather than encrypt it for a later larger group. Re-encryption after a branch or epoch change
requires the same check. A sender that observed DM invalidation MUST NOT send a queued answer after the two-account
view returns. Discarding an unsent message MUST NOT discard owner evidence or reopen a prompt.

This gate prevents new disclosure by queued sends; it cannot revoke plaintext or old keys copied by an existing member,
or make a history-sharing client conceal an interaction that was already delivered.

A choice outside `effectiveDM` MAY be created only for a maintainer-reviewed use case with nonsensitive opaque choices.
It MUST NOT permit custom text or carry an approval. Review MUST account for every group member seeing every field.
The owner MUST NOT treat arbitrary model output as such a reviewed use case.

The originating input MUST be a delivered authenticated event authored by the named responder in the same group
instance. Its account identity comes from MLS authentication, not a name in its content. The input is untrusted data
and MUST NOT itself grant approval. The owner MUST retain its immutable identity and authentication evidence.
An approval MUST describe the pending action and its scope in the readable request. That description grants no rights
beyond the pending operation bound by the owner.

The [claim checks](#claim-and-resolver-durability) use current membership and gates even for responses authenticated
in an earlier source epoch. Historical membership authenticates authorship, not current permission.
A response from another leaf of the named responder account MAY qualify. Another account, an admin acting for the
responder, or a sibling transcript import MUST NOT qualify merely because it can display the request.

## Creation and deadlines

Before creating a request, the owner MUST reserve fixed bounded capacity for its durable state, claim evidence,
terminal outcome, and receipt publication. Resource refusal MUST NOT leave an executable request behind.
An owner MUST NOT evict an open or claimed record in a way that permits it to be recreated or claimed again.

Optional reorder and evidence caches for known prompts MUST have documented finite entry-count, byte, and elapsed-time
ceilings. Excess input MUST be discarded without invocation or generic dispatch. The execution path MUST discard unknown
request or prompt identities without per-identity owner state or reference fetches. Eviction or expiry MUST preserve required
owner evidence and no-replay facts and MUST NOT reopen prompts.

Client presentation MAY buffer structurally valid, MLS-authenticated resolution observations before their requests
arrive, in a separate volatile cache with documented finite entry-count, byte, and elapsed-time ceilings. Observations
MUST remain non-actionable until the original request establishes their receipt authority. They MUST NOT create durable
per-identity state, executable owner records, reference fetches, or generic dispatch. Excess or expired observations
MUST be discarded. This presentation exception does not buffer unknown executable requests or responses for later claim.

The owner MUST persist the complete `open` record and stable request event before publication can expose the request.
Publication failures MUST NOT generate another pending operation under the same prompt identity.
The owner MUST use the wire contract's lifetime bounds and default, with the same unextendable deadline.
Changing the pending operation, responder, options, or deadline requires superseding the old prompt and creating a fresh
prompt with fresh identities, subject to the same authorization and capacity checks.

For every response or terminalization candidate, the owner MUST first persist
`effective_now = max(current_backend_time, last_persisted_effective_now)`.
When `effective_now >= expires_at`, an open prompt MUST become `expired` before that candidate can have any effect.
Event timestamps, sender clocks, and claimed send times MUST NOT override this check.
A timer MAY expire an open prompt proactively, but a timer firing is not required to enforce the deadline.
Restart or clock rollback MUST NOT decrease the persisted effective time or extend the deadline.

## Durable prompt lifecycle

The table describes owner state, not a state machine reconstructed from network receipts.
Each transition MUST be serialized by the one owner. At most one transition out of `open` can win.
Timestamps and response arrival order at other clients MUST NOT choose the winner.

| From | Condition | To | Execution consequence |
| --- | --- | --- | --- |
| No owner | Authorized creation with reserved capacity | `open` | The bound operation waits. |
| `open` | Deadline reached | `expired` | The resolver is never invoked. |
| `open` | Cancellation or an invalidated prerequisite | `cancelled` | The resolver is never invoked. |
| `open` | The owner replaces the pending prompt | `superseded` | Only a separately created prompt may proceed. |
| `open` | One authorized candidate passes every claim check | `claimed` | Its evidence is durable before invocation. |
| `claimed` | The runtime acknowledges accepting the decision | `resolved` | The decision was accepted, not necessarily executed successfully. |
| `claimed` | The invocation outcome cannot be established | `indeterminate` | No resolver retry is permitted. |
| Any terminal state | Any later input, restart, or rediscovery | Unchanged | The prompt never reopens. |

`resolved`, `indeterminate`, `expired`, `cancelled`, and `superseded` are terminal states.
`claimed` disables further answers even before a terminal receipt is available.
Local rejection of a malformed, unauthorized, or losing candidate does not itself change an otherwise valid open
prompt. Those candidates MUST be consumed without generic dispatch or invocation.

## Claim and resolver durability

After bounded parsing, the owner MUST validate the original immutable events and the live owner binding.
Before `open` becomes `claimed`, every check below MUST pass in the same serialized decision:

1. The deadline has not expired under the persisted effective-time rule.
2. The request, originating input, and response are delivered authenticated events in the bound group instance.
3. The author and responder are currently eligible, the group is active and settled, and `effectiveDM` holds if required.
4. The adapter connection, runtime generation, and pending operation are still the exact live binding registered at creation.
5. The response author is the named responder, and its request reference and prompt identity match the immutable request.
6. Its option is one offered by that request, or its custom text is permitted by that request and the wire contract.
7. No known cancellation, supersession, mutation, withdrawal, or source invalidation makes the candidate ineligible.
8. This prompt still holds the pending-operation reservation, and no prompt has previously claimed that operation.

The atomic claim MUST make the selected response's stable identity, exact decision and authentication evidence,
resolver-operation identity, claimed state, and consumed pending-operation reservation recoverable before the resolver
can be invoked. The reservation check and consumption MUST be atomic with the claim, not a separate preflight check.
An invocation MUST be fenced so interruption cannot make a possibly attempted invocation appear unattempted.
The resolver MUST be invoked at most once for that prompt, regardless of duplicate events, ids, answers, or devices.

`resolved` requires recoverable acknowledgement that the bound runtime accepted the decision, not proof of tool or
external-action success; presentation MUST preserve that distinction. Missing acknowledgement after possible invocation,
or connection loss after claim without such acknowledgement, MUST produce `indeterminate`. The owner MUST document
and enforce a finite acknowledgement-wait ceiling across restart; reaching it without acknowledgement has the same
result. The resolver MUST NOT be retried, even against the same runtime. Connection loss or wait expiry MUST NOT permit
replay, reassignment to another generation, or automatic operation recreation. Connection loss before claim MUST cancel
the open prompt. After a crash, a claim provably not yet invoked MAY conservatively become `indeterminate`.

Before terminal publication, the owner MUST make the outcome and stable receipt bytes recoverable. Retries of those
same bytes MAY occur under normal outbound gates, with documented finite attempt-count, aggregate-byte, and elapsed-time
ceilings and restart-persistent accounting. Exhaustion MUST stop publication and mark the receipt locally undelivered,
without discarding the outcome or no-replay facts. Publication failure MUST NOT change the outcome or retry the resolver.
Receipts only observe outcomes; no network receipt authorizes invocation.

## Cancellation and supersession

The [author-withdrawal rules](../foundation/structured-interactions-v1.md#author-withdrawal) govern request,
response, and receipt mutations, including pre-claim candidate invalidation, post-claim irreversibility,
and display-only changes. The owner MUST apply [deadline expiry](#creation-and-deadlines) before cancellation
or supersession. A replacement MUST be a fresh prompt, not an in-place executable edit.

A valid same-author `cancelled` or `superseded` resolution MAY request the matching terminal transition while the local
prompt is open. Other network resolution states are observations only. A resolution from another account MUST NOT
change owner state. A terminalization request that loses to a claim cannot undo that claim.

The owner MUST cancel an open prompt if its request, origin, or other required authorization evidence is withdrawn or
becomes unavailable. Claimed work remains subject to [resolver durability](#claim-and-resolver-durability),
even if its display is withdrawn.

## Client controls and receipts

A supporting client MUST validate the wire record and authenticated original request before enabling rich controls.
Controls MUST be limited to the named responder and disabled if the client cannot establish the applicable current
membership, deadline, request availability, or interaction support. Display names and request body text are not proof.
The client MUST present the request author's identity, pending action or question, offered choices, and expiry.
It MUST distinguish an approval from an ordinary choice and MUST NOT preselect an approval on behalf of the user.

Sending an answer MUST disable that local submission's controls while its outcome is pending.
A local send or an echoed response MUST NOT be displayed as accepted solely because it was published.
Only a resolution satisfying the [wire receipt-authority rules](../foundation/structured-interactions-v1.md#resolution)
can supply network terminal status or identify the accepted response.
A client MAY indicate that another device answered, but MUST NOT infer acceptance from a response alone.
All terminal receipts MUST leave the request's controls disabled. `indeterminate` MUST be shown as an unknown outcome,
not a denial or invitation to retry the same operation.

Receipts are semantically identical when their terminal state and accepted-response evidence are identical.
Multiple identical receipts are not a conflict. Differing terminal states or accepted-response evidence in otherwise
valid same-author receipts constitute a protocol violation. Clients MUST select the authenticated valid receipt with
the lexicographically lowest event id for display, show a conflict diagnostic, and keep controls disabled.
That display tie-break MUST NOT select a resolver invocation, undo owner state, or change canonical group state.
A receipt's disappearance from display MUST NOT clear a locally known claim or terminal outcome.

## Convergence, retention, and restart

Only delivered app payloads can enter the authorization path. Retained ciphertext, a candidate branch, a transport
acknowledgement, or an imported historical row MUST NOT create permission to execute.
[Selected-branch application](../protocol-core/convergence.md#applying-the-selected-branch) can withdraw previously
delivered payloads and state notifications. The [cancellation](#cancellation-and-supersession) and permanent
[DM invalidation](#authorization-and-current-membership) rules apply even if a later pass selects the old view.

Clients MUST withdraw affected display when required, without reversing a claim or external effect or clearing
nonexecution facts. Redelivery MUST NOT recreate ownership or bypass the [lifecycle](#durable-prompt-lifecycle).
`Settled` does not prevent a later branch change from withdrawing the prompt or answer.

[Protocol durability](../protocol-core/durability.md#application-effects-after-restart) still governs effective delivery
and withdrawal. Feature owners MUST additionally recover their claim, terminal, deadline, and invocation facts before
accepting further candidates. Missing facts MUST block execution, not be guessed from the visible transcript.
Normal application-effect replay MUST NOT be treated as permission to replay an external resolver.

[Message retention](../app-components/message-retention-v1.md) and
[retained history](../protocol-core/retained-history.md) may shorten prompt availability but MUST NOT extend execution.
An owner MUST retain enough nonexecution facts through at least the original deadline to reject stale or duplicate
answers, and longer while a claim, possible invocation, or receipt obligation remains unresolved.
The consumed pending-operation reservation MUST additionally survive until the bound runtime generation ends;
pruning an old prompt MUST NOT permit that operation to be claimed through a new prompt.
Pruning request or answer content MUST NOT reconstruct an open prompt from history or clear a no-replay restriction.
If required content must be removed before claim, the owner MUST cancel rather than prolong availability.

## Privacy and downgrade

Every request, option, answer, fallback, and receipt is group plaintext available to all group members entitled to
receive its MLS message. Naming one responder does not make a responder-agent private path.
Senders MUST omit secrets and unnecessary action details. Even an opaque choice can reveal context through its labels,
request body, timing, or answer. Encryption does not conceal those fields from group members or erase saved copies.

Logs and telemetry produced by conforming feature components MUST omit prompt, action, scope, and answer values,
and account, group, and message identifiers. This includes malformed and rejected candidates, resolver errors, and
fallback handling. This rule does not claim control over external runtimes, operating systems, relays, or user exports.

Clients without rich support can read the complete fallback body. A responder MAY send a
[correlated text fallback](../foundation/structured-interactions-v1.md#correlated-text-fallback), subject to the same
authorization and claim checks. The wire contract's [dispatch rules](../foundation/structured-interactions-v1.md#profile-and-dispatch)
keep malformed, unsupported, stale, duplicate, losing, unknown, and unowned attempts out of model and command input.
Bounded parsing MUST precede owner-state lookup. This version defines no migration of prior textual approvals
into authority.
