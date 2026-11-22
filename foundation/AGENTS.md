# AGENTS.md - foundation

Agent operating rules for the foundation surface. Read [`README.md`](README.md) for the human orientation; the
cross-surface map is in [`../AGENTS.md`](../AGENTS.md).

## Scope

Foundation owns the stable Marmot invariants only: Nostr-public-key identity, the unsigned Nostr-shaped app payload
inside MLS, MLS as the group key-agreement layer, the canonical byte rules, the Marmot-owned registries, and the shared
result/rejection vocabulary. A change here is a protocol-level change, not a feature tweak — change these files rarely
and deliberately.

## Read order

1. [`README.md`](README.md), then [`../principles.md`](../principles.md) ("Write the stable Marmot invariants once",
   "Define protocol bytes exactly").
2. The specific foundation file you are editing. The spine is [`identity.md`](identity.md),
   [`canonical-encoding.md`](canonical-encoding.md), and [`registries.md`](registries.md).

## Rules

- Do not restate foundation rules in feature, transport, or protocol-core docs — point here instead.
- [`registries.md`](registries.md) is the id registry of record. Every component id, proposal type, extension type,
  Nostr kind, and exporter label/context lives there; keep it in sync with the owning docs whenever an id changes.
- Any new signed, hashed, replay-stored, equality-compared, or state-selecting byte surface MUST follow the Marmot
  binary profile in [`canonical-encoding.md`](canonical-encoding.md), or explicitly name the encoding it uses instead.
- Never derive a delivery address from identity material (see [`identity.md`](identity.md), "Delivery addressing is
  separate"). The account inbox and the account's backup pointer are the deliberate exceptions.
- Keep transport specifics and darkmatter code names out of foundation; those belong in transport docs or
  [`../implementation-model.md`](../implementation-model.md).

## Verification

- When you add, rename, or remove a file, update both this directory's [`README.md`](README.md) "Files" list and the
  tree in [`../layout.md`](../layout.md) in the same change.
- When you assign or change any id, confirm it is reflected in [`registries.md`](registries.md) and matches the owning
  component/extension/proposal doc.

## Pointers

- Up to the cross-surface map: [`../AGENTS.md`](../AGENTS.md).
- Component-id assignments and component byte rules: [`../app-components/`](../app-components/README.md).
- Transport ownership boundary: [`wire-envelopes.md`](wire-envelopes.md) ("Transport envelopes") and
  [`../transports/`](../transports/README.md).
