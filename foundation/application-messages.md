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
The following rules cover event-id references inside the common six-field app-event envelope; they do not define
address-based deletion via `a` tags. Each `e` tag begins `["e", event_id]`, with `event_id` in the canonical lowercase
64-hex form. Trailing elements are ignored. Receivers evaluate references independently: a missing or invalid id has
no effect for that reference, and repeated references have no additional effect. There is no kind-specific reference
count bound. The `content` string MAY be empty or explain the request without changing its effect; `k` tags and other
auxiliary tags do not select or authorize targets.

The `e` tags reference app event ids in the same group; to delete a whole chat message they name its original event.
A receiver MUST verify that its MLS-authenticated sender account equals each target's authenticated account author before honoring
that target's deletion. Admin status MUST NOT authorize kind-5 deletion of another account's content. Unknown targets
remain unresolved until their authorship can be verified; a known unauthorized or cross-group reference has no effect
without preventing other valid references from taking effect.

An honored chat-message deletion makes that message unavailable, including in report-review surfaces; later edits
MUST NOT restore its content. An effective admin removal takes precedence if both actions exist. This interpretation
uses the NIP-09 author-deletion path; it does not extend NIP-09 authorization or define a deletion-undo action.
These chat-specific rules do not restrict all kind-5 targets to chat messages. Other target kinds retain their owning
application semantics; this section does not define those kinds. Feature-owned kinds can restrict deletion effects, as
[group content moderation](../features/content-moderation.md#admin-removal-kind-4891) does for its control events.

Deletion suppresses retained content while its request remains delivered. If convergence withdraws the request,
clients MUST recompute its effects from the remaining delivered payloads. While withdrawal remains possible, clients
MUST preserve otherwise unexpired content needed for that recomputation; this does not extend content retention or
restore content still hidden by an independent deletion or admin removal.
The withdrawal window is governed by [candidate eligibility](../protocol-core/convergence.md#eligibility), including
the `max_rewind_commits` rollback horizon and any already-admitted unfinished convergence pass. Once no eligible
candidate can withdraw the request's source branch and no such pass remains, clients MAY erase the suppressed content
while retaining the deletion evidence. Content expiry can end availability earlier; this is not a new wall-clock
retention period.

## Content reports and shared review (v1)

The optional [group content moderation v1](../features/content-moderation.md) feature owns the interpretation of inner
reports (kind 1984), dismissal labels (kind 1985), and admin removals (kind 4891), including their validation,
authorization, review lifecycle, and retention. They use the common app-event envelope and sender authentication
specified in this document.
