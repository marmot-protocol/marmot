# Per-message expiry v1

Status: draft.

This optional app-event profile lets a sender shorten one chat message's lifetime without changing group state.
[Per-message expiry](../features/message-expiry.md) owns reveal, deletion, and compatibility behavior.

## Scope and encoding

The profile applies to kind `9`, including its ordinary encrypted-media attachments. It allocates no MLS component
or required capability. It does not apply to group-state messages or live agent streams.

The carrier is the `tags` array of the [unsigned app event](./application-messages.md), using Nostr string-array
encoding rather than the Marmot binary profile. Tag order has no policy meaning, but remains part of the event id.
Tag names and values are compared as exact UTF-8 bytes without normalization.

An expire-after-send message carries exactly one NIP-40-compatible tag:

```json
["expiration", "1700000060"]
```

Its value is the absolute per-message cap, `message_expires_at`, in integer Unix seconds. A producer derives it by
checked addition of its app event's `created_at` and the selected expire-after-send duration.

A burn-after-read message carries that tag and exactly one additional tag:

```json
[
  ["expiration", "1700086400"],
  ["marmot-expiry", "1", "30", "1700086400"]
]
```

The `marmot-expiry` fields are the name, the version string `1`, `after_read_seconds`, and `unopened_expires_at`.
The last value MUST equal the `expiration` value. The version is an ASCII string because this is a Nostr tag
profile, not a binary wire structure. The unopened cap is mandatory, including when group retention is disabled.
A producer derives it by checked addition of `created_at` and the selected unopened duration.

## Validation

A client supporting this profile MUST validate the following after app-event and MLS sender authentication:

- An `expiration` tag has exactly two fields. A `marmot-expiry` tag has exactly four fields for version `1`.
- Each numeric field is an ASCII decimal unsigned integer with no leading zero, sign, whitespace, fraction,
  or exponent. It has at most 20 digits and fits `uint64`. Arithmetic uses exact, checked unsigned integers.
- There is at most one tag of each name, including identical duplicates. A burn tag without `expiration` is invalid.
- `message_expires_at` is greater than `created_at`. Their difference is from `1` to `2419200` seconds, inclusive
  (four weeks). `after_read_seconds`, when present, is in the same range. Zero never disables an existing policy.
- The two burn caps agree. The after-read duration may exceed the remaining unopened lifetime: the earlier cap wins.
- No other event kind may select this profile. Edits inherit their target's policy as the feature document defines.

Malformed policy does not invalidate otherwise-valid MLS processing or affect branch selection. The client MUST
withhold the event's content and attachments, show at most an unsupported-policy placeholder, and create no timer or
notification from it. It MUST NOT silently treat malformed policy as an ordinary non-expiring message.

An unknown `marmot-expiry` version is unsupported, not version `1`. Preserve its authenticated bytes where protocol
retention requires them, but do not expose its content. A client MAY apply a separately valid `expiration` cap to
remove the unsupported placeholder and its local app content. It MUST NOT infer unknown after-read semantics.

These bounds do not restrict valid group-retention component values. An event with neither policy tag follows its
existing message-kind and group-retention rules.

## Pinned decision

Let `group_expires_at` be the finite expiry from the message's authenticated source-epoch
[retention component](../app-components/message-retention-v1.md). Disabled retention or an undefined checked sum
contributes no finite group deadline. The per-message cap is independently mandatory for a message using this profile.

```text
absolute_expires_at = min(each finite value in {group_expires_at, message_expires_at})
effective_expires_at = min(absolute_expires_at, local_read_expires_at if established)
```

The client MUST retain or reconstruct the validated policy and source-epoch group deadline with the accepted message.
It MUST NOT derive an old message's deadline from the group's current settings. First-read facts and expired state
are local to an account-device and MUST NOT be reset by duplicate receipt, replay, reorganization, or restart.

Only authenticated app-event time is a policy input. Outer transport time never substitutes for it. At each local
admission or content access, an event whose `created_at` exceeds the device's current Unix time by more than `300`
seconds MUST remain withheld, without notifications or a read transition, until its time is within that bound.
The client does not rewrite the authenticated timestamp. A past cap is due immediately, even on first receipt.
The future-time check is local presentation policy, not a reason to invalidate MLS state.

## Calculation examples

All timestamps below are integer Unix seconds. The example message has `created_at = 1700000000`.

| Group duration | Message cap | First reveal | After-read duration | Effective expiry |
| --- | --- | --- | --- | --- |
| `0` | `1700000060` | absent | absent | `1700000060` |
| `20` | `1700000060` | absent | absent | `1700000020` |
| `120` | `1700000060` | absent | absent | `1700000060` |
| `18446744073709551615` (group sum undefined) | `1700000060` | absent | absent | `1700000060` |
| `0` | `1700086400` | `1700000100` | `30` | `1700000130` |
| `0` | `1700086400` | `1700086390` | `30` | `1700086400` |

A cap equal to `created_at`, a duration of `2419201`, duplicate tags, decimal `01`, `-1`, or `1e2`, and a checked
addition beyond `18446744073709551615` are invalid. The wire tag values above are policy fragments, not complete
app events; an event's canonical id authenticates its complete tags and content.
