# Marmot Protocol

Status: adopted.

This repository contains the Marmot protocol text, the version of the protocol ready for adoption. The MIP-era
documents describe a deprecated version of the protocol.

The spec is organized by protocol surface. Foundation documents define stable Marmot invariants. Protocol-core
documents define how Marmot groups move through MLS flows. Transport documents define how Marmot bytes move over a
network. App component documents define versioned group-state payloads. Feature documents describe optional or
user-visible flows and point to the surfaces they touch.

## What is Marmot?

Marmot is a protocol for end-to-end encrypted group messaging. It uses Nostr public keys for identity, Nostr
event-shaped app payloads inside MLS, and MLS as the continuous group key agreement layer. Those three choices are the
core protocol invariants; [principles.md](./principles.md) lists the full set, including redundant delivery and metadata
minimization.

Transport beyond that stays agnostic. Marmot clients currently move messages over Nostr relays, but the identity,
content, and key agreement layers do not depend on Nostr relays as the only possible transport.

Marmot is designed for group messaging that keeps working when parts of the transport fail. With Nostr, clients connect
to several relays at once, so a relay that goes down, gets blocked, or turns malicious does not break the group. Marmot
transports MUST support redundant delivery so a group does not depend on one server, relay, or endpoint.

The protocol also tries to expose as little metadata as the design allows. Perfect metadata privacy is not possible in a
decentralized messaging system, but Marmot SHOULD avoid new metadata leaks unless a feature cannot work without them.

## Review Guidance

When reviewing changes to the spec, focus on these questions:

- Are rules in the right surface?
- Are byte encodings exact enough?
- Are authorization and validation rules clear?
- Are transport-specific rules kept out of foundation and protocol-core docs?
- Could another implementation build the behavior and write conformance tests from the text?

## Spec Map

The canonical directory tree and per-surface ownership rules live in [layout.md](./layout.md). Start there when deciding
where new protocol text belongs. The writing rules behind that split live in [principles.md](./principles.md). Use
[mip-coverage.md](./mip-coverage.md) only as a historical map from the deprecated MIPs to this spec's surfaces, and
[implementation-model.md](./implementation-model.md) for the non-normative mapping to this repository's code.

The surfaces, each with its own section README (human orientation) and `AGENTS.md` (agent operating rules):

- [foundation/](./foundation/README.md) - stable Marmot invariants: identity, encodings, registries, errors.
- [protocol-core/](./protocol-core/README.md) - required group flows and group-state transitions.
- [app-components/](./app-components/README.md) - versioned MLS `app_data_dictionary` component bytes.
- [transports/](./transports/README.md) - how Marmot bytes move over a network (Nostr, QUIC).
- [features/](./features/README.md) - optional or user-visible flows that span surfaces.

Non-normative work in progress lives in [ideas/](./ideas/README.md): future protocol directions published for early
feedback. Nothing there is part of the protocol.

## Working Rules

- Keep implementation architecture out of normative protocol documents.
- Prefer short normative rules over long explanation.
- Use `MUST`, `SHOULD`, and `MAY` only when the sentence is meant to become normative.
- Put transport-specific fields in transport-specific components or transport docs.
- Put group flow semantics in protocol-core docs or group app components.
- A feature SHOULD usually point to one app component or add one component version.
- A feature SHOULD name every surface it changes.
- App component docs own component bytes. Feature docs own user-visible flows and the surfaces those flows touch.
