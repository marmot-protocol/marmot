# marmot.group.agent-text-stream.quic.v1

Status: retired; still supported for existing groups.

## Registry

- Component id: `0x8006`
- Name: `marmot.group.agent-text-stream.quic.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: none. New groups MUST NOT include it ([Retirement](#retirement)).
- Owning feature: [agent-text-streams-quic.md](../features/agent-text-streams-quic.md) (retired)

## Retirement

The raw QUIC live preview of agent text is retired. Clients no longer send or watch live previews. Clients that
implemented it added this component to every group they created, with the `receive` role required, so many existing
groups still require it. This section says what clients stop doing and what they keep doing so those groups keep
working. It overrides the rest of this document, the [feature document](../features/agent-text-streams-quic.md) and
the [QUIC binding](../transports/quic.md) wherever they disagree. A future design for live agent text will use new ids;
it will not revive this one.

### What clients stop doing

- A client MUST NOT include this component in a new group. It MUST NOT add this component to an existing group's
  required `app_components`, and MUST NOT propose or commit an update that replaces this component's state.
- A client MUST NOT send a kind `1200` stream start or a QUIC preview record. It MUST NOT put a `stream`,
  `stream-start`, `stream-hash` or `stream-chunks` tag on a kind `9` message it sends.
- A client MUST NOT connect to an endpoint candidate in a kind `1200` stream start.

These rules govern what a client sends and does. They do not change which Commits are valid: a client still accepts a
Commit from an older client that updates this component, if the Commit passes [Authorization](#authorization) and
[Validation](#validation).

### Receiving from older clients

Older clients may still send stream starts and tagged final messages.

- A client SHOULD NOT display a kind `1200` stream start.
- A client MUST treat a kind `9` message that carries the `stream`, `stream-start`, `stream-hash` or `stream-chunks`
  tags as an ordinary chat message. It MAY ignore those tags, and MUST NOT use them to hide, delay, replace or verify
  the message.

### What clients keep doing

A group that requires this component can add only members whose KeyPackage advertises support for its component id
(`0x8006`) and for the `receive` role capability (`0xf2d1`). A client that stopped advertising them could no longer be
added to such a group, or add its own new devices to it.

- A client SHOULD keep advertising support for this component and the `receive` role capability in its KeyPackages and
  in its leaves.
- A client that advertises support for this component MUST validate its state as in [Validation](#validation) on
  every Commit, including the member role check. Validation decides whether a Commit is valid, so a client that skipped
  it could accept a Commit that other members reject.
- Supporting `receive` needs no QUIC code: it is this validation and the receiving rules above.
- As for any required component, a client MUST keep supporting this component while it is a member of a group that
  requires it ([README.md](./README.md#advertising-support)).

The `send` (`0xf2d2`) and `fanout` (`0xf2d4`) roles are retired. A client SHOULD stop advertising them, in new
KeyPackages and in its next replacement LeafNode in each group. It cannot drop a role from its leaf in a group whose
state still requires that role ([Validation](#validation)). No group is known to require either role: groups were
created with `required_member_roles` set to `receive` and `allowed_member_roles` set to `receive` and `send`, and no
client offered a way to change that.

### Removing the component from a group

An active admin MAY stop requiring this component and remove its state, in one Commit, as in
[Removal](#removal). No client is required to. A client MUST NOT commit this removal unless its user asks it to. The
removal changes nothing a client following this section does, and a removal made automatically would have every
admin's client committing in the same groups at once. After the removal, members MAY stop advertising support for this
component in that group ([README.md](./README.md#advertising-support)), and the group can add members that do not
support it.

### Reserved identifiers

None of these is ever reassigned:

- component id `0x8006` and the name `marmot.group.agent-text-stream.quic.v1`;
- extension types `0xf2d1`, `0xf2d2` and `0xf2d4`, and their role capability names;
- app event kind `1200`;
- the exporter label and context `"marmot"`, `"agent-text-stream-quic"`;
- the ALPN identifiers `marmot.quic_stream.v1` and `marmot.quic_broker.v1`.

They stay listed in [../foundation/registries.md](../foundation/registries.md). Kinds `1201` and `1202` are not part
of this retirement; the registry keeps them reserved for agent events.

## State

This component records the group-level policy for the retired raw QUIC live preview of agent text. It does not store stream transcripts, endpoint candidates, broker URLs, or app-event kinds.

The state is 12 bytes:

```text
uint8 MarmotAgentTextStreamQuicRoleMaskV1;

const uint8 receive = 0x01;
const uint8 send    = 0x02;
const uint8 fanout  = 0x04;

