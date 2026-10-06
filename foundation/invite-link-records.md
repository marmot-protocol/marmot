# Invite-link records v1

Status: proposed; not adopted. This document owns the feature's canonical records and device-consent signature.
Delivery envelopes are owned by the [Nostr extension](../transports/nostr-invite-links.md), state by the
[invite-links component](../app-components/group-invite-links-v1.md), and processing by the
[feature](../features/group-invite-links.md).

## Encoding and scope

Structures below use the [Marmot binary profile](canonical-encoding.md). Variable fields have shortest QUIC lengths.
Decoders MUST consume the entire record, reject unknown discriminants, reject out-of-bound values, and reject
non-canonical bytes rather than normalize them. Fixed identifiers and hashes are bytes, not hex text.
This first version supports the required MLS ciphersuite `0x0001` only. Other suites require a future record version.

```text
struct {
  uint16 version;
  opaque inbox_pubkey[32];
  opaque link_id[32];
  opaque request_id[32];
  opaque requester_account[32];
  opaque consent_key[32];
  uint64 valid_until;
} InviteRequestContextV1;

struct {
  InviteRequestContextV1 context;
  uint32 revision;
  opaque previous_request_hash[32];
  opaque bearer[32];
  opaque key_package_ref[32];
  opaque transport_offer<1..8192>;
} InviteRequestTBSV1;

struct {
  InviteRequestTBSV1 tbs;
  opaque consent_signature[64];
} InviteRequestV1;
```

`version` is exactly one. `request_id` is fresh random bytes created for this account-device attempt; retries preserve
it. Revision values are zero through seven; greater values are invalid in v1. The public keys are valid keys for their stated algorithms. `requester_account` is the account in the offered
KeyPackage's BasicCredential; its adopted
[account identity proof v2](../app-components/account-identity-proof-v2.md) authorizes the offered leaf key.
`key_package_ref` is RFC 9420 MakeKeyPackageRef over the inner KeyPackage, not a publication event id or slot id.
`transport_offer` is the canonical Nostr offer defined by the transport owner; it binds the exact publication and
delivery coordinates into the request, without making those coordinates identity or membership authority.
`valid_until` is a nonzero Unix time in seconds no greater than `9007199254740991`, fixed for the entire context.
Admission and tombstone retention use it as defined by the feature; it is separate from link and package expiry.

