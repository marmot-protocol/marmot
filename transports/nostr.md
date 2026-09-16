# Nostr transport

Status: adopted.

This document defines the first Marmot transport binding: MLS bytes carried over Nostr relays.

Nostr also appears in Marmot identity and app payloads. Those are separate foundation rules:

- Marmot account identity is a Nostr public key.
- Marmot app payloads use an unsigned Nostr event shape inside MLS.

This transport document covers only the outer relay-facing Nostr events used to publish, fetch, and route MLS bytes.

## Transport name and version

This binding is `marmot.transport.nostr`, version 1. There is no single on-wire version field; the binding is versioned
structurally through the event kinds, tag shapes, and the `marmot.transport.nostr.routing.v1` component below. An
interop-visible change uses the narrowest hook in [README.md](./README.md) ("Versioning") — a new envelope version, a
new Nostr kind, a new routing component id, or a new required capability — rather than a binding-wide version number.

## Required group state

A Nostr-routed group requires the `marmot.transport.nostr.routing.v1` app component.

That component owns:

- `nostr_group_id`, the 32-byte transport group id;
- the canonical relay list for group messages.

The Nostr transport uses those values. It does not derive them from account ids, MLS group ids, KeyPackage ids, relay
URLs, or Nostr event ids.

## Transport byte encoding

Fields in this binding that carry Marmot, MLS, or AEAD bytes use base64 with the standard alphabet and padding
(RFC 4648, section 4) unless the field is explicitly defined as lowercase hex. "Standard" here distinguishes this
alphabet from URL-safe base64 (RFC 4648, section 5), which this binding does not use.

This binding does not use `encoding` tags to negotiate byte encoding. A sender MUST NOT add an `encoding` tag for any
event shape in this document. A receiver MUST NOT switch decoders based on an `encoding` tag; each field is decoded by
the rule that defines that field.

## Relay URL profile

Relay URL fields and `relay`/`relays` tag values use the Nostr relay URL profile:

- the value MUST be valid UTF-8 and no more than 512 bytes;
- the URL MUST be absolute;
- the scheme MUST be `wss` or `ws`;
- the host MUST be present;
- username, password, and fragment components MUST be absent.

Producers SHOULD use `wss`, lowercase DNS hostnames, omit default ports, and avoid redundant path spelling. Receivers
compare relay URL byte strings exactly after validation. Local safety policy MAY refuse to connect or publish to a
valid relay URL, but it MUST NOT rewrite signed group state.

## Event identity and tag cardinality

**CRITICAL:** A receiver MUST verify a signed Nostr event's NIP-01 id and signature before treating its `id`, `pubkey`,
`created_at`, `kind`, `tags`, or `content` as authenticated transport metadata. Before that verification succeeds, those
fields are untrusted bytes and MUST NOT be used as trusted routing, replay, telemetry, or KeyPackage evidence.

**CRITICAL:** Required Marmot transport tags have exact cardinality. If a required singleton tag is missing, repeated,
has no value, or has extra values beyond the one defined here, the event is malformed. If a required list tag is missing,
repeated, empty, or contains duplicate values after validation, the event is malformed. A receiver MUST NOT read only the
first matching tag and ignore later duplicates.

| Event shape | Tag | Cardinality and value rule |
| --- | --- | --- |
| kind `445` group message | `h` | exactly one tag, exactly one value: lowercase hex `nostr_group_id` |
| kind `1059` welcome gift wrap | `p` | exactly one tag, exactly one value: lowercase hex account identity of the recipient |
| kind `444` welcome rumor | `e` | exactly one tag, exactly one value: lowercase hex Nostr event id of the claimed KeyPackage event |
| kind `444` welcome rumor | `relays` | exactly one tag, one or more relay URL values using the relay URL profile |
| kind `30443` KeyPackage | `d` | exactly one tag, exactly one 64-character lowercase hex value decoding to 32 bytes |
| kind `30443` KeyPackage | `mls_protocol_version` | exactly one tag, exactly one value: `1.0` |
| kind `30443` KeyPackage | `i` | exactly one tag, exactly one value: lowercase hex KeyPackageRef |
| kind `30443` KeyPackage | `mls_ciphersuite` | exactly one id-list tag |
| kind `30443` KeyPackage | `mls_extensions` | exactly one id-list tag |
| kind `30443` KeyPackage | `mls_proposals` | exactly one id-list tag |
| kind `30443` KeyPackage | `app_components` | exactly one id-list tag |

