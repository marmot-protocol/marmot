# Structured interaction messages v1

Status: draft; proposed decisions for [mdk#858](https://github.com/marmot-protocol/mdk/issues/858).
This document does not authorize deployment before that design is accepted.

This optional app-payload profile defines requests, answers, and terminal receipts for approvals and single-select
questions. [Structured interactions](../features/structured-interactions.md) owns authorization, execution, and client
behavior. This document owns their bytes, including text fallback. No MLS component, new event kind, transport
extension, or agent-runtime identifier is introduced.

## Profile and dispatch

All three records are ordinary encrypted kind-`9` [Marmot app events](./application-messages.md). The shared envelope,
event-id calculation, and MLS sender binding apply unchanged. An event id here always names the inner app event,
never an MLS message or transport envelope. References are scoped to the same group instance.

An interaction attempt is any app event with a tag whose first string starts with `marmot-interaction` or
`marmot-option`, or whose content starts with the literal ASCII `marmot-answer`. Feature-aware agent connectors MUST
intercept these attempts before ordinary conversation, model, or slash-command dispatch, even when the kind, version,
shape, reference, or authorization is invalid. Unknown or unowned attempts MUST be consumed without creating executable
state or fetching their references. These rules do not require a client to reject an otherwise-valid MLS message.

A structured record MUST have exactly the tags listed below, in the listed order. Every tag is an array of strings
with exactly the listed arity. The first tag is the single `marmot-interaction` descriptor. The second is the single
reference. Only requests have subsequent `marmot-option` tags. Extra, duplicate, reordered, unknown-version, or
unknown-type data invalidates the entire interaction record, not just one field. A malformed structured record MUST
NOT be retried as a text fallback or ordinary agent input. Clients render invalid or unsupported records as inert text,
without controls. Unknown data need not be interpreted or retained by this feature.

Every reference has exactly this shape:

```text
["e", referenced_event_id, "", "reply"]
```

No relay hint or tag-asserted author supplies authority. The authenticated event author is the request-author account
for requests and resolutions, and the responder account for responses. Clients MUST NOT infer these roles from labels,
prose, `p` tags, or timeline position.

## Bounds and text

The encoding is the string-array representation inside the existing Nostr-shaped JSON envelope, rather than the Marmot
binary profile. Event hashing uses [canonical Nostr serialization](./canonical-encoding.md#nostr-shaped-values).
Strings are compared as raw UTF-8 bytes without trimming, Unicode normalization, or case folding. Bounds apply after
JSON decoding, before correlation, owner allocation, or resolver dispatch.

| Value | Required encoding or bound |
| --- | --- |
| Event id or account | Exactly 64 lowercase hexadecimal characters; accounts must decode to valid x-only keys. |
| `prompt_id`, `response_id`, option id | 1–64 ASCII bytes matching `[A-Za-z0-9_-]+`. |
| Fresh prompt or response id | At least 128 bits of cryptographic randomness; never reused by its author. Fixed fixture ids are synthetic. |
| Timestamp | Integer seconds since Unix epoch, `0..9007199254740991`; descriptor timestamps are decimal strings without leading zeroes except `0`. |
| Request lifetime | `1 <= expires_at - created_at <= 900` seconds. Owner default: 300 seconds. |
| Options | 1–4 for choice; exactly two for approval. |
| Option label | 1–128 UTF-8 bytes. |
| Readable `content` | 1–4096 UTF-8 bytes for each record. |
| Custom-text value | 1–2048 UTF-8 bytes. |
| Extension data | At most 8192 bytes: sum of UTF-8 byte lengths of every string in every tag, including names and reference. |
| Structured tags | At most six; at most eight strings per tag. |

All profile strings MUST contain only Unicode scalar values. Labels, content, and custom text MUST NOT contain
U+0000–U+001F, U+007F–U+009F, U+061C, U+200E–U+200F, U+202A–U+202E, or U+2066–U+2069, except that content and custom
text MAY contain LF (U+000A). Labels MUST NOT contain LF. Receivers MUST reject forbidden characters, not repair them.
These restrictions reject explicit bidi formatting controls, not ordinary right-to-left language text. Clients SHOULD
use isolated plain-text controls for labels and answers and MUST NOT execute embedded commands or URLs.

The wire expiry is fixed at creation. The owner MUST use the same deadline for its local authority and MUST NOT extend
it from response timestamps, edits, receipt delivery, or client clocks. The owner's monotonic deadline evaluation is
specified in the [feature lifecycle](../features/structured-interactions.md).

## Request

The descriptor and reference are:

```text
["marmot-interaction", "1", "request", prompt_id, responder_account, request_type, expires_at, custom_text]
["e", originating_input_event_id, "", "reply"]
["marmot-option", option_id, label]
```

The last line repeats once per option. `request_type` is exactly `approval` or `choice`. `custom_text` is exactly `0`
or `1`. The original request event's authenticated author supplies the request-author identity. The originating input
MUST be an authenticated delivered input from the named responder in the same group; an unproven origin produces only
inert ordinary text, not an executable request.

For `approval`, the option tags MUST be exactly these, in this order, and `custom_text` MUST be `0`:

```json
[["marmot-option","once","Allow once"],["marmot-option","deny","Deny"]]
```

`once` authorizes only the concrete pending action bound to this prompt. `deny` denies that action. Neither option
creates a session-wide or persistent capability. An adapter unable to enforce that scope MUST NOT emit an approval.
The complete action and relevant resource MUST be visible in the readable body before the user answers.

For `choice`, option ids MUST be unique and in ascending ASCII byte order. Labels are display data and MUST NOT be
passed to the resolver in place of stored option ids. Choice labels MUST also be byte-distinct; visually similar labels
remain a presentation risk. Custom text is permitted only when `custom_text` is `1` and the feature's effective-DM
requirements hold. A choice never grants permission to execute an action that requires a separate approval.

`content` MUST state the entire question or approval scope, the options, the expiry, and instructions for the exact text
fallback. A producer MUST NOT emit a structured request if that complete body exceeds the bound. It can shorten the
question before minting a request, or send inert text. A request cannot contain its own event id without a circular
hash dependency: the instructions tell the user to copy the request's inner id from message details. A fallback client
that cannot expose that id cannot answer safely and leaves the request unanswered. Bare numbered replies do not work.

## Response

```text
["marmot-interaction", "1", "response", prompt_id, response_id, selection_type, value]
["e", request_event_id, "", "reply"]
```

`selection_type` is exactly `option` or `text`. For `option`, `value` MUST equal one stored option id on the referenced
immutable request. For `text`, `value` is the bounded custom text and MUST satisfy that request's custom-text policy.
Exactly one selection is carried. There is no denial-reason field. `content` is readable fallback only and MUST NOT
change the descriptor's meaning. A feature-aware client renders the authenticated selection from the original request
and response descriptor, not contradictory prose.

Retransmission MUST reuse the same event bytes. Reuse of a `response_id` with different event bytes under the same
request is an invalid attempt. A second response id does not provide a second chance after claim. No response event,
including a response authored by the named account, is a receipt or proof of resolver acceptance.

## Resolution

```text
["marmot-interaction", "1", "resolution", prompt_id, state, accepted_response_event_id]
["e", request_event_id, "", "reply"]
```

`state` is exactly `resolved`, `expired`, `cancelled`, `superseded`, or `indeterminate`. For `resolved`, the last field
MUST be a canonical event id identifying the accepted structured or text-fallback response to this exact request.
For every other state it MUST be the empty string. Runtime-local handles, resolver-operation ids, action arguments,
custom answers, and denial reasons MUST NOT appear in receipt tags or content. `content` MUST be a readable description
of the state, without quoting those values.

Only a resolution from the original request-author account has receipt meaning. A receipt MUST match both request id
and prompt id in the same group. A missing request or accepted response does not justify recursive fetching or control
activation; clients may display an unresolved, non-actionable observation within their bounded cache policy.

A `cancelled` or `superseded` resolution from the request author can also ask its owner to close an open request. It
passes the same deadline and serialization rules as other candidates. Other received resolution states are observations
only. No received receipt creates ownership, claims a response, invokes a resolver, or reopens a terminal request.
A superseded receipt does not authorize a replacement: a replacement is a fresh request with a fresh prompt id and the
full creation checks. No replacement chain is followed automatically.

## Correlated text fallback

Fallback is a standard kind-`9` reply without any reserved interaction or option tag. It MUST carry exactly one marked
reply tag `['e', request_event_id, '', 'reply']`. It MAY additionally carry one
`['e', root_event_id, '', 'root']` tag before that reply tag, with a distinct canonical root id. No other tags are
permitted in this baseline. The root is an inert thread hint and never changes the request being answered.

Its content MUST match exactly one of these byte grammars:

```text
marmot-answer 1 REQUEST_ID PROMPT_ID RESPONSE_ID option OPTION_ID
marmot-answer 1 REQUEST_ID PROMPT_ID RESPONSE_ID text\nCUSTOM_TEXT
```

Uppercase names denote fields, not literal strings. `\n` denotes one LF byte. Other separators are single ASCII spaces.
The ids and custom text use the bounds above. The whole body still has the 4096-byte content bound. For the option form,
no leading or trailing whitespace, extra field, or newline is allowed. For the text form, every byte after the first LF
belongs to custom text, including a trailing LF if supplied; custom text cannot be empty. No escaping or normalization
is performed. The content's request id MUST equal the reply tag's request id. A response id is mandatory for either
form, and the fallback event's authenticated author is still the responder.

The owner MUST process a valid fallback through exactly the structured response's authorization and one-shot claim
path. A reply to a receipt, bare option label, `yes`, `no`, numbered answer, `/approve`, or ambiguous prose MUST NOT be
inferred as a decision. A malformed reserved-prefix attempt is consumed, not handed to the model. Ordinary uncorrelated
conversation remains conversation and never resolves a prompt.

## Author withdrawal

For this optional profile, an authenticated kind-`1009` edit with exactly `[["e", target_event_id]]` uses the existing
[edit rules](./application-messages.md#message-edits-kind-1009). An inner kind-`5` withdrawal uses exactly the same single
`e` tag and an empty `content`. These are not outer transport deletion requests. The target MUST be a known request or
response in this group. Its original authenticated author MUST equal the mutation's authenticated author.

A request-author mutation cancels only an open request. It never replaces stored request semantics. A response-author
mutation known before claim makes that response ineligible; it does not cancel the request. After claim, neither
mutation undoes the decision. An edit or withdrawal of a resolution has presentation effect only and cannot reopen the
prompt. Third-party edits, author claims in tags, admin deletion, and generic timeline hiding have no execution effect.
Unknown targets MUST NOT allocate execution records or trigger fetches. Mutation content is never agent input merely
because its target carried a prompt. Structured records remain semantically immutable even where the ordinary timeline
overlays an edit; clients MUST disable controls rather than present edited prose with original executable semantics.

## Conformance fixtures

[structured-interactions-v1.json](./fixtures/structured-interactions-v1.json) is the normative synthetic input corpus for
this draft. Every implementation of this feature MUST exercise its applicable wire, authorization, and lifecycle cases.
It contains no production secrets and supplies event-level evidence, not raw MLS ciphertext or proof of MLS validation.
A test driver establishes the stated authenticated context before applying app semantics.

- `events` maps stable fixture names to complete unsigned app events. Each `id` is computed from the exact canonical
  Nostr preimage. The original input and golden requests, responses, fallback, and receipts are included.
- `raw_cases` carries malformed payload bytes as lowercase `payload_utf8_hex`. Hex-decode these bytes before strict
  UTF-8 and JSON string decoding. `envelope_reject` requires rejection before feature dispatch; these inputs have no
  valid canonical event-id claim. Keeping them outside `events` lets scalar-string decoders load the corpus itself.
- `wire_cases` names an event and its expected parser result: `request`, `response`, `resolution`, `fallback`, or
  `inert`. A syntactically valid record may still fail authorization. A hostile event still has a correct event id
  unless its expected result is `envelope_reject`. Parsing here checks field syntax and bounds; request-relative
  selection, authorship, and execution eligibility are checked by scenarios, not inferred from a parser result.
- `scenarios` names its initial owner state and context, an ordered list of candidate actions, and expected final state,
  resolver-call count, and dispatch outcome. Actions are serialized owner-observed transitions, not claims that relay
  order chooses distributed state. Scenarios are independent; the defaults below reset before each one.

The default synthetic context is one owned, open approval in a Stable, Settled active group, authored by `agent`, with
`responder` as its only other distinct account. Its deadline is `1700000300`, effective backend time `1700000001`, the
origin and request are delivered, and the original adapter connection and runtime generation remain live. The request
id is `events.approval.id`. All event authors are authenticated to their `pubkey` unless a scenario says otherwise.
An `absent` initial state has no owner; `absent` is a fixture sentinel, not a prompt lifecycle state.
For `open`, setup first establishes a valid owner, then applies the context overrides as observations before actions.

| Context override | Meaning |
| --- | --- |
| `request` | Fixture name of the owned request; default `approval`. |
| `backend_time`, `last_effective_now` | Owner clock and persisted clamp; default `1700000001`. |
| `response_group: "other"` | Candidate response is authenticated in a different group, not the owner group. |
| `eligible_responder: false` | Owner observes removal of the named responder. |
| `runtime_generation: "other"` | Owner observes loss of its bound generation. |
| `origin_authenticated: false` | Previously established origin evidence is no longer available. |
| `third_account: true` | Current membership additionally contains `accounts.third`. |
| `membership_resolved: false` | Owner cannot establish current canonical membership. |
| `owned: false`, `history_import: true` | No owner exists; transcript import supplies no execution authority. |
| `group_choices_reviewed: true` | The group-choice use case has received the required nonsensitive-content review. |
| `known_responses` | Fixture names already delivered to the app but not yet offered to the owner's serialized claim path. |

Each action is one string from the table below, or exactly `{"event": NAME}` to deliver a named event into the owner's
candidate path, or `{"context": OBJECT}` to apply context observations before the next candidate. An event delivery
attempts claim immediately when eligible. Successfully claiming invokes the bound resolver once and waits for `ack`.
`claim_only` deliberately interrupts between the recoverable claim and invocation. Ordinary wire parsing of a response
does not itself claim it.

| Action | Meaning |
| --- | --- |
| `claim`, `deny` | Offer `events.allow` or `events.deny`, respectively. |
| `claim_only` | Validate `events.allow` and persist claim evidence without invoking yet. |
| `ack` | Recoverably record the runtime's acceptance for a currently claimed decision. |
| `ack_timeout` | Reach the owner's finite acknowledgement-wait ceiling without proven acceptance. |
| `crash_uncertain` | Restart after invocation may have occurred but no acknowledgement is recoverable. |
| `connection_loss`, `runtime_restart` | Lose the bound live adapter connection or generation. |
| `origin_withdrawn`, `request_withdrawn` | Convergence withdraws that delivered prerequisite. |
| `receipt_failure`, `receipt_retry` | Fail terminal receipt delivery, or retry its exact stored bytes once. |

Context invalidation is permanent for an open prompt. Deadline precedence still applies before terminalization.
`normal_dispatch: false` requires attempts to stay out of ordinary model and command input, including rejected ones.

`send_cases` starts with the named event composed in an effective DM for the named request. `encryption_accounts`
names accounts in the canonical state used for encryption; `settled` says whether that state is usable.
`observed_dm_invalidation` records whether the sender already saw its DM-only prerequisite fail, including a view that
later returned to two accounts. `expect_encrypt` is whether the queued event may now be encrypted and published.
All cases use active Stable group state; no case permits owner evidence to be discarded.

`client_cases` supplies named events in receive order to a feature-aware responder client at time `1700000001`, in the
default effective DM. No answer was submitted locally. All input fits its reorder cache. After consuming all events,
`expect.receipt` is the selected authenticated receipt's event id or null, `conflict` is the protocol-violation diagnostic,
and `controls_enabled` says whether the original request can still offer controls. Every case starts without prior
request knowledge. Unknown references stay non-actionable until already-arriving evidence supplies their context;
the driver MUST NOT invent a fetch or executable owner from that context.

The corpus does not certify cryptography, runtime compliance, implementation durability, or deployment safety.
