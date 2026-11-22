# MLS protocol

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#assumptions).

Marmot currently uses MLS as its continuous group key agreement (CGKA) protocol.

Implementations MAY use any MLS library if they produce and validate the same protocol bytes.

## Required ciphersuite

All Marmot implementations MUST support MLS ciphersuite `0x0001`:

`MLS_128_DHKEMX25519_AES128GCM_SHA256_Ed25519`.

Implementations MAY support additional MLS ciphersuites. A group can use only a ciphersuite supported by every current
member and by every KeyPackage used to add a new member.

## What Marmot uses from MLS

Marmot builds on:

- MLS groups and epochs;
- MLS Commits, Proposals, application-message content, and Welcomes;
- MLS KeyPackages and KeyPackage references;
- MLS `BasicCredential` for member credentials;
- the Marmot account identity proof LeafNode component;
- MLS capability advertisement and required capabilities.

The Marmot account identity carried in credentials is defined in [identity.md](./identity.md). The LeafNode component
that binds that identity to the MLS leaf signature key is defined in
[../app-components/account-identity-proof-v2.md](../app-components/account-identity-proof-v2.md).

## Handshake wire format

Marmot handshake messages — Commits and Proposals — use a single MLS wire format within a group, so the serialized
`MLSMessage` bytes of a given commit are deterministic: every member that processes the same commit recovers the same
bytes. The first profile uses MLS `PublicMessage` for handshake content. Every active transport binding MUST keep those
bytes confidential from untrusted delivery infrastructure and MUST define the mechanism it uses. That mechanism may be
a confidential message envelope or a confidential point-to-point transport; see the owning transport document for its
construction.

Pinning one wire format matters for convergence. MLS defines a single canonical TLS serialization for an `MLSMessage`,
and Marmot does not mix `PublicMessage` and `PrivateMessage` carriage for handshake content, so the commit identity used
by convergence is well defined: the `commit_digest` / `tip_digest` (see
[../protocol-core/convergence.md](../protocol-core/convergence.md)) and the dedup `message_id` (see
[wire-envelopes.md](./wire-envelopes.md)) are each `SHA-256` over the serialized commit `MLSMessage` bytes, and two
members never derive different digests for the same authenticated commit by choosing a different carriage.

## App components

New application-owned data SHOULD use MLS app components carried in `app_data_dictionary` at the location whose
lifecycle matches the data. Persistent group state belongs in GroupContext components. Per-member metadata and
application-owned leaf proofs normally belong in LeafNode components. KeyPackage- or GroupInfo-specific data belongs
in a component on that object.

The shared component model is defined in [../app-components/](../app-components/). Component ids are registered in
[registries.md](./registries.md).

## Custom extensions and proposals

Persistent group state SHOULD use app components. Leaf scope or security-critical validation is not, by itself, a reason
to allocate a custom extension. A custom MLS extension is appropriate only when a feature needs MLS protocol machinery
or extension semantics that the application-component mechanisms cannot express. A custom MLS proposal type is
appropriate only when the feature needs proposal semantics that a component update cannot express.

The current account identity proof uses a LeafNode application component, not a custom extension. Extension type
`0xf2f1` documents only the superseded v1 proof and is not part of the current profile. New custom extensions MUST be
registered in [registries.md](./registries.md).

## Commit-attached data, authenticated data, and exporters

Application data or an authorization proof whose lifetime is exactly one Commit SHOULD use an `AppEphemeral` proposal
rather than MLS `authenticated_data`. The owning component document MUST define the ComponentID, exact bytes,
validation, and authorization rules. A group that permits such proposals MUST negotiate support for the registered
`app_ephemeral` proposal type.

`AppEphemeral` data is included in the Commit transcript but does not change persistent GroupContext state. It is not an
`AppDataUpdate`, and it MUST NOT be retained as component state merely because a Commit carried it.

Marmot documents that write MLS `authenticated_data` MUST own their byte contribution and define how it composes with
other contributors.

SafeAAD is appropriate when a feature genuinely needs to contribute to the MLS `authenticated_data` field. It SHOULD
NOT be enabled solely to attach component-owned data to a Commit when `AppEphemeral` provides the required lifecycle.

If the GroupContext dictionary contains the upstream `safe_aad` component, the entire `authenticated_data` field MUST
be the draft-10 `SafeAAD` structure. No unframed prefix or suffix is permitted. A feature that enables `safe_aad` MUST
define its component id, require that id in the GroupContext `safe_aad` list, and require every member LeafNode to
advertise support for that SafeAAD component.

Marmot documents that use MLS exporter secrets MUST define:

- the exporter label;
- the exporter context;
- the output length;
- the consuming feature;
- any post-export key schedule or application key context.

Exporter labels and contexts MUST be domain-separated from every other Marmot exporter use. A feature that needs a
reusable epoch secret MUST say so in its owning document and MUST derive per-use keys with a feature-owned context below
the exporter output.

Registered Marmot exporter labels are listed in [registries.md](./registries.md).
