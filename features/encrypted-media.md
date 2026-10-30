# Encrypted Media

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#t8-external-media-shared-credentials-and-deletion-limits).

Encrypted media lets a Marmot app payload refer to one or more encrypted blobs stored outside the MLS message.

This feature is for message-attached files: images, videos, audio, documents, and other binary attachments. Group
profile images are separate and remain owned by their own group image or avatar components.

## Surfaces

- App component: `marmot.group.encrypted-media.v2` owns the group media policy.
- MLS protocol: media key material comes from `MLS-Exporter("marmot", "encrypted-media", 32)`.
- App payload: kind-9 chat messages carry ordered NIP-92-style `imeta` tags.
- Blob storage: locators identify upload/fetch backends. Blossom is the first reference locator kind.

Blob upload and download are outside MLS group state. A failed upload or failed fetch does not change the group epoch.

## Current Version

The current media format is `encrypted-media-v2`.

New media references MUST use `encrypted-media-v2`. A legacy v1 reference is processed only under the frozen
[v1 profile](./encrypted-media-v1.md) when the client supports it; a receiver MUST NOT reinterpret another version as
v2.

## Message Shape

Media messages are regular Marmot kind-9 chat app events.

- `content` is the message-level caption.
- each attachment is one ordered `imeta` tag.
- a message MAY contain multiple `imeta` tags.
- per-attachment captions are out of scope for v2.

A V2 attachment `imeta` tag contains:

- `v encrypted-media-v2`
- one or more `locator <kind> <value>` fields
- `ciphertext_sha256 <hex>`
- `plaintext_sha256 <hex>`
- `nonce <24-hex-chars>`
- `m <canonical media type>`
- `filename <display filename>`
- optional `dim <width>x<height>` for render hints
- optional `thumbhash <value>` for previews

`blurhash` is invalid in `encrypted-media-v2`.

The source epoch is not an `imeta` field. It is the MLS epoch of the application message that carried the media tag.
Clients need that epoch to select the correct media exporter secret.

## Locator Kinds

`blossom-v1` is the initial locator kind.

For Blossom, `locator blossom-v1 <value>` stores an encrypted blob URL. Clients SHOULD verify that any content hash
encoded in the locator URL matches `ciphertext_sha256`.

The group component's `default_blob_endpoints` list supplies ordered fallback endpoints. A client MAY try explicit
locators first, then construct backend-specific fallback fetch URLs from the default endpoints and `ciphertext_sha256`.

