# Account sync

Status: draft.

An account's devices keep some state the same everywhere: which messages the user has read, and per-chat settings such
as pins, mutes and archived chats. The account's devices exchange it inside their device group
([device-group.md](./device-group.md)), so it never reaches a chat, a relay or another account.

The non-normative direction is described in [../ideas/account-sync.md](../ideas/account-sync.md). This document covers
small state. History transfer, backups and invite decisions are not specified yet.

## Surfaces

- Feature: [device-group.md](./device-group.md), which defines the device group, when a device trusts one, and its
  roster.
- Marmot app events: kind `475` (small-state update), kind `476` (snapshot request) and kind `477` (snapshot), sent only
  in a device group ([Messages](#messages)). Their kinds are registered in
  [../foundation/registries.md](../foundation/registries.md).
- Protocol core: [../protocol-core/convergence.md](../protocol-core/convergence.md) and
  [../protocol-core/retained-history.md](../protocol-core/retained-history.md), which decide when a device-group message
  is delivered, withdrawn or lost.

## Small state

Small state is per-chat state that follows the user from device to device. Each device keeps its own copy, applies it to
its own chats, and tells its siblings when the user changes it. Small state never changes group state, and nothing
about it is sent in the chat it describes.

Drafts are not small state: a draft belongs to the device it was typed on.

### Items

Small state is a set of items. An item is one setting of one chat, named by the chat and the item's name. The chat is
the group's MLS group id ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)), never a transport
routing id.

| Item      | What it holds                                   | Which value wins                   |
| --------- | ----------------------------------------------- | ---------------------------------- |
| `read`    | the furthest message the user has read          | the furthest position              |
| `pin`     | whether the chat is pinned                      | the highest version, then the tie-break |
| `mute`    | whether the chat's notifications are muted, and until when | the highest version, then the tie-break |
| `archive` | whether the chat is archived                    | the highest version, then the tie-break |

**Read positions.** A read position names one message of the chat: a Marmot app event
([../foundation/application-messages.md](../foundation/application-messages.md)) that was delivered in the chat, not one
a client synthesizes locally. Chat order compares, in this order:

1. the MLS epoch the message was sent in;
2. its `created_at`;
3. its `id`, as 32 bytes.

Every device of the account sees the same values for the same message, so every device puts positions in the same
order. A read position only moves forward: a device takes a received position only when it is further than the one it
holds. A device marks as read every message of the chat at or before the position it holds, including ones that reach
it later. It may hold a position before it holds the message the position names.

**Versioned items.** `pin`, `mute` and `archive` each carry a version and a change id:

- When the user changes a versioned item on a device, the device gives the change a version one higher than the highest
  version it holds for that item, from any device, and a fresh change id: 16 bytes from a cryptographically secure
  random source.
- Of two values for the same item, the one with the higher version wins. At an equal version, the one with the lower
  change id, compared as bytes, wins. The same change id is the same change.
- A value that loses is discarded. A device applies the winning value to its own state of the chat.

Every device picks the same winner from the same values, whatever order they arrive in and however often, and neither
the sender nor any clock decides it. A setting turned back off, such as a chat unpinned, is a value like any other and
keeps its version.

How a device orders its pinned chats is its own: a chat that becomes pinned through small state goes where the device
puts newly pinned chats.

A mute value of `true` mutes the chat until it is unmuted; a time mutes it until then. A time that has passed means the
chat is not muted, and no update is needed when it passes.

### Starting

A device that starts to take part in small state holds no item yet for settings it already has. When it first trusts a
device group ([device-group.md](./device-group.md), "Trust"), it gives each setting that differs from the default (not
read, not pinned, not muted, not archived) a value at version `1` with a fresh change id, takes its current read position
for each chat, sends them to its siblings in updates, and asks a sibling for a snapshot ([Snapshots](#snapshots)).
Where two devices start with different settings for one chat, the rules above pick the same winner on both.

A device keeps the items it holds for a chat it is not in, so a chat it joins later starts with the account's state.

### Messages

| Kind  | Message          | Sent by                                     |
| ----- | ---------------- | ------------------------------------------- |
| `475` | Update           | a device whose user changed small state     |
| `476` | Snapshot request | a device that may have missed updates       |
| `477` | Snapshot         | the sibling a snapshot request names        |

All three are Marmot app events ([../foundation/application-messages.md](../foundation/application-messages.md)) sent
as MLS application messages in the device group. Each one's content is one UTF-8 JSON object, written without
whitespace, with its members in the order shown, and at most 32,768 bytes long.

An update's and a snapshot's content is `{"v":1,"items":[...]}`: `v` is `1`, and `items` holds one or more items. An
item is one JSON object:

| Member    | Value |
| --------- | ----- |
| `chat`    | the chat's MLS group id, lowercase hexadecimal |
| `item`    | the item's name: `read`, `pin`, `mute` or `archive` |
| `value`   | the item's value, below |
| `version` | for `pin`, `mute` and `archive` only: the version |
| `change`  | for `pin`, `mute` and `archive` only: the change id, 32 lowercase hexadecimal characters |

| Item      | `value` |
| --------- | ------- |
| `read`    | `{"epoch":e,"at":t,"id":"<id>"}`: the epoch the message was sent in, its `created_at` and its `id` (64 lowercase hexadecimal characters) |
| `pin`     | `true` or `false` |
| `mute`    | `false`, `true`, or a time in seconds since the Unix epoch |
| `archive` | `true` or `false` |

Every number in an item is a decimal integer from 0 to 9007199254740991, without leading zeros, and a version is at
least 1. One message holds at most one item for each chat and item name.

A snapshot request's content is `{"v":1,"to":"<slot>"}`: `to` is the slot of the sibling asked
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State"), 64 lowercase hexadecimal
characters.

### Sending

- A device sends an update when its user changes small state on it. It MAY combine several items in one update, and MAY
  wait a few seconds to combine read positions that move quickly, since only the furthest one matters.
- A device whose update branch selection invalidates
  ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Applying the selected branch") sends each item it
  carried again, unless the device now holds a value for that item that beats it. Resending keeps the item's version
  and change id.
- An update or snapshot that would be longer than 32,768 bytes is split into several, each with the same `v`.

### Snapshots

A device can miss updates: it may be offline longer than its device group's relays keep messages, and then those
messages are lost for good ([../protocol-core/retained-history.md](../protocol-core/retained-history.md)). It asks a
sibling for every item instead:

- A device sends a snapshot request when it first trusts a device group, and when it knows it may have lost messages in
  its device group, for example after being offline longer than those relays keep messages.
- The request names one sibling the roster lists as a device. If no snapshot from that sibling arrives within an hour,
  the device MAY ask another.
- The device a request names answers it once, by its Marmot app event `id`, with every item it holds, in as many
  snapshots as that takes. Each snapshot stands alone: a receiver merges its items as they arrive and waits for no
  other part.

### Receiving

A device reads updates, snapshot requests and snapshots only in the device group it trusts
([device-group.md](./device-group.md), "Trust"), and ignores kinds `475`, `476` and `477` in any other group. Every
member of that group is one of the account's devices, so any member's message counts; a device does not need to tell
which sibling sent it.

- It drops a message whose content is not JSON of the shape above, or whose `v` is not `1`.
- It skips an item whose `item` it does not know, so a later version can add items without older devices dropping the
  message. It skips an item whose other members break the rules above.
- It merges every other item, from an update or a snapshot, whether or not it asked for that snapshot.
- It answers a snapshot request only when `to` is its own slot.

A device reads small state from its device group whether or not it is in the chat an item names.

## Convergence and retained history

Small state is not group state. A branch selection that withdraws a device-group message's payload does not undo what
the message set on a device that already merged it. The merge rules make every device converge on the same values once
it has every value, and the resend rule above restores what a withdrawn update carried.

## Security considerations

- Small state names the account's chats by their MLS group id, which is private group security state. It travels only
  inside the device group, among the account's own devices, which already hold those ids.
- Any device of the account can set any item, including a stolen linked device until it is removed. A device that sends
  the largest version for an item keeps that value until another change wins the tie-break at that version. A read
  position that names a message no device holds can mark a whole chat as read. These are within what a linked device
  can already do.
- Nothing in small state is shown to other members of a chat, and no other account can read or write it.
