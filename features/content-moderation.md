# Group content moderation v1

Status: draft.

Group members can report messages, and admins can dismiss reports or delete messages directly. These are independent
application events carried inside the group's existing encrypted messages. All members can receive them, including
reporter identity; they are not private submissions to admins. Report lists, grouping, counts, notifications, and review
UI are client choices.

The [application payload contract](../foundation/application-messages.md) already permits unsigned Nostr-shaped events
of these kinds and owns their encoding and sender authentication. This optional feature adds no group component or
transport change and places no restriction on group size or name.

## Reports (kind 1984)

Members report a message using [NIP-56](https://github.com/nostr-protocol/nips/blob/master/56.md). Its `e` tag references
the reported Marmot app event in the same group, and its `p` tag identifies that event's author. Report categories and
optional explanatory `content` follow NIP-56. Reporting alone does not delete the target.

Examples below show kind-specific fields; the common app-event envelope still applies, and angle-bracket values are
placeholders for canonical event ids and account keys.

```json
{"kind":1984,"tags":[["e","<message id>","spam"],["p","<message author>"]],"content":"Repeated unsolicited advertising"}
```

## Dismissal labels (kind 1985)

An admin dismisses a report using a [NIP-32](https://github.com/nostr-protocol/nips/blob/master/32.md) label event with
`["L", "marmot.report-review.v1"]`, `["l", "dismissed", "marmot.report-review.v1"]`, and one or more `e` tags referencing
kind-1984 report events in the same group. Its `content` may explain the dismissal, as in NIP-32.

Each referenced report is labeled dismissed by that admin. The label does not apply to other reports about the same
message, delete the reported message, or override an admin deletion. Clients choose how to display these labels.

```json
{"kind":1985,"tags":[["L","marmot.report-review.v1"],["l","dismissed","marmot.report-review.v1"],["e","<report id>"]],"content":""}
```

## Admin deletion (kind 4891)

Kind 4891 is a Marmot-specific request to delete a chat message. An admin MAY delete any member's message, including
their own, whether or not it has been reported.

- Exactly one `e` tag begins `["e", original_message_id]`, referencing an original kind-9 message in the same group.
- The id MUST be 64 lowercase hexadecimal characters. Trailing tag elements and other tags are ignored.
- `content` MUST be a JSON object with exactly `v` and `action`, whose values are the integer `1` and `"remove"`.
  Duplicate JSON keys are invalid.

A malformed or unauthorized deletion MUST have no deletion effect.

```json
{"kind":4891,"tags":[["e","<original message id>"]],"content":"{\"v\":1,\"action\":\"remove\"}"}
```

Clients supporting this feature MUST hide an authorized deletion's target, including its edits and attachments, in all
application views. This also applies when the target or an edit arrives after the deletion. A dismissal label cannot
make deleted content visible, regardless of which event arrives first. This version defines no admin undo event.

## Authorization and existing protocol rules

For an admin dismissal or deletion, receivers MUST verify that the MLS-authenticated sender was an
[active admin](../app-components/admin-policy-v1.md#active-admins) in the event's authenticated source-epoch state on its
branch. The current admin list and event timestamp do not determine that authority. A later demotion does not revoke
an already authorized action. Unproven authority MUST NOT be treated as permission to dismiss or delete.

References identify app events in the same group. Receivers apply dismissal labels to each referenced report
independently when the report and admin authority can be established; unrelated or cross-group references have no
moderation effect. Admin deletions apply only to the chat targets defined above.

[Convergence](../protocol-core/convergence.md#applying-the-selected-branch),
[durability](../protocol-core/durability.md#recoverable-protocol-facts), and
[message retention](../app-components/message-retention-v1.md) govern these events as other app payloads. If convergence
withdraws an admin event, clients MUST withdraw its effects. Deletion suppresses display; otherwise unexpired content
MUST remain available for recomputation while the deletion's branch can still be withdrawn under
[convergence eligibility](../protocol-core/convergence.md#eligibility). This does not extend content retention.

These application semantics cannot enforce deletion on clients that do not support them or erase copies saved outside
the application.
