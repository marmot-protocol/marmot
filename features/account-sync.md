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
([../foundation/application-messages.md](../foundation/application-messages.md)) delivered in the chat. A device never
sends a position naming an edit (kind `1009`) or a row a client synthesizes locally, such as a kind `1210` group system
row; a receiver cannot tell what a position names before it holds that message, so it judges a position by its
encoding alone. A read position carries no version or change id. Positions are in chat order, which compares, in this
order:

1. the MLS epoch the message was sent in;
2. its `created_at`;
3. its `id`, as 32 bytes.

Every device of the account sees the same values for the same message, so every device puts positions in the same
order. A read position only moves forward: a device takes a received position when it holds none for that chat, or
when the received one is further than the one it holds. A device marks as read every delivered message of the chat at
or before the position it holds, including ones that reach it later; the position changes nothing else, so a message
that never counts as unread, such as an edit, stays that way after it. A device may hold a position before it holds the
message the position names.

**Versioned items.** `pin`, `mute` and `archive` each carry a version and a change id:

- When the user changes a versioned item on a device, the device gives the change a version one higher than the highest
  version it holds for that item, from any device, and a fresh change id: 16 bytes from a cryptographically secure
  random source. A device that holds no value for the item counts its highest version as 0, so its first change has
  version 1.
