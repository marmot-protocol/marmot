# Private group invite links v1

Status: proposed; not adopted. The requirements describe this draft feature, not baseline Marmot conformance.

## Surfaces and negotiation

- [Invite-links component](../app-components/group-invite-links-v1.md): policy, immutable generations and updates.
- [Invite records](../foundation/invite-link-records.md): device consent, refresh, withdrawal and private decisions.
- [Nostr invite extension](../transports/nostr-invite-links.md): codes, preview, envelopes, delivery and bounded decoding.
- Adopted [joining](../protocol-core/joining.md), [publish lifecycle](../protocol-core/publish-lifecycle.md),
  [convergence](../protocol-core/convergence.md) and [durability](../protocol-core/durability.md).

This feature is optional and currently Nostr-only. The component's support/required negotiation gates activation and
invitation. There is no unauthenticated ExternalCommit or alternate membership-add authority.
Clients without support MAY continue in groups that have not enabled the feature, but cannot join an enabled group.
The [walkthrough](../ideas/group-invite-links.md) is non-normative context; this draft does not delegate rules to it.

## Creating and sharing

An active admin prepares a fresh invitation generation, independent inbox key, bearer and preview key. It encodes
the immutable preview, computes the component commitments, and activates the entry with an authorized policy Commit.
It MUST wait for publish-before-apply and component activation before advertising the invitation as usable.
Descriptor publication and per-admin secret distribution are separate delivery obligations. Neither creates policy.
The private record and descriptor MUST match the active entry before sharing a code.

The creator encrypts a grant for each active admin, including itself, and carries those copies in normal group traffic.
A promoted admin or another device of a current admin account already in the group receives a fresh grant from a
current admin. If no current
admin can recover the material, issue a new generation; do not derive the inbox from the group or an account.
Each grant includes the complete code's discovery coordinates as well as its secrets. A recipient MUST retain them
and be able to fetch the descriptor and requests independently, without guessing the group's routing relays.
The component is public to group members; only administrators receive its secret material and private requests.

The share sheet offers the complete code, a QR when the complete payload fits, and optionally a short URL. Opening a preview MUST NOT send a join
request. The preview is marked unconfirmed and the app explains who can see a request. A short URL host can read the
preview and bearer. A direct code or its QR avoids that host.
Previews contain a bounded inline image in v1; implementations MUST NOT fetch URLs embedded in preview text.

## Consent and request admission

After explicit Join, the originating device creates revision zero using the exact KeyPackage it offers and its leaf
signing key. It records the preview bytes the user saw. Request consent is distinct from account identity proof.
The device chooses `valid_until` no more than thirty days after its current time. This deadline cannot be extended
by refresh; another deadline requires a new request id and user consent.

Before retaining an actionable request, an admin MUST validate its version, canonical encoding, bearer commitment,
account-to-leaf proof, device signature, offer evidence, context and prerequisites. The invitation entry must be
present in current selected group state. Admission rejects an expired request deadline or one more than thirty days
in the receiver's future. These clock gates constrain local processing, not Commit validation or branch selection.
The descriptor/code inbox is not authority to erase or decide another request.

Two devices of the same account use distinct contexts and offered leaves. Deduplication is by complete context and
revision, not by account alone. The same account may have multiple leaves under adopted Marmot identity rules.
The receiver MUST NOT make a second Add for an already realized context, including after removing and later re-adding
that account through an unrelated operation. A new intended join uses fresh consent and a new context.

## Admin review and realization

An admin authenticates control records against the enclosing MLS source-epoch sender and active-admin policy.
Before initiating a new action, it also checks selected current state, current admin eligibility and link generation.
A historical grant does not let a former admin act. Commit authorization always uses the candidate parent; a proposed
admin-policy change cannot grant its committer permission retroactively.

Manual approval requires an explicit admin choice. Automatic processing additionally requires automatic mode, an
unexpired link, an unexpired request, a fully validated current offer and no observed withdrawal, decline, or conflicting
refresh. Approval produces a normal Add Commit. The admin tracks the exact prepared obligation before any publication.
Unknown publication outcome remains unresolved; restart retries the byte-identical obligation as durability specifies.
The inviter does not generate another Add merely because a status or Welcome delivery failed.

Competing admins do not acquire locks or consume packages at a coordinator. Ordinary MLS validation and Marmot
convergence decide group state. A prepared losing Commit does not authorize a Welcome; the client reconciles whether
its exact offered leaf was added on the selected branch before preparing further work. Automatic retry revalidates
current prerequisites and consent. A decision record, transport acknowledgment or relay timestamp never selects a
branch. Concurrent decline or withdrawal does not remove a member added by the selected branch.

