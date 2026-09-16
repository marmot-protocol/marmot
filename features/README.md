# Feature specs

Status: adopted.

Feature specs describe user-visible Marmot behavior that spans several surfaces.

A feature doc SHOULD explain the flow, name the protocol surfaces involved, and point to the documents that own exact
bytes. It MUST NOT copy component schemas, MLS structures, transport event shapes, or foundation rules.

Features are optional or user-visible behavior built from foundation, protocol core, transports, and app components.

Mandatory protocol flows belong in [../protocol-core/](../protocol-core/) or [../foundation/](../foundation/), even when
they used to be described in a MIP. The old-to-new MIP map lives in [../mip-coverage.md](../mip-coverage.md).

## Current feature docs

- [content-moderation.md](./content-moderation.md) - draft group reports, admin dismissal labels, and admin deletion.
- [encrypted-media.md](./encrypted-media.md) - current v2 message-attached encrypted blobs.
- [encrypted-media-v1.md](./encrypted-media-v1.md) - frozen legacy encrypted-media v1 wire behavior.
- [agent-text-streams-quic.md](./agent-text-streams-quic.md) - experimental QUIC-backed live previews for agent text
  streams, anchored by normal durable final messages.
- [push-notifications.md](./push-notifications.md) - optional native push notification flow.
- [multi-device.md](./multi-device.md) - branch-draft multi-device support.

## Relationship to app components

App components stay in [../app-components/](../app-components/).

A feature MAY require one or more app components. The feature doc explains when the feature reads or changes the
component data. The component doc owns the component id, valid locations, bytes, validation, lifecycle, authorization,
replacement or removal, and migration.

For example, a group profile feature can point to `marmot.group.profile.v1`. The group profile component still owns the
two UTF-8 fields and their length limits.

## Feature document checklist

Each feature document SHOULD define:

- feature name and status;
- user-visible behavior;
- required capabilities, proposal types, app components, message kinds, or transports;
- creation or activation flow;
- update flow;
- authorization;
- interaction with protocol-core convergence and retained history;
- failure behavior that affects interop;
- migration from MIP-era behavior, if any.

## Versioning

Git history is not a version-negotiation mechanism; an interop-visible change needs an explicit protocol versioning
hook.

Use component ids for app component state versions. Use proposal ids for custom MLS proposal versions. Use event kinds
or payload versions for app messages. Use a new feature document name when the high-level flow changes enough that
readers need both versions side by side.

Compatible clarifications can update an existing feature doc in place.
