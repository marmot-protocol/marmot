# Application payloads

Status: adopted.

Marmot app payloads use a Nostr event shape inside MLS.

This is a foundation rule. It is separate from the Nostr relay transport. A future non-Nostr transport would still carry
MLS application messages whose plaintext has this Nostr-shaped payload.

## Terminology

Use these terms consistently:

- `MLS application message`: the MLS content type that carries encrypted application bytes.
- `Marmot app payload`: the plaintext bytes inside an MLS application message.
- `Marmot app event`: the current Nostr-shaped object encoded as a Marmot app payload.
- `Delivered app payload`: a Marmot app payload that passed convergence and is safe to hand to the application.

Avoid using "application message" by itself when the sentence could mean either the MLS input or the app-facing output.

## Shape

A Marmot app event has the same fields as a Nostr event, except `sig`:

- `id`
- `pubkey`
- `created_at`
- `kind`
- `tags`
- `content`

`id` is the Nostr event id for the rest of the event shape. It is computed from the canonical Nostr event serialization
of `[0, pubkey, created_at, kind, tags, content]` as defined by
[NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md) and pinned in
[canonical-encoding.md](./canonical-encoding.md) ("Nostr-shaped values"): the lowercase-hex `SHA-256` of that
whitespace-free UTF-8 JSON serialization. This is the same hash preimage Nostr uses before signing, even though Marmot
does not produce a Nostr signature for the inner Marmot app event. Because decoders MUST reject a payload whose `id`
does not match (see "Encoding"), every implementation MUST produce byte-identical serialization; the exact rules are
NIP-01's, not implementation-defined.

The payload is not signed as a Nostr relay event and is not a valid standalone Nostr event for relay publication. MLS
authenticates the sender as a group member, and the `pubkey` field identifies the Marmot account that authored the
message.

The missing `sig` is intentional. A client MUST NOT add a Nostr signature to the inner Marmot app event before placing
it inside MLS.

`id` is a Marmot app event id. It is separate from the MLS message id and from any outer transport event id.

## Encoding

A Marmot app payload that uses the unsigned Nostr event shape is serialized as one UTF-8 JSON object with exactly the
members `id`, `pubkey`, `created_at`, `kind`, `tags`, and `content`, and no others. Field values, tag arrays, and string
content follow Nostr event conventions; the signature member is absent.

Decoders MUST reject a payload that:

- contains a `sig` member;
- contains an unknown top-level member;
- contains duplicate object keys;
- has an `id` that does not match the canonical Nostr event id computed from the other members ("Shape" above).

Decoders do not police inner tag names. Tags carry application content; the active transport binding builds the outer envelope's routing tags from group state, never from the inner event, so an inner tag never affects delivery (see [../protocol-core/group-messaging.md](../protocol-core/group-messaging.md), "App payloads").

If a future message kind needs binary content, canonical JSON, or another encoding rule, that rule belongs in the
message-kind document and MUST name the exact bytes carried inside MLS.

## Receiver authentication

After structural decoding, a receiver MUST decode the inner event's `pubkey` from exactly 64 lowercase hexadecimal
characters to a raw 32-byte x-only public key and compare those bytes with the Marmot account identity authenticated by
the MLS sender leaf for that application message. If decoding fails or the bytes are not equal, the receiver MUST drop
the Marmot app payload and MUST NOT render or deliver it to the application. The mismatch does not alter canonical group
state or roll back other authenticated MLS processing.

## Message kinds

Kind `9` is Marmot's default ordinary chat-message kind. Its `content` is the chat body unless an owning optional
feature, such as encrypted media, adds feature-specific tags or handling.

The registry is not an allowlist of inner event kinds. Any Nostr-shaped event that satisfies the shared encoding and
receiver-authentication rules is a valid Marmot app payload unless an active required feature imposes another check.
Protocol processing MUST NOT reject an otherwise-valid app payload merely because its event kind is unknown.

Feature or app-payload docs define which additional kinds are protocol-required and what they mean. A client MAY ignore
or decline to render unsupported application semantics after delivering the accepted payload to its application layer.

## Message edits (kind 1009)

Kind `1009` is an in-place replacement of a prior chat message's text. The edit references the original event id via a
single `e` tag; its `content` is the replacement plaintext. Edits are not chat — they MUST NOT render as a separate row
in the conversation transcript. Clients SHOULD overlay the latest replacement onto the original message body and SHOULD
indicate that the row has been edited.