The kind `444` `e` tag sits on the trust boundary: it is a claim about which KeyPackage event was consumed. It is not
proof that the event exists, was authored by the invitee account, or carried the decoded KeyPackage. A client that needs
those facts MUST fetch and verify the referenced kind `30443` event and then verify the decoded KeyPackageRef under
[../foundation/key-packages.md](../foundation/key-packages.md).

## Group message delivery

Nostr group messages use Nostr kind `445`.

A kind `445` event MUST include exactly one `h` tag whose value is the lowercase hex encoding of the group's
`nostr_group_id`. The only other tag permitted on a kind `445` event is the NIP-40 `expiration` tag defined in "Message
expiration" below; a kind `445` event MUST NOT carry any other tag.

The event `pubkey` MUST be a fresh ephemeral Nostr public key generated for that event. The kind `445` event MUST be
signed by the matching ephemeral key. The ephemeral key MUST NOT be the sender's Marmot account identity, and it MUST
NOT be reused across events.

The event content carries one encrypted MLS message:

```text
group_event_key = MLS-Exporter("marmot", "group-event", 32)
nonce           = random(12)
aad             = ""
ciphertext      = ChaCha20-Poly1305.encrypt(group_event_key, nonce, mls_message_bytes, aad)
event.content   = base64(nonce || ciphertext)
```

The base64 encoding is standard base64 with padding.

The `ciphertext` value is the full AEAD output and includes the authentication tag. The 12-byte nonce is prepended to
the ciphertext before base64 encoding. The AAD is the empty byte string and is not serialized into the event.

The exporter label/context pair is registered for the Nostr kind `445` outer encryption layer only. It MUST NOT be
reused for app payloads, media, stream records, or other feature keys.

Security note: `group_event_key` is scoped to one MLS group epoch, so nonce uniqueness for a given key is probabilistic.
Each `random(12)` nonce MUST be sampled independently and uniformly with a cryptographically secure random generator.
Marmot v1 does not impose an event-count limit per epoch; after `q` events under one epoch key, the approximate random
collision probability is `q(q-1) / 2^97`.

The Nostr event id, event `pubkey`, tags, relay timestamp, and relay URL are not AEAD AAD for kind `445`. They are
validated as the transport envelope and then treated as transport evidence only.

Receivers MUST verify the kind `445` event id and Nostr signature before attempting to decrypt its content. That
signature proves only integrity of the ephemeral transport envelope. Marmot sender identity still comes from the MLS
message after decryption.

Receivers MUST reject kind `445` content that is not valid base64 or that decodes to fewer than 28 bytes. The minimum is
12 nonce bytes plus the 16-byte ChaCha20-Poly1305 tag.

Marmot v1 does not impose a universal maximum Nostr event or decoded-content size. Relays and clients MAY apply local
resource limits to transport objects they can observe and MAY discard an object that exceeds such a limit before
decoding or decryption. A relay can limit visible kind `445`, `1059`, and `30443` events; it cannot inspect the kind
`444` rumor sealed inside a kind `1059` gift wrap. A client MAY additionally limit that rumor after unwrapping. Such a
discard is a transport availability outcome; it does not establish that recovered MLS bytes would be protocol-invalid
or change canonical group state.

Kind `445` Nostr event ids, relay timestamps, relay arrival order, and subscription order are transport evidence. They
MUST NOT choose group state.

## Outer decryption and epoch selection