After successful Add publication and canonical realization, the admin retains the exact Welcome and publishes it
under the adopted transport binding. It sends a status binding that Welcome, Commit and request revision, and an
encrypted invited record to the admin channel. The logical state is Invited, not Joined. A subsequent convergence
invalidation MUST update the request projection; an earlier receipt does not pin a losing branch.

The requester handles a Welcome through the adopted first-join flow, including tentative processing, inviter
identity, resulting-state admin authorization and the retained-group check. If the consumed package was offered by
a retained request, the receiver MUST check the corresponding invitation entry against the preserved preview
commitment and policy fields during tentative validation, before durable group storage, package rotation or private
initialization-key deletion. No matching entry or a preview mismatch leaves those mutations unapplied and requires
a new explicit user choice, including when accepting the Welcome as an ordinary invitation instead. The requester
MUST NOT silently swap its preview for a newer descriptor. Missing status does not bypass this consent check.
When multiple retained contexts offered the same package, any preview used for this check MUST belong to a context
with that exact offer and a matching invitation entry; an unrelated request cannot supply consent.

Association additionally requires the exact offered package, status Welcome hash and status author to match.
Missing status leaves an otherwise validated invitation unassociated, not invalid, and MUST NOT delay a matching
Welcome. Association may complete after the join when the authenticated status arrives.
Only successful Welcome validation and request association produce Joined. Inviter receipts cannot assert that the
remote device joined. The authenticated inviter remains the first-contact trust root; preview matching is not an
independent proof of intended-group authenticity.

## Processing private control records

Only delivered app payloads from the selected history may affect the request projection. The receiver MUST verify
that the record's group id and source epoch match the enclosing MLS message, and that its author is an active admin
at that source epoch. Every batch recipient MUST be an active admin in that authenticated source state. The receiver
MUST NOT accept a nested seal detached from that enclosing message as group authority.

- A grant must match the complete source-state entry and the current active generation. Verify all secret commitments
  before using it. A grant for a retired generation provides no current admission authority.
- A forwarded request must validate its original requester signature, revision ancestry and signed package evidence.
  The forwarding admin cannot change those bytes or substitute its own account for the requesting account.
- Withdrawal requires the original device-consent signature. A missing revision-zero binding waits for recovery.
- A decline must name a validated request hash under that context. It suppresses automatic processing across revisions;
  it does not change group state. Unknown referenced requests wait for their authenticated evidence.
- An invited claim must name a validated request revision. Before projecting realization, match its Commit hash to
  retained selected history and confirm that Commit added the exact offered package. Missing Commit evidence remains
  a recoverable prerequisite. The claim alone cannot justify a duplicate Add or asserted membership.

For new decisions or grants, recheck current author eligibility and generation. Replay preserves attributed historical
facts but does not authorize a former admin to initiate new work. A receiver MUST discard malformed or unauthorized
control semantics without rolling back otherwise-valid MLS processing. Unsupported semantics have no request-state
effect. Invalid bytes map to the adopted rejection vocabulary; missing evidence remains recoverable.

## Refresh and failed delivery

A stale, expired, unavailable or consumed offered package produces a recoverable offer problem. The requester may
send a chained refresh signed by the original consent key. The new package's account proof and publication are checked
anew. Relays may deliver refreshes out of order; missing ancestry waits for recovery rather than becoming a rejection.
The fresh leaf key may change without changing the originating consent key. If that consent key is lost, create a
new request with explicit consent. Same-account package discovery does not authorize an admin to substitute a device.

The eight-revision retention limit counts revision zero plus refreshes; revision seven is the last usable revision.
Further refresh requires a new request and withdrawal of the old context if its consent key is available.
An authenticated withdrawal suppresses automatic work across the entire old context, including an out-of-order refresh.
The highest fully validated unambiguous revision governs new preparation. Conflicting refreshes stop new manual
and automatic admission until renewed consent in a fresh context; they do not discard prepared publication facts.

A refresh received after an Add is realized does not automatically produce another Add. If the exact Welcome cannot
be recovered or is unusable because the original private key was deleted, show a recoverable invitation problem.
The admin reconciles selected membership and the requester explicitly starts a new join attempt before any replacement
membership is authorized. Existing membership removal/rejoin and retained-group safeguards still apply; this feature
does not define repair-by-Welcome. KeyPackage private material is never retained beyond its adopted deletion bound.

## Expiry, revocation and withdrawal

Link expiry stops automatic admission and new normal requests; requests already retained remain eligible for an
explicit manual choice until their own deadline. Requests first discovered after link expiry are marked timing
unverified and manual-only. Request timestamps and randomized NIP-59 timestamps do not establish pre-expiry consent.
A local clock check cannot make a Commit with otherwise valid membership authorization invalid on another client.

