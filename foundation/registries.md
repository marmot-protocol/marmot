# Registries

Status: adopted.

This file collects Marmot-owned ids so new documents do not accidentally reuse a value.

The owning document defines the bytes and validation rules. This registry only names the value.

## App component ids

Marmot app components use MLS private-use component ids.

| Component id | Name                                            | Document                                                            |
| ------------ | ----------------------------------------------- | ------------------------------------------------------------------- |
| `0x8001`     | `marmot.group.profile.v1`                       | [doc](../app-components/group-profile-v1.md)                        |
| `0x8002`     | `marmot.group.blossom.image.v1`                 | [doc](../app-components/group-blossom-image-v1.md)                  |
| `0x8003`     | `marmot.group.admin-policy.v1`                  | [doc](../app-components/admin-policy-v1.md)                         |
| `0x8004`     | `marmot.transport.nostr.routing.v1`             | [doc](../app-components/nostr-routing-v1.md)                        |
| `0x8005`     | `marmot.group.message-retention.v1`             | [doc](../app-components/message-retention-v1.md)                    |
| `0x8006`     | `marmot.group.agent-text-stream.quic.v1`        | [doc](../app-components/agent-text-stream-quic-v1.md)               |
| `0x8007`     | `marmot.group.avatar-url.v1`                    | [doc](../app-components/group-avatar-url-v1.md)                     |
| `0x8008`     | `marmot.group.encrypted-media.v1`               | [doc](../app-components/group-encrypted-media-v1.md)                |
| `0x8009`     | `marmot.member.account-identity-proof.v2`       | [doc](../app-components/account-identity-proof-v2.md)               |
| `0x800a`     | `marmot.authorization.multi-device-join.v1`     | [draft](../app-components/multi-device-join-authorization-v1.md)    |
| `0x800b`     | `marmot.group.encrypted-media.v2`               | [doc](../app-components/group-encrypted-media-v2.md)                |
| `0x800c`     | `marmot.group.lifecycle.v1`                     | [doc](../app-components/group-lifecycle-v1.md)                      |
| `0x800d`     | `marmot.group.history-purge.v1`                 | [doc](../app-components/history-purge-v1.md)                        |

## Upstream MLS extension draft ids

These values are pinned for the MLS extensions draft profile currently used by Marmot. If the upstream draft changes
these assignments, Marmot needs an explicit compatibility plan before changing wire behavior.

| Namespace      | Value    | Name                        | Upstream source                     |
| -------------- | -------- | --------------------------- | ----------------------------------- |
| ComponentID    | `0x0001` | `app_components`            | MLS extensions draft `ComponentID`  |
| ComponentID    | `0x0002` | `safe_aad`                  | MLS extensions draft `ComponentID`  |
| ComponentID    | `0x0004` | `last_resort_key_package`   | MLS extensions draft `ComponentID`  |
| Extension type | `0x0006` | `app_data_dictionary`       | MLS extensions draft extension type |
| Proposal type  | `0x0008` | `app_data_update`           | MLS extensions draft proposal type  |
| Proposal type  | `0x0009` | `app_ephemeral`             | MLS extensions draft proposal type  |
| Proposal type  | `0x000a` | `self_remove`               | MLS extensions draft proposal type  |

These values match draft-ietf-mls-extensions-10. In that draft, an implementation that supports
`app_data_dictionary` must understand and advertise `app_components` and must understand `safe_aad`. Last-resort
KeyPackage marking is the empty-data `last_resort_key_package` application component in the KeyPackage
`app_data_dictionary`, not an MLS extension type.

`app_ephemeral` associates component-owned data with one Commit without changing persistent GroupContext state.
`safe_aad` instead negotiates component-separated framing for the MLS `authenticated_data` field. They are distinct
carriers and MUST NOT be treated as interchangeable merely because both use a `ComponentID`.

## Marmot custom MLS extension types

| Extension type | Name                                            | Document                                                    |
| -------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| `0xf2d1`       | `marmot.feature.agent_text_stream_quic.receive.v1` | [doc](../app-components/agent-text-stream-quic-v1.md)    |
| `0xf2d2`       | `marmot.feature.agent_text_stream_quic.send.v1`    | [doc](../app-components/agent-text-stream-quic-v1.md)    |
| `0xf2d4`       | `marmot.feature.agent_text_stream_quic.fanout.v1`  | [doc](../app-components/agent-text-stream-quic-v1.md)    |
| `0xf2ef`       | `marmot.encrypted-device-name.v1`               | [doc](../features/multi-device.md)                         |
| `0xf2f0`       | `marmot.multi-device.v1`                        | [doc](../features/multi-device.md)                         |
| `0xf2f1`       | `marmot.account-identity-proof.v1`              | [doc](./account-identity-proof-v1.md)                       |

