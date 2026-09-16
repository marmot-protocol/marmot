# Group content moderation v1

Status: draft.

Members report a chat message with a category and optional explanation. Reports refer to a particular revision and
cover the whole message, including its attachments and completed agent content. All members can inspect reports,
including reporter identity. Group encryption provides no admin-only confidentiality for this information.

Reporting, shared review, and admin removal are disabled in unnamed two-account conversations; named two-account
groups remain enabled. The exact test and its mutable limits are in
[moderation eligibility](#authenticated-source-epoch-authority-and-moderation-eligibility).

Admins share a review list and either keep the content by dismissing selected reports or remove the entire message.
Keeping content leaves a reviewed indication. New logical reports reopen review unless the message has been removed;
editing alone does not clear reports. Removal closes pending review for all revisions. Admins can also remove unreported
messages. There is no restore or undo flow in this version.

This feature owns reports (kind 1984), dismissal labels on reports (kind 1985), and admin removals of messages (kind 4891).
It uses the [application payload contract](../foundation/application-messages.md) and existing
[admin policy](../app-components/admin-policy-v1.md), and adds no group component or transport change.
[Convergence](../protocol-core/convergence.md), [retained history](../protocol-core/retained-history.md), and
[message retention](../app-components/message-retention-v1.md) govern delivered app payloads and content lifetime.
[Kind 5](../foundation/application-messages.md#author-deletion-kind-5) is the separate author-deletion path.

Clients can activate this optional application behavior without changing group state. Compatible clients display pending,
reviewed, and removed states and can show pending counts without creating chat unread activity or report push notifications.
User gestures, localized labels, and review-screen layout are application choices. Every group member receives the same
report and review events; restricting review actions is an authorization rule, not an information-access boundary.

Mixed-client groups require coordinated client updates before presenting consistent moderation as a group-wide
guarantee. This feature does not change membership or prevent an author from sending a new message after removal.

## App-event interpretation

The [application payload contract](../foundation/application-messages.md) owns the common six-field unsigned event
shape and MLS sender authentication. This feature owns the following kind-specific interpretation. Events of kinds
1984, 1985, and 4891 are modifiers: clients MUST NOT render them as standalone transcript rows. Their references name
Marmot app event ids in the same group. A chat target means an original kind-9 event, not an edit, system event, or stream-start event.

For kinds 1984, 1985, and 4891, an event that fails any stated shape, bound, type, or authorization rule MUST have no
moderation effect. Receivers MUST NOT partially apply a malformed event. Unknown dependencies remain unresolved as
specified below; they are not evidence of invalidity. Referenced ids and account authors MUST use lowercase 64-hex
encoding. This section uses the following fixed Unicode White_Space set: U+0009–U+000D, U+0020, U+0085, U+00A0,
U+1680, U+2000–U+200A, U+2028–U+2029, U+202F, U+205F, and U+3000.

### Reports (kind 1984)

A report uses [NIP-56](https://github.com/nostr-protocol/nips/blob/master/56.md), with one reported chat message:

- Exactly one `e` tag, beginning `["e", original_message_id, report_type]` (at least three elements).
- Exactly one `p` tag, beginning `["p", original_author]` (at least two elements), naming the original message's
  authenticated account author. The `e` tag alone selects the report type; a third `p` element is optional and ignored.
- Producers MUST include exactly one `revision` tag, beginning `["revision", revision_event_id]` (at least two
  elements). Receivers MUST accept its absence from older producers and normalize it to the original message id before
  deduplication; duplicate `revision` tags are invalid. A revision is either the original kind-9 event or a valid
  kind-1009 edit of it by the same author.
- `content` is the reporter's UTF-8 explanation, at most 4096 bytes, preserved without Unicode normalization.
  It MAY be empty except for report type `other`, which MUST contain at least one character outside White_Space.

Producers emit the tag prefixes shown above. Receivers MUST ignore trailing elements after those prefixes, including
any third or later `p` element. Missing required elements invalidate the whole event. Supported report types are
`nudity`, `malware`, `profanity`, `illegal`, `spam`, `impersonation`, and `other`. Unknown auxiliary tags do not change
report semantics. An unrecognized `report_type` invalidates the whole report event.

A logical report is keyed by group, original message, normalized revision id, and reporting account. Receivers MUST
count duplicate events once and select their displayed details by lower `created_at`, with lexicographically lower
lowercase-hex `id` breaking a tie. Retrying MUST NOT create a new logical report. A valid dismissal referencing any
duplicate resolves that logical report, including duplicates received later. Unknown targets and revisions MUST remain
unresolved until their authenticated dependencies are available. A mismatched `p` author, cross-group target,
unrelated edit, or non-chat target MUST have no moderation effect.

A retry MUST preserve the original message and normalized revision id of its logical report, including across client
upgrades. Reporting a later edit is a new logical report, not a retry of a report about the original revision.

Example kind-specific fields (the common six-field app-event encoding still applies; angle-bracket values below are
placeholders for canonical ids and account keys):

```json
{"kind":1984,"tags":[["e","<original message id>","spam"],["p","<message author>"],["revision","<original or edit id>"]],"content":"Repeated unsolicited advertising"}
```

### Dismissal labels (kind 1985)

A shared admin dismissal uses [NIP-32](https://github.com/nostr-protocol/nips/blob/master/32.md) to label report
**events**, leaving the reported message available. It MUST carry exactly one `L` tag naming `marmot.report-review.v1`
and exactly one `l` tag with label `dismissed` and that namespace. Between 1 and 100 `e` tags carry referenced event
ids. The required tag prefixes are `["L", "marmot.report-review.v1"]`, `["l", "dismissed", "marmot.report-review.v1"]`,
and `["e", event_id]`; receivers MUST ignore trailing elements. A missing prefix element invalidates the whole event.
Producers MUST deduplicate ids and order them lexicographically; repeated references have no additional effect.
Producers MUST emit empty `content`; received explanatory content does not change the label's meaning. Other tags are
ignored. Only an active admin in the authenticated source-epoch state can authorize dismissal, as defined below.

```json
{"kind":1985,"tags":[["L","marmot.report-review.v1"],["l","dismissed","marmot.report-review.v1"],["e","<reviewed report id>"]],"content":""}
```

After shape and authorization validation, receivers MUST evaluate each `e` reference independently: a resolved valid
report in the same group resolves its logical report; an unknown id MUST remain unresolved until its authenticated
dependencies are available, without delaying other references; a known non-report, invalid report, or cross-group
reference has no effect for that reference only. These per-reference outcomes do not make the label malformed.

Dismissal affects only those logical reports. Unless the message has been removed, another account's new report or a
report about another revision remains pending. Multiple valid dismissals commute; receivers MUST select displayed
review attribution by lower `created_at`, with lexicographically lower lowercase-hex `id` breaking a tie. Editing a
reported message does not dismiss its reports. This version defines no report withdrawal, dismissal undo, or restoration
action.

This attribution is a deterministic display choice from sender-asserted timestamps, not proof of who reviewed first
in real time.

### Admin removal (kind 4891)

Kind 4891 is a Marmot-specific admin removal. Exactly one `e` tag, beginning `["e", original_message_id]`, names the
original chat message; receivers MUST ignore trailing tag elements. The action removes that message and all its revisions.
Its content MUST be a JSON object with exactly `v` and `action`, whose values are the integer `1` and `"remove"`.
Duplicate JSON keys are invalid. Other tags are ignored. Only an active admin in the authenticated source-epoch state
can authorize this event, including when its sender is also the target author.
Admins MAY remove unreported content. Unknown targets MUST remain unresolved; cross-group or non-chat targets MUST
have no moderation effect.

```json
{"kind":4891,"tags":[["e","<original message id>"]],"content":"{\"v\":1,\"action\":\"remove\"}"}
```

An effective removal MUST close pending review for every logical report about that message or any of its revisions.
Reports received later MAY remain as historical records but MUST NOT reopen review or increase pending counts.
Removal takes precedence over dismissal and later edits. Clients MUST NOT reveal the removed message's retained content
in any application view, including transcripts, reply previews, search results,
[attachments](./encrypted-media.md), and the report review described in this feature. These are client presentation
views subject to this rule, not separate protocol surfaces.

[Author deletion](../foundation/application-messages.md#author-deletion-kind-5) remains a separate path and does not grant
non-admins kind-4891 authority. A kind-5 reference to a kind-1984 report, kind-1985 dismissal, or kind-4891 removal MUST
have no effect, even when that control was authored by its sender: it MUST NOT withdraw the control or change its
moderation effects. Deleting reported chat content with kind 5 MUST NOT close pending review or dismiss reports.
These restrictions do not change author deletion of other allowed content.

### Authenticated source-epoch authority and moderation eligibility

Receivers MUST authorize an admin action against the [active admins](../app-components/admin-policy-v1.md#active-admins)
in its authenticated MLS source-epoch state, not the latest admin list or its wall-clock timestamp. As in
[authorization evaluation](../app-components/README.md#authorization-evaluation), the relevant state belongs to the
authenticated candidate branch, not merely any state with that epoch number. A later demotion does not revoke that
authorization; source-epoch authentication does not prove the real-world time the action was created.

Clients MUST retain or reconstruct the evidence needed to reproduce authorization after restart. A persisted verdict
established from authenticated source-epoch state and bound to the action and its branch counts as this evidence.
If no such evidence is available and no verdict has been established, authority MUST remain unresolved; clients MUST
NOT substitute the latest policy or freeze a denial. Missing or pruned old snapshots MUST NOT undo a previously
authorized removal or dismissal: clients MUST preserve its recorded verdict and resolution until explicitly withdrawn
by convergence invalidation. This follows [durability](../protocol-core/durability.md#recoverable-protocol-facts) and
[retained-history pruning](../protocol-core/retained-history.md#pruning), without requiring expired MLS secrets to remain.

An action with unresolved authority MUST NOT contribute a report count, dismiss a report, or suppress target content.
The target remains subject to its other validated modifiers and retention policy. In particular, an unresolved removal
does not override an existing authorized removal, and does not itself hide otherwise available content. Clients MUST
retry when the missing evidence becomes available. Applying an unproven removal would let a sender without established
admin authority suppress another member's content.

For this feature, moderation is enabled in every authenticated source-epoch state except when both conditions hold:

- it has exactly two distinct current member accounts; and
- its [group profile](../app-components/group-profile-v1.md) is absent, or its `name` is empty or consists only of the
  White_Space characters defined above.

Kinds 1984, 1985, and 4891 MUST have no moderation effect in that excluded state. Count distinct MLS-authenticated
account identities, not member leaves; an account with multiple devices counts once. Do not normalize profile bytes.
Where moderation is enabled, every member MAY report; only active admins MAY dismiss reports or remove content,
including their own content. Kind-5 author deletion is unaffected. This moderation rule is separate from convergence's
branch eligibility.

This is a mutable application-profile heuristic, not a permanent direct-conversation type or protection against an
admin changing the group. An active admin can enable moderation in a two-account conversation by naming it or adding
a third account. Removing the name or returning to two accounts can disable it for later events; each event is judged
against its own authenticated source-epoch state. Named two-account groups intentionally remain enabled.
Previously valid reports and decisions retain their effects when the current state becomes excluded; unresolved review
can remain pending. New dismissals or removals require an eligible source state, which an admin can establish by naming
the conversation or adding a third account.

[Convergence](../protocol-core/convergence.md#applying-the-selected-branch) owns app-payload delivery and invalidation.
Clients MUST derive moderation effects from delivered app payloads and their authenticated dependencies. When
convergence withdraws a payload that decrypts only on a losing branch, clients MUST withdraw the effects that depend
on it and recompute from the remaining delivered payloads. A branch change MUST NOT leave a withdrawn removal or
dismissal in effect.

Removal suppresses content; it does not itself require destroying the retained payload. While a removal can still be
withdrawn by convergence, clients MUST preserve content that would otherwise remain available under the applicable
content-retention policy so that withdrawing that removal can reveal it again. This does not extend retention or undo
an independent author deletion: expired content stays unavailable, and any remaining deletion or removal still applies.
Withdrawing an invalidated action is protocol recomputation, not a user restoration action.
The withdrawal window is bounded by [candidate eligibility](../protocol-core/convergence.md#eligibility), including
the `max_rewind_commits` rollback horizon and any already-admitted unfinished convergence pass. Once no eligible
candidate can withdraw the removal's source branch and no such pass remains, clients MAY erase the suppressed content
while preserving minimal removal evidence. Ordinary content expiry still applies earlier; this rule adds no wall-clock
retention period.

### Retention and compatibility

Reporting MUST NOT extend the target's content-retention lifetime. Report references MUST NOT embed copies of target
text or attachment bytes. Review surfaces MUST show an unavailable-content placeholder after deletion or expiry,
without revealing retained target content. Reporter identity, category, explanation, and review attribution MAY remain
visible while those records are retained; report explanations obey applicable retention. Beyond applicable content
retention, clients MUST retain only the minimal reference and resolution evidence needed to keep expired or removed
content from returning and duplicates from reopening resolved reports.
Explanations are independently authored text and can repeat removed content; suppressing the target does not perform
semantic redaction of report explanations.

Clients with the same delivered app payloads and authenticated dependencies MUST derive the same report counts and
outcomes regardless of delivery order. Personal blocking MUST NOT change shared validity. Report and review events
MUST NOT increment chat unread counts.
Here, authenticated dependencies include the source-epoch authority evidence or an established verdict. A client still
missing that evidence can retain an unresolved action while another client has resolved it; equal outcomes are required
once both have the same authenticated dependencies.

These are optional application semantics. Older clients may ignore dismissal labels or removal events;
this feature cannot guarantee removal on incompatible clients or erase copies already saved outside the application.
On upgrade, a client MUST preserve previously honored author-deletion and admin-removal tombstones and dismissal
resolutions even if their historical snapshots are unavailable. This compatibility rule does not authorize newly
received deletion, removal, or dismissal events.
