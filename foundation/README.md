# Marmot foundation

Status: adopted.

These files define the shared choices that make a Marmot implementation a Marmot implementation. Feature docs,
transport docs, and protocol-core docs SHOULD point here instead of restating these rules.

Foundation docs SHOULD change slowly. A change here usually means the whole protocol has changed, not just one feature.

## Files

- [identity.md](./identity.md) - Marmot account identity, MLS credentials, and capability negotiation.
- [authorization-proofs.md](./authorization-proofs.md) - common local Nostr-event proof envelope and validation rules.
- [account-identity-proof-v1.md](./account-identity-proof-v1.md) - superseded custom-extension account proof retained
  for legacy wire documentation.
- [key-packages.md](./key-packages.md) - KeyPackage meaning, discovery requirements, and lifecycle.
- [canonical-encoding.md](./canonical-encoding.md) - byte encoding rules used across Marmot-owned structures.
- [application-messages.md](./application-messages.md) - the unsigned Nostr-shaped payload inside MLS messages.
- [wire-envelopes.md](./wire-envelopes.md) - the split between application payloads, MLS bytes, and transport envelopes.
- [mls-protocol.md](./mls-protocol.md) - the MLS protocol pieces Marmot builds on.
- [conformance.md](./conformance.md) - canonical protocol-state equivalence and crash/restart scenarios for
  deterministic testing.
- [errors.md](./errors.md) - shared result and rejection vocabulary.
- [registries.md](./registries.md) - Marmot-owned ids and namespaces.
- [invite-link-records.md](./invite-link-records.md) - proposed device-consent and private admin records for invite links;
  not a baseline requirement.

## Layering

Marmot has three Nostr-related commitments, and they do not all live in the same layer:

- Marmot account identity is a Nostr public key. This is a foundation rule.
- Marmot app payloads use an unsigned Nostr event shape inside MLS. This is a foundation rule.
- Nostr relays are the first transport for Marmot bytes. This is a transport binding.

A future transport can replace the relay binding. It does not replace Marmot identity or the inner app payload shape
unless the Marmot protocol itself changes.