`0xf2d3` is intentionally unassigned and has no reserved meaning. A future use MUST claim it in this registry before
emitting it.

`0xf2d1`, `0xf2d2`, and `0xf2d4` are the agent-text-stream-QUIC member role capabilities. A member advertises a role by
listing the matching extension type in its LeafNode capabilities; the `required_member_roles` mask in
`marmot.group.agent-text-stream.quic.v1` is enforced against these ids at invite and join. The `receive` role
(`0xf2d1`) means the member understands the component and can fall back to the durable final message; it does not require
opening a live-preview transport. The `send` and `fanout` roles are live-preview data-plane roles. The bit values
(`0x01`, `0x02`, `0x04`) are role-mask bits inside the component payload, distinct from these extension type ids.

These three extension types are capability markers only: v1 defines no extension data for them. They appear solely in
`LeafNode.capabilities.extensions` to advertise role support and are never emitted as LeafNode or GroupContext
extension bodies.

`0xf2ef` and `0xf2f0` are reserved for the draft multi-device feature (see
[../features/multi-device.md](../features/multi-device.md)) and are not yet implemented; confirm the values when that
feature lands.

`0xf2f1` is the superseded v1 account-identity-proof extension. It is not required or emitted by the current profile;
component id `0x8009` replaces it. It remains registered so the legacy wire value is never reassigned.

## Marmot custom proposal types

No Marmot-owned custom MLS proposal type is assigned in this spec yet.

`IdentityRemove` is the first likely candidate. It MUST claim a proposal type here before becoming normative.

## Nostr event kinds used by Marmot

These are the event kinds Marmot allocates or assigns meaning to. The owning document defines each exact event shape;
this table only names the value and points at the owner.

The table includes Marmot-allocated kinds and standard app-event kinds to which Marmot assigns an inner payload meaning.
Standard transport kinds that the Nostr binding reuses unchanged — kind `1059` (NIP-59 gift wrap), kind `13` (NIP-59
seal), kind `10002` (NIP-65 relay list), and kind `10050` (NIP-17 DM inbox relay list) — remain defined in
[../transports/nostr.md](../transports/nostr.md).