`group_event_key` is derived from the MLS epoch's exporter secret, so it differs per group epoch. The kind `445`
envelope carries no epoch hint and uses an empty AAD, so a receiver cannot read the target epoch before decrypting.

A receiver decrypts the outer layer by trying the `group_event_key` of each retained candidate group state until one
authenticates, then hands the recovered MLS message to the peeler. The candidate set is the retained states the
convergence policy already requires: the current canonical epoch, any retained epoch inside the rollback horizon, and
any staged-but-unmerged local commit. A receiver MUST NOT widen this set using transport evidence, and trial decryption
MUST NOT by itself choose the canonical branch; it only recovers candidate MLS bytes for protocol-core convergence to
judge.

Trying the staged-but-unmerged local commit's key here is candidate construction, not application. It does not conflict
with the rule in [../protocol-core/group-state.md](../protocol-core/group-state.md) that inbound MUST NOT be applied to canonical group state during
`PendingPublish` or `Merging`: trial decryption only recovers bytes for convergence to judge, and the inbound message is
not applied while the group is in those states.

If no retained candidate key authenticates the content, the event is undecryptable transport input and is not applied
to group state. A retained event has the `transport_deferred` availability category. The client MUST retry it after a
canonical epoch change, retained-candidate change, staged-state change, or verified repair changes the candidate key
set; it MAY suppress repeated attempts while that set is unchanged.

If a local resource limit prevents retention or retires the event after a bounded number of attempts, the event has
the `resource_refused` availability category. The client MUST NOT record that event id as terminally seen or
permanently unreadable, and the same event id remains eligible when later delivered or fetched.

A subscription or backfill range containing a resource-refused event is not synchronized merely because the relay
reported end-of-stored-events or the client advanced a local cursor. After capacity becomes available, the client MUST
give the refused event another delivery opportunity by refetching an overlapping range or by an equivalent
transport-specific recovery mechanism. Deferred or refused events MUST NOT block unrelated valid input from being
processed and MUST NOT choose canonical group state.

The public routing id and required fresh ephemeral event key do not provide a member-authenticated prefilter for kind
`445`; a non-member can submit envelopes that reach trial decryption. Relay admission controls and client-side input,
CPU, and retry budgets are operational policy, not Marmot group-state rules. In particular, a budget decision MAY drop
or defer transport input, but it MUST NOT make that input valid, choose a canonical branch, or change the bounded set of
candidate keys tried for an accepted envelope.

## Message expiration

The `expiration` tag applies to MLS application messages only. When the message's source-epoch
`marmot.group.message-retention.v1` state enables a retention duration, the sender of its kind `445` event SHOULD attach
a NIP-40 `expiration` tag whose value is the exact `expiry_timestamp` defined by
[../app-components/message-retention-v1.md](../app-components/message-retention-v1.md). If that value is undefined or
unrepresentable, the sender omits the tag. A kind `445` event that carries a commit or proposal MUST NOT carry an
`expiration` tag, regardless of the retention policy: group-state history stays fetchable for members catching up. A
message whose source epoch has no enabled retention emits no `expiration` tag.

The `expiration` tag is relay-facing transport metadata that asks relays to delete the event after the expiry time.
Receivers MUST NOT use the tag for message validity, ordering, or branch selection, and a missing or mismatched tag
does not invalidate a message. A sender-supplied expiration tag on the inner app payload is replaced or removed
according to the active retention component ([../protocol-core/group-setup.md](../protocol-core/group-setup.md),
"Message retention").

Enabling retention is a trade-off the group accepts:

- Privacy: the `expiration` tag reveals the group's retention policy to every relay and reader of the event.
- Availability: relays delete expired events. An application message that has expired from every relay is unrecoverable
  for a member that did not fetch it in time. Commits and proposals never carry the tag, so retention does not block
  group-state catch-up.

## Account inbox relays

A Marmot account advertises its inbox relay set by publishing a standard Nostr kind `10050` event — the NIP-17 DM
inbox relay list — with one `relay` tag per inbox relay URL. Kind `10050` is not Marmot-allocated; Marmot reuses the
standard kind unchanged, and the list is public signed account metadata.