Removing an invitation entry revokes all unfulfilled requests for that generation, including previously seen requests.
Security-driven inbox retirement follows the same rule. It never removes a member already added on the selected
branch, destroys another device's saved copy, or prevents an admin from making an ordinary independent invitation.
Demoting an admin or removing an admin leaf requires the component's generation rotation in the same Commit,
including a removed device whose account retains another admin leaf. Each such change retires every shared code and
cancels every still-pending request for those generations, not just requests handled by the departing admin. The
admin UI MUST explain that effect before preparing the policy change. Requesters need new codes and renewed consent;
promotion alone does not retire links. Voluntary departure uses the adopted demotion before SelfRemove: retire links
at demotion, then leave the component unchanged in a non-admin SelfRemove-only Commit.
A self-demotion Commit leaves links empty; a staying admin creates replacements later. The departing device does not
generate replacement secrets. A sole admin promotes a successor before demotion. Promoting an admin grants no access
until a current admin supplies private material. A known retired generation never reopens closed requests merely by reappearing in
component state.

Withdrawal or decline suppresses automatic processing of that context. A current admin may approve a declined
request only through a new explicit manual decision while its consent and generation remain valid. A withdrawn
context needs fresh requester consent and a new context. To outsiders, a decline is an account-attributed claim,
not proof of global rejection by all admins. An authenticated Add realization always determines membership.
When retirement is selected, current admins SHOULD send an attributed retired status for each retained open request,
using its validated revision and ordinary status delivery. The requester UI MUST distinguish that notice from a
personal decline or membership removal, show who reported it, and offer obtaining a new code. The notice is not
independent proof of current policy; a former inbox holder could forge such an account-attributed claim. No status
can undo a validated Welcome. If no notice arrives, the requester cannot infer revocation from silence and remains
waiting until its deadline. Status failure never delays the policy Commit.
Disbanding follows the adopted terminal lifecycle; all request processing stops without modifying its Commit shape.

## Retention, capacity and restart

Reading, forwarding or acknowledging transport receipt MUST NOT delete or retire a request. Local row hiding is not
a shared decision. Retain or reconstruct the exact context, revision chain, preview-at-consent, authenticated offer
evidence, decisions, publication uncertainty and Welcome association needed to reproduce the result after restart.
Retained group history may expire; current admins can forward device-authenticated records to another current admin.
Absence of a relay copy is neither rejection nor proof that processing completed.

Open records expire at their signed `valid_until`. An expired context cannot become actionable merely by replay or
restart. Retain its terminal outcome and duplicate-suppression tombstone until at least twenty-four hours after that
deadline; thereafter the signed deadline rejects a replay without needing the tombstone. Outstanding uncertain MLS
publication and convergence facts retain their adopted lifetimes even if a request expires.

A retired generation's contexts and tombstones no longer count against current admission capacity, because its entry
is absent. Its requests remain revoked. Retain facts still needed for rollback, uncertain publication and recovery
under the adopted lifetimes; capacity release is not permission to erase them. If convergence restores a previously
selected live generation, reconstitute its capacity accounting before admitting work. A retirement on an invalidated
branch no longer counts as selected-history retirement evidence; restore the prior generation's eligible requests
after revalidating current prerequisites. Independently authenticated requester withdrawals remain effective.
Do not treat a malicious
reintroduction as new consent. Retained selected-history retirement evidence keeps it inert for automatic processing.
This lets an admin retire a spam-filled generation and issue a fresh one without waiting for old request deadlines.

The transport's 100-context per-link and 1000-reservation/tombstone per-group ceilings are capacity gates. Before
admitting an open context, reserve one terminal slot: admission MUST keep open reservations plus retained terminal
contexts across active generations at most 1000. Completing a context converts its reservation to a tombstone without
increasing this count. Duplicates and refreshes reuse the existing reservation. Retirements release current-capacity
reservations while preserving required facts; rollback MUST restore them before any new admission, and a recovered
excess pauses new admission until capacity becomes available. Recovery facts MUST NOT be evicted to force the count
under the admission ceiling. A client MUST NOT evict
still-required facts to admit another request. It stops admitting new contexts when the relevant capacity is reached,
keeps current work recoverable, and exposes capacity separately from declined or joined. Retention release does not
erase another device's copy or grant an outsider deletion authority. A sender retries only with bounded backoff;
resubmission after loss preserves the context and deadline.

## Deployment profile and user warnings