| Kind    | Name                                | Layer                               | Document                                                |
| ------- | ----------------------------------- | ----------------------------------- | ------------------------------------------------------- |
| `9`     | Default chat message                | Marmot app payload                  | [application-messages.md](application-messages.md)      |
| `444`   | Marmot welcome rumor                | Nostr welcome transport             | [nostr.md](../transports/nostr.md)                      |
| `445`   | Marmot group message                | Nostr group transport               | [nostr.md](../transports/nostr.md)                      |
| `446`   | Push notification rumor             | Push notification transport         | [nostr.md](../transports/nostr.md)                      |
| `447`   | Push token request                  | Marmot app payload                  | [push-notifications.md](../features/push-notifications.md) |
| `448`   | Push token list response            | Marmot app payload                  | [push-notifications.md](../features/push-notifications.md) |
| `449`   | Push token removal                  | Marmot app payload                  | [push-notifications.md](../features/push-notifications.md) |
| `450`   | Account identity proof v2 event     | Local signing template, not relayed | [account-identity-proof-v2.md](../app-components/account-identity-proof-v2.md) |
| `451`   | Push owner proof event              | Local signing template, not relayed | [push-notifications.md](../features/push-notifications.md) |
| `452`   | Multi-device join authorization v1 | Local signing template, not relayed | [multi-device-join-authorization-v1.md](../app-components/multi-device-join-authorization-v1.md) |
| `453`   | History-purge control event         | Marmot app payload                  | [history-purge-v1.md](../app-components/history-purge-v1.md) |
| `454`   | History-purge member decision       | Local signing template, not relayed | [history-purge-v1.md](../app-components/history-purge-v1.md) |
| `455`   | History-purge request proof         | Local signing template, not relayed | [history-purge-v1.md](../app-components/history-purge-v1.md) |
| `456`   | History-purge cancellation proof    | Local signing template, not relayed | [history-purge-v1.md](../app-components/history-purge-v1.md) |
| `457`   | History-purge terminal proof        | Local signing template, not relayed | [history-purge-v1.md](../app-components/history-purge-v1.md) |
| `1009`  | Message edit                        | Marmot app payload                  | [application-messages.md](application-messages.md)      |
| `1200`  | Agent text stream start             | Marmot app payload                  | [agent-text-streams-quic.md](../features/agent-text-streams-quic.md) |
| `1210`  | Group system event                  | Marmot app payload                  | [application-messages.md](application-messages.md)      |
| `1984`  | Content report (NIP-56)             | Marmot app payload                  | [content-moderation.md](../features/content-moderation.md#reports-kind-1984) |
| `1985`  | Report dismissal labels (NIP-32)    | Marmot app payload                  | [content-moderation.md](../features/content-moderation.md#dismissal-labels-kind-1985) |
| `4891`  | Admin content deletion v1           | Marmot app payload                  | [content-moderation.md](../features/content-moderation.md#admin-deletion-kind-4891) |
| `30443` | Marmot KeyPackage event             | Nostr KeyPackage publication        | [nostr.md](../transports/nostr.md)                      |

Kind `4891` is allocated by Marmot for admin deletion inside MLS app payloads.

The experimental agent text stream QUIC feature claims kind `1200` for durable stream start app events. Live stream
chunks are transient QUIC records.

Kinds `1201` and `1202` are reserved for possible experimental agent activity and operation events. Marmot currently
defines no payload schema or conformance behavior for them; application experiments use them under the ordinary
unknown-app-event rules. Future adoption MUST add their exact semantics to the main table before relying on them for
interoperability. Future durable abort, media-final, or fallback preview app-event kinds likewise MUST be added before
use.

Kind `450` is the local signing event for the adopted account identity proof v2. Its exact event shape is defined by its
component document and uses the envelope and validation rules in
[authorization-proofs.md](./authorization-proofs.md). Kind `452` is reserved for the separate draft multi-device
active-admin join authorization, whose component document uses the same common proof rules.

Kind `451` is the local signing event for current push token-record and removal owner proofs. Its two templates use
distinct `d` tags and are defined by [push-notifications.md](../features/push-notifications.md). Its signature-only
carrier is feature-specific and does not use `MarmotAuthorizationProof`.

Kinds `450`, `451`, `452`, `454`, `455`, `456`, and `457` are local signing templates, not transport objects. Clients MUST NOT publish them to
relays. Legacy-group verification of push signatures created with kind `450` does not change the current allocation:
clients MUST NOT produce a new push owner proof with kind `450`.

The `d` tag strings in these local signing events are fixed proof-domain labels, not component names. Implementations
MUST use the exact `d` value in each owning proof document and MUST NOT derive it from the component name.

Kind `1210` is reserved for durable group system rows, such as membership, name, avatar, or other group-lifecycle
notices that clients render separately from human chat.

Kind `1009` is reserved for message edits — an in-place replacement of a prior chat message's text. The event carries a
single `e` tag referencing the edited event id and `content` is the replacement plaintext. Clients render the latest
replacement onto the original row's body, never as a separate transcript row.

## ALPN and protocol identifiers

| Identifier                    | Use                                      | Document                         |
| ----------------------------- | ---------------------------------------- | -------------------------------- |
| `marmot.quic_stream.v1`       | direct-path QUIC ALPN                    | [quic.md](../transports/quic.md) |
| `marmot.quic_broker.v1`       | broker QUIC ALPN and control identifier  | [quic.md](../transports/quic.md) |

An incompatible transport or control protocol registers a new identifier rather than reinterpreting one of these
strings.

## Exporter labels

Existing Marmot exporter uses SHOULD be treated as registered until their owning docs move or replace them.

Each entry is an `MLS-Exporter(label, context, length)` invocation: the first column is the exporter `label`, the second
is the `context`, and the third is the output length in bytes.

The `label` and `context` pair is the top-level domain separator. Owning documents define any additional key context
used below the exporter output.

| Label      | Context                        | Length   | Consumer                               |
| ---------- | ------------------------------ | -------- | -------------------------------------- |
| `"marmot"` | `"group-event"`                | `32`     | kind `445` outer encryption key        |
| `"marmot"` | `"encrypted-media"`            | `32`     | encrypted-media per-file key schedule  |
| `"marmot"` | `"agent-text-stream-quic"`     | `32`     | agent text stream QUIC record crypto   |
| `"marmot"` | `"convergence-conformance-v1"` | `32`     | synthetic conformance state commitment |
| `"marmot"` | `join_psk_id`                  | `KDF.Nh` | multi-device external PSK material     |

Fixed `32`-byte outputs are used where the owning document feeds a 32-byte AEAD key or feature key schedule.
`KDF.Nh` is used for the multi-device join PSK because that output is external PSK material for the MLS ciphersuite KDF.

The multi-device join entry is versioned inside the structured `join_psk_id` context. A future incompatible join-PSK
design MUST register a new exporter label or context shape.
