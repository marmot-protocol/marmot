# Agent text streams over QUIC

Status: retired.

> **Retired.** Clients no longer send or watch live previews of agent text. A client MUST NOT send a kind `1200` stream
> start or a QUIC preview record, and MUST NOT connect to the endpoint candidates in a stream start it receives. It
> treats a kind `9` message that carries stream tags as an ordinary chat message. Many existing groups still require
> `marmot.group.agent-text-stream.quic.v1`; what clients keep doing for those groups is in the component's
> [Retirement](../app-components/agent-text-stream-quic-v1.md#retirement) section, which overrides this document. The rest of this document records the retired design.
> Implementations do not implement it. Kinds `1201` and `1202` are not retired; the
> [registry](../foundation/registries.md) keeps them reserved for agent events.

This feature adds live text previews for agent output in an existing Marmot group. MLS remains the membership,
authentication, epoch, and durable-message layer. QUIC carries only transient preview records. Live preview delivery is a
progressive enhancement: every stream finishes as a normal durable Marmot message that clients can display without
opening a QUIC connection.

## Invariant

A text preview stream has two durable MLS app payloads:

- a hidden kind `1200` start payload that authorizes one live preview stream;
- a normal final payload, kind `9` for text, that becomes group history.

QUIC records are renderable only when they match the MLS start payload. They are not durable group history. A client that
stores history, indexes content, sends notifications, exports data, or runs automation uses the final MLS payload.
Clients that do not implement raw QUIC still participate in the group by accepting the MLS start/final message semantics,
ignoring the live preview route, and rendering the final kind `9` message.

Agent activity, operation progress, and group lifecycle rows are not chat text and are not preview text. They use separate
durable inner app-event kinds when they need to survive reload or sync:

- kind `1201`: agent activity/status;
- kind `1202`: agent operation event.

Kind `1210` group system events are a separate, core concept defined in
[foundation application payloads](../foundation/application-messages.md#group-system-events-kind-1210). A connector MAY
emit them, but this feature does not own or define them.

All of these are inner Marmot app-event kinds carried inside encrypted group messages. They do not change the outer
Nostr group transport kind.

## Registered surfaces

- App component: [`marmot.group.agent-text-stream.quic.v1`](../app-components/agent-text-stream-quic-v1.md), component
  id `0x8006`
- Start app-event kind: `1200`
- Agent activity app-event kind: `1201`
- Agent operation app-event kind: `1202`
- First stream type: `text`
- First final kind: `9`
- Exporter: `MLS-Exporter("marmot", "agent-text-stream-quic", 32)`

The app component carries group policy and capability requirements. The stream secret MUST be derivable more than once
in the same epoch, so v1 uses a registered MLS exporter label and then domain-separates each stream with the key context
below.

## Capabilities

KeyPackages advertise agent-stream roles with normal Marmot capabilities. Each role is an MLS extension-type capability
listed in the LeafNode capabilities; a member advertises a role by listing its extension type. The authoritative role,
capability-name, extension-type, and role-mask mapping is in
[../app-components/agent-text-stream-quic-v1.md](../app-components/agent-text-stream-quic-v1.md) ("State"); the ids are
registered in [../foundation/registries.md](../foundation/registries.md).

The `receive` role is the baseline agent-stream compatibility role. A `receive` member understands the component, accepts
kind `1200` start payloads and final kind `9` stream anchors, and can safely ignore the live QUIC route while waiting for
the durable final message. `receive` does not require implementing the raw QUIC data plane or rendering live deltas.

The `send` role means the member can originate raw QUIC preview records for this profile and publish the matching
start/final MLS messages. The `fanout` role means the member or helper can forward stream records for others, for example
through a broker.

Groups that are agent-stream-ready require `marmot.group.agent-text-stream.quic.v1` in GroupContext `app_components`.
A member that cannot understand the component and the required role capabilities cannot join the group. Application
profiles MAY make groups agent-stream-ready by default to avoid exposing a user-facing "agent enabled" setting; that
default still treats live QUIC preview rendering as progressive enhancement.

For the first user-to-agent profile:

- every member supports `receive`, including clients that only display the final MLS message;
- the agent member supports `send` when it emits raw QUIC preview records;
- `fanout` is optional and MAY be advertised by a member or broker helper.

## Flow

1. A user sends a prompt as an ordinary Marmot app payload.
2. The agent publishes a hidden kind `1200` start payload through MLS.
3. Online preview-capable receivers watch the start payload's `quic://` candidates. Other receivers ignore the route.
4. The agent sends encrypted, ordered preview records over QUIC.
5. Preview-capable receivers render text deltas only as provisional preview text, visibly distinct from confirmed
   durable content, and MAY surface stream status.
6. The agent publishes the final kind `9` message through MLS.
7. Clients that rendered a preview replace or verify it with the final message. Clients that skipped the preview display
   the final message as normal chat history.

Offline members and non-QUIC members miss the live preview and read the final message when they sync.

An agent turn SHOULD have at most one active Marmot text preview that represents the eventual kind `9` answer. Cursor-only
frames, gateway notices, pre-operation chatter, and operation progress SHOULD NOT open their own kind `1200` starts. If
the sender started a preview and later determines that the text was not part of the final answer, it SHOULD abort that
preview and MAY publish an application-defined durable activity event instead.

## Start payload

The start payload is an unsigned Nostr-shaped Marmot app event delivered through MLS:

```text
kind: 1200
tags:
  ["stream", stream_id_hex]
  ["stream-type", "text"]
  ["final-kind", "9"]
  ["route", "quic"]
  ["parent", prompt_event_id]
  ["broker", broker_candidate]       // zero or more, one per endpoint candidate
content:
  canonical JSON for metadata that does not fit a tag
```

The `stream`, `stream-type`, and `final-kind` tags are owned by this feature. The `parent` tag is optional. The `route`
tag selects the transport binding (`quic` for the raw QUIC binding). The candidate tags - the `route` value and each
`["broker", broker_candidate]` endpoint - are owned by that transport binding: their byte format and discovery rules are
defined in [../transports/quic.md](../transports/quic.md), where each `broker_candidate` is a `quic://host:port`
endpoint. A start payload MAY carry more than one `broker` tag (one per candidate). A client that implements `receive`
but not raw QUIC MAY ignore the route and candidate tags.

`stream_id_hex` is lowercase hex for 32 random bytes generated by the sender. `start_event_id` is the 32-byte Marmot app
event `id` of this kind `1200` payload (see
[../foundation/application-messages.md](../foundation/application-messages.md), "Encoding"), not the enclosing MLS
message id or an outer transport event id. It is the durable stream anchor included in the key context and transcript
hash.

For `stream-type=text`, `final-kind` MUST be `9`. Receivers MUST ignore a final payload whose kind does not match the
start payload's `final-kind`.

## QUIC records

Each live update is a length-delimited encrypted record:

```text
AgentTextStreamRecordV1 {
  uint8  version = 1;
  opaque stream_id<1..64>;
  uint64 seq;
  uint8  record_type;
  uint8  flags;
  opaque ciphertext<0..2^16-1>;
}
```

`stream_id`, `ciphertext`, and the other `opaque name<min..max>` fields use the Marmot binary profile's QUIC
variable-length length prefix ([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)); `version`,
`seq`, `record_type`, and `flags` are fixed-width big-endian integers. The record's `stream_id<1..64>` bound is the
general envelope limit; the first text profile uses exactly 32 random bytes (see "Start payload"), and the key context
binds that profile length as fixed `stream_id[32]` bytes. A v1 receiver MUST reject a record whose `stream_id` is not the
32-byte value of the stream it is rendering.

`ciphertext` is the AEAD output for one plaintext frame: `ciphertext_len = plaintext_len + 16`, the plaintext frame
plus the 16-byte ChaCha20-Poly1305 tag. The component policy bound on `max_plaintext_frame_len`
([../app-components/agent-text-stream-quic-v1.md](../app-components/agent-text-stream-quic-v1.md)) keeps a
maximum-length frame's ciphertext within the `ciphertext<0..2^16-1>` field bound.

`flags` is reserved in v1: no bit is defined. A sender MUST set `flags` to `0x00`. `flags` is bound into the record AEAD
AAD, so its value is authenticated end to end. A v1 receiver MUST NOT ascribe meaning to any `flags` bit; a future
profile that defines flag bits will negotiate through a new capability or record version before relying on them.

`seq` starts at `1` and increases by one for each record in the stream. A receiver accepts each `seq` value at most
once and never folds a record into the preview or transcript out of order; the transport binding
([../transports/quic.md](../transports/quic.md)) defines how duplicates, transport-level replay, and gaps are handled.

One kind `1200` start payload defines at most one cryptographic publisher session. A publisher MUST NOT restart `seq`
or reuse any prior `seq` value for the same `AgentTextStreamKeyContextV1`, including after reconnect, retry, process
restart, or daemon resume. A publisher MAY resume only when it has retained the next unused sequence value. If it cannot
prove which sequence value is next, it MUST stop publishing preview records for that start payload and rely on the
authoritative final kind `9` message. A later preview attempt requires a new kind `1200` start payload with a freshly
generated `stream_id`, which produces a new `start_event_id` and key context.

The first text profile defines these plaintext frame types:

```text
0x01 TextDelta
0x02 ProgressDelta
0x03 Status
0x04 Checkpoint
0x05 Abort
0x06 FinalNotice
```

`TextDelta` records carry UTF-8 text fragments. Receivers concatenate `TextDelta` plaintext frames, in sequence order, to
build the provisional preview text. Senders SHOULD batch output instead of sending one record per token. Only
`TextDelta` appends to the provisional answer text; a supported `Checkpoint` may replace it as defined below.

`ProgressDelta` records carry UTF-8 operation-progress text or JSON. Receivers MAY display this as live non-chat agent
progress chrome. Receivers MUST NOT append `ProgressDelta` plaintext to preview text, final message content,
notifications, indexes, or automation input. An application MAY publish separate application-defined durable operation
history.

`Status` records carry UTF-8 provisional state labels such as `thinking`. Receivers MAY display, replace, or ignore the
latest status for local UI. Receivers MUST NOT append `Status` plaintext to preview text, final message content,
notifications, indexes, or automation input.

`Checkpoint` records carry a UTF-8 full preview snapshot. Receivers that support checkpoints replace the provisional
preview text with the checkpoint plaintext, then continue applying later `TextDelta` records. Receivers that do not
support checkpoints MAY mark the preview unverifiable and wait for the final kind `9`.

`Abort` records end the live preview without producing durable chat text. Receivers remove or mark the preview as
cancelled and wait for later durable events.

`FinalNotice` records announce that the sender is about to publish the durable final. They are advisory; the final kind
`9` remains authoritative.

Every record type consumes a `seq` value and contributes to the transcript. This includes `Status` records even when a
receiver ignores them in UI.

## Typed durable agent rows

Kinds `1201` and `1202` are reserved for possible experimental agent activity and operation rows. This protocol version
does not define a JSON field schema, ordering model, storage rule, presentation contract, or conformance requirement for
either kind. Applications that experiment with those values do so under the normal unknown-app-event rules. Neither
kind is part of the interoperable QUIC preview flow, a kind `9` chat body, or the authoritative final answer.

Kind `1210` group system events (durable membership/admin/profile rows) are defined in
[foundation application payloads](../foundation/application-messages.md#group-system-events-kind-1210), not here.

## Key derivation

The stream secret is derived from the MLS epoch in which the start payload is valid:

```text
stream_secret = MLS-Exporter("marmot", "agent-text-stream-quic", 32)
key_context   = AgentTextStreamKeyContextV1

record_key = HKDF-Expand-Label(stream_secret, "record key", key_context, 32)
nonce_base = HKDF-Expand-Label(stream_secret, "record nonce", key_context, 12)
```

HKDF is `HKDF-SHA256`, independent of the group's MLS ciphersuite. `stream_secret` is used directly as the HKDF PRK —
Expand only, with no Extract step and no salt. For this feature, `HKDF-Expand-Label(secret, label, context, L)` means
HKDF-Expand with `info = len(label) || label || context`, where `len(label)` is the Marmot binary profile's QUIC
variable-length length prefix ([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)); this is the
TLS/MLS label-and-context pattern specialized to Marmot's length prefix. The output length is 32 bytes for `record_key`
and 12 bytes for `nonce_base`.

The exporter label/context pair is registered for agent text stream QUIC record crypto only. `stream_secret` is reusable
inside the epoch. Implementations MAY derive it more than once for send, watch, retry, or daemon resume paths. Per-stream
keys MUST be derived through `AgentTextStreamKeyContextV1`; implementations MUST NOT use `stream_secret` directly as an
AEAD key. Re-deriving the same per-stream key and nonce base does not create a new publisher session and MUST NOT reset
the record sequence.

`AgentTextStreamKeyContextV1` uses Marmot canonical encoding:

```text
struct {
  opaque version<1..255>;        // "v1"
  opaque group_id<1..1024>;
  opaque stream_id[32];
  uint64 mls_epoch;
  opaque sender_id[32];
  opaque start_event_id[32];
} AgentTextStreamKeyContextV1;
```

`group_id` is the MLS group id bytes, not the Nostr routing id (`nostr_group_id`). `sender_id` is the sender's 32-byte
Marmot account identity — the same bytes as the MLS `BasicCredential` identity, the raw x-only public key
([../foundation/identity.md](../foundation/identity.md)). The `"v1"` in `version` is a text domain separator and
appears only inside this derivation context; wire structures carry their version as a fixed-width integer
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)).

The AEAD profile is ChaCha20-Poly1305:

```text
nonce = nonce_base XOR uint96_be(seq)
aad   = AgentTextStreamRecordAadV1
ct    = AEAD_Encrypt(record_key, nonce, aad, plaintext_frame)

struct {
  uint8  version = 1;
  opaque group_id_hash[32];
  opaque stream_id[32];
  uint64 mls_epoch;
  opaque sender_id[32];
  uint64 seq;
  uint8  record_type;
  uint8  flags;
} AgentTextStreamRecordAadV1;
```

The AAD is the canonical encoding of `AgentTextStreamRecordAadV1` and binds records to the group, sender, epoch, stream
id, sequence number, type, and flags. The raw group id is not sent on the wire; `group_id_hash` is `SHA-256(group_id)`,
the 32-byte digest of the raw MLS group id. `version` is the record wire version — the single byte `0x01`, never the
`"v1"` key-context text bytes. The `stream_id` and `sender_id` fields are fixed 32-byte values in this profile.

## Preview authenticity

The stream secret is group shared. It hides plaintext from a broker or passive outsider, but any current member can derive
the same record key.

For v1, preview records are provisional. The final MLS app payload is authoritative because MLS authenticates it as an
application message from the sender. A client that renders preview records MUST distinguish them from confirmed durable
content until the final payload authenticates and anchors them. Applications MUST NOT treat unsigned preview records as
durable instructions or automation input unless they explicitly accept that risk.

## Transcript hash

Receivers track a transcript hash over plaintext frames:

```text
H_0 = SHA-256("marmot agent text stream transcript v1" ||
              len(stream_id) || stream_id ||
              len(start_event_id) || start_event_id)
H_n = SHA-256(H_{n-1} || seq || record_type || plaintext_frame)
```

`hash` is `SHA-256`, so each `H_n` is 32 bytes. The fixed label `"marmot agent text stream transcript v1"` is its raw
ASCII bytes with no length prefix. Every `len(...)` in this construction is the Marmot binary profile's QUIC
variable-length integer (the same encoding the QUIC record uses for `stream_id`), never a fixed-width integer: a
32-byte id's length prefix is the single byte `0x20`. `seq` is `uint64` big-endian and `record_type` is `uint8`, as in
the record. `plaintext_frame` is the decrypted frame bytes with no extra prefix beyond what `H_n` already concatenates.

The final message carries `H_final`. `H_final` covers every accepted transcript record, including records a receiver did
not render as text. A receiver that saw the live preview compares its local hash to the final message and marks the
preview unverified on mismatch.

## Final message

The first text profile finishes with a normal kind `9` Marmot app event:

```text
kind: 9
tags:
  ["stream", stream_id_hex]
  ["stream-start", start_event_id]
  ["stream-hash", transcript_hash_hex]
  ["stream-chunks", chunk_count]
content:
  final text
```

The final message `stream` tag MUST match the start payload's `stream` tag. `stream-start` is the lowercase hex
`start_event_id` defined above: the Marmot app event `id` of the kind `1200` start payload. `stream-hash` is the
lowercase hex 32-byte transcript hash. `stream-chunks` is the unsigned decimal count of all transcript records,
including `Status` records. The content is the final text only;
`Status` plaintext MUST NOT appear in the final message content unless the agent deliberately includes similar text in
the final answer.

Clients that rendered a preview SHOULD replace the preview row with the final message when `stream_id` matches. Clients
that did not render a preview MUST treat the final kind `9` payload as normal chat text and MAY ignore the stream tags
for display. Implementations MAY keep preview chunks as local diagnostic state.

## Epoch behavior

A v1 stream is pinned to one MLS epoch. If an accepted Commit changes the sender's current epoch while a stream is
active, the sender closes the old stream. The sender MAY publish a new start payload in the new epoch and link it to the
previous stream in local UI or a future extension.

If convergence later invalidates the kind `1200` start payload because its MLS application message existed only on a
losing branch, the sender and every receiver MUST stop that live preview and withdraw its provisional text. Its records,
checkpoints, and transcript hash remain bound to the invalidated start anchor and MUST NOT be reused for another start
payload or treated as authenticated by a later final message.

This keeps stream access aligned with MLS membership changes.

## Transport binding boundary

This feature owns start payload semantics, record encryption, preview status, final-message anchoring, transcript hashes,
and epoch behavior.

The raw QUIC transport binding, [../transports/quic.md](../transports/quic.md), owns:

- endpoint candidate formats (the `route` value and `broker` candidate URLs);
- direct path and broker-relayed discovery;
- broker authentication and connection setup;
- reconnect and short-replay policy;
- transport-visible diagnostics;
- wire framing below `AgentTextStreamRecordV1`.

Broker authentication is only for broker access. It does not make preview records authoritative and does not replace MLS
membership.

## Non-goals

- MLS is not a byte-stream protocol.
- QUIC records are not Nostr events.
- Preview chunks are not durable group history.
- QUIC TLS is not Marmot end-to-end encryption.
- Images and files use encrypted media references unless a later media-streaming profile says otherwise.