Gift-wrapped events addressed to an account — including kind `444` welcome rumors — are published to the recipient's
kind `10050` inbox relay set. A sender MAY also publish to a contextual relay hint: a relay URL learned outside this
binding for delivery to that recipient. Such a hint is local, advisory delivery information; it is not authenticated
recipient metadata and does not change event validity. When a sender has no such hint, it publishes to the recipient's
published kind `10050` list alone.

An account with no published kind `10050` list cannot reliably receive Welcomes: the sender publishes to whatever hint
relays it has for the recipient, and nothing tells it where the recipient listens. An account SHOULD publish a kind
`10050` relay list before expecting Welcomes or other account-directed delivery.

## Welcome delivery

Nostr Welcomes use NIP-59 gift wraps.

The outer relay event is kind `1059`. It contains a kind `13` NIP-59 seal. The seal contains an unsigned kind `444`
Marmot welcome rumor.

The gift-wrap recipient is the invitee's Nostr public key.

The inner kind `444` rumor MUST include:

- `content`: serialized MLSMessage bytes whose wire format is `mls_welcome`, encoded as base64;
- `e` tag: the Nostr event id of the KeyPackage event used for the invite;
- `relays` tag: relay URLs, using the relay URL profile above, where the new member SHOULD fetch group messages.

The inner kind `444` rumor MUST NOT have a `sig` field. The kind `13` seal and kind `1059` gift wrap are signed by
NIP-59.

A receiver MUST reject a Welcome that is not addressed to its own account identity.

A receiver MUST reject a kind `444` rumor that does not satisfy its `e` and `relays` rows in "Event identity and tag
cardinality" or whose content is not valid base64-encoded `MLSMessage` bytes with the `mls_welcome` wire format.

## Push notification delivery

The optional push feature owns the kind `446` notification-rumor content and processing rules
([../features/push-notifications.md](../features/push-notifications.md)). The Nostr binding carries that unsigned rumor
in a NIP-59 envelope:

```text
kind 1059 gift wrap
  kind 13 seal
    unsigned kind 446 Marmot notification rumor
```

The seal is signed by the same fresh ephemeral key named by the rumor's `pubkey`. The gift wrap uses a separate fresh
ephemeral key and is addressed to the notification server's account identity. The publish target is defined under
"Publish targets and acknowledgements."

## KeyPackage publication

Nostr KeyPackages use kind `30443`.

The event content is serialized `MLSMessage` bytes whose wire format is `mls_key_package`, encoded as base64. The
`MLSMessage` wraps the public `KeyPackage`; private `init_key` material is never published. This mirrors the kind `444`
Welcome framing above, where the content is an `MLSMessage` with `mls_welcome` wire format. The event is authored by the
account identity that owns the KeyPackage. The event MUST be signed as a normal Nostr event.

The current tag set is:

- `d`: stable random KeyPackage publication-slot id, encoded as a 32-byte lowercase hex value;
- `mls_protocol_version`: `1.0`;
- `i`: lowercase hex KeyPackageRef;
- `mls_ciphersuite`: MLS ciphersuite id;
- `mls_extensions`: supported MLS extension ids;
- `mls_proposals`: supported MLS proposal ids;
- `app_components`: supported Marmot app-component ids.