For a `blossom-v1` endpoint, let `server_root` be its normalized `base_url` with all trailing `/` bytes removed, and let
`hash_hex` be the 64-character lowercase hex encoding of `ciphertext_sha256`. The fallback fetch URL is
`server_root || "/" || hash_hex`; clients fetch it with the
[Blossom BUD-01](https://github.com/hzrd149/blossom/blob/master/buds/01.md) `GET` operation and do not add an extension,
query, or fragment. The upload URL is `server_root || "/upload"` and uses the
[Blossom BUD-02](https://github.com/hzrd149/blossom/blob/master/buds/02.md) upload operation. An explicit locator returned
by the server is stored exactly as received after structural URL validation; it need not equal the fallback URL or be
WHATWG-canonical. Explicit locators are authenticated message metadata, not canonical group state or a cryptographic
input. Whether a client contacts the parsed destination is local application policy and does not affect reference
validity. Non-normative guidance for that contact decision is in
[../implementation-model.md](../implementation-model.md) ("Network destination safety").

The protocol is not Blossom-specific. Additional locator kinds require component policy support and backend-specific
upload/fetch rules.

## Media Type Canonicalization

Before using the MIME type in key derivation or AAD, senders and receivers MUST apply the shared Marmot media-type
algorithm in [../foundation/canonical-encoding.md](../foundation/canonical-encoding.md) ("Media type canonicalization").
The producer stores that canonical result in the `m` field. A receiver applies the algorithm to the stored `m` value
and rejects the reference unless the result is byte-for-byte equal to the stored bytes. Only those verified stored
bytes are the `media_type` input below; a receiver MUST NOT silently normalize a non-canonical `m` value for key
derivation or AAD.

## Filename Profile

`filename` is display metadata. Its value MUST be valid UTF-8, contain 1..255 bytes, and contain no U+0000 character.
Its UTF-8 bytes are preserved exactly; senders and receivers MUST NOT normalize or case-fold it.

## Key Derivation

`encrypted-media-v2` uses the group media exporter secret for the message source epoch:

```text
media_secret = MLS-Exporter("marmot", "encrypted-media", 32) at source_epoch
file_key     = HKDF-Expand(media_secret,
                           "encrypted-media-v2" || 0x00 || plaintext_sha256_bytes ||
                           0x00 || media_type || 0x00 || filename ||
                           0x00 || "key",
                           32)
```

HKDF is HKDF-SHA256. `media_secret` is used directly as the HKDF PRK (Expand only, no Extract step). This choice is
fixed and independent of the group's MLS ciphersuite; only the `MLS-Exporter` line is computed with the ciphersuite's
own hash, as MLS defines. The info bytes are exactly the concatenation shown: fields joined by single `0x00` separator
bytes, with no length prefixes. This inherited delimiter is unambiguous because `plaintext_sha256_bytes` has a fixed
32-byte length, the media-type profile permits only the listed ASCII token bytes and therefore excludes U+0000, and the
filename profile also forbids U+0000.

`media_secret` is key material. Clients MUST NOT publish, transmit, log, or expose it in diagnostics. A `file_key` is
key material too. A client MAY send a `file_key`, never `media_secret`, to the devices of its own account in a history
bundle ([account-sync.md](./account-sync.md), "History bundles"), so a device that joined after the epoch can open that
one file; it MUST NOT send it anywhere else. Clients SHOULD protect cached source-epoch media secrets at rest with
confidentiality controls appropriate to the platform. Clients SHOULD retain recent epoch media secrets long enough to
decrypt delayed media references according to local retention policy. If a past-epoch media secret is no longer
available, media from that epoch cannot be decrypted.

## Encryption

`encrypted-media-v2` uses ChaCha20-Poly1305.

```text
nonce             = random(12)
aad               = "encrypted-media-v2" || 0x00 || plaintext_sha256_bytes || 0x00 || media_type || 0x00 || filename
encrypted_content = ChaCha20-Poly1305.encrypt(file_key, nonce, plaintext, aad)
```

The AAD bytes are exactly the concatenation shown, with the same single `0x00` separators and no length prefixes.

For every encryption operation, the producer MUST sample a fresh, independent, uniformly random 12-byte nonce with a
cryptographically secure random generator and MUST NOT knowingly reuse a nonce with the same `file_key`. The derivation
produces the same `file_key` when the same plaintext hash, media type, and filename are sent again in the same epoch, so
a resend or retry still requires a new nonce. The deterministic key and protected `plaintext_sha256` also reveal
same-attachment equality to current group members, who can already derive the key and decrypt the attachment; they do
not expose that equality outside MLS.

`plaintext_sha256` is the SHA-256 hash of the original plaintext file. `ciphertext_sha256` is the SHA-256 hash of the
encrypted content and is the preferred content id for blob storage.

## Validation

A receiver MUST reject an encrypted media reference when its authenticated fields are malformed or it fails a
reference-level locator rule below. A receiver MUST reject a reference if:

- the `imeta` tag cannot be decoded
- the version is absent or not `encrypted-media-v2`
- no locator is present
- a locator has an empty kind or an empty value, or its value does not parse as a URL
- a `blossom-v1` locator uses a URL scheme other than `http` or `https`
- required MIME type, filename, ciphertext hash, plaintext hash, nonce, or version fields are missing
- the MIME type is not byte-for-byte canonical under the shared algorithm, or the MIME type or filename otherwise does
  not satisfy its profile above
- a single-occurrence field appears more than once in the `imeta` tag. Exactly the `locator` field repeats (one or
  more); every other field — `v`, `ciphertext_sha256`, `plaintext_sha256`, `nonce`, `m`, `filename`, `dim`, and
  `thumbhash` — occurs at most once. A receiver MUST reject a duplicate rather than picking a first or last occurrence,
  because `m`, `filename`, and `plaintext_sha256` feed the `file_key` derivation and the AEAD AAD: a first-wins decoder
  and a last-wins decoder would otherwise derive different keys for the same authenticated tag
- `ciphertext_sha256` or `plaintext_sha256` is not a 32-byte hex SHA-256 value
- `nonce` is not exactly 12 bytes encoded as 24 hex characters
- `blurhash` is present

Rejecting a reference is attachment-local: the receiver omits that `imeta` attachment from rendering. It MUST NOT
invalidate or drop the carrying app payload, its caption, or any other valid attachment.

After a reference passes those checks, fetching and rendering are attachment-availability decisions. Any of the
following makes that attachment unavailable and MUST NOT retroactively invalidate the reference or its carrying app
payload:

- the encrypted bytes cannot be fetched or do not match `ciphertext_sha256`
- decryption fails
- the plaintext SHA-256 does not match `plaintext_sha256`
- the decrypted media type or size violates application policy

A locator kind is NOT a validity condition. A well-formed locator whose kind is not in the group's
`marmot.group.encrypted-media.v2` `allowed_locator_kinds`, or whose kind the receiving client does not support, makes
that locator UNFETCHABLE: the client skips it, and the attachment is unfetchable if no usable locator or fallback
endpoint remains. An out-of-policy or unsupported locator MUST NOT invalidate the media reference and MUST NOT
invalidate or drop the containing message. The rationale is that media content is authenticated by its
`ciphertext_sha256` / `plaintext_sha256` and the AEAD independent of the locator, so an out-of-policy or otherwise wrong
locator cannot forge content; only the structural conditions above protect integrity.

Fetchability is judged at fetch time against the group's current `allowed_locator_kinds` and the receiving client's
current support and configuration, not against the source epoch. Because the locator policy no longer gates delivery,
validation needs no source-epoch policy snapshot.

## Migration

Encrypted media v2 supersedes the frozen [v1 feature](./encrypted-media-v1.md) and uses the new
[`marmot.group.encrypted-media.v2`](../app-components/group-encrypted-media-v2.md) component id. Current-profile senders
MUST NOT create v1 references.

A group migrating from v1 may atomically add the v2 component, replace the required component id, and remove the v1
component. Historical v1 references remain v1 and are not rewritten. A client MAY retain legacy rendering support, but
v1 support is not required for a newly created v2-only group.
