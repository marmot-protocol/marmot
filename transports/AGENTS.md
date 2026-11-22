# AGENTS.md - transports

Agent operating rules for the transport surface. Read [`README.md`](README.md) for the human orientation and the
transport-document checklist; the cross-surface map is in [`../AGENTS.md`](../AGENTS.md).

## Scope

A transport doc owns the outer envelope, delivery addressing, publish/fetch rules, and transport-specific validation.
App-component payload bytes, including signed Nostr routing state, remain owned by `app-components/`. One file per
transport binding. Current bindings:
[`nostr.md`](nostr.md). [`quic.md`](quic.md) is retired and kept only as a record.

## Read order

1. [`README.md`](README.md) (transport-document checklist + Versioning).
2. [`../principles.md`](../principles.md) ("Keep identity, delivery addressing, and transport separate"; "Do not let
   transport behavior choose group state").
3. The transport file you are editing.

## Rules

- A transport doc MUST cover the README checklist (name/version, delivery addresses, envelopes, publish/fetch, dedup
  and replay inputs, validation-before-peeling, required capabilities, and metadata-privacy constraints).
- A transport doc MUST NOT define Marmot account identity, inner app-payload shape, MLS credential binding, group-state
  branch selection, or app-component payload bytes. It says how to find and deliver bytes, never which branch wins.
- Nostr routing and relays are signed group state owned by `marmot.transport.nostr.routing.v1`
  ([`../app-components/nostr-routing-v1.md`](../app-components/nostr-routing-v1.md)), not local hints.
- An interop-visible transport change needs an explicit hook (a new envelope version, a new kind/route/topic/frame
  type, a new app component id, or a new required capability). Git history is not a version-negotiation mechanism; an
  interop-visible change needs an explicit protocol versioning hook.

## Verification

- When adding, renaming, or removing a spec document, update [`../layout.md`](../layout.md) and this surface's
  [`README.md`](README.md) in the same change.
- Confirm the transport doc references only delivery mechanics, not group-state selection.
- Confirm Nostr kinds match those registered in [`../foundation/registries.md`](../foundation/registries.md) and that
  no removed kind (legacy `443`) lingers.

## Pointers

- Up to the cross-surface map: [`../AGENTS.md`](../AGENTS.md).
- Branch selection and convergence: [`../protocol-core/`](../protocol-core/README.md).
- Signed routing state: [`../app-components/nostr-routing-v1.md`](../app-components/nostr-routing-v1.md).