`mls_ciphersuite`, `mls_extensions`, `mls_proposals`, and `app_components` are id-list tags. Each is exactly one tag
whose values follow the tag name in a single tag array, for example `["app_components", "0x8001", "0x8009"]`.
A producer MUST NOT split the ids of one list across repeated tags. Each value is the `0x`-prefixed lowercase
hexadecimal encoding of the 16-bit id, zero-padded to four hex digits, such as `0x0001` or `0xf2f1`. Each id-list tag
MUST carry at least one value and MUST NOT repeat a value inside the same tag. Consumers compare id-list values as exact
strings; under the text rule in [../foundation/canonical-encoding.md](../foundation/canonical-encoding.md), the producer
emits exactly this form. A consumer MUST reject a KeyPackage event that carries more than one tag with the same id-list
name (so the producer's "exactly one tag" rule is enforced, not assumed); it MUST NOT read only the first occurrence
and ignore the rest.

The `i` tag is the KeyPackageRef, not the account identity. Receivers MUST verify it against the decoded KeyPackage.

The `app_components` tag MUST include the value `0x8009` for `marmot.member.account-identity-proof.v2`. Receivers MUST
still validate the decoded KeyPackage LeafNode's support list and proof data; the transport tag is only an
advertisement and fetch filter. The current profile does not require legacy extension type `0xf2f1` in
`mls_extensions`.

KeyPackage publication is account transport. It helps other users find fresh KeyPackages. It does not create group
state.

KeyPackage relay discovery uses the account's kind `10002` NIP-65 relay list. For this purpose, the account's
write-capable relay set contains each `r` entry whose marker is `write` or whose marker is omitted; an entry marked only
`read` is not in the set. The account publishes its kind `30443` KeyPackage events to its write-capable set, and another
client fetches that account's KeyPackages from one or more relays in the same set. Fetching from every relay is not an
interop requirement. Clients MUST apply the markers this way rather than treating every `r` entry as an undifferentiated
publish-and-fetch target. There is no dedicated KeyPackage relay list, and KeyPackage events do not repeat those relays.

Kind `30443` is a Nostr addressable event. Two events occupy the same slot when their `author`, `kind`, and `d` tag
value are all equal, comparing the `d` value as exact bytes. For one `(author, kind, d)` slot, clients SHOULD keep the
newest valid event by `created_at`, with lower event id as the deterministic tie-breaker when timestamps are equal.
Across different `d` slots, each valid event is a separate candidate KeyPackage. Candidate ranking then follows
[../foundation/key-packages.md](../foundation/key-packages.md).

A publishing MLS client creates a logical KeyPackage publication slot by generating its `d` value once from 32 random
bytes and retaining that value locally. Replacing the KeyPackage in that logical slot MUST reuse the same `d`; a routine
replacement MUST NOT generate a fresh slot id. A client generates a different random `d` only when it intentionally adds
another concurrently discoverable KeyPackage slot. The slot id MUST NOT be derived from an account key, MLS leaf key,
KeyPackageRef, device label, or other identity material.

When candidates from different `(author, kind, d)` slots are otherwise equivalent after foundation ranking, clients
SHOULD select the candidate with the lexicographically lower decoded KeyPackageRef from the `i` tag. The `i` tag is
hex-decoded before comparison.

### Migration from kind 10051

Kind `10051` was the former dedicated KeyPackage relay-list scheme. It is not part of this binding. The account's kind
`10002` write-capable set above is now the source of kind `30443` publication and fetch destinations; there is no kind
`10051` publication or lookup step in this binding. This migration does not change Welcome delivery: the recipient's
kind `10050` list remains the source of its advertised inbox destinations.

The existing publisher rules give the following preparation sequence:

1. publish a current signed kind `10002` record through metadata lookup paths where intended inviters can retrieve it;
2. publish each kind `30443` KeyPackage to the resulting write-capable set; and
3. publish a current signed kind `10050` record through retrievable metadata lookup paths and listen on its advertised
   inbox set before expecting reliable Welcome delivery.

The corresponding inviter sequence is:

1. retrieve and verify the invitee's kind `10002` metadata, then resolve its write-capable set;
2. fetch one or more of that account's kind `30443` events from that set and validate candidates under
   [KeyPackages](../foundation/key-packages.md) and "KeyPackage publication" above; and
3. separately retrieve and verify the invitee's kind `10050` metadata, resolve its inbox set, and publish the Welcome
   under "Account inbox relays" and "Welcome delivery" above.

The relays from which kind `10002` or kind `10050` metadata is retrieved are metadata lookup locations, not implied
KeyPackage or Welcome destinations. Finding one record at a bootstrap or hint relay does not prove that the other record
is reachable there, and it does not prove that either account advertises that relay as a destination. This binding does
not guarantee metadata discovery from an arbitrary default relay. The applicable receive queries are summarized in
"[Subscriptions and fetch rules](#subscriptions-and-fetch-rules)" below.

An absent current record, a current record that resolves to an empty usable destination set, and a record that cannot be
retrieved because its metadata lookup locations are unavailable are distinct operational outcomes. In all three cases,
that lookup has supplied no usable advertised destination set. Without a usable kind `10002` record, the discovery step
above has no write-capable set to query; for kind `10050`, the contextual-hint permission in "Account inbox relays"
remains unchanged. This note does not define cache freshness or retry policy. Local retry, cache, or fallback choices
do not turn a read-only NIP-65 entry, a metadata lookup relay, or an arbitrary default relay into an advertised
destination or an interoperability guarantee.

For example, suppose an invitee's kind `10002` has `["r", K, "write"]`, `["r", R, "read"]`, and `["r", U]`, while
its kind `10050` advertises inbox relay `I`. An inviter can retrieve the signed metadata records through discovery relay
`D`, fetch the invitee's KeyPackages from `K` or `U` but not `R`, and deliver the Welcome to `I`. Established-group
messages can use a separate group relay `G`; the inviter's own inbox and NIP-65 relays can also be separate. No overlap
among these roles is required. The example assumes that the metadata is reachable through the inviter's configured
lookup inputs; it does not make `D` a fallback destination.

## Subscriptions and fetch rules

A Nostr transport client subscribes to:

- account inbox gift wraps: kind `1059`, `p` tag equal to the local account pubkey, on the account's own kind `10050`
  inbox relay set ("Account inbox relays" above);
- group messages: kind `445`, with a `#h` filter equal to the current `nostr_group_id` or each prior routing id the
  rotation rules still require, fetched from one or more relays in the routing state associated with that id
  ([../app-components/nostr-routing-v1.md](../app-components/nostr-routing-v1.md), "Routing rotation"); fetching from
  every relay in those states is not an interoperability requirement, and the filter does not replace receiver
  validation of the signed event and exact `h` tag;
- NIP-17 inbox relay lists: kind `10050`, author equal to the account being addressed, to discover that account's
  inbox relay set;
- NIP-65 relay lists: kind `10002`, author equal to the account being queried, to discover where that account
  publishes its KeyPackages;
- KeyPackage events: kind `30443`, using the account lookup rules defined by
  [../foundation/key-packages.md](../foundation/key-packages.md).

Clients SHOULD use a `since` value when resubscribing if they have a retained transport timestamp. The timestamp is a
fetch hint only.

## Publish targets and acknowledgements

Group messages are published to the relay list in `marmot.transport.nostr.routing.v1`, after applying any local safety
policy. A commit that changes routing state is published to the prior epoch's routing address
([../app-components/nostr-routing-v1.md](../app-components/nostr-routing-v1.md), "Routing rotation").
When the sender creates the signed event, it snapshots that applicable relay target list and durably records the
serialized event plus per-target attempt status. A later routing rotation does not rewrite this fanout obligation.

The sender MUST attempt publication of the same signed event to every snapshotted relay that local policy permits. The
first accepted acknowledgement can satisfy the publish lifecycle, but it does not permit the sender to skip the other
permitted targets. Each target remains outstanding across process restart until the sender has made at least one
publication attempt or records that current local policy prohibits contacting it. The obligation ends when every target
is complete or the transport object reaches its authenticated expiration. That later fanout does not keep or return the
group to `PendingPublish`, undo canonical apply, or re-stage the Commit; retrying a target after its required first
attempt is transport or local policy.

Welcome messages are published to the recipient's inbox relay set ("Account inbox relays" above).

KeyPackage events are published to the account's NIP-65 (kind `10002`) write-capable relay set defined above.

Push-notification gift wraps carrying a kind `446` rumor are published to the `relay_hint` values in the selected
token records for that notification server. If none of those records carries a relay hint, they are published to the
server account's inbox relay set. The trigger and token-record shapes are defined by
[../features/push-notifications.md](../features/push-notifications.md).

A publish to a relay is acknowledged when the relay returns a NIP-01 `OK` response accepting the event; anything else —
a rejecting `OK`, an error, a timeout, or no response — is not an acknowledgement. The transport MAY report
endpoint-level acceptances and failures. Publish acknowledgement is not group consensus. The protocol-core publish
lifecycle defines when locally created MLS work MAY be applied.

## Validation before peeling

A Nostr transport client MUST validate the complete event shape before passing recovered MLS bytes to the MLS peeler.
The event-shape sections above own those rules; this checklist points to them rather than restating a second, narrower
set:

- kind `445` group messages MUST satisfy every envelope, tag, content, and signature rule in "Group message delivery"
  before outer decryption;
- kind `1059` Welcomes and their kind `444` rumors MUST satisfy every recipient, envelope, tag, content, and signature
  rule in "Welcome delivery" as each NIP-59 layer is unwrapped;
- kind `30443` KeyPackage events MUST satisfy every outer envelope, tag, content-encoding, and signature rule in
  "KeyPackage publication";
- fields that claim to be hex or base64 MUST decode successfully;
- unsupported Nostr kinds are ignored or reported as malformed transport input.

The Nostr transport client owns NIP-59 unwrapping, kind `445` outer AEAD authentication, and outer recipient checks. It
passes recovered `MLSMessage` bytes unchanged to the MLS/Foundation layer. That layer parses the MLS wire format,
extracts a KeyPackage when applicable, and performs MLS, account-proof, lifetime, and capability validation. Protocol
core validates group state and join rules. A transport checklist MUST NOT require a decoded inner field before the
owning MLS parser has recovered it.

## Duplicate and replay handling

Relays MAY redeliver the same event, and a client subscribing to several relays will receive the same group message
more than once. The Nostr event id is transport evidence and MUST NOT be used as the Marmot deduplication id: the id
used for dedup and replay is defined over the recovered MLS message bytes (see
[../foundation/wire-envelopes.md](../foundation/wire-envelopes.md), "Message ids", and
[../protocol-core/inbound-processing.md](../protocol-core/inbound-processing.md), "Message identity"). A client peels
the transport envelope, recovers the MLS message, and deduplicates on that stable id before applying state, so relay
redelivery and cross-relay duplication collapse to a single `duplicate` outcome. Relay `created_at` timestamps, relay
arrival order, and subscription order are fetch hints only and MUST NOT choose group state.

## Metadata exposed to the transport

Relays see only transport-envelope metadata, never plaintext or MLS secrets:

- kind `445` events expose the group's random `nostr_group_id` via the `h` tag (it is not derived from any member key,
  so it does not link members across groups), a fresh per-event ephemeral `pubkey` (never the sender's account identity
  and never reused), the relay timestamp, and — when retention is enabled — the group's retention policy via the
  NIP-40 `expiration` tag ("Message expiration" above). Tag presence also reveals that the event carries an application
  message, because commits and proposals never carry it. Tag absence is not conclusive: the tag is a `SHOULD`, and an
  application message omits it when the exact expiry is unrepresentable. The MLS message is encrypted under the
  per-epoch group-event key.
- Welcomes are NIP-59 gift wraps addressed to the invitee's account public key; the inbox address is the deliberate
  account-addressing exception ([../foundation/identity.md](../foundation/identity.md)). The gift wrap and seal hide the
  sender and the inner `kind 444` rumor.
- kind `30443` KeyPackage events are authored by the account identity, because their purpose is to let others find that
  account's packages.

A client MUST NOT add tags, content, or `encoding` markers that expose account ids, group ids, message ids, payloads,
or key material beyond what each event shape above already requires. Refusing a relay URL follows the local-policy rule
in "Relay URL profile" and does not change these authenticated bytes.
