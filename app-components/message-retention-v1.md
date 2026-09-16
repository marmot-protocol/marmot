# marmot.group.message-retention.v1

Status: adopted.

## Registry

- Component id: `0x8005`
- Name: `marmot.group.message-retention.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: optional

## State

```text
struct {
  uint64 disappearing_message_secs;
} MarmotMessageRetentionV1;
```

`disappearing_message_secs = 0` means disappearing messages are disabled.

Any nonzero value is a requested application retention duration in seconds.

Each application message pins the retention state from its own MLS source epoch. Later component updates or removal do
not shorten, extend, or restore that message's expiry. A retry or transport republication of the same MLS message uses
the same pinned duration and expiry value. The only adopted exception is the separately negotiated, unanimous local
plaintext effect in [marmot.group.history-purge.v1](./history-purge-v1.md); that one-shot authorization does not change
the pinned expiry value or the prospective default.

The retention duration is signed group state, and the transport-level expiry timestamp uses the exact calculation
defined below. Transport expiry applies to application messages only: group-state history — commits and proposals —
never carries a transport expiry hint, so retention does not affect group-state catch-up. The duration is authenticated;
the base timestamp is the sender's own `created_at`, so a sender that backdates or forward-dates `created_at` shifts
when its own message expires.
Disappearing-message expiry is therefore advisory and inherits the trust already placed in the MLS-authenticated
sender. It is not a deletion guarantee enforced against a hostile sender.

The expiry calculation uses exact, checked unsigned-64-bit addition:

```text
expiry_timestamp = checked_u64(app_payload.created_at + disappearing_message_secs)
```

`app_payload.created_at` and `expiry_timestamp` are integer Unix timestamps in seconds. The calculation is defined only
when `created_at` is a non-negative integer representable as `uint64` and the sum is no greater than `2^64 - 1`. An
implementation MUST NOT wrap, saturate, or compute through an inexact JSON number. When the calculation is undefined or
the active transport cannot represent the exact result, the sender omits the transport expiry hint; the component state
and application message remain valid.

## Update

The update payload is a full replacement state:

```text
MarmotMessageRetentionV1 MarmotMessageRetentionUpdateV1;
```

## Validation

Any `disappearing_message_secs` value in the `uint64` range is a valid retention state. v1 defines no protocol-level
maximum. An application MAY refuse to enable a duration its UI considers unreasonable, but that local cap is not signed
group state and MUST NOT invalidate otherwise-valid retention state received from the group.

This component governs application plaintext retention. It MUST NOT force deletion of MLS state, retained anchors,
pending message records, publish obligations, or other protocol data before the protocol retention rules allow that data
to be discarded. A consensual history purge remains subject to the same protocol-data exclusion.

## Authorization

Only an active admin MAY send a standalone message-retention update proposal.

Only an active admin MAY commit a message-retention update.

Commit authorization, including removal authorization, follows the shared candidate-parent rule in
[README.md](./README.md) ("Authorization Evaluation").

## Removal

Only an active admin MAY commit removal of this component.

Removal is equivalent to `disappearing_message_secs = 0`.

## Migration

This component carries the `disappearing_message_secs` field from the MIP-01 `marmot_group_data` extension (see
[../mip-coverage.md](../mip-coverage.md)). v1 is the first versioned form; a breaking change gets a new component id and
file.
