# Raw QUIC transport (agent text stream previews)

Status: retired.

Security context: [protocol threat model](../security-considerations.md#t9-preview-brokers-and-group-shared-stream-keys).

This binding carried the live preview records of the retired
[agent text streams](../features/agent-text-streams-quic.md) feature over QUIC, either directly between members or
through a broker. It carried nothing else: no KeyPackages, no Welcomes and no group messages.

A client MUST NOT open a connection under this binding or run a broker for it
([Retirement](../app-components/agent-text-stream-quic-v1.md#retirement)). Its ALPN identifiers,
`marmot.quic_stream.v1` for the direct path and `marmot.quic_broker.v1` for brokers, stay registered in
[../foundation/registries.md](../foundation/registries.md) so they are never reassigned.

The retired binding is in the [last full version of this document](https://github.com/marmot-protocol/marmot/blob/91617ebd6be614dd1ea56830b8bd0c4c7a8e5438/transports/quic.md).