The default sharing path SHOULD be the complete code or a fitting QR. Short-link hosting is optional. Before
uploading a code to a short-link service, the app MUST explain that this service can read its secrets and obtain
explicit consent for that disclosure. Hostnames, abuse controls and service retention are deployment policy; they
do not change the code, revoke it or provide membership authority.

Clients using an external account signer MUST explain the purpose and intended recipient of account-seal and
encryption operations. An encryption-capable signer is a trusted plaintext processor, not only a signing oracle:
[NIP-46](https://github.com/nostr-protocol/nips/blob/master/46.md) passes plaintext to `nip44_encrypt` and returns it
from `nip44_decrypt`. For requests that includes bearer and device data; for admin grants it includes invitation
secrets. The app MUST disclose this trust boundary before enabling that path. Signer denial, unavailability or
unsupported encryption leaves the operation pending or canceled locally, never reported as relay delivery,
admission or a decision by another party. Rewrapping after recovery preserves the logical signed record.

V1 uses the stated local clock gates without an implicit grace period. A client that detects an unreliable clock
MUST pause new request creation and admission, explain the clock problem, and revalidate after correction. Manual
approval cannot extend the signed deadline or bypass expiry checks that apply to the request. Deployment choices
for time synchronization do not make relay timestamps evidence of pre-expiry consent or change MLS validity.

## Versioning and adoption checks

The component id, record version and transport kinds jointly identify this draft. Unknown required component versions
fail normal negotiation; unknown records are ignored with an unsupported outcome and no state effect.
No migration from ad hoc invitation URLs or alternate account-signature schemes is defined.

The fixed v1 choices are Nostr delivery, immutable generations, original-leaf-key refresh consent, inline bounded
JPEG/PNG previews, and revocation canceling unfulfilled requests. Changes require versioned owning-surface updates.
The deployment profile above settles the privacy and failure requirements while leaving hosting and clock sources
implementation-defined. Neither an external signer nor a public
key-package publication makes the request inbox confidential after its private key leaks.

## Required conformance scenarios

Implementations MUST cover: duplicate wraps, a refresh before its parent, conflicting refreshes, two devices sharing
one account, another account's withdrawal, former-admin replay, admin removal with stale grants, preview substitution,
link expiry during offline time, request deadline replay, capacity without eviction, capacity relief through generation retirement, admin demotion then non-admin SelfRemove,
sole-admin succession, self-demotion with replacement links rejected, retired-status attribution and loss,
QR capacity without truncation, Commit publication uncertainty,
Add success with failed Welcome/status delivery, losing-branch invitation invalidation, and process interruption at
each adopted publish boundary. Fixtures exercise both correct bytes and negative authorization, not only happy-path UX.
Also cover preview mismatch with missing status before any irreversible join mutation; an offline grant recipient
using only its granted code; refresh ancestry after all referenced publication slots were replaced; the highest
validated revision with reordered delivery; 999 terminal contexts plus concurrent completion; and retirement rollback
restoring eligibility and capacity while preserving an independent withdrawal.

## Threat model and adoption checks

| Adversary or failure | Protection | Residual limit |
| --- | --- | --- |
| Relay drops, duplicates or reorders ciphertext | Retained exact requests, signed ancestry and idempotent retry | Availability is best effort; no retained copy means no recovery |
| Link holder submits unwanted requests | Bearer gate, explicit device consent, bounded admission and manual mode | Automatic mode deliberately admits eligible link holders; a leaked link permits spam |
| Account-key attacker substitutes a package | Original leaf-key consent chain binds the exact offer | Account compromise still allows new account-authorized devices and fresh malicious requests |
| Former admin retains private inbox material | Current policy gates action; admin/device removal rotates generations | Old codes can still disclose new requests to old key holders; old records remain readable/disclosable |
| Malicious admin changes a preview | Immutable component commitment and preserved preview-at-consent | An authorized inviter can create a different group with the same commitment; first-contact trust remains |
| Admins race or restart during publication | Adopted candidate-parent authorization, durable exact obligations and convergence | Private decisions are best effort; an unseen withdrawal cannot revoke an already prepared/published Add |
| Untrusted preview contains an image or URL | Bounded inline rendering, plain text and no external fetch | Recipient and hosting network metadata remain observable |
| External signer handles NIP-44 operations | Explicit disclosure, recipient/purpose UI and truthful failure outcomes | The signer can read plaintext, including invitation secrets; it must be trusted |

Before adopting or deploying this draft, maintainers must reconcile the proposed ids with the complete registry,
coordinate the Nostr kind allocations and verify draft-10 component-scoped signing, and run cross-implementation MLS,
NIP-59 and external-signer tests. The repository's byte fixtures are partial evidence, not a production security audit.
