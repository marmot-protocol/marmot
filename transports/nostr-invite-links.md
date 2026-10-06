# Nostr invite-link extension v1

Status: proposed; not adopted. This optional extension supplements [nostr.md](nostr.md); it does not change existing
KeyPackage, group-message, or Welcome envelopes. The feature is currently specified for Nostr only.
The associated state and record formats are owned by the
[component](../app-components/group-invite-links-v1.md) and
[record document](../foundation/invite-link-records.md).

## Allocations

- Kind `459`: request or withdrawal rumor inside a NIP-59 gift wrap.
- Kind `460`: status rumor inside a NIP-59 gift wrap.
- Kind `461`: private admin-control rumor inside recipient gift wraps, carried in an unsigned MLS app event of the
  same kind. The two layers have distinct schemas below.
- Kind `30444`: signed parameterized-replaceable encrypted preview descriptor.

These proposed allocations are indexed in [registries.md](../foundation/registries.md#proposed-invite-link-allocations).
The outer kinds `1059` and `13`, NIP-44 encryption, and NIP-59 validation remain upstream primitives.
For every new request, status and admin gift wrap, the seal has empty tags and the outer gift wrap has exactly one
`p` tag with exactly the recipient's lowercase-hex account/inbox key. No extra tags are permitted. The outer author
is the fresh NIP-59 ephemeral key, never an inviter or group identity.
There is no new MLS exporter or account-signature proof class.
All new rumors use exactly the adopted unsigned Nostr-shaped fields and NIP-01 id calculation; no extra JSON members
are accepted. Signed descriptor, seal and gift-wrap objects have those fields plus `sig`. `created_at` is an integer
in `0..9007199254740991`; kinds and tags are the fixed values specified here. This bounds event metadata as well as content.

## Long code

```text
struct {
  uint16 version;
  opaque inbox_pubkey[32];
  opaque link_id[32];
  opaque bearer[32];
  opaque preview_key[32];
  RelayURL request_relays<1..4096>;
} InviteCodeV1;

struct {
  opaque url<1..512>;
} RelayURL;
```

`version` is one. Keys and identifiers have the meanings in the component. Bearer and preview key are independently
random 32-byte secrets, distinct from the inbox private key. The list has one through eight unique URLs sorted by
UTF-8 content bytes. URLs satisfy the Nostr relay URL profile and MUST use `wss://`; decoder normalization is forbidden.
Local endpoint safety policy MAY refuse a URL without rewriting the code; a syntactically valid URL is not permission
to access a protected local network or send credentials to it. These relays locate the descriptor and request inbox, not the group's delivery stream or recipient account inbox.

Encode the exact binary bytes with Bech32m using prefix `marmot`. Use BIP-350's checksum constant and standard
eight-to-five-bit conversion with zero padding. Decoding rejects excess/nonzero padding, mixed case, other prefixes,
bad checksums, the Bech32 checksum variant, unknown versions, and malformed binary values. Producers emit lowercase;
decoders accept entirely uppercase forms. This format explicitly permits up to 7000 characters rather than the
generic Bech32 ninety-character limit. Longer strings are invalid before allocation or decoding.
QR capacity is a separate bound, determined by the chosen version, character mode and error correction level
([capacity reference](https://www.qrcode.com/en/about/version.html)). A producer MUST verify that the complete code fits the chosen QR version and error
correction level before offering that QR. It SHOULD use an entirely uppercase code for QR alphanumeric mode; this
is the same accepted code, not mixed case. Codes near the 7000-character ceiling may not fit any QR. Offer text or
a short URL instead; never truncate a code or alter encoded relay bytes to force it to fit.
It is not an `naddr` or a `nostr:` entity and MUST NOT be passed to an ordinary NIP-19 decoder as either.

Apps MAY wrap the code in an HTTPS URL fragment or encode it directly in a QR. A fragment is not sent in an ordinary
HTTP request, but page scripts and recipients can read it. Hosts handling a direct-code URL MUST NOT upload the
fragment for resolution or analytics. An outer URL is app routing, not a second protocol encoding.

The optional short URL maps to this complete code. A host storing it can read all its secrets. Deleting a short URL
does not revoke the code. Short-id alphabet, hostname and lookup protection are deployment policy, not protocol ids.

## Preview descriptor

```text
struct {
  uint16 version;
  opaque inbox_pubkey[32];
  opaque link_id[32];
  opaque bearer_hash[32];
  uint64 expires_at;
  uint8 approval_mode;
  opaque name<1..256>;
  opaque description<0..4096>;
  uint8 image_type;
  opaque image<0..49152>;
} InvitePreviewV1;
```

Version, keys, hashes, mode and expiry have the component's meaning. Text is valid UTF-8 with byte equality and no
normalization. Image types are none zero, JPEG one, and PNG two. None requires empty image bytes; JPEG/PNG require
nonempty image bytes. Unknown types or inconsistent type/length combinations invalidate the record. Before rendering,
clients MUST bound decoded dimensions to at most 1024 by 1024, require the declared JPEG/PNG format, and reject malformed
or unsupported images from the renderer. An image-rendering failure leaves a text-only preview and MUST NOT change the
committed plaintext bytes. No SVG, HTML, external image URL, executable markup, or automatic URL fetch is provided in v1.
Text is displayed as plain text, not interpreted Markdown or HTML.

`preview_hash = SHA-256(encoded InvitePreviewV1)`. Generate a fresh random twelve-byte nonce for each encryption.
Encrypt the exact plaintext with ChaCha20-Poly1305 using the invitation's independent `preview_key` directly as its
32-byte key. AAD is the canonical binary tuple `uint16(1) || inbox_pubkey[32] || link_id[32]`.
The ciphertext includes the sixteen-byte AEAD tag. Reuse of a nonce with the same key is forbidden.
This key is not an MLS exporter, a NIP-44 conversation key, or an inbox private key.

The descriptor's Nostr author is `inbox_pubkey`, kind is `30444`, tags are exactly `[["d", lowercase_hex(link_id)]]`,
and content is standard padded base64 of `nonce || ciphertext`. NIP-01 id and signature verification precede
decryption. The total decoded content is bounded to 54000 bytes. The plaintext's inbox, id and bearer hash MUST
match the code, including `SHA-256(code.bearer)`. Its remaining fields are committed by `preview_hash`.
An inbox holder can replace this signed descriptor; a changed preview is not silently substituted for the one the
requester approved. The receiver preserves the exact plaintext seen at consent.

Fetch from the code's relays with kind/author/`d` filters, apply NIP-01 validation, and use NIP-01 parameterized
replacement order: latest `created_at`, then lowest event id on ties. The timestamp selects a descriptor only; it
never chooses MLS group state or proves a request preceded expiry.
After joining, compare all preview policy fields and the hash with the Welcome's invitation entry. A mismatch
requires a new user choice. A match still has the adopted Welcome-bootstrap trust limitation.

## Request delivery and package evidence

```text
struct {
  opaque key_package_event_id[32];
  RelayURL welcome_hints<0..4096>;
} NostrInviteOfferV1;

struct {
  uint8 operation;
  opaque record<1..16384>;
} NostrInviteRequestV1;
```

The offer is the `transport_offer` in the request TBS. `welcome_hints` has zero through eight sorted unique WSS URLs
using the code's RelayURL encoding. They are contextual hints permitted by the existing inbox binding, not account
metadata or evidence of ownership. The event id names one exact signed kind `30443` publication, not its `d` slot.
Fetch it through the account's NIP-65 write-capable set. Verify the event id/signature, publication author, decoded
KeyPackageRef, LeafNode account identity proof, and device signature. Initial ancestor verification can use retained
publication evidence even after it is superseded or expired; admitting a member still requires a currently valid
offer under the adopted KeyPackage selection and lifetime rules.

Operations are request zero and withdrawal one; their record bytes are exactly InviteRequestV1 and InviteWithdrawalV1.
The rumor is kind `459`, has no tags or `sig`, and content is padded base64 of NostrInviteRequestV1. Its pubkey and
the NIP-59 seal author equal the requester account. Gift wraps are addressed to the code's inbox public key.
Requests are published to every usable code relay with independent endpoint outcomes. A first acknowledged NIP-01
accept is delivery-to-relay evidence only. All initial fanout attempts remain required; failure is retryable.
The requester MUST retain the original record before sending, may rewrap it, and MUST NOT change logical request
identity on a transport retry. Admins query kind `1059` and recipient `p` matching the inbox, then validate every
NIP-59 layer before processing the device-signed record. No recipient filter alone authenticates a sender.

For forwarding evidence, `opaque publication<1..12288>` is a UTF-8 JSON signed kind `30443` event encoded with RFC 8785
JSON canonicalization. Reject duplicate object keys and non-canonical re-encoding; then apply NIP-01 and existing
KeyPackage publication validation. JSON canonicalization does not replace NIP-01's event-id signing preimage.

## Status delivery

A kind `460` rumor has no tags or `sig` and content is padded base64 of exactly InviteStatusV1. Its pubkey equals the
admin-account seal author. The gift-wrap recipient is the requester account, never the link inbox.
Use the requester's signed kind `10050` inbox list plus the validated offer's contextual hints under the existing
Welcome binding. An absent, empty, or unavailable list is not permission to guess a default destination.
Clients query their account inbox and authenticate NIP-59 before treating a status as an attributed claim.

The Welcome itself remains kind `444`, with its existing KeyPackage event `e` tag and group relay metadata.
Request ids, bearers and private request records MUST NOT be added to publicly visible routing tags or KeyPackage
publications. Join correlation uses the encrypted status's Welcome hash and the exact offer's publication reference.
Status transport failure MUST NOT delay valid Welcome delivery or change group membership.

## Admin delivery inside MLS

The inner app event carries the [canonical admin batch](../foundation/invite-link-records.md#admin-app-batches).
For this binding, each `transport_envelope` is a NIP-59 gift-wrap event. Producers split using the canonical recipient
and byte bounds; each logical record is retried independently. JSON is RFC 8785 canonical encoding of a complete NIP-59 gift-wrap event. The outer event has exactly its
NIP-59 recipient `p` tag, naming `recipient_account`; validate the signature and each NIP-59 layer before using it.
The decrypted kind `461` rumor has no tags or `sig`, and content is padded base64 of InviteAdminRecordV1.
Its pubkey and seal author MUST equal the account of the enclosing MLS-authenticated app-event sender.
The inner record's source epoch equals the enclosing MLS application's source epoch. A forwarded nested requester
record retains its own consent signature and account binding; it is not reauthored by the admin.

The enclosing kind `461` Marmot app event has no tags and content is padded base64 of InviteAdminBatchV1.
Its shape and sender binding follow the adopted unsigned app payload rules; adding `sig` is invalid.
It is delivered by normal MLS/Nostr group messaging, not published as a standalone kind `461` relay event.
Each recipient MUST be an active admin in the authenticated source-epoch state. Only that recipient opens its copy;
ordinary members see recipient accounts but not the records. Secret or request data in plaintext tags is invalid.

Fetch and catch-up follow normal group delivery. Transport duplicates do not retire requests. Replay and current
authorization are evaluated by the feature, not by an outer event timestamp. Key grants name one group/generation;
they MUST NOT be accepted merely because an inbox private key decrypts other ciphertext successfully.

## Relay budgets and failures

The structural bounds permit events larger than some relays accept. They are receiver safety ceilings, not a promise
that every relay supports them. Before preparing a descriptor, record or batch, producers SHOULD estimate its complete
relay event size after JSON, all nested encryption, base64 and MLS overhead. Use compatible code/group relays, reduce
preview image bytes, and split admin batches within both bounds and endpoint budgets. A single oversized request or
forwarded package evidence cannot be truncated; report a recoverable size/delivery problem or use another conforming
relay. A 54000-byte decoded descriptor can exceed a 64 KiB event budget after base64.

Relay rejection, size-policy refusal or unavailable endpoint is delivery failure, not a request decision or MLS state
change. Preserve the outstanding exact logical record or prepared MLS obligation, show the actionable delivery error,
and follow existing publish recovery without generating a duplicate Add. This deployment assumption must be tested
with intended relays before enabling the feature. A smaller receiver ceiling needs a future version rather than
silently rejecting conforming bytes as malformed.

## Limits and privacy

This v1 profile limits each NIP-44 plaintext to 65535 UTF-8 bytes, including both the rumor and the signed seal
inside a gift wrap. Upstream support for larger extended-length payloads does not raise this feature limit.
Producers MUST check both layers before sending; oversized records are a local capacity error, never truncated.
The admin-record body and publication-evidence limits leave room for JSON, base64 and NIP-44 padding. Receivers
MUST reject gift-wrap JSON above 90000 bytes and enforce the same two decrypted-layer limits.

Before decoding base64, enforce its encoded-length bound derived from each decoded maximum; reject malformed padding
or alternative alphabets. Unknown record kinds/versions do not fall back to chat or another invite format.
Receivers MUST limit unauthenticated envelope processing and retain at most 100 open contexts per link, at most eight
retained refresh revisions per context, and at most 1000 terminal context tombstones across currently active generations per group.
Retired-generation accounting and still-required recovery facts follow the feature; additional local storage safety
limits MAY refuse new work without deleting required facts. Admission limits do
not grant senders authority to erase other records. Overflow returns a local capacity outcome without claiming the
request was rejected or joined. The feature specifies retention and retries.

Use bounded per-inbox validation work. After repeated transport failure, exponentially back off with jitter, with
at least one minute between attempts for a context and a maximum backoff of one hour; stop at its signed deadline. Requests MUST NOT be sent automatically merely on opening a preview.
Applications MUST NOT log decrypted requests, bearers, private keys, preview text, or message content.

Relays can observe inbox addresses, recipient accounts, event sizes and timing. They cannot read protected records.
Publishing a KeyPackage beside a request may correlate the events. A short-link host knows the complete code.
Removing an admin or retiring a key cannot erase their retained copies. Neither MLS nor NIP-59 makes the join anonymous.
QUIC's current agent-stream binding provides no invite-link delivery and MUST NOT be treated as an alternative here.

## Executable examples

[Fixture documentation](../tests/README.md) describes the synthetic code, component, request/refresh, withdrawal and
preview vectors. They test canonical and cryptographic boundaries without claiming MLS/Nostr client interoperability.
