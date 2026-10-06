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
- selection of the highest complete signed revision, reordered ancestors and conflicting consent branches;
- deterministic preview AEAD and hash, rejection of changed key, AAD or ciphertext;
- cross-bindings among code, component, preview and AAD, component signing domains and revision limits;
- withdrawal signatures, context binding, all five admin actions and status context/outcome/hash validation;
- admin-batch recipient ordering, uniqueness, counts and byte ceilings;
- preview UTF-8, version, policy, image discriminants and type/length consistency;
- canonical padded base64 and request-delivery evidence presence, size and operation constraints;
- worst-case preview, code, forwarded evidence and nested NIP-44 payload sizes;
- abstract invite-component transitions for its own candidate-parent authorization, immutable generations, self-demotion,
  admin-leaf removal, successor requirements and the disband exception;
- agreement among proposed registry entries, their owners, indexes and layout.

The fixture fields ending in `_hex` are exact bytes. `request_sign_content_hex` includes RFC 9420's two vector fields
and the component-scoped operation label inside the RFC label prefix. The context's consent key is Ed25519, derived from `consent_seed_hex`; the inbox and requester account
are x-only secp256k1 points derived from synthetic private scalars one and two. The preview has no image.
The ciphertext omits the nonce, which is in its separate fixture field, and includes the AEAD tag.
The literal signing assertion follows [draft-10 section 4.1](https://www.ietf.org/archive/id/draft-ietf-mls-extensions-10.html#section-4.1)
and [section 4.3](https://www.ietf.org/archive/id/draft-ietf-mls-extensions-10.html#section-4.3): the fixed base label is
`MLS Component`, followed by the component id and operation label, and SafeSignWithLabel passes that encoded label
to RFC 9420 SignWithLabel. This source-checked literal is not an independently produced MLS-stack vector; obtaining
and comparing such a vector remains an adoption requirement.

The transition helper assumes authenticated candidate-parent identities and resolved proposals; it is a policy model,
not an MLS Commit processor. Admin-policy changes, Remove authorization and last-leaf/admin coupling are assumed
already validated by the adopted core; this model does not test them. The receiver helpers are intentionally partial. They do not implement full relay URL parsing, RFC 8785, NIP-01/NIP-59,
KeyPackage validation, MLS Commit authentication, Welcome processing or MLS convergence. Implementers must run the
[required lifecycle scenarios](../features/group-invite-links.md#required-conformance-scenarios) with those stacks.
Admin examples validate record structure, device signatures and local bindings; their publication and envelope bytes
are placeholders, with no transport authentication. Context checks cover version, deadline and secp256k1 keys; they
do not validate the MLS account proof or the originating consent-key binding. Image examples check field structure,
not image decoding or rendering. The workflow checks fixture assertions only; passing it does not mean this draft
has been adopted.