- Of two values for the same item, the one with the higher version wins. At an equal version, the one with the lower
  change id, compared as bytes, wins. At an equal version and change id, the one whose `value` is lower, compared as the
  bytes of its encoding ([Messages](#messages)), wins; only a device that breaks these rules sends two values that way.
- A value that loses is discarded. A device applies the winning value to its own state of the chat.

Every device picks the same winner from the same values, whatever order they arrive in and however often, and neither
the sender nor any clock decides it. A setting turned back off, such as a chat unpinned, is a value like any other and
keeps its version.

A version is at most 9007199254740991. A device that holds an item at that version cannot give a change a higher one,
so its user cannot change that item: the device puts the held value back. Each change adds one to a version, so no
device that follows these rules comes near that number ([Security considerations](#security-considerations)).

How a device orders its pinned chats is its own: a chat that becomes pinned through small state goes where the device
puts newly pinned chats.

A mute value of `true` mutes the chat until it is unmuted; a time mutes it until then. A time that has passed means the
chat is not muted, and no update is needed when it passes.

### Starting

A device starts taking part in small state the first time it both trusts a device group
([device-group.md](./device-group.md), "Trust") and supports this document: when it first trusts one, or, for a device
that already trusts one, when it gains support. It holds no item yet for settings it already has. When it starts, it
gives each versioned setting that differs from the default (not pinned, not muted, not archived) a value at version `1`
with a fresh change id, and takes its current read position for each chat it has read. It then needs snapshots
([Snapshots](#snapshots)), which sends these items to its siblings. Where two devices start with different settings for
one chat, the rules above pick the same winner on both.

A device keeps the items it holds for a chat it is not in, so a chat it joins later starts with the account's state.

### Messages

| Kind  | Message          | Sent by                                     |
| ----- | ---------------- | ------------------------------------------- |
| `475` | Update           | a device whose user changed small state     |
| `476` | Snapshot request | a device that may have missed updates       |
| `477` | Snapshot         | the sibling a snapshot request names        |

All three are Marmot app events ([../foundation/application-messages.md](../foundation/application-messages.md)) sent
as MLS application messages in the device group. Each one's content is one UTF-8 JSON object, written without
whitespace, with its members in the order shown, and at most 32,768 bytes long. No object in it repeats a member name.

An update's content is `{"v":1,"items":[...]}`: `v` is `1`, and `items` holds one or more items. An item is one JSON
object:

| Member    | Value |
| --------- | ----- |
| `chat`    | the chat's MLS group id: its raw bytes, every one, as lowercase hexadecimal with no prefix |
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

An item has exactly the members above for its name, and a `read` value exactly its three. Every number in these
messages is a decimal integer from 0 to 9007199254740991, without leading zeros, and a version is at least 1. One
message holds at most one item for each chat and item name.

A snapshot request's content is `{"v":1,"to":"<slot>","request":"<id>"}`:

- `to` is the slot of the sibling asked ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
  "State"), 64 lowercase hexadecimal characters;
- `request` is 16 bytes from a cryptographically secure random source, fresh for each request, as 32 lowercase
  hexadecimal characters.

A snapshot's content is `{"v":1,"request":"<id>","part":p,"parts":n,"items":[...]}`: `request` is the request it
answers, `parts` is how many snapshots the answer has, at least 1, `part` is this one's number, from 1 to `parts`, and
`items` holds items as in an update. A snapshot's `items` may be empty: a device that holds no item answers with one
snapshot, `part` 1 of 1, with no items.

### Sending

- A device sends an update when its user changes small state on it. It MAY combine several items in one update, and MAY
  wait a few seconds to combine read positions that move quickly, since only the furthest one matters.
- An update that would be longer than 32,768 bytes is split into several updates.
- When branch selection withdraws an update or snapshot that a device sent or merged
  ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Applying the selected branch"), the device sends
  each item that message carried again, in updates, unless it now holds a value for that item that beats it. Resending
  keeps the item's version and change id. Every device that merged the message does this, not only its sender, which
  may no longer be in the device group.

### Snapshots

A device can miss small state. It cannot read device-group messages sent before it joined the device group. It loses a
device-group message for good when the device group's canonical tip moves more than `app_payload_past_epoch_limit`
epochs past the message's epoch before the device reads it, even if relays still hold the message
([../protocol-core/retained-history.md](../protocol-core/retained-history.md), "App-payload retention"). It asks a
sibling for every item instead. No one sibling is sure to hold every value, since it may have missed some too, so the
device asks every sibling, and its siblings learn what it holds:

- A device needs snapshots when it starts ([Starting](#starting)), and whenever it may have lost a device-group
  application message: when one expired before it read it, and whenever it cannot rule that out, such as when the
  device group's canonical tip moved more than `app_payload_past_epoch_limit` epochs past an epoch whose messages it
  may not all have fetched, as after time offline. Asking when nothing was lost costs only messages.
- Then it sends every item it holds to its siblings, in updates, and sends a snapshot request to each device the roster
  lists other than itself, whatever its status, each with its own request id.
- The device a request names answers it once, with every item it holds, in as many snapshots as that takes and at
  least one; each names the request, its part number and the number of parts. Each snapshot stands alone: a receiver
  merges its items as they arrive and waits for no other part.
- A device has a sibling's snapshot once it has merged every part, 1 to `parts`, of that sibling's answer to its latest
  request to it. Until then, while the roster lists that sibling, the device asks it again with a new request id: at
  once when branch selection withdraws the request, and otherwise when an hour has passed since it asked. It MAY wait
  longer between later requests to the same sibling, such as one that has been away for a long time.

### Receiving

A device reads updates, snapshot requests and snapshots only in the device group it trusts
([device-group.md](./device-group.md), "Trust"), and ignores kinds `475`, `476` and `477` in any other group. Every
member of that group is one of the account's devices, so any member's message counts; a device does not need to tell
which sibling sent it.

- It drops a message whose content is not one JSON object with exactly the members above for its kind, whose `v` is
  not `1`, that is longer than 32,768 bytes, in which an object repeats a member name, that holds two items with the
  same `chat` and `item`, or, for a snapshot, whose `part` is not from 1 to `parts`.
- In a message it keeps, it checks each item on its own. It skips an item whose `item` it does not know, so a later
  version can add items without older devices dropping the message, and it skips an item that breaks the rules above.
  It merges every other item, from an update or a snapshot, whether or not it asked for that snapshot.
- It answers a snapshot request only when `to` is its own slot.

A device reads small state from its device group whether or not it is in the chat an item names.

## Convergence and retained history

Small state is not group state. A branch selection that withdraws a device-group message's payload does not undo what
the message set on a device that already merged it. Every device converges on the same values once it holds every
value: the merge rules pick the same winner everywhere, every device that merged a withdrawn update or snapshot sends
its items again, and a device that may have lost messages sends what it holds and keeps asking each sibling the roster
lists until that sibling's snapshot is whole. A value held only by a device that never comes back is lost with it.

A read position taken on a branch that branch selection later withdraws stays where it is: the selected branch's
messages at or before it in chat order count as read, including ones the user never saw. Positions only move forward,
so no device moves it back; a later position moves it again once that one is further in chat order.

## Security considerations

- Small state names the account's chats by their MLS group id, which is private group security state. It travels only
  inside the device group. Every device in the device group learns the group id and small state of every chat any
  sibling syncs, including a chat it is not in, such as an older chat it was not added to when it was linked. A device
  MUST NOT publish a group id it learned this way through a transport envelope, and an item is not evidence that the
  device is, or may become, a member of that chat.
- Any device of the account can set any item, including a stolen linked device until it is removed. A device that sends
  an item at the largest version, 9007199254740991, fixes that item's value on every device for good: no later change
  can beat it, and removing the device does not undo it. A read position that names a message no device holds can mark
  a whole chat as read. A linked device can already read and send in the account's chats; these let it also fix or
  change their settings.
- Nothing in small state is shown to other members of a chat, and no other account can read or write it.
