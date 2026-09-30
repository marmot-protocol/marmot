# Multi-device security and sync choices

Status: idea (non-normative). This is a companion to [multi-device.md](./multi-device.md), proposing refinements to its
walkthrough. These recommendations are for discussion, not adopted behavior or wire formats. The walkthrough's
figures show its baseline flow; selective sync and the warning refinements below would need updated figures if adopted.

## Existing signatures and the missing continuity guarantee

A Marmot KeyPackage already has several authentication layers:

- MLS signs the KeyPackage and its embedded LeafNode with the leaf's signature key; see
  [RFC 9420 sections 7.2, 7.3 and 10](https://www.rfc-editor.org/rfc/rfc9420.html#section-10).
- The [account identity proof](../app-components/account-identity-proof-v2.md) authorizes that MLS signature key under
  the Nostr account. It is a key binding, not permission to join a chat.
- The [Nostr publication](../transports/nostr.md#keypackage-publication) is signed by the account and includes the
  publication slot and KeyPackage reference.

Thus adding another signature by the *new* MLS key does not solve slot replacement. Someone with account signing
access can generate their own MLS key, authorize it with a valid account proof, and publish a valid package in a
victim's known slot. The slot is public, not a secret or an authentication credential. A newest-event rule can hide the
previous package, and detection based only on unknown slot ids misses this case.

Bidirectional signatures establish that the two signing keys endorse an association. They do not establish that
Alice approved it, or that the device is the same one she trusted yesterday. Both sides of a newly generated pair can
be controlled by the attacker. The useful extra signature would come from an **already trusted device key**, with trust
anchored in an earlier verified link and retained independently of the newest account publication.

### Options to explore

1. **A persistent installation continuity key.** During code-verified enrollment, siblings pin a key for this
   installation in the private roster. That key authenticates future packages and successor keys. This separates
   installation identity from chat leaves, but adds key storage, rotation and recovery responsibilities.
2. **A pinned MLS signing key.** Use an already trusted MLS signing key to authorize future packages. This might avoid
   another key, but the design has to say which leaf supplies the authority, how its lifecycle survives leaving that
   group, and how changes of that key are approved. There is no implicit single MLS key for all of a device's chats.
   Reusing a key across contexts also needs privacy and cryptographic review.
3. **Authenticated device-group announcements.** A linked device announces its replacement package through the device
   group. This gives siblings an authenticated source without making a public continuity identity. It leaves
   offline delivery, group recovery and verification by outside inviters unresolved.

Recommendation: explore the persistent continuity key together with private device-group announcements, and compare
it with the pinned MLS-key option before choosing. Do not derive the random publication slot from any of these keys.

Any continuity statement would need an unambiguous binding to the account, slot, exact package reference, predecessor
and intended successor authority. Pairing also needs a binding to the particular approval session and destination.
The owning surfaces would define canonical signed inputs, domain separation, replay protection and rotation rules;
this idea does not define their bytes. Avoid a circular construction in which a signature inside a package signs that
same package's final reference.

### What continuity would and would not achieve

- A known slot with an unrecognized successor key would become an anomaly, rather than a quiet refresh. Siblings
  would retain the last trusted association and pause automatic linking, chat adds and history delivery to the
  suspect replacement. An unverifiable package would not become trusted just because it is newer on a relay.
- A legitimate rotation could be authorized by the predecessor and accompanied by evidence of control of the new
  key. Losing the predecessor key would require explicit relinking, not an account-signature-only reset of trust.
- A valid MLS signature demonstrates control of the signing key, not possession of the separate private Welcome
  initialization key. Enrollment needs to resolve how to demonstrate the latter, with a fresh, session-bound exchange,
  before releasing history. Comparing a public code alone is not proof of private-key possession.
- Relay overwrite, withholding and split views remain possible. Continuity could detect an observed unauthorized
  replacement; it cannot force a relay to retain or deliver the legitimate event. A new installation with no trusted
  roster cannot infer continuity from the account signature alone.
- Other people's inviters cannot automatically verify a private roster. They may still invite an attacker with a
  valid account proof. Public continuity evidence might help them, but risks linking installations and needs an
  explicit negotiation and trust-distribution design.
- An attacker controlling both account signing access and the trusted device key can produce valid successors.
  An already authorized malicious sibling is also inside the proposed trust boundary. Continuity is a narrower
  protection, not recovery from account or device compromise.

## Welcome delivery: bootstrap first, then private coordination

The adopted [Nostr Welcome delivery](../transports/nostr.md#welcome-delivery) uses ordinary NIP-59 gift wraps addressed
to the account. The walkthrough does not change that carrier. Opening the account envelope does not let a sibling
decrypt a Welcome whose private initialization key it does not have.

Proposed direction:

1. Bootstrap membership in the hidden device group with an ordinary Welcome. The new device cannot read the device
   group before joining it, so sending its bootstrap Welcome only inside that group would be circular.
2. Once linking is accepted and device-group membership is established, carry subsequent chat Welcomes inside
   authenticated device-group messages. Preserve the MLS Welcome's encryption to the destination KeyPackage.
3. Keep ordinary gift wraps for invitations from other people. A linked device could coordinate their handling inside
   the device group, subject to the recipient's chat selection and acceptance decision.

This needs a new, explicitly negotiated carrier; it is not permission to reinterpret today's Welcome rumor. A future
design would preserve the exact package reference and relevant source evidence, authenticate the sending sibling,
and tie delivery to the accepted chat membership change. Receipt of a device-group message alone would not authorize
joining a chat or certify that the chat accepted an add.

Repeated delivery through either carrier would resolve to one join. Acknowledgements, bounded retries, expiry and
recovery after an offline interval need agreement. A retry for a deleted or expired initialization key needs a current
package and, where necessary, a fresh authorized add; it cannot pretend an old Welcome became decryptable.
Unsupported clients would show a reason instead of silently bypassing approval or sending history.

The device group hides coordination from relays, not from its members. All participating devices can see any plaintext
chat names, routing hints and mappings put in its messages. Selective sync may need destination-encrypted metadata or
a more limited roster message design. Hiding the carrier does not hide public KeyPackage slots or chat leaf counts.

## Selective chats, history and future invites

Proposed replacement for the two all-or-nothing toggles in Scene 4:

- **Existing chats:** All, Selected, or None, with a picker and per-chat progress or failure reasons.
- **History for each selected chat:** None, Recent, or Available history, with a clear date range or size estimate.
- **Future chats on this device:** Automatically add, Ask first, or Keep off this device.

The approving device would explain the choices before linking. A device can be linked for coordination without joining
every chat. Selecting a chat gives fresh MLS membership; history is a separate consent and transfer step. The default
choices, whether history is opt-in, and the meaning of Recent remain product questions rather than settled defaults.

Siblings would preserve a per-device, per-chat selection so gap filling repairs an intended membership, not a
deliberate exclusion. Choices could later change on the Devices screen. Concurrent edits, device-group merges and
offline replay need deterministic reconciliation; absence of a leaf alone is insufficient evidence to add it.

There is a conflict to resolve with Scene 6: an outside inviter currently proposes adding every fresh compatible
package before Alice accepts. A private exclusion cannot prevent that inviter from creating an unwanted leaf or
sending its Welcome. Options include recipient-side cleanup of unwanted leaves or a different invitation fan-out
design. Cleanup cannot undo disclosure of Welcome secrets to a device that already received them. Until this is
resolved, the UI cannot promise that Keep off means a device never receives a new chat's cryptographic access.

Selective sync reduces local data and supports different device roles. It is not a security boundary against a device
with unrestricted account signing access or a malicious sibling able to approve membership. A strong restriction
would need scoped authority, enforcement by chat members, and a way to limit coordination metadata too.

## How old messages reach a new device

A Welcome supplies membership and join secrets for the new leaf. It does not carry the chat's old messages or their
historical decryption state. Replaying old relay ciphertext alone is not history recovery.

Proposed direction: after the destination joins a selected chat, an authorized sibling exports the history it still
has, and transfers it through an authenticated, encrypted channel bound to that destination and the approved scope.
Large chunks could use a separately encrypted transfer, with coordination in the device group. Labels, read markers,
pins and notification settings need their own small-state sync semantics; they are not all chat history.

History transfer would preserve available authorship evidence and provenance. An imported record is not a new live
message from its original sender, and a transfer-source signature alone does not prove the original authorship.
The destination would distinguish verified evidence from assertions by the transferring sibling. Do not clone a
sibling's live MLS state or restore a removed device's old membership.

The transfer needs consent, cancellation, resumable progress, integrity checks, duplicate handling, retention rules
and resource limits. Do not resurrect expired or deleted messages merely because a sibling retained a copy; removal
or denial cancels pending history release. Previously delivered plaintext cannot be recalled. Backups need a separate
recovery secret or authority, not encryption to the nsec alone. The export format, eligible records, attachment keys,
history age limits and interaction with disappearing messages remain open.

## Warning policy for discussion

Prompts follow observed, authenticated evidence. Before classifying a sign-in, check the transport signature and account
binding, decoded package and leaf signatures, account proof, lifetime and freshness. A Welcome's reference alone is
an unverified claim: fetch and validate its package evidence before treating it as a sign-in. Invalid or unauthenticated
input is not evidence that account signing access was stolen.

| Observed case | Proposed response |
| --- | --- |
| Valid, fresh package in an unknown slot | Ask whether Alice added an installation; offer code-verified linking, Not now and This wasn't me. |
| Refresh in a known slot with verified continuity | Update quietly; no repeated sign-in alert. |
| Known slot with a successor lacking trusted continuity | Pause automatic actions for that candidate and ask Alice to reverify; explain that signing access may be compromised. |
| Fresh valid publication in a retired slot | Strong returning-device warning; never automatically restore membership or history. |
| Alice chooses This wasn't me | Keep a persistent account-security warning, reject the candidate and cancel pending adds and history delivery. |
| Invalid signatures, malformed input or a replay of already handled evidence | Discard or deduplicate; no new compromise alert from unauthenticated input. |
| Code collision, changed package during approval or inconsistent pairing evidence | Stop linking that attempt, explain the anomaly and begin a fresh verification. |
| New client tag without other anomaly evidence | Treat as a self-reported client change, not proof of a new physical device or theft. |

The continuity rows depend on choosing and specifying a continuity mechanism. Older clients cannot claim to provide
that guarantee. Without it, the baseline quietly handles known-slot refreshes and cannot reliably detect an attacker
replacing a known slot; that is an accepted limitation of the baseline, not a verified continuity check. Expired
evidence is not a current invitation candidate; authenticated historical anomalies may still
merit investigation, with wording that distinguishes a past event from an active sign-in.

Suggested wording after denial:

> Your account's signing access may be compromised. This could involve your private key or an authorized signer.
> Rejecting this installation cannot prevent someone with your private key from acting as you.

For a signer grant or session compromise, explain how to revoke that access and inspect other grants. If the raw nsec
was stolen, revoking a grant or removing a leaf cannot revoke the attacker's copy; moving to a new account is the
complete identity remedy. Do not claim that a denied sign-in proves which secret was stolen.

Alerts would appear when evidence reaches a device, which may be after reopening the app. Offline devices and
withholding relays prevent a promise of immediate detection. Bound and deduplicate prompts without silently losing
distinct authenticated anomalies. Lockscreen alerts would omit codes, chat names and sensitive account details;
linking and security decisions happen after unlocking the app.

Sibling decisions need an agreed authenticated order, not relay arrival order or public publication timestamps.
Approval followed by denial would revoke the device and stop unfinished transfers, while explaining that already
released history cannot be recovered. Outstanding chat removals would remain visible until confirmed, including
chats where authorization or offline membership prevents immediate cleanup. Rejection would suppress repeats of the
same evidence, not hide a later suspicious replacement in that slot.

## Threat model and remaining exposure

Assets include account signing authority, device keys and MLS state, old messages and attachments, the trusted roster,
chat selections, and the user's ability to recognize and revoke a device. The trust boundary includes every approved
sibling under the current any-one-device approval proposal.

| Adversary or failure | Proposed protection | Remaining exposure |
| --- | --- | --- |
| Attacker with nsec, without device secrets | Verified prompts, trusted continuity and explicit enrollment | Can create valid account proofs, replace slots, impersonate the account and receive future invites. Nsec does not directly decrypt old chats, but deceiving gap filling or history release can expose them until continuity is enforced. |
| Compromised signer session or grant | Revoke affected access, check grants and verify new device approval | The exact authority depends on the signer; a stolen raw key remains usable after grant revocation. |
| Lost or compromised installation | Remove its leaves, retire its slot and revoke signer access | Stored plaintext and captured keys remain exposed; removal is prospective and depends on accepted chat commits. |
| Malicious approved sibling | Explicit scope and visible approval/removal history | Under single-sibling authorization it may enroll others, export available history or remove siblings; stronger consent would require a different trust model. |
| Malicious relay | Authentication, continuity, replay handling and independent relay observations | Withholding, overwrite, split views and delayed detection remain possible; no completeness proof follows from a relay query. |
| Pairing substitution or replay | Exact candidate/session binding, private-key possession checks and code comparison | Word-code grinding and human comparison errors need analysis; a visible matching code alone is not private-key proof. |
| Excess slots, repeated anomalies or oversized history | Bounded work, visible failures and retained decisions | Caps can exclude legitimate devices; limits, fairness and recovery still need design. |

An external signer reduces raw-key exposure on a phone, but does not erase its local messages or MLS secrets. App lock
does not change network membership. Deleting a public event does not revoke account authority or prove every relay
deleted it. A new device and its public client tag are self-reported software identities, not hardware attestation.

## Questions to settle before spec work

1. Which continuity option gives a useful guarantee with acceptable key storage and privacy costs? Is continuity
   visible only to siblings, or also verifiable by outside inviters without exposing private device relationships?
2. How are continuity keys initially pinned, rotated, retired and recovered? What happens when an old key is lost,
   devices disagree, every device is lost, or an attacker overwrites the public slot before discovery?
3. What exact approval transcript and initialization-key possession exchange supplement the four-word code? How are
   candidate replacement, code grinding, expiry, retries, replay and concurrent enrollment bounded?
4. How does selective membership interact with fan-out invites, account-wide accept/decline, sibling adds and removal
   authority? Can scoped signer or membership authority make exclusion an enforceable security property?
5. Which roster and chat metadata can excluded devices see? Can destination encryption limit that disclosure while
   still enabling gap filling, removal and merges?
6. Which negotiated carrier supports linked-device Welcomes? How are source evidence, commit acceptance, destination,
   deduplication, acknowledgements, stale packages and unsupported clients handled without circular bootstrap?
7. What orders roster decisions and selection changes? How do partitioned device groups merge without reviving a
   removed device, rejected candidate or excluded chat? What wins when approval races denial or removal?
8. Which history and small-state records are eligible, how is provenance represented, and how are retention, deleted
   messages, attachments, cancellation and partial imports handled? What is the separate backup/recovery design?
9. Which warning defaults, lockscreen text and signer-specific remediation can clients present consistently? How do
   they preserve security alerts while bounding spam, and surface incomplete removals without implying protection?
10. Which adversary capabilities and negative cases become shared conformance scenarios, and which risks are explicitly
    accepted rather than fixed? Review last-resort package reuse and delayed Welcomes alongside continuity.

## Placement when a decision is adopted

- **Foundation:** identity and key binding, continuity trust anchors, capabilities and cryptographic proof roles.
- **Protocol core:** membership transitions, removal and join acceptance, without depending on relay ordering.
- **App components:** any selected continuity, roster or selection state with an appropriate lifecycle.
- **Transports:** negotiated Welcome carriers, publication/discovery and authenticated delivery evidence.
- **Features:** enrollment, selective sync, history transfer, warning policy and recovery across those surfaces.

Adoption needs explicit interoperability hooks and a separately reviewed threat model and validation plan. No component
ids, event kinds, signed encodings or new validation rules are assigned by this document.
