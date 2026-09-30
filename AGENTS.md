# AGENTS.md - marmot

Agent map for the Marmot protocol.

## Scope

This repository is the spec text for protocol surfaces a clean-room implementation would need. The canonical
directory tree, surface ownership model, and feature/component split live in `layout.md`.

Do not put darkmatter module names, database schemas, queue mechanics, local API shapes, or crate-specific test plans in
normative spec files. Put those in `implementation-model.md` or implementation-repository docs.

## Surface map

Each surface has a `README.md` (human orientation) and an `AGENTS.md` (agent operating rules: scope, read order,
boundary, verification). Start at the surface you are editing; its `AGENTS.md` carries the rules specific to it, so this
top-level file stays cross-surface only.

| Surface / doc | Start here |
| --- | --- |
| Stable invariants: identity, encodings, registries, errors | `foundation/AGENTS.md` |
| Required group flows and group-state transitions | `protocol-core/AGENTS.md` |
| Versioned MLS `app_data_dictionary` component bytes | `app-components/AGENTS.md` |
| How Marmot bytes move over a network (Nostr, QUIC) | `transports/AGENTS.md` |
| Optional or user-visible flows that span surfaces | `features/AGENTS.md` |
| Non-normative future directions for early feedback | `ideas/AGENTS.md` |
| Where new text belongs (canonical tree + ownership) | `layout.md` |
| How to write the spec (placement + detail rules) | `principles.md` |
| Map from deprecated MIPs to this spec's surfaces | `mip-coverage.md` |
| Non-normative mapping to this repo's code | `implementation-model.md` |

## Read Order

1. `README.md`
2. `layout.md`
3. `principles.md`
4. The `AGENTS.md` for the surface you are changing (it links its README and the owning docs).
5. `mip-coverage.md` only when mapping from deprecated MIPs.
6. `implementation-model.md` only when local implementation guidance matters.

## Rules

- Principles explain how to write the spec. Keep exact client requirements in the document for the surface they affect.
- Keep Marmot component ids in the private-use MLS range.
- Component major versions are represented by component ids. A breaking version gets a new component id and document.
- Component payloads are direct bytes for that component id. Do not add a generic Marmot envelope inside each component.
- Keep transport data in transport components. Nostr routing belongs in `marmot.transport.nostr.routing.v1`.
- Treat Nostr relays in the Nostr routing component as canonical signed group state for Nostr-routed groups.
- Keep app components in `app-components/`. Feature docs MAY require and reference them.
- Transport docs own outer envelopes, delivery addressing, publish targets, fetch rules, and transport validation.
- Protocol-core docs own required group flows and group-state transitions.
- Feature docs own optional or user-visible flows and cross-reference the surfaces that implement them.
- AppDataUpdate proposal forms and their default request path are defined in
  [`app-components/README.md`](app-components/README.md) ("GroupContext Update Processing").

## Verification

After editing spec text, review matches from these commands from the repository root:

```sh
rg -n \
  "Rust crate|database table|queue shape|retry worker|local API|test harness|\\bengine\\b|darkmatter" \
  .
rg -n \
  "CgkaEngine|PendingStateRef|drain_auto_publish|drain_auto_proposals|confirm_published|publish_failed" \
  .
rg -n \
  "Nostr kind|event id|relay URL|gift wrap|h tags?" \
  protocol-core
```

Matches in `AGENTS.md`, `layout.md`, `principles.md`, `implementation-model.md`, and explicit surface-boundary
disclaimers may be intentional. Review every match; do not treat the exemption list as an instruction to ignore it.
Matches in normative foundation, component, or lifecycle rules usually need closer review.
