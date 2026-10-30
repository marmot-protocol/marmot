# Account sync

Status: draft.

An account's devices keep some state the same everywhere: which messages the user has read, and per-chat settings such
as pins, mutes and archived chats. The account's devices exchange it inside their device group
([device-group.md](./device-group.md)), so it never reaches a chat, a relay or another account.

The non-normative direction is described in [../ideas/account-sync.md](../ideas/account-sync.md). This document covers
small state and the history keys that chat history is sealed to. History transfer, backups and invite decisions are not
specified yet.

## Surfaces

- Feature: [device-group.md](./device-group.md), which defines the device group, when a device trusts one, and its
  roster.
- App component: [../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), whose device entries
  carry each device's history key ([History keys](#history-keys)).
- Marmot app events: kind `475` (small-state update) and kind `476` (broadcast request), sent only in a device group
  ([Messages](#messages)). Their kinds are registered in
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
routing id. Small state covers only chats whose MLS group id is at most 256 bytes long, so that every item fits in one
update; a device holds, sends and merges no item for another chat.

| Item      | What it holds                                   | Which value wins                   |
| --------- | ----------------------------------------------- | ---------------------------------- |
| `read`    | the furthest message the user has read          | the furthest position              |
| `pin`     | whether the chat is pinned                      | the highest version, then the tie-break |
| `mute`    | whether the chat's notifications are muted, and until when | the highest version, then the tie-break |
| `archive` | whether the chat is archived                    | the highest version, then the tie-break |

**Read positions.** A read position names one message of the chat: a Marmot app event
([../foundation/application-messages.md](../foundation/application-messages.md)) delivered in the chat, other than an
edit (kind `1009`), whose epoch and `created_at` are each at most 9007199254740991. A read position carries no version
or change id. Positions are in chat order, which compares, in this order:

1. the MLS epoch the message was sent in;
2. its `created_at`;
3. its `id`, as 32 bytes.

Every device of the account sees the same values for the same message, so every device puts positions in the same
order.

The position a device takes from its own state names the furthest message, of those a position may name, that its user
has read on that device, or none when there is no such message. Which messages count as read is the client's own, as it
is without small state: a client that shows rows no position names, such as an edit, a synthesized group system row or a
message not delivered yet, judges from its own transcript which messages its user has read. Only the device whose user
read takes a position from that reading, and it merges that position as it would a received one. From there a position
is an item like any other, sent in updates, broadcasts and resends by every device that holds it, and every device
merges positions by the rules here, so two clients need not judge the same reading alike.

A receiver cannot tell what a position names before it holds that message, so it takes any position whose encoding is
valid, whatever the message turns out to be, and never reconsiders it. A read position only moves forward: a device
takes a received position when it holds none for that chat, or when the received one is further than the one it holds. A
device marks as read every delivered message of the chat at or before the position it holds, including ones that reach
it later; the position changes nothing else, so a message that never counts as unread, such as an edit, stays that way
after it. A device may hold a position before it holds the message the position names.

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
so its user cannot change that item: the device puts the held value back. Values at that version still compare by
change id and value like any others, so every device keeps picking the same winner. Each change adds one to a version,
so no device that follows these rules comes near that number ([Security considerations](#security-considerations)).

How a device orders its pinned chats is its own: a chat that becomes pinned through small state goes where the device
puts newly pinned chats.

A mute value of `true` mutes the chat until it is unmuted; a time mutes it until then. Each device judges by its own
clock whether a time has passed. A time that has passed means the chat is not muted on that device, and no update is
needed when it passes.

### Starting

A device starts taking part in small state the first time it both trusts a device group
([device-group.md](./device-group.md), "Trust") and supports this document: when it first trusts one, or, for a device
that already trusts one, when it gains support. It holds no item yet for settings it already has. When it starts, it
gives each versioned setting that differs from the default (not pinned, not muted, not archived) a value at version `1`
with a fresh change id, and takes its current read position for each chat it has read. It then broadcasts and sends a
broadcast request ([Broadcasts](#broadcasts)), so its siblings learn what it holds and it learns what they hold. Where
two devices start with different settings for one chat, the rules above pick the same winner on both.

A device keeps the items it holds for a chat it is not in, so a chat it joins later starts with the account's state.

### Messages

| Kind  | Message           | Sent by                                                     |
| ----- | ----------------- | ----------------------------------------------------------- |
| `475` | Update            | a device whose user changed small state, or that broadcasts |
| `476` | Broadcast request | a device that starts, or may have missed updates            |

Both are Marmot app events ([../foundation/application-messages.md](../foundation/application-messages.md)) sent as MLS
application messages in the device group. Each one's content is one UTF-8 JSON object, written without whitespace, with
its members in the order shown, and at most 32,768 bytes long. No object in it repeats a member name.

An update's content is `{"v":1,"items":[...]}`: `v` is `1`, and `items` holds one or more items. An item is one JSON
object:

| Member    | Value |
| --------- | ----- |
| `chat`    | the chat's MLS group id: its raw bytes, every one, as lowercase hexadecimal with no prefix, so at most 512 characters |
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

A broadcast request's content is `{"v":1}`. It names no device and no item: it asks every sibling to broadcast.

### Sending

- A device sends an update when its user changes small state on it. It MAY combine several items in one update, and MAY
  wait a few seconds to combine read positions that move quickly, since only the furthest one matters.
- An update whose content would be longer than 32,768 bytes is split into several updates. The limit is on the
  content's UTF-8 bytes alone, not the app event or MLS message around it.
- When branch selection withdraws an update that a device sent or merged
  ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Applying the selected branch"), the device sends
  each item that update carried again, in updates, unless it now holds a value for that item that beats it. Resending
  keeps the item's version and change id. Every device that merged the update does this, not only its sender, which may
  no longer be in the device group.
- When branch selection withdraws a broadcast request, every device that sent or read it sends a new broadcast request,
  so a device whose request no sibling read still gets their broadcasts.

### Broadcasts

A device can miss small state. It cannot read device-group messages sent before it joined the device group. It loses a
device-group message for good when the device group's canonical tip moves more than `app_payload_past_epoch_limit`
epochs past the message's epoch before the device reads it, even if relays still hold the message
([../protocol-core/retained-history.md](../protocol-core/retained-history.md), "App-payload retention"), and a relay
may drop a message sooner. No one sibling is sure to hold every value either, since it may have missed some too. So
every device sends everything it holds again from time to time, and its siblings merge whatever they missed. No device
asks a particular sibling, waits for an answer, or keeps track of what its siblings hold.

A device broadcasts by sending every item it holds, in updates. Updates sent in a broadcast are like any other. A
device broadcasts:

- when it starts ([Starting](#starting));
- once 24 hours have passed since its last broadcast, by its own clock, or as soon as it runs again after that;
- whenever the device group's canonical tip is more than `app_payload_past_epoch_limit` epochs past the tip at which
  its last broadcast began. Every update of a broadcast goes out in that epoch or a later one, even when commits land
  while it is being sent, and a message is lost to the app-payload window only as the tip moves, so this keeps every
  update of a running device's latest broadcast within reach of a sibling that lost earlier messages;
- in answer to a broadcast request, below.

A device sends a broadcast request when it starts. It MAY send one at other times, such as when it comes back after a
long time away or finds that a device-group message expired before it read it. A device that reads a broadcast request
broadcasts once in answer, at most once an hour: when it reads one less than an hour after its last broadcast, it
waits until that hour has passed. One broadcast answers every request it read before sending it.

### Receiving

A device reads updates and broadcast requests only in the device group it trusts ([device-group.md](./device-group.md),
"Trust"), and ignores kinds `475` and `476` in any other group. Every member of that group is one of the account's
devices, so any member's message counts; a device does not need to tell which sibling sent it.

- It drops a message whose content is not one JSON object with exactly the members above for its kind, whose `v` is
  not `1`, whose content is longer than 32,768 bytes, in which an object repeats a member name, or that holds two
  items with the same `chat` and `item`.
- In an update it keeps, it checks each item on its own. It skips an item whose `item` it does not know, so a later
  version can add items without older devices dropping the update, and it skips an item that breaks the rules above.
  It judges a read position by its encoding alone ([Items](#items)). It merges every other item, whether the update
  was sent for a change or in a broadcast.
- It answers a broadcast request as [Broadcasts](#broadcasts) says.

A device reads small state from its device group whether or not it is in the chat an item names.

## History

A device that joins a chat cannot read the chat's earlier messages: they were encrypted for epochs it was never part
of. Its siblings that hold them send them to it, sealed so that only that device can read them, even though they travel
through the device group that every sibling reads.

### History keys

Each device has one history key: an HPKE key pair ([RFC 9180](https://www.rfc-editor.org/rfc/rfc9180)) under the KEM of
the device group's ciphersuite. It generates the key pair from a cryptographically secure random source, keeps the
private half on the device, and never sends it anywhere. The public half goes in its own entry in the device group's
roster ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)), as that entry's
`history_key`.

A device writes its history key in a roster update it already makes, so the key costs no commit of its own:

- the device that creates the device group puts it in its own entry in the founding roster;
- a device that joins the device group puts it in the update that first sets its own `tag_signature_key`
  ([device-group.md](./device-group.md));
- a device whose entry has no history key, or another one, writes its own in an update of its own entry, which MAY
  carry other changes to that entry, such as its next KeyPackage announcement.

A device MUST NOT change the `history_key` of another device's entry; an update that replaces another device's entry
for another reason, such as a rename, carries that entry's `history_key` as it was. A key never rotates in this
version. A device that loses the private half generates a new key pair and writes the new public half the same way.

To seal a value to a device, a sibling uses `EncryptWithLabel` ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420),
section 5.1.3) with that device's history key as the public key, the label `"Marmot History"`, and the context the
message carrying the value defines, under the HPKE of the device group's ciphersuite. The sealed value is the
`HPKECiphertext` that `EncryptWithLabel` returns, encoded as in RFC 9420. The context binds a sealed value to its
purpose, so a value sealed for one purpose never opens for another. The device opens it with `DecryptWithLabel`, the
same label and context, and the private half of its history key. A sealed value that has bytes after its
`HPKECiphertext`, or that does not open, is dropped.

A sibling sends history only to a device whose roster entry has a history key it can seal to. A `history_key` that is
not a public key of the KEM is not an error ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md));
that device gets no history.

## Convergence and retained history

Small state is not group state. A branch selection that withdraws a device-group message's payload does not undo what
the message set on a device that already merged it. Every device converges on the same values once it holds every
value: the merge rules pick the same winner everywhere, whatever order values arrive in and however often. Every device
that merged a withdrawn update sends its items again, and every running device broadcasts what it holds at least every
24 hours and whenever the tip moves past the app-payload window. So a value that a running device holds reaches every
sibling that keeps reading the device group, however many messages that sibling lost. A value held only by a device
that never comes back is lost with it.

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
  an item at the largest version, 9007199254740991, takes that item out of its user's hands on every device for good: no
  change a user makes can beat it, and removing the device does not undo it. Only another value at that version can
  still replace it, by the tie-break. A read position that names a message no device holds can mark a whole chat as
  read, and one at the largest epoch and `created_at` marks every later message read as well: positions never move back,
  so removing the device does not clear it. A broadcast request makes every sibling broadcast, at most once an hour
  each. A linked device can already read and send in the account's chats; these let it also fix or change their
  settings.
- Nothing in small state is shown to other members of a chat, and no other account can read or write it.
- Any device of the account can rewrite another device's `history_key`, including a stolen linked device until it is
  removed. Siblings then seal history meant for that device to a key the stolen device chose, until that device writes
  its own key back. That history can include chats the stolen device is not in, such as a chat the user kept off a
  device linked with "add to all my chats" off.
- A history key is long-lived and never rotates in this version. A device that leaks the private half exposes every
  value sealed to it, past and future, until it writes a new key.
