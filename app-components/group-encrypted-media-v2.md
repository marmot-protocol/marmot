# marmot.group.encrypted-media.v2

Status: adopted.

## Registry

- Component id: `0x800b`
- Name: `marmot.group.encrypted-media.v2`
- Location: GroupContext `app_data_dictionary`
- Default requirement: required for new app groups under a media-capable application profile; optional otherwise
- Owning feature: [encrypted-media.md](../features/encrypted-media.md)

## State

The component state is a full media policy replacement. It uses the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)); `allowed_locator_kinds` and
`default_blob_endpoints` are `Type items<V>` vectors (a QUIC variable-length byte length followed by the concatenated
items):

```text
struct {
  opaque locator_kind<V>;
} MediaLocatorKindV2;

struct {
  opaque locator_kind<V>;
  opaque base_url<1..2048>;
} BlobStoreEndpointV2;

struct {
  opaque              media_format<V>;
  MediaLocatorKindV2  allowed_locator_kinds<V>;
  BlobStoreEndpointV2 default_blob_endpoints<V>;
} EncryptedMediaPolicyV2;
```

`media_format` MUST be `encrypted-media-v2`. It is a fixed format constant, not independent version negotiation. It
cannot select another format under component id `0x800b`; another breaking format requires a new component id and
document.

The separately negotiated [view-once v1 component](group-view-once-v1.md) requires this policy as its locator and
endpoint policy. It does not change `media_format`, reinterpret ordinary v2 references, or let v2 support alone imply
view-once support. The view-once feature owns its additional attachment format and cryptographic domain.

`allowed_locator_kinds` is the list of locator kinds that media messages MAY use. The initial v2 locator kind is
`blossom-v1`.

`default_blob_endpoints` is the fallback list for upload and fetch. Each endpoint carries the locator kind it serves and
a normalized base URL.

Both lists are ordered, and their order is part of the canonical component state. For `default_blob_endpoints` the
order is the upload/fetch fallback priority, so it is semantically significant and MUST NOT be reordered. Encoders
preserve the producer's order for both lists; unlike `relays` in `marmot.transport.nostr.routing.v1` and `admins` in
`marmot.group.admin-policy.v1`, these lists are NOT sorted. Two policies that differ only in order are different
canonical values.

The default test/reference policy uses:

```text
media_format = "encrypted-media-v2"
allowed_locator_kinds = ["blossom-v1"]
default_blob_endpoints = [{ locator_kind = "blossom-v1", base_url = "https://blossom.primal.net/" }]
```

## Update

The update payload is a full replacement state:

```text
EncryptedMediaPolicyV2 EncryptedMediaPolicyUpdateV2;
```

Endpoint updates are group-state updates. They are not message metadata and do not rewrite existing media references.

## Validation

A policy state is valid if:

- `media_format` is exactly `encrypted-media-v2`
- every locator kind is 1..64 bytes and contains only lowercase ASCII letters (`a-z`), digits (`0-9`), and `-`
- `allowed_locator_kinds` is non-empty and contains at most 16 unique entries
- `default_blob_endpoints` is non-empty and contains at most 16 unique entries
- every endpoint locator kind appears in `allowed_locator_kinds`
- every endpoint base URL is 1..2048 bytes
- every endpoint base URL is a normalized `http` or `https` URL
- endpoints with userinfo, queries, fragments, or missing hosts are invalid

A base URL is normalized when it is byte-equal to its own parse-and-serialize output under the
[WHATWG URL Standard](https://url.spec.whatwg.org/) — the same normalization
[group-avatar-url-v1.md](group-avatar-url-v1.md) defines for avatar URLs.

State bytes MUST be canonical per [../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)
("Canonical decoding"): a decoder rejects state whose bytes differ from the canonical re-encoding of the decoded value
and MUST NOT trim, case-fold, normalize, or deduplicate a value while decoding it. List order and uniqueness are
producer-side rules; a decoder rejects a duplicate entry rather than removing it, and rejects a non-normalized URL or
locator kind rather than repairing it.

Component-state validity is the same for every member. Destination reachability, trust, and permission to contact an
endpoint are local application policy and MUST NOT affect whether the component bytes or their carrying Commit are
valid. Non-normative guidance for that contact decision is in
[../implementation-model.md](../implementation-model.md) ("Network destination safety").

## Authorization

Only an active admin MAY send a standalone encrypted-media policy update proposal.

Only an active admin MAY commit an encrypted-media policy update.

Commit authorization, including removal authorization, follows the shared candidate-parent rule in
[README.md](./README.md) ("Authorization Evaluation").

## Removal

Only an active admin MAY commit removal of this component.

This component MAY be removed in the same authorized Commit that removes it from resulting GroupContext
`app_components`; it is invalid if the resulting state still lists it as required. Application-profile policy is not
authenticated group state and MUST NOT independently make otherwise-valid component removal invalid.

The authenticated [view-once support invariant](group-view-once-v1.md#activation-and-authorization) requires this
component to remain present and required while view-once is required. Such a group cannot remove or stop requiring it.

## Migration

This component supersedes [`marmot.group.encrypted-media.v1`](./group-encrypted-media-v1.md). Component id `0x8008`
remains the frozen v1 policy and MUST NOT be reinterpreted as v2.

An authorized Commit MAY atomically add this component, replace `0x8008` with `0x800b` in resulting
`app_components`, and remove the v1 component. That migration does not rewrite historical v1 media references. A client
MAY retain legacy v1 rendering support; current-profile senders create only v2 references.
The additional [view-once v1 profile](../features/view-once-v1.md) is an explicitly negotiated exception, not a new
meaning of ordinary v2.
