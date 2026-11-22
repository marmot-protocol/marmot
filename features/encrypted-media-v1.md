# Encrypted Media V1

Status: deprecated; retained for legacy wire documentation.

Encrypted media v1 lets a Marmot app payload refer to one or more encrypted blobs stored outside the MLS message.

## Surfaces

- App component: `marmot.group.encrypted-media.v1` owns the legacy group media policy.
- MLS protocol: media key material comes from `MLS-Exporter("marmot", "encrypted-media", 32)`.
- App payload: kind-9 chat messages carry ordered NIP-92-style `imeta` tags.
- Blob storage: locators identify upload/fetch backends. Blossom is the first reference locator kind.

Blob upload and download are outside MLS group state. A failed upload or failed fetch does not change the group epoch.

## Version

The legacy media format is `encrypted-media-v1`. Its rules are frozen in this document. Current-profile senders use
[`encrypted-media-v2`](./encrypted-media.md); a receiver MUST NOT apply v2 canonicalization or validity rules to a v1
reference.

## Message Shape

Media messages are regular Marmot kind-9 chat app events.

- `content` is the message-level caption.
- each attachment is one ordered `imeta` tag.
- a message MAY contain multiple `imeta` tags.
- per-attachment captions are out of scope for v1.

A V1 attachment `imeta` tag contains:

- `v encrypted-media-v1`
- one or more `locator <kind> <value>` fields
- `ciphertext_sha256 <hex>`
- `plaintext_sha256 <hex>`
- `nonce <24-hex-chars>`
- `m <canonical media type>`
- `filename <display filename>`
- optional `dim <width>x<height>` for render hints
- optional `thumbhash <value>` for previews

`blurhash` is invalid in `encrypted-media-v1`.

The source epoch is not an `imeta` field. It is the MLS epoch of the application message that carried the media tag.
Clients need that epoch to select the correct media exporter secret.

## Locator Kinds

`blossom-v1` is the initial locator kind.

For Blossom, `locator blossom-v1 <value>` stores an encrypted blob URL. Clients SHOULD verify that any content hash
encoded in the locator URL matches `ciphertext_sha256`.

The group component's `default_blob_endpoints` list supplies ordered fallback endpoints. A client MAY try explicit
locators first, then construct backend-specific fallback fetch URLs from the default endpoints and `ciphertext_sha256`.

The protocol is not Blossom-specific. Additional locator kinds require component policy support and backend-specific
upload/fetch rules.

## Media Type Canonicalization

The MIME type is canonicalized before it is used in key derivation and as AAD:

1. take the substring before the first `;`, dropping any parameters
2. trim leading and trailing ASCII whitespace
3. lowercase using ASCII case folding only
4. reject the reference if the result is empty or does not contain `/`
5. apply the canonical alias `image/jpg` -> `image/jpeg`

Sender and receiver MUST apply this identical algorithm. Adding an alias or normalization step is a breaking
media-version change.

## Key Derivation

`encrypted-media-v1` uses the group media exporter secret for the message source epoch:

```text
media_secret = MLS-Exporter("marmot", "encrypted-media", 32) at source_epoch
file_key     = HKDF-Expand(media_secret,
                           "encrypted-media-v1" || 0x00 || plaintext_sha256_bytes ||
                           0x00 || media_type || 0x00 || filename ||
                           0x00 || "key",
                           32)
```

HKDF is HKDF-SHA256. `media_secret` is used directly as the HKDF PRK (Expand only, no Extract step). This choice is
fixed and independent of the group's MLS ciphersuite; only the `MLS-Exporter` line is computed with the ciphersuite's
own hash, as MLS defines. The info bytes are exactly the concatenation shown: fields joined by single `0x00` separator
bytes, with no length prefixes.

`media_secret` is key material. Clients MUST NOT publish, transmit, log, or expose it in diagnostics. A `file_key` is
key material too: clients MUST NOT log it or expose it in diagnostics. A client MAY send a `file_key`, never
`media_secret`, to the devices of its own account in a history bundle ([account-sync.md](./account-sync.md), "History
bundles"), so a device that joined after the epoch can open that one file; it MUST NOT send it anywhere else. Clients
SHOULD protect cached source-epoch media secrets at rest with confidentiality controls appropriate to the platform.
Clients SHOULD retain recent epoch media secrets long enough to decrypt delayed media references according to local
retention policy. If a past-epoch media secret is no longer available, media from that epoch cannot be decrypted.

## Encryption

`encrypted-media-v1` uses ChaCha20-Poly1305.

```text
nonce             = random(12)
aad               = "encrypted-media-v1" || 0x00 || plaintext_sha256_bytes || 0x00 || media_type || 0x00 || filename
encrypted_content = ChaCha20-Poly1305.encrypt(file_key, nonce, plaintext, aad)
```

The AAD bytes are exactly the concatenation shown, with the same single `0x00` separators and no length prefixes.

`plaintext_sha256` is the SHA-256 hash of the original plaintext file. `ciphertext_sha256` is the SHA-256 hash of the
encrypted content and is the preferred content id for blob storage.

## Validation

A receiver MUST reject (invalidate) an encrypted media reference ONLY for structural-integrity or the frozen v1
destination rules. A receiver MUST reject a reference if:

- the `imeta` tag cannot be decoded
- the version is absent or not `encrypted-media-v1`
- any legacy media version string is present
- no locator is present
- a locator has an empty kind or an empty value, or its value does not parse as a URL
- a `blossom-v1` locator points at a host in the frozen v1 unsafe-host set (loopback, private, CGNAT, link-local,
  unspecified, documentation, benchmarking, reserved or broadcast, multicast, ULA, or an IPv6 transition prefix with
  an unsafe embedded address), or uses cleartext `http` to a non-loopback host
- required MIME type, filename, ciphertext hash, plaintext hash, nonce, or version fields are missing
- a single-occurrence field appears more than once in the `imeta` tag. Exactly the `locator` field repeats (one or
  more); every other field — `v`, `ciphertext_sha256`, `plaintext_sha256`, `nonce`, `m`, `filename`, `dim`, and
  `thumbhash` — occurs at most once
- `ciphertext_sha256` or `plaintext_sha256` is not a 32-byte hex SHA-256 value
- `nonce` is not exactly 12 bytes encoded as 24 hex characters
- `blurhash` is present
- the fetched encrypted bytes do not match `ciphertext_sha256`
- decryption fails
- the plaintext SHA-256 does not match `plaintext_sha256`
- the decrypted media type or size violates application policy

A locator kind is not a validity condition. A well-formed locator whose kind is outside the group's v1
`allowed_locator_kinds`, or whose kind the receiving client does not support, is unfetchable rather than invalid.

Host safety is the one locator property that invalidates a v1 reference, and it applies only to `blossom-v1` locators.
An unsafe-host or cleartext-`http` Blossom locator is rejected under the frozen v1 rule.

Fetchability is judged at fetch time against the group's current v1 policy and the receiving client's support and
configuration, not against the source epoch.

## Migration

V1 media references and component id `0x8008` remain v1 forever. They are not compatibility encodings for v2. A client
MAY retain legacy v1 rendering support, but current-profile senders create only v2 references.
