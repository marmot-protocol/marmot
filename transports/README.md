# Transport specs

Status: adopted.

Transport specs describe how a network carries Marmot MLS bytes.

Foundation docs own identity, app payload shape, MLS choices, and shared wire rules. Protocol-core docs own group-state
convergence. App components own signed group routing state. A transport doc owns the outer envelope, delivery addresses,
publish and fetch rules, and transport-specific validation.

## Current transports

- [nostr.md](./nostr.md) - the primary binding: MLS group messages, welcomes, and KeyPackages over Nostr relays.
- [quic.md](./quic.md) - experimental raw QUIC binding for transient agent text stream previews (companion to
  [../features/agent-text-streams-quic.md](../features/agent-text-streams-quic.md)).

The proposed optional [Nostr invite-link extension v1](./nostr-invite-links.md) supplements the primary binding with
codes, encrypted previews and request/admin delivery. It retains the existing MLS group-message and Welcome envelopes.

## Transport document checklist

Each transport document MUST define:

- transport name and version;
- transport-specific group delivery address;
- recipient inbox address, if the transport has one;
- envelope bytes for MLS group messages, if the transport carries them;
- envelope bytes for MLS Welcome delivery, if the transport carries Welcomes;
- publish targets and acknowledgement rules;
- redundant target fanout and the lifecycle of outstanding first-attempt obligations, or an explicit statement that
  the binding does not carry required MLS group delivery;
- receive filters or fetch rules;
- duplicate ids and replay handling inputs;
- stale-input hints, if the envelope carries any;
- validation that runs before MLS peeling;
- required app components or capabilities;
- privacy constraints for metadata exposed to the transport.

Transport documents MAY define transport-specific Nostr kinds, HTTP routes, relay filters, mailbox topics, endpoint
sets, or other delivery mechanics.

Transport documents MUST NOT define Marmot account identity, inner Marmot app payload shape, MLS credential binding,
group-state branch selection, or app component payload bytes.

## Versioning

Git history is not a version-negotiation mechanism; an interop-visible change needs an explicit protocol versioning
hook.

Use the narrowest hook that fits the change:

- a new envelope version for a compatible outer-envelope change;
- a new Nostr kind, route, topic, or frame type for an incompatible transport envelope;
- a new app component id when signed transport state changes incompatibly;
- a new required capability when clients MUST negotiate support before using the change.