struct {
  MarmotAgentTextStreamQuicRoleMaskV1 required_member_roles;
  MarmotAgentTextStreamQuicRoleMaskV1 allowed_member_roles;
  uint32                               max_plaintext_frame_len;
  uint32                               replay_ttl_secs;
  uint16                               padding_bucket_bytes;
} MarmotAgentTextStreamQuicV1;
```

Each role-mask bit names one member role capability. A member advertises a role by listing that capability's MLS
extension type in its LeafNode capabilities; the extension type ids are registered in
[../foundation/registries.md](../foundation/registries.md).

| Bit    | Role      | Role capability                                    | Extension type |
| ------ | --------- | -------------------------------------------------- | -------------- |
| `0x01` | `receive` | `marmot.feature.agent_text_stream_quic.receive.v1` | `0xf2d1`       |
| `0x02` | `send`    | `marmot.feature.agent_text_stream_quic.send.v1`    | `0xf2d2`       |
| `0x04` | `fanout`  | `marmot.feature.agent_text_stream_quic.fanout.v1`  | `0xf2d4`       |

`receive` means the member validates this component and follows the receiving rules in
[Retirement](#retirement). It never required opening QUIC connections or rendering live text.

`send` and `fanout` named the retired roles of members that sent live preview records and of members or helpers that
forwarded them. They are retired ([Retirement](#retirement)).

`required_member_roles` is the set of role capabilities every current member MUST advertise. Invite and join checks
enforce it before a new member enters the group:

- a client MUST NOT invite a member whose KeyPackage does not advertise every role capability named by
  `required_member_roles`;
- a joiner that does not support every role capability named by `required_member_roles` MUST NOT join the group.

`allowed_member_roles` is the set of role capabilities that this group policy permits `required_member_roles` to
contain. It constrains future component updates, not LeafNode capability advertisement. A member MAY advertise support
for additional role capabilities that are not in `allowed_member_roles`; advertising support does not grant permission
to exercise a role and does not make that role required by the group.

For a component replacement, the subset check compares `required_member_roles` and `allowed_member_roles` from the same
complete resulting state. The prior allowed-role mask determines neither mask in the replacement. Commit authorization
is still evaluated against the candidate-parent state, so a replacement cannot grant its own committer authority.

`max_plaintext_frame_len` capped the plaintext bytes in one live preview frame. `replay_ttl_secs` was the group's
requested maximum time a broker kept preview records for replay; `0` meant none. `padding_bucket_bytes` was reserved and
never used. These three fields no longer affect anything, but clients still check them against the bounds below.

This component version pins these maximums:

- `max_plaintext_frame_len <= 65519`, so a maximum-length frame's ciphertext (`plaintext_len + 16` AEAD tag bytes)
  fits the record's `ciphertext<0..2^16-1>` field bound;
- `replay_ttl_secs <= 300`;
- `padding_bucket_bytes <= 4096`.

## Update

The update payload is a full replacement state. Clients no longer send updates ([Retirement](#retirement)), but still
validate one they receive:

```text
MarmotAgentTextStreamQuicV1 MarmotAgentTextStreamQuicUpdateV1;
```

## Validation

A state is valid if:

- `required_member_roles` is not empty;
- `required_member_roles` is a subset of `allowed_member_roles`;
- every current member LeafNode advertises every role capability named by `required_member_roles`;
- every bit in both role masks is one of `receive`, `send`, or `fanout`;
- `max_plaintext_frame_len` is nonzero and no greater than the v1 maximum above;
- `replay_ttl_secs` is no greater than the v1 maximum above;
- `padding_bucket_bytes` is no greater than the v1 maximum above.

The member-capability check is a resulting-epoch invariant. It runs on every Commit, including a Commit that changes
this component, adds or updates a member leaf, or carries the prior component state forward unchanged. A component
update that adds a required role is therefore invalid unless every member in the resulting epoch already advertises
that role, and a member leaf update cannot drop a role that the carried-forward component still requires.

## Authorization

Only an active admin MAY send a standalone agent text stream QUIC update proposal.

Only an active admin MAY commit an agent text stream QUIC update.

Commit authorization, including removal authorization, follows the shared candidate-parent rule in
[README.md](./README.md) ("Authorization Evaluation").

## Removal

Only an active admin MAY commit removal of this component.

This component MAY be removed in the same authorized Commit that removes it from resulting GroupContext
`app_components`; it is invalid if the resulting state still lists it as required.

Existing Marmot messages, including kind `9` messages that carry stream tags, remain valid after removal.
[Retirement](#retirement) says when a client commits a removal.

## Migration

There is no MIP-era component to migrate from, and there is no successor. A future design for live agent text gets new
ids ([Retirement](#retirement)).