```json
{
  "id": "<hex event id of this edit event>",
  "pubkey": "<hex account public key of the editor>",
  "created_at": 1700000000,
  "kind": 1009,
  "tags": [["e", "<hex event id of the edited message>"]],
  "content": "the replacement plaintext"
}
```

A kind `1009` event is an ordinary Marmot app event and carries exactly the six members from "Shape" above (no top-level
`v`; its `content` is the replacement plaintext, not JSON).

- The original message's projected `kind` does not change; only its rendered body is overlaid.
- The edit does not change the original message's logical transcript position or ordering timestamp. The edit event's
  `created_at` orders competing edits; it is not a replacement activity timestamp for the target.
- The unread count MUST NOT advance on an edit. A receiver who is caught up with the original is caught up with the
  edit.

Applications normally should not treat an edit as new conversation activity or bump a chat-list preview, regardless of
the target message's age; chat-list presentation remains application policy.

Authorship is enforced by Marmot account identity: an edit is honored only when the account identity authenticated by
its MLS sender leaf equals the original message's authenticated account author. Another valid leaf for the same account
therefore may edit that account's message. A client receiving a kind `1009` from a different account MUST ignore the
edit. A client MAY retain accepted edit events for history while rendering only the selected overlay.

Multiple edits to the same target are ordered by their inner event's `created_at`. The most recent edit wins as the
overlaid body. A history surface MAY list each version with its timestamp.

A client receiving an edit whose target it has not yet ingested MAY hold the edit for a bounded window and apply it
when the target arrives, or drop it. Either choice is acceptable.

## Group system events (kind 1210)

Kind `1210` is a durable group system row: a record of an authenticated change to group state — a member added,
removed, or left; an admin granted or revoked; the group renamed; the group avatar changed; or the group disbanded.
These rows are not chat.
A client MUST render them separately from kind `9` chat bubbles and MUST NOT treat their `content` as a chat body.

A kind `1210` row is **synthesized locally** from canonical group state, not sent as a message. When a client applies a
commit and the protocol surfaces a state notification (see
[`../protocol-core/inbound-processing.md`](../protocol-core/inbound-processing.md)), the client MAY derive the
corresponding kind `1210` row from that authenticated change. Because the row is derived from MLS-authenticated state
rather than a separately delivered message, it cannot be forged by a single member and converges across clients that
apply the same commit. A client MUST NOT depend on receiving a kind `1210` *message* over the wire to know that group
state changed; the state notification is authoritative. (A client or connector MAY still *send* a kind `1210`
event to post an explicit free-text notice; such a sent event is an assertion by its author, not a derived state fact.)

The `content` is JSON:

```json
{
  "v": 1,
  "system_type": "member_added",
  "text": "Member added",
  "data": { "actor": "<hex pubkey>", "subject": "<hex pubkey>" }
}
```

- `v` is the schema version (`1`).
- `system_type` names the change. Defined values: `member_added`, `member_removed`, `member_left`, `admin_added`,
  `admin_removed`, `group_renamed`, `group_avatar_changed`, `group_disbanded`.
- `text` is a human-readable fallback only. Clients SHOULD render from `system_type` plus `data` so the row can be
  localized and re-resolved as display names change.
- `data` carries structured fields: `actor` (hex pubkey of the committing member, when attributable), `subject` (hex
  pubkey of the member the change concerns, for the member/admin types), and `name` (the new group name, for
  `group_renamed`).

`group_disbanded` carries the authenticated committer in `actor` and no
`subject`. It is the only presentation row synthesized for the terminal
Commit; the Commit's coupled member/admin removals do not produce additional
kind `1210` rows.

A complete unsigned kind `1210` Marmot app event for `group_disbanded` is:

```json
{
  "id": "126e47076e4d0a75ed260b279c33ed433acd764fc80e2de2e0315a64116d1f52",
  "pubkey": "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",
  "created_at": 1700000000,
  "kind": 1210,
  "tags": [["system", "group_disbanded"]],
  "content": "{\"v\":1,\"system_type\":\"group_disbanded\",\"text\":\"Group disbanded\",\"data\":{\"actor\":\"79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798\"}}"
}
```

The `id` above is the lowercase-hex SHA-256 of these exact canonical
Nostr-event preimage bytes:

```text
[0,"79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",1700000000,1210,[["system","group_disbanded"]],"{\"v\":1,\"system_type\":\"group_disbanded\",\"text\":\"Group disbanded\",\"data\":{\"actor\":\"79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798\"}}"]
```