The signature uses the pinned [MLS extensions draft-10 SafeSignWithLabel](https://datatracker.ietf.org/doc/html/draft-ietf-mls-extensions-10#section-4.3)
with the Ed25519 private key corresponding to `consent_key`, component id `0x800e`, operation label `request`, and
content equal to the exact encoded `InviteRequestTBSV1`. Verification uses SafeVerifyWithLabel with the same inputs.
The draft's encoded ComponentOperationLabel contains base label `MLS Component`, that uint16 component id and the
operation label. RFC 9420 SignWithLabel then prefixes those encoded label bytes with `MLS 1.0 ` inside SignContent.
Both upstream structures use RFC 9420 `<V>` variable lengths (one, two or four bytes, maximum `2^30-1`), not fixed TLS
lengths. For these bounded inputs their minimal encodings equal the Marmot profile. No independent IANA signature
label is introduced. The signature proves originating-leaf consent independently of the account-to-leaf proof.

For revision zero, `previous_request_hash` is all zero bytes and `consent_key` equals the offered LeafNode signature
key. Define `request_hash = SHA-256(encoded InviteRequestV1)`. A refresh increments revision by exactly one, names
the immediately preceding `request_hash`, preserves the complete context and bearer, and is signed by the original
`consent_key`. The refreshed package carries its own valid account identity proof. Its leaf key may differ.
All ancestors through revision zero MUST be available and validated before a refresh is eligible.
An account match or a replaceable publication slot match does not prove originating-device continuity.
For new admission preparation, use the highest fully validated revision in the unambiguous chain. An older revision
MUST NOT start a new Add after that refresh is validated. A missing ancestor does not supersede a validated revision;
retain the incomplete refresh as a recoverable prerequisite. Already prepared obligations keep their adopted
publication and reconciliation rules rather than being silently replaced by new bytes.

Two distinct valid requests at the same revision under one context constitute `conflicting_refresh`. They MUST NOT
be resolved by arrival time, hash ordering or a manual choice of one conflicting branch. New admission preparation
stops for that context until the
requester withdraws it and starts a fresh request id with renewed consent. `conflicting_refresh` is a feature-local
request-state annotation, not a new inbound rejection or MLS convergence disposition: the individual signed records
remain valid. A blocked admission action maps to `authorization_failed` for ambiguous consent under the
[shared vocabulary](errors.md). Exact byte duplicates are idempotent.
Missing ancestors are recoverable missing prerequisites, not rejection.

## Withdrawal

```text
struct {
  InviteRequestContextV1 context;
} InviteWithdrawalTBSV1;

struct {
  InviteWithdrawalTBSV1 tbs;
  opaque consent_signature[64];
} InviteWithdrawalV1;
```

SafeSignWithLabel uses component id `0x800e`, operation label `withdrawal`, and the encoded TBS, with the same
ComponentOperationLabel and SignContent framing as requests. The signer is the original consent key
from a validated revision-zero request. Withdrawal closes that context across all revisions and never removes a
member. It may arrive before the original request; processing waits for the original binding. If the consent key
is lost, the account may start a fresh request but MUST NOT forge continuity or a withdrawal for that device.
An application may retain that signing key while consent remains open, subject to its existing MLS key lifecycle;
it MUST NOT retain a deleted KeyPackage initialization key or relax adopted deletion rules to support refresh.

## Status

```text
struct {
  InviteRequestContextV1 context;
  opaque request_hash[32];
  uint8 outcome;
  opaque commit_hash[32];
  opaque welcome_hash[32];
} InviteStatusV1;
```

Outcomes are `observed=0`, `declined=1`, `invited=2`, and `retired=3`. Unknown values are invalid. For observed,
declined or retired, both hashes are zero. For invited they are SHA-256 hashes of the complete serialized
`MLSMessage` Commit and Welcome
respectively; zero hashes are invalid. The status is authenticated by its transport's admin-account seal.
A status carries no independent proof of current group-admin authority to an outsider. The app MUST attribute
observed/declined/retired claims to that account, not present them as group consensus. A retired notice reports that
the invitation generation was withdrawn, not that this person was rejected or removed from membership.
Invited is provisional until a
matching Welcome passes the adopted join flow and its GroupInfo signer account equals the status author.
The client MUST NOT wait for a status to process an otherwise valid ordinary Welcome.

## Private admin records

```text
struct {
  opaque group_id<1..255>;
  uint64 source_epoch;
  opaque link_id[32];
  uint8 action;
  opaque body<1..24576>;
} InviteAdminRecordV1;
```

`group_id` is the MLS group id and stays inside recipient-encrypted records. `source_epoch` identifies the group
state in which the enclosing MLS application message was authored. Actions and exact body encodings are:

- `grant=0`: encoded `InviteLinkV1`, then inbox private key `[32]`, then `opaque transport_code<1..8192>` containing
  the complete code in the transport's canonical binary encoding. It carries the bearer, preview key and request
  discovery coordinates; a grant MUST NOT depend on group routing or external lookup to reconstruct them.
- `forward_request=1`: an encoded `InviteRequestV1`, followed by the transport's length-prefixed authenticated
  publication evidence for that offer.
- `withdrawal=2`: an encoded `InviteWithdrawalV1`.
- `declined=3`: an encoded `InviteStatusV1` whose outcome is declined.
- `invited=4`: an encoded `InviteStatusV1` whose outcome is invited.

No trailing bytes are allowed inside a body. A grant's entry id equals the enclosing `link_id`; the private key
derives its inbox public key. The transport code's id and inbox match that entry, and its bearer hashes to the
entry's commitment. A grant alone cannot authenticate the preview:
the descriptor and plaintext commitment are checked separately. For other actions the context's link id and inbox
must match the relevant invitation generation. The transport validates the admin sender binding, and the feature
validates source/current authorization. Forwarded requester records retain their device signatures.
Unknown actions fail closed for this version; they do not create decisions or change membership.

## Admin app batches

The proposed kind `461` unsigned Marmot app event has empty tags and padded-base64 content of exactly this batch:

```text
struct {
  opaque recipient_account[32];
  opaque transport_envelope<1..90000>;
} InviteAdminEnvelopeV1;

struct {
  InviteAdminEnvelopeV1 envelopes<1..262144>;
} InviteAdminBatchV1;
```

Each batch contains one through sixteen unique recipients sorted by account bytes. Producers MUST split by both
recipient count and total encoded byte length; sixteen full-sized envelopes do not fit one batch. Larger sets or
payloads use multiple batches. The field's opaque envelope bytes and validation are owned by the
[Nostr binding](../transports/nostr-invite-links.md#admin-delivery-inside-mls). The batch adds no membership or
current-admin authority beyond the authenticated source/current-state checks in the feature.

## Versioning

Breaking record or consent-signature changes require a new record version and the corresponding transport/app-event
kind. Implementations MUST NOT reinterpret unknown versions as v1. Account identity proofs retain their own adopted
component version and MUST NOT be repurposed as request-consent signatures.

## Examples and verification

[Synthetic fixtures](../tests/README.md) provide complete bytes and hashes for request/refresh and withdrawal signing.
The fixture package/publication references are illustrative; they are not signed MLS KeyPackages or relay events.
Implementers still need the feature's lifecycle and authorization conformance scenarios with real MLS and Nostr stacks.
