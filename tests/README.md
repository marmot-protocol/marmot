# Invite-link v1 fixtures

These are executable examples for the proposed [feature](../features/group-invite-links.md), not a production implementation.
All seeds and keys in [vectors/invite-links-v1.json](vectors/invite-links-v1.json) are public synthetic test values.
The package references and event ids are illustrative bytes, not real MLS or signed Nostr publications.

Run with Python 3.12 or later and `cryptography==50.0.0`:

```sh
python -m unittest discover -s tests -v
```

The tests cover:

- component size, minimal length prefixes, duplicate and unsorted ids/inboxes, malformed keys and invalid policy;
- complete-code Bech32m encoding, uppercase acceptance, checksum/variant/prefix/version rejection and padding;
- relay ordering, duplicates and WSS/count limits on the fixture's ASCII URL subset;
- exact request preimage and hash, signed refresh continuity, protected fields and withdrawal domain separation;
- deterministic preview AEAD and hash, rejection of changed key, AAD or ciphertext;
- cross-bindings among code, component, preview and AAD, component signing domains, revision limits, and status/admin record examples;
- worst-case preview, code, forwarded evidence and nested NIP-44 payload sizes;
- agreement among proposed registry entries, their owners, indexes and layout.

The fixture fields ending in `_hex` are exact bytes. `request_sign_content_hex` includes RFC 9420's two vector fields
and the component-scoped operation label inside the RFC label prefix. The context's consent key is Ed25519, derived from `consent_seed_hex`; the inbox and requester account
are x-only secp256k1 points derived from synthetic private scalars one and two. The preview has no image.
The ciphertext omits the nonce, which is in its separate fixture field, and includes the AEAD tag.

The receiver helpers are intentionally partial. They do not implement full relay URL parsing, RFC 8785, NIP-01/NIP-59,
KeyPackage validation, component Commit authorization, Welcome processing or MLS convergence. Implementers must run the
[required lifecycle scenarios](../features/group-invite-links.md#required-conformance-scenarios) with those stacks.
The workflow checks fixture assertions only; passing it does not mean this draft has been adopted.
