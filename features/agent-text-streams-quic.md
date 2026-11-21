# Agent text streams over QUIC

Status: retired.

Security context: [protocol threat model](../security-considerations.md#t9-preview-brokers-and-group-shared-stream-keys).

This feature showed live previews of an agent's text over QUIC while the agent was still writing. A preview began with a
hidden kind `1200` stream start delivered through MLS. Its records went over the raw QUIC binding, and it ended with an
ordinary kind `9` chat message carrying `stream`, `stream-start`, `stream-hash` and `stream-chunks` tags. Nobody
used it in practice, and it is retired.

Clients no longer send or watch previews. Many existing groups still require the feature's component, so what clients
stop doing and what they keep doing for those groups is in the component's
[Retirement](../app-components/agent-text-stream-quic-v1.md#retirement) section.

The feature used these surfaces. All are retired, and none is ever reassigned
([../foundation/registries.md](../foundation/registries.md)):

- app component [`marmot.group.agent-text-stream.quic.v1`](../app-components/agent-text-stream-quic-v1.md) (`0x8006`),
  still supported in the existing groups that require it;
- app event kind `1200`;
- the exporter `MLS-Exporter("marmot", "agent-text-stream-quic", 32)`;
- the raw QUIC binding, [../transports/quic.md](../transports/quic.md).

Kinds `1201` and `1202`, which this document once reserved for agent activity and operation rows, are not retired. The
registry keeps them reserved for agent events.

A future design for live agent text will use new ids. The retired design is in the
[last full version of this document](https://github.com/marmot-protocol/marmot/blob/91617ebd6be614dd1ea56830b8bd0c4c7a8e5438/features/agent-text-streams-quic.md).
