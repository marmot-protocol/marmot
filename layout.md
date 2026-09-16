# Spec layout

Status: adopted.

The deprecated MIP set mixes stable protocol surfaces with feature behavior. This
spec organizes docs around the surface an implementer is building.

MIPs remain useful history. This repository records their adopted replacements in [`mip-coverage.md`](mip-coverage.md);
the frozen MIP repository is not maintained as part of this specification.

## Top Level

```text
README.md
layout.md
principles.md
mip-coverage.md
foundation/
  README.md
  identity.md
  authorization-proofs.md
  account-identity-proof-v1.md
  key-packages.md
  canonical-encoding.md
  application-messages.md
  wire-envelopes.md
  mls-protocol.md
  conformance.md
  errors.md
  registries.md
protocol-core/
  README.md
  group-setup.md
  joining.md
  group-messaging.md
  member-departure.md
  group-state.md
  publish-lifecycle.md
  inbound-processing.md
  convergence.md
  retained-history.md
  durability.md
app-components/
  README.md
  group-profile-v1.md
  group-blossom-image-v1.md
  admin-policy-v1.md
  nostr-routing-v1.md
  message-retention-v1.md
  agent-text-stream-quic-v1.md
  group-avatar-url-v1.md
  group-encrypted-media-v1.md
  group-encrypted-media-v2.md
  group-lifecycle-v1.md
  account-identity-proof-v2.md
  multi-device-join-authorization-v1.md
transports/
  README.md
  nostr.md
  quic.md
features/
  README.md
  content-moderation.md
  encrypted-media.md
  encrypted-media-v1.md
  agent-text-streams-quic.md
  push-notifications.md
  multi-device.md
implementation-model.md
```

This tree is the canonical list of spec documents and per-surface `README.md` indexes. Repository-operating files such
as `AGENTS.md`, and compatibility symlinks, are not entries in the normative spec tree. When you add, rename, or remove
a spec document, update this tree in the same change, and update the matching index in the surface's `README.md` (and
`foundation/registries.md` when an id changes). The subdir `AGENTS.md` files carry this as a verification step.

## Foundation

Foundation documents define shared surfaces:

- identity, credentials, KeyPackages, and capability negotiation
- canonical encodings
- app payload shape
- wire envelopes
- MLS protocol choices
- canonical protocol-state equivalence, including crash/restart conformance testing
- error and stale-result taxonomy
- registries for component ids, proposal ids, and extension ids

Foundation documents SHOULD change rarely. They carry stable Marmot invariants: Nostr identity, unsigned Nostr-shaped
app payloads, MLS group security, canonical byte rules, capability advertisement, and Marmot-owned registries.

## Protocol Core

Protocol-core documents define protocol behavior that every transport and feature relies on:

- group setup
- joining through MLS Welcomes
- group messaging
- member departure
- local publish lifecycle
- inbound message processing
- group lifecycle states
- duplicate handling
- convergence and branch selection
- retained history requirements
- non-application input classification

These documents describe required transitions and validation rules. They do not prescribe local module names, queues,
database schemas, or API boundaries.

## App Components

App component documents define custom MLS app components carried in `app_data_dictionary`. The component document
chooses the location whose lifecycle matches the data: GroupContext for authenticated group state, LeafNode for
per-member data, KeyPackage for package-specific data, or GroupInfo for data attached to one GroupInfo object.

The authoritative component-document checklist is
[app-components/README.md](./app-components/README.md) ("Common Rules"). Component ids carry the major version; there is
no generic separate payload version field.

Most feature-owned group state and per-member application metadata SHOULD land here.

## Transports

Transport documents define how Marmot bytes move over a network.

Transport documents MAY define transport-specific delivery addresses, event shapes, relay or endpoint selection, and
fetch rules. They MUST follow the ownership boundary in
[transports/README.md](./transports/README.md): transport documents do not define identity, inner app payloads, MLS
credential binding, branch selection, or app-component bytes.

## Features

Feature documents describe optional or user-facing behavior that spans components or protocol surfaces.

A feature document SHOULD mostly reference foundation, protocol-core, and component documents. It SHOULD NOT duplicate
their rules.

Feature documents stay separate from app components. The feature doc explains the flow. The app component doc owns the
component bytes. Encrypted media follows that split: [app-components/group-encrypted-media-v2.md](./app-components/group-encrypted-media-v2.md)
owns group policy bytes, while [features/encrypted-media.md](./features/encrypted-media.md) owns message attachment
format, key derivation, and AEAD behavior.

When a feature has an interop-visible breaking change, the owning document MUST name the new version in a capability,
component id, proposal id, event kind, or feature document. Git history is not a version-negotiation mechanism; an
interop-visible change needs an explicit protocol versioning hook.

## Implementation Model

The implementation model is non-normative. It can map the protocol to local terms used by this repository, including
local APIs, queues, storage choices, and diagnostics.

## MIP Coverage

This spec keeps MIP history separate from normative organization.

Use [mip-coverage.md](./mip-coverage.md) to see where MIP-era concerns moved. The stable spec SHOULD be readable
without replaying the MIP history.