The event SHOULD carry a `["system", system_type]` tag. A row is anchored to the epoch the change reached, so it sorts
into history at the point the change took effect.

## Relationship to transport events

The inner Marmot app event and an outer Nostr transport event are different objects.

When Marmot uses Nostr relays, the transport MAY wrap MLS bytes in signed or unsigned Nostr events such as kind `445` or
NIP-59 gift wraps. Those outer events are transport envelopes. They do not replace the inner app payload.

## Author deletion (kind 5)

Kind `5` requests author deletion using [NIP-09](https://github.com/nostr-protocol/nips/blob/master/09.md).
For Marmot chat messages, `e` tags reference original app event ids in the same group. A receiver MUST verify that
its MLS-authenticated sender account equals each target's authenticated account author before honoring that target's
deletion. Admin status MUST NOT authorize kind-5 deletion of another account's content. Unknown targets remain
unresolved until their authorship can be verified.

An honored chat-message deletion makes that message unavailable, including in report-review surfaces; later edits
MUST NOT restore its content. An effective admin removal takes precedence if both actions exist. This interpretation
uses the NIP-09 author-deletion path; it does not extend NIP-09 authorization or define a deletion-undo action.

## Content reports and shared review (v1)

Status: draft. The user-visible flow is [group content moderation](../features/content-moderation.md).
This interpretation adds no group component and uses the existing admin policy. Report and review events are
modifiers: clients MUST NOT render them as standalone transcript rows. Their references name Marmot app event ids
in the same group. A chat target means an original kind-9 event, not an edit, system event, or stream-start event.

For kinds 1984, 1985, and 4891, an event that fails any stated shape, bound, type, or authorization rule MUST have no
moderation effect. Receivers MUST NOT partially apply a malformed event. Unknown dependencies remain unresolved as
specified below; they are not evidence of invalidity. Referenced ids and account authors MUST use lowercase 64-hex
encoding. This section uses the following fixed Unicode White_Space set: U+0009–U+000D, U+0020, U+0085, U+00A0,
U+1680, U+2000–U+200A, U+2028–U+2029, U+202F, U+205F, and U+3000.

### Reports (kind 1984)

A report uses [NIP-56](https://github.com/nostr-protocol/nips/blob/master/56.md), with one reported chat message:

- Exactly one `e` tag: `["e", original_message_id, report_type]`.
- Exactly one `p` tag naming the original message's authenticated account author.
- At most one `revision` tag: `["revision", revision_event_id]`. Producers MUST include this tag; receivers MUST
  normalize its absence to the original message id before deduplication. A revision is either the original kind-9
  event or a valid kind-1009 edit of it by the same author.
- `content` is the reporter's UTF-8 explanation, at most 4096 bytes, preserved without Unicode normalization.
  It MAY be empty except for report type `other`, which MUST contain at least one character outside White_Space.

Supported report types are `nudity`, `malware`, `profanity`, `illegal`, `spam`, `impersonation`, and `other`.
Unknown auxiliary tags do not change report semantics.

A logical report is keyed by group, original message, normalized revision id, and reporting account. Receivers MUST
count duplicate events once and select their displayed details by lower `created_at`, with lexicographically lower
lowercase-hex `id` breaking a tie. Retrying MUST NOT create a new logical report. A valid dismissal referencing any
duplicate resolves that logical report, including duplicates received later. Unknown targets and revisions MUST remain
unresolved until their authenticated dependencies are available. A mismatched `p` author, cross-group target,
unrelated edit, or non-chat target MUST have no moderation effect.

Example kind-specific fields (the common six-field app-event encoding still applies; angle-bracket values below are
placeholders for canonical ids and account keys):

```json
{"kind":1984,"tags":[["e","<original message id>","spam"],["p","<message author>"],["revision","<original or edit id>"]],"content":"Repeated unsolicited advertising"}
```

### Dismissal labels (kind 1985)

A shared admin dismissal uses [NIP-32](https://github.com/nostr-protocol/nips/blob/master/32.md) to label report
**events**, leaving the reported message available. It MUST carry exactly one `L` tag naming `marmot.report-review.v1`
and exactly one `l` tag with label `dismissed` and that namespace. Between 1 and 100 `e` tags name report event ids.
Producers MUST deduplicate ids and order them lexicographically; repeated references have no additional effect.
Producers MUST emit empty `content`; received explanatory content does not change the label's meaning. Other tags are
ignored. Only an active admin in the authenticated source state can authorize dismissal, as defined below.

```json
{"kind":1985,"tags":[["L","marmot.report-review.v1"],["l","dismissed","marmot.report-review.v1"],["e","<reviewed report id>"]],"content":""}
```

Dismissal affects only the logical reports named by its references. Unless the message has been removed, another
account's new report or a report about another revision remains pending. Multiple valid dismissals commute; receivers
MUST select displayed review attribution by lower `created_at`, with lexicographically lower lowercase-hex `id`
breaking a tie. Unknown report references MUST remain unresolved. Editing a reported message does not dismiss its
reports. This version defines no report withdrawal, dismissal undo, or restoration action.

### Admin removal (kind 4891)

Kind 4891 is a Marmot-specific admin removal. Exactly one `e` tag names the original chat message id; the action
removes that message and all its revisions. Its content MUST be a JSON object with exactly `v` and `action`, whose
values are the integer `1` and `"remove"`. Duplicate JSON keys are invalid. Other tags are ignored. Only an active
admin in the authenticated source state can authorize this event, including when its sender is also the target author.
Admins MAY remove unreported content. Unknown targets MUST remain unresolved; cross-group or non-chat targets MUST
have no moderation effect.

```json
{"kind":4891,"tags":[["e","<original message id>"]],"content":"{\"v\":1,\"action\":\"remove\"}"}
```

An effective removal MUST close pending review for every logical report about that message or any of its revisions.
Reports received later MAY remain as historical records but MUST NOT reopen review or increase pending counts.
Removal takes precedence over dismissal and later edits. Ordinary timeline, reply, search, attachment, and report-review
surfaces MUST NOT reveal the removed message's retained content. [Author deletion](#author-deletion-kind-5) remains a
separate path and does not grant non-admins kind-4891 authority.

### Source-state authority and eligibility

Receivers MUST authorize an admin action against the [active admins](../app-components/admin-policy-v1.md#active-admins)
of the authenticated MLS source state that carried it, not the latest admin list or its wall-clock timestamp. Source
state identifies the authenticated branch and epoch, including its member leaves, admin policy, and group profile.
Clients MUST retain or reconstruct the evidence needed to reproduce this decision after restart. Unavailable evidence
MUST leave authority unresolved; clients MUST NOT substitute the latest policy or freeze a denial. A later demotion
does not revoke source-state authorization; this does not prove the real-world time the action was created.

Kinds 1984, 1985, and 4891 MUST have no moderation effect when their source state has exactly two distinct current member
accounts and the [group profile](../app-components/group-profile-v1.md) is absent or its `name` is empty or consists only
of the White_Space characters defined above. Count distinct MLS-authenticated account identities, not member leaves;
an account with multiple devices counts once. Do not normalize the profile bytes. This eligibility is evaluated per
source state and can change as membership or the name changes. In eligible states, every member MAY report; only active
admins MAY dismiss reports or remove content, including their own content. Kind-5 author deletion is unaffected.

[Convergence](../protocol-core/convergence.md#applying-the-selected-branch) owns app-payload delivery and invalidation.
Clients MUST derive moderation effects from delivered app payloads and their authenticated dependencies. When
convergence withdraws a payload that decrypts only on a losing branch, clients MUST withdraw the effects that depend
on it and recompute from the remaining delivered payloads. A branch change MUST NOT leave a withdrawn removal or
dismissal in effect.

### Retention and compatibility

Reporting MUST NOT extend the target's content-retention lifetime. Report references MUST NOT embed copies of target
text or attachment bytes. Review surfaces MUST show an unavailable-content placeholder after deletion or expiry,
without revealing retained target content. Reporter identity, category, explanation, and review attribution MAY remain
visible while those records are retained; report explanations obey applicable retention. Clients MUST retain only the
minimal reference and resolution evidence needed to keep expired or removed content from returning and duplicates
from reopening resolved reports.

Clients with the same delivered app payloads and authenticated dependencies MUST derive the same report counts and
outcomes regardless of delivery order. Personal blocking MUST NOT change shared validity. Report and review events
MUST NOT increment chat unread counts.

These are optional application semantics. Older clients may ignore dismissal labels or removal events;
this feature cannot guarantee removal on incompatible clients or erase copies already saved outside the application.
On upgrade, a client MUST preserve previously honored deletion tombstones even if their historical authorization
evidence is unavailable. This compatibility rule does not authorize newly received deletion or removal events.
