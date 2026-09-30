# Ideas

Status: non-normative.

Ideas are protocol directions we are still working out in the open. Each idea document explains what we want to build,
walks through it from the user's side, and lists the trade-offs and open questions, so people can give feedback before
anything becomes spec text.

Nothing in this directory is part of the Marmot protocol. An idea:

- does not assign component ids, extension types, proposal types, event kinds, or exporter labels;
- does not define wire bytes or validation rules;
- may change completely or be dropped.

Implementations MUST NOT treat an idea document as an interop surface.

## Current ideas

- [multi-device.md](./multi-device.md) - one account on several devices: linking, invites, device management, removal.

## From idea to spec

When part of an idea is settled, its rules move into the surface that owns them (foundation, protocol-core,
app-components, transports, or features) in the usual way, with ids registered in
[../foundation/registries.md](../foundation/registries.md). The idea document then shrinks to what is still open, or
is deleted once nothing is.

Feedback is welcome as issues or pull requests against the idea document.
