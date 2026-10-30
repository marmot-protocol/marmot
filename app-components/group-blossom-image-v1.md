# marmot.group.blossom.image.v1

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#t8-external-media-shared-credentials-and-deletion-limits).

## Registry

- Component id: `0x8002`
- Name: `marmot.group.blossom.image.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: optional

This component is for encrypted group images stored through Blossom. It is not the generic group-image model for every
possible image reference.

A group that wants to reference a plain URL, an IPFS object, an application-owned CDN object, or another blob store
SHOULD use a different component. In particular, [`marmot.group.avatar-url.v1`](group-avatar-url-v1.md) is the
plain-`https` alternative. A group MAY carry both components at once; when both are present, the URL avatar wins for
rendering. [`group-avatar-url-v1.md`](group-avatar-url-v1.md) ("Coexistence and precedence") owns that precedence rule.

## State

```text
struct {
  opaque image_hash<0..32>;
  opaque image_key<0..32>;
  opaque image_nonce<0..12>;
  opaque image_upload_key<0..32>;
  opaque media_type<0..128>;
} MarmotGroupBlossomImageV1;
```

An absent image is encoded as all fields empty.

When an image is present:

- `image_hash` is exactly 32 bytes
- `image_key` is exactly 32 bytes
- `image_nonce` is exactly 12 bytes
- `image_upload_key` is exactly 32 bytes. It is the secret key that authorizes Blossom writes for this blob (see Image
  bytes). It is not the content-decryption key; that is `image_key`.
- `media_type` is non-empty valid UTF-8, at most 128 bytes, and names the decrypted image's media type (see Image
  bytes)

The component stores the cryptographic metadata clients need for a Blossom-backed image. It does not define the Blossom
upload or download request flow, server selection, relay behavior, or CDN behavior.

Server selection is intentionally an application-profile concern rather than component state. Two applications need a
shared out-of-band Blossom service/discovery profile to exchange this image; Marmot v1 does not make independently
chosen servers interoperable. A client with no configured way to locate `image_hash` treats the image as unavailable,
without invalidating the component or its carrying commit.

## Image bytes

The image is encrypted, content-addressed, and stored as one opaque blob. The component fields bind to that blob as
follows.

Encryption is ChaCha20-Poly1305 keyed with `image_key` and the 12-byte `image_nonce`:

```text
aad            = "marmot-group-image-v1" || 0x00 || media_type
encrypted_blob = ChaCha20-Poly1305.encrypt(image_key, image_nonce, plaintext_image, aad)
```

The AAD bytes are exactly the concatenation shown: the ASCII version label `marmot-group-image-v1`, one `0x00`
separator byte, and the canonical media type bytes, with no length prefixes. `media_type` is canonicalized with the
frozen algorithm in [../features/encrypted-media-v1.md](../features/encrypted-media-v1.md) ("Media Type
Canonicalization"); the producer stores the canonical form, and the AAD input on both ends is the canonical media type
derived from the stored `media_type` field. The encrypted blob is the AEAD output, including the 16-byte authentication
tag.

A producer MUST generate a fresh random `image_key` and `image_nonce` for every new image and MUST NOT reuse a
key-nonce pair.

`image_hash` is the SHA-256 hash of the encrypted blob. It is the blob's content id: the producer uploads the encrypted
blob under that hash, and a fetching client addresses the blob by it. A fetching client MUST verify that the fetched
bytes hash to `image_hash` before decrypting.

`media_type` describes the decrypted image, not the encrypted blob. The encrypted blob is opaque bytes to the blob
store.

`image_upload_key` is the secret key of a Nostr keypair generated fresh for this image. It authorizes Blossom writes:
the producer signs the Blossom upload authorization event with this key, so the corresponding public key is the blob's
server-side write credential. Because the secret travels inside the MLS-protected component, any current member can
sign later authorization events for the same blob. A producer MUST generate a fresh keypair for every new image and
MUST NOT use an account identity key, so the blob store cannot link the blob to a Marmot account.

This shared credential is an accepted v1 availability limitation. Any current member, and any former member that
retained the secret, can issue whatever write or delete authorization the chosen Blossom server accepts for that key.
The component's admin gate protects only updates to canonical group state; it cannot revoke an already-disclosed
server-side capability. Deletion makes the referenced image unavailable but does not change or invalidate group state.
An admin can restore availability only by uploading an image under a fresh `image_upload_key` and committing the full
replacement component state. Servers with narrower or expiring authorization policies may reduce this risk, but those
policies are outside Marmot v1.

Blob upload and download are outside MLS group state. A fetch, hash-mismatch, or decryption failure is an
application-level fetch failure: the image is unavailable, and the failure MUST NOT invalidate the component state or
the commit that carried it.

Fixed test vectors for this scheme will be published with the conformance fixtures.

## Update

The update payload is a full replacement state:

```text
MarmotGroupBlossomImageV1 MarmotGroupBlossomImageUpdateV1;
```

Updating the image replaces every field. Clearing the image sends the empty state.

## Validation

A non-empty image state is valid only if all cryptographic fields have their exact required lengths.
Its `media_type` MUST be non-empty valid UTF-8, at most 128 bytes, and byte-equal to the canonical media type produced
by the algorithm referenced under "Image bytes."

Mixed partial states are invalid. For example, a state with `image_hash` set and `image_key` empty is invalid.

## Authorization

Only an active admin MAY send a standalone image update proposal.

Only an active admin MAY commit an image update.

Commit authorization, including removal authorization, follows the shared candidate-parent rule in
[README.md](./README.md) ("Authorization Evaluation").

## Removal

Only an active admin MAY commit removal of this component.

Removal is equivalent to the empty image state for application rendering.

## Migration

This component carries the `image_hash`, `image_key`, `image_nonce`, and `image_upload_key` fields from the MIP-01
`marmot_group_data` extension (see [../mip-coverage.md](../mip-coverage.md)), plus `media_type`. v1 is the first
versioned form; a breaking change gets a new component id and file.
