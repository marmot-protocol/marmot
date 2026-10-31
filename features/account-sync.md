# Account sync

Status: draft.

An account's devices keep some state the same everywhere: which messages the user has read, and per-chat settings such
as pins, mutes and archived chats. The account's devices exchange it inside their device group
([device-group.md](./device-group.md)), so it never reaches a chat, a relay or another account.

The non-normative direction is described in [../ideas/account-sync.md](../ideas/account-sync.md). This document covers
small state and history: the history keys that chat history is sealed to, history bundles, and the history deliveries
that carry them from the device that adds a sibling to a chat; and the recovery key that backups are sealed to.
Writing and restoring backups, and invite decisions, are not specified yet.

## Surfaces

- Feature: [device-group.md](./device-group.md), which defines the device group, when a device trusts one, and its
  roster.
- App component: [../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), whose device entries
  carry each device's history key ([History keys](#history-keys)) and whose account entry carries the account's
  recovery key and backup writer ([The account's recovery key](#the-accounts-recovery-key)).
- Marmot app events: kind `475` (small-state update), kind `476` (broadcast request) and kind `473` (history delivery),
  sent only in a device group ([Messages](#messages), [History deliveries](#history-deliveries)). Their kinds are
  registered in [../foundation/registries.md](../foundation/registries.md).
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
([../foundation/application-messages.md](../foundation/application-messages.md)) delivered in the chat, or imported from
a sibling's history ([History bundles](#history-bundles)) with the epoch its bundle gives it, other than an edit (kind
`1009`), whose epoch and `created_at` are each at most 9007199254740991. A read position carries no version
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
device marks as read every message of the chat, delivered or imported, at or before the position it holds, including
ones that reach it later; the position changes nothing else, so a message that never counts as unread, such as an edit, stays that way
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
  no longer be in the device group. A device that does not keep which items an update carried MAY instead send every
  item it holds again.
- When branch selection withdraws a broadcast request, every device that sent or read it sends a new broadcast request,
  so a device whose request no sibling read still gets their broadcasts.
- A device that cannot tell whether a withdrawn device-group message was an update or a broadcast request MAY treat it
  as both.

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
of. The sibling whose Commit adds it to the chat sends them to it ([History deliveries](#history-deliveries)), sealed so
that only that device can read them, even though they travel through the device group that every sibling reads.

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
for another reason, such as a rename, carries that entry's `history_key` as it was. This binds senders only: a roster
update that changes another device's `history_key` is still valid ([Security considerations](#security-considerations)).
A device does not rotate its key in this version; it replaces it only when it loses the private half, by generating a
new key pair and writing the new public half the same way.

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

### History bundles

A device sends history as bundles. A bundle holds one stretch of one chat's history, as the sending device holds it,
for one receiving device.

**Stretches.** Chat order puts every app event of the chat in the order read positions use ([Items](#items)): the epoch
it was sent in, then its `created_at`, then its `id`. A position names one event by those three values, encoded as a
read position's value: `{"epoch":e,"at":t,"id":"<id>"}`. Unlike a read position, it may name any event, an edit
included. A stretch is every event from one position to another in chat order, both included. A position may name an
event the receiver does not hold, or one the bundle leaves out.

**What a bundle carries.** Every Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
of the chat that the sender holds in the stretch, as the inner event it received, sent or imported from a sibling's
history, except:

- an event whose retention ([../app-components/message-retention-v1.md](../app-components/message-retention-v1.md)) has
  expired; a retention of `0`, disappearing messages off, never expires;
- an event whose epoch, `created_at` or retention is larger than 9007199254740991, which no bundle number can hold;
- an event that branch selection withdrew ([../protocol-core/convergence.md](../protocol-core/convergence.md)), or that
  the sender sent and no relay accepted;
- a message removed by an admin (kind `4891`) with the authority the sender holds for it, or deleted in any other way
  the sender's client applies, and every event that names such a message in its `e` tag to change or answer for it,
  such as a reaction (kind `7`), an edit (kind `1009`) or a report (kind `1984`). A chat message that replies to it is
  not one of these. The removal itself is carried, so a later bundle from a sibling that missed it does not bring the
  message back once the receiver holds the removal's authority.

A bundle never carries MLS state, an epoch secret, or an epoch's media exporter secret.

**Encoding.** A bundle is one UTF-8 JSON object, and no object in it repeats a member name. Every number in it is a
decimal integer from 0 to 9007199254740991, without leading zeros. Its encoding is at most 8,388,608 bytes long. The
sender writes it without whitespace, with its members in the order shown.

| Member   | Value |
| -------- | ----- |
| `v`      | `1` |
| `chat`   | the chat's MLS group id: its raw bytes, one to 256 of them, every one, as lowercase hexadecimal with no prefix, so 2 to 512 characters |
| `from`   | the position the stretch starts at |
| `to`     | the position the stretch ends at, at or after `from` |
| `events` | the events, each one object below, in chat order |

| Member      | Value |
| ----------- | ----- |
| `event`     | the inner event, as a JSON object with exactly the members [../foundation/application-messages.md](../foundation/application-messages.md) gives it |
| `epoch`     | the MLS epoch the event was sent in |
| `retention` | the event's retention in seconds, from the retention decision the sender holds for it, with `0` for disappearing messages off as in [../app-components/message-retention-v1.md](../app-components/message-retention-v1.md); absent when the sender holds none |
| `grant`     | for a review label (kind `1985`) or an admin removal (kind `4891`) only: `true` when the sender holds that the event's author had the authority the kind needs at the event's epoch, `false` when it holds they did not, whether it found that itself or imported it with the event; absent when the sender has not decided |
| `keys`      | for an event with encrypted-media attachments only: one or more attachment keys, below; absent when the sender can give none |

An attachment key is `{"ciphertext_sha256":"<hash>","key":"<key>"}`: the `ciphertext_sha256` of one of the event's
media references ([encrypted-media.md](./encrypted-media.md)) and that file's `file_key`, each as 64 lowercase
hexadecimal characters.

**Splitting.** A history longer than one bundle allows is split into bundles over consecutive stretches: each bundle's
`from` is the previous bundle's `to`, and an event at that shared position travels in either bundle.

**Encryption.** The sender encrypts each bundle with ChaCha20-Poly1305 ([RFC 8439](https://www.rfc-editor.org/rfc/rfc8439))
under a fresh 32-byte key from a cryptographically secure random source, a nonce of 12 zero bytes, and the 24 ASCII
bytes of `marmot history bundle v1` as associated data. It uses each key for one bundle only, so the fixed nonce never
repeats under a key. The key and the SHA-256 of the ciphertext reach the receiving device sealed to its history key
([History keys](#history-keys)) in the message that carries the bundle. No compression is applied.

**Importing.** A device that receives a bundle:

- drops the whole bundle if it does not decrypt, has a `v` other than `1`, names a chat other than the one its carrying
  message names, has a `from` after its `to`, or breaks the encoding above other than in layout: it is longer than
  8,388,608 bytes, an object in it lacks a member it must have, has one not shown or repeats one, a member holds the
  wrong kind of value (`null` included), a number is out of range or not written as a decimal integer without leading
  zeros (such as `9.0` or `9e0`), hexadecimal is not lowercase or not the length shown,
  or `keys` is empty. It does not check whitespace or member order, which only the sender's rule fixes;
- checks each event on its own, and drops one whose `id` does not match its content
  ([../foundation/application-messages.md](../foundation/application-messages.md)), whose position is outside the
  bundle's stretch, that has `grant` on another kind, or whose retention has expired;
- adds every other event it does not already hold, and leaves every event it holds as it is, so an import never undoes a
  newer update. An edit, reaction or deletion that arrived before its target takes effect once the target arrives;
- takes `grant` as the event's authority and keeps it, and gives an event without one no authority until a copy of the
  event reaches it live, when it judges that copy's authority as for any live event;
- drops each attachment key whose `ciphertext_sha256` names none of the event's media references, and imports the event
  without it;
- keeps every other attachment key, and opens the file it names with it, as that file's `file_key`, when it does not
  hold the media exporter secret of the event's epoch ([encrypted-media.md](./encrypted-media.md));
- has each event whose `retention` is more than `0` expire at its `created_at` plus its `retention`, as message retention
  does for live messages. An event whose `retention` is `0`, or that has none, does not expire this way.

An imported event did not reach the receiver as an MLS message in the chat. Where a rule checks the account of an
event's MLS sender, such as an edit's authorship ([../foundation/application-messages.md](../foundation/application-messages.md)),
the receiver checks the account the event's `pubkey` names. Where a rule checks that sender's authority at the event's
epoch, such as an admin's ([content-moderation.md](./content-moderation.md)), the event's `grant` is that authority's
recorded verdict. An imported event is no payload of a branch the receiver holds, so a later branch selection in the
chat never withdraws it there.

The receiver cannot check that an event's author was a member of the chat at its epoch, or held any authority there.
Imported history is as trustworthy as the sibling that sent it ([Security considerations](#security-considerations)).
A client MAY show which device a message was imported from.

Importing history is not reading it. It never moves the device's read position, so the device never sends a read
position for a message only because it was imported. A client SHOULD NOT count imported messages as unread.

### History deliveries

History comes from the device that adds a sibling to a chat, and from no other. When a device's own Commit adds a
sibling's leaf to a chat, the device sends that sibling the chat's history as history deliveries, one bundle each,
through the device group.

**Message.** A history delivery is a Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
of kind `473`, sent as an MLS application message in the device group and nowhere else. Its content is one UTF-8 JSON
object with exactly these members, each once, written in this order without whitespace, at most 32,768 bytes long:
`v`, `from`, `to`, `chat`, `sealed`, then exactly one of `bundle` and `blossom`. `v` is a JSON number, written `1`;
`blossom` is a JSON array of strings; the other members are JSON strings. Every character in a string is written as
itself, never as a JSON escape (`\/` included). Unlike a bundle's layout, this one binds receivers too.

| Member   | Value |
| -------- | ----- |
| `v`      | `1` |
| `from`   | the sending device's slot ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)), as 64 lowercase hexadecimal characters |
| `to`     | the receiving device's slot, the same way |
| `chat`   | the chat's MLS group id, as in a bundle: its raw bytes, one to 256 of them, as lowercase hexadecimal with no prefix |
| `sealed` | the sealed bundle key and hash, below, in standard base64 with padding ([RFC 4648, section 4](https://www.rfc-editor.org/rfc/rfc4648#section-4)) |
| `bundle`  | the bundle's ciphertext ([History bundles](#history-bundles)), non-empty, in standard base64 with padding |
| `blossom` | one to four Blossom servers that hold the bundle's ciphertext as one blob, each as its base URL, valid as an encrypted-media endpoint's base URL is ([../app-components/group-encrypted-media-v2.md](../app-components/group-encrypted-media-v2.md)): a normalized `http` or `https` URL of 1 to 2,048 bytes with a host and no userinfo, query, or fragment; no URL appears twice |

`sealed` is the bundle's 32-byte key followed by the 32-byte SHA-256 of its ciphertext, 64 bytes in all, sealed to the
history key of `to`'s roster entry ([History keys](#history-keys)) with the context

```text
struct {
  opaque purpose<V>;
  opaque from<V>;
  opaque to<V>;
  opaque chat<V>;
} HistoryDeliveryContextV1;
```

in the Marmot binary profile ([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)): `purpose` is
the 26 ASCII bytes of `marmot history delivery v1`, `from` and `to` are the two slots' 32 bytes, and `chat` is the chat's
MLS group id. The context binds a sealed value to its sender, receiver and chat, so it never opens for another. Under
ciphersuite `0x0001`, `sealed` is 115 bytes: the 32-byte KEM output with a one-byte length, then the 80-byte ciphertext
with a two-byte length, as RFC 9420's variable-length vectors encode them. A bundle whose plaintext is at most 23,552
bytes always fits a delivery inline. A delivery that names Blossom servers carries no bundle, so its bundle may be as
long as [History bundles](#history-bundles) allows.

**Blossom.** A bundle's blob is its ciphertext, at the address its SHA-256 gives it, which `sealed` already carries. For
each server, let `server_root` be its base URL with all trailing `/` bytes removed and `hash_hex` the 64-character
lowercase hexadecimal encoding of that SHA-256. The sender uploads the ciphertext to `server_root || "/upload"` with the
[Blossom BUD-02](https://github.com/hzrd149/blossom/blob/master/buds/02.md) upload operation; the receiver fetches
`server_root || "/" || hash_hex` with the [Blossom BUD-01](https://github.com/hzrd149/blossom/blob/master/buds/01.md)
`GET` operation and adds no extension, query, or fragment, as [encrypted-media.md](./encrypted-media.md) ("Locator
Kinds") does for its fallback fetch URLs. Whether a device contacts a server is its own policy; non-normative guidance
is in [../implementation-model.md](../implementation-model.md) ("Network destination safety").

**Sending.**

- After the publish obligation of a device's own Commit succeeds
  ([../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md)), the device owes the chat's history to
  each sibling whose leaf that Commit adds: a leaf of its own account whose device tag, read against its trusted roster,
  names a device in that roster ([device-group.md](./device-group.md), "Matching leaves to devices"). It records that it
  owes the history before it sends any of it. A Commit that adds a sibling to the device group itself owes nothing.
- It sends a history it owes only while the sibling is still a device in its roster whose entry has "bring chat history"
  on and a history key it can seal to, and only while the device still holds the chat. It checks these when it would
  send, and forgets the history as soon as one fails; it does not wait for a history key to appear. A sibling it can
  add carries a tag, and a device writes its history key in the same update that sets its `tag_signature_key`
  ([History keys](#history-keys)), so a sibling whose client supports history has one by then.
- It sends only while its own leaf in the device group carries a device tag that reads as its slot, as for heartbeats
  ([device-group.md](./device-group.md#heartbeats)); until then the history stays owed.
- It sends everything it holds of the chat, as [History bundles](#history-bundles) gives it, each bundle in one
  delivery: inline, split so that each bundle fits a delivery, or through Blossom. It uploads a bundle it sends through
  Blossom to servers of its own choosing, such as the chat's `blossom-v1` encrypted-media endpoints
  ([encrypted-media.md](./encrypted-media.md), "Locator Kinds"), and sends the delivery only once the upload to each
  server it names has succeeded. It does not delete a blob it uploaded: the receiver may fetch it until it drops the
  delivery, and nothing tells the sender when that is. An event too large to fit any bundle it can send is left out; the
  rest of the history is sent.
- A device MAY bound how many deliveries one history takes. When a history needs more, the device either sends the
  deliveries of its newest bundles, as many as the bound allows, and leaves the older history out, or forgets the
  history, sending none of it.
- A bundle whose upload fails, or a delivery whose publication fails without reaching any relay, leaves the history
  owed, to be sent again. When branch selection withdraws a delivery the device sent
  ([../protocol-core/convergence.md](../protocol-core/convergence.md)), the history is owed again. A device forgets a
  history 7 days after the Commit that made it owed, sent or not.
- A device sends no other history. There are no receipts and no requests for history.

**Receiving.** A device reads a history delivery only from the device group it trusts ([device-group.md](./device-group.md),
"Trust"), and ignores kind `473` in any other group. It drops one unless:

- its content is exactly the encoding above, byte for byte, each member holding a value the table allows: another member
  order, whitespace, an escaped character, a repeated, missing or extra member, or a value the table does not allow,
  such as an empty `blossom`, a fifth server, a URL named twice or one that is not normalized, drops it;
- `to` is its own slot;
- `from` is another device in its current roster;
- the leaf that sent it, as that leaf was in the epoch the delivery was sent in, carries a device tag that reads as
  `from`'s against its current roster ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md),
  "Reading tags"). The device reads that leaf from the member state it retains for that epoch
  ([../protocol-core/retained-history.md](../protocol-core/retained-history.md), "Retained cryptographic material"); a
  delivery from an epoch whose member state it no longer retains has no readable sender and is dropped, as is one whose
  sender's `tag_signature_key` in the current roster no longer verifies the tag;
- `sealed` opens with its history key and the context above to exactly 64 bytes.

It then takes the bundle's ciphertext: it base64-decodes `bundle`, or fetches the blob from one of the `blossom`
servers, reading no more than 8,388,624 bytes, the longest bundle's 8,388,608 bytes and its 16-byte tag. It checks
that the SHA-256 of the ciphertext is the hash it opened, decrypts it with the key it opened, and imports the bundle as
[History bundles](#history-bundles) gives it. A delivery the device cannot import yet is kept: one for a chat it does
not hold yet, such as one read before the chat's Welcome, until it joins that chat, and one whose blob it has not
fetched, until a fetch succeeds. A fetch that fails, or that returns other bytes, is tried again, from any of the
servers. A kept delivery is imported once it can be if `from` is still a device in the roster then. Every kept delivery,
whether it waits for its chat or its blob, is dropped 7 days after the device read it, and with it any fetch still to
try. A device MAY bound how many deliveries it keeps this way, and it MAY fetch a kept delivery's blob before or after
it joins. A branch selection in the device group that later withdraws a delivery neither undoes its import nor drops it
while it is kept, as it does not undo small state a device merged ([Convergence and retained
history](#convergence-and-retained-history)); only the sender owes the history again.

**Limits of this version.** History deliveries cover the normal path, the adder sending to the device it adds, and no
more:

- Only the adder sends. A sibling that holds more of the chat, such as one with older messages, sends nothing.
- There are no receipts. A delivery accepted by a relay but never read, or read only once the device no longer retains
  the member state of the epoch it was sent in or once the sender's `tag_signature_key` in the current roster no longer
  verifies its tag, is lost, and so is that history. A sender owes a withdrawn delivery's history again only when it
  learns of the withdrawal, so one whose record of the delivery is already gone, or that stops before it acts on the
  withdrawal, loses that history too.
- A device that a device of another account adds to a chat, or whose entry has no history key or has "bring chat history"
  off when the history is sent, gets no history. Neither does a chat whose MLS group id is empty or longer than 256 bytes,
  which no bundle or delivery can name; small state covers none longer than 256 bytes either.
- A history needs as many deliveries as it has bundles, and the sender may bound them, so a long history can arrive
  without its oldest messages, or not at all. A sender with no Blossom server to upload to sends no more of a history
  than fits the inline deliveries it will send. An event too large for any bundle is left out, as is one whose epoch,
  `created_at` or retention is larger than a bundle number can hold.
- Blobs are not deleted. A Blossom server keeps each blob it holds, with its size and when it was uploaded and fetched,
  until the server expires it ([Security considerations](#security-considerations)). A receiver that fetches a blob
  after its server expired it gets no history from that delivery.
- An imported attachment key is used only when the device does not hold the media exporter secret of the event's epoch.
  A device that holds a secret for that epoch from another branch of the chat than the event's opens the file with that
  secret, not the imported key, and the file does not open.
- History is owed once the adding Commit's publication succeeds. When branch selection in the chat later withdraws that
  Commit, the history is still sent; the sibling imports it only if it joins the chat, and drops it 7 days after
  reading it otherwise.

## Backups

A backup keeps an account's history for when every device that holds it is gone. Backups are sealed to the account's
recovery key, which is separate from the account's signing key: holding the signing key, or being a linked device, does
not open a backup. This version specifies the recovery key and how the account's devices keep it. Writing, finding and
restoring backups are not specified yet.

### Recovery key

The recovery key is 12 words from the English word list of
[BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki): 128 bits of entropy and their 4-bit checksum,
encoded as BIP-39 encodes them. A device generates the entropy from a cryptographically secure random source. The user
never chooses it: a password the user chose would be too weak to protect a backup that anyone can download and attack
offline.

The words derive an HPKE key pair ([RFC 9180](https://www.rfc-editor.org/rfc/rfc9180)) under DHKEM(X25519,
HKDF-SHA256), the KEM of ciphersuite `0x0001`, whatever ciphersuite the device group uses, because a device that
restores a backup may hold no group:

```text
prk      = HKDF-Extract(salt = "marmot recovery key v1", IKM = entropy)
ikm      = HKDF-Expand(prk, info = "marmot recovery key pair", L = 32)
(sk, pk) = DeriveKeyPair(ikm)
```

HKDF is HKDF-SHA256 ([RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)), and the salt and info are their ASCII bytes.
`entropy` is the 16 bytes the words encode, not BIP-39's seed, and there is no passphrase. `DeriveKeyPair` is that
KEM's (RFC 9180, section 7.1.3). Test vectors:

```text
words:   abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about
entropy: 00000000000000000000000000000000
ikm:     f2b851179e27ff0fa2a197b538c8e525aac11fcf3d8570bc8afb3e5dd48aea28
sk:      f99da3bd75751479570bd7d7a807bebb49c8da68aed12e813862cccdff5a577d
pk:      aed5608fc1960f7992decafb36786d19508dce48e02288785cf24e557d58a368

words:   legal winner thank year wave sausage worth useful legal winner thank yellow
entropy: 7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f
ikm:     20d2dc269edddf61ef7859324c9459eb96ae0d34ffbace54b404d63862bba855
sk:      8570ead0cc10c1ae63c6357959fdb15996475dabe3b781c4ebecdacb2015ef83
pk:      9076c238afd9311184e7dda595f7d42f5c73b48bff561e88482c4435d5cb5f10
```

To seal a value to the recovery key, a device uses `EncryptWithLabel` ([RFC 9420](https://www.rfc-editor.org/rfc/rfc9420),
section 5.1.3) with the recovery key's public half as the public key, the label `"Marmot Backup"`, and the context the
format carrying the value defines, under the HPKE of ciphersuite `0x0001`. The sealed value is the `HPKECiphertext`
that `EncryptWithLabel` returns, encoded as in RFC 9420. It opens with `DecryptWithLabel`, the same label and context,
and the private half the words derive. A sealed value that has bytes after its `HPKECiphertext`, or that does not open,
is dropped. The label keeps a value sealed for a backup from opening as history ([History keys](#history-keys)), and
the other way round.

Devices keep only the public half. A device derives the private half only while the user's words are in hand, to open
a backup. It MUST NOT write the words, the entropy or the private half to persistent storage of any kind, and MUST NOT
send them anywhere.

### The account's recovery key

The account's recovery key is the `recovery_public_key` of the account entry in its device group's roster
([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)), and `backup_writer` names, by slot,
the one device that writes the account's backups. While the account entry has no `recovery_public_key`, backups are
off.

A device turns backups on, or replaces the words, in four steps:

1. It generates new words and shows them to the user once.
2. The user types back at least two of them, at positions the device picks, to show they were written down. The device
   goes on only if they match.
3. It derives the public half and writes it as the account entry's `recovery_public_key`, in a roster update whose
   only operation sets the account entry. When the entry has no `recovery_public_key`, the update also names this
   device as `backup_writer`; otherwise it keeps the `backup_writer` the entry names, or names this device if it names
   none. A device that trusts no device group keeps the public half instead, in place of any it kept (below).
4. Once the update is committed, or the public half kept, it forgets the words, the entropy and the private half.

A device that trusts no device group ([device-group.md](./device-group.md), "Trust") keeps the public half itself,
across restarts, as the account's recovery key; new words replace it, and none of the rules below for roster updates
apply until the device trusts a device group. When it creates a device group, the founding roster's account entry holds
that key and names this device as `backup_writer`. When it joins one instead, the roster's account entry stands,
whatever it holds, since a roster with no key may be one whose backups the user turned off. Either way, once the device
trusts the device group it forgets the key it kept, and the roster's account entry is the account's recovery key from
then on.

An update that sets the account entry replaces it whole, so the account entry changes only by compare-and-set: the
update is computed from the entry as the device read it, and a device MUST NOT commit it on a roster whose account
entry, at the tip of the selected branch ([../protocol-core/convergence.md](../protocol-core/convergence.md)), is not
the one it read. Otherwise an update from a stale read would undo newer words another device wrote.

A device turns backups off with an update that sets the account entry to hold neither `recovery_public_key` nor
`backup_writer`, under the same rule. No device writes backups while they are off, and turning them on again takes new
words, in the four steps above. Backups already written stay until they are deleted. A device that trusts no device
group turns backups off by forgetting the key it keeps.

A device commits an update that sets the account entry again only when branch selection drops the Commit that carried
it, and only under the same compare-and-set; never because the roster does not hold what the user chose: a roster with
no key looks the same before backups were turned on and after they were turned off again, so committing a change again
on what the roster holds could undo another device's turn-off. A device shows backups as the account entry of the
selected roster holds them now. How a device holds the words while it cannot commit their update, retries, and holds
back its other changes to the account entry while one of its updates is unsettled is local to it.

Two limitations are known. An update that branch selection drops and the compare-and-set then refuses, or whose
publication fails ([../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md)), is lost, and the
user makes the change again: after a fork the rule above may commit an earlier change again and refuse a later one,
and a device shows the account entry of the branch selected now, even while branch selection could still pick
another. And the compare-and-set compares values: when branch selection drops an update turning
backups on, and the winning branch turns backups on with other words and off again before the device reads it, the
entry holds no key, as it did when the device read it, and the update is committed again.

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
  sibling syncs, including a chat it is not in, such as an older chat it was not added to when it was linked. It also
  learns the group id of every chat any sibling sends history for, from that delivery's `chat`. A device MUST NOT publish
  a group id it learned either way through a transport envelope, and an item or a delivery is not evidence that the
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
- Every sibling reads every history delivery: it sees that the sender sent the receiver history and which chat it was
  for, but cannot open it. It sees how large an inline bundle is. Of a delivery that names Blossom servers it sees the
  servers but not the blob's hash, which is sealed with its key; a server that lists the blobs an uploader stored can
  still show it the blob and its size. The rule above against publishing a group id learned this way applies.
- A Blossom server that holds a history blob learns what the upload's authorization says of the uploader, the blob's
  size, when it was uploaded and fetched, and where each request came from, and keeps the blob until it expires it. The
  receiver fetches from servers the sender chose, which may be a chat's encrypted-media endpoints that another account's
  admins set. Only the receiver's history key opens the blob's key.
- Any device of the account can replace the recovery key and name itself as `backup_writer`, including a stolen linked
  device until it is removed. Backups written after that are sealed to words its holder chose, until a device of the
  user replaces the words again. Backups already written stay sealed to the words they were sealed to.
- Any device of the account can turn backups off, including a stolen linked device until it is removed. No backups are
  written until a device of the user turns them on again.
- The recovery key's public half is in the roster, so every device ever in the device group, a removed one included,
  can seal a value to it. Only the words open one.
- The words are the one secret that opens backups. Anyone who sees them can open every backup sealed to them, so a
  device shows them only while the user writes them down, and never stores them. 128 bits of entropy put an offline
  search out of reach.
- Imported history is as trustworthy as the sibling that sent it. A stolen linked device can send invented events
  alongside real ones, with any author, time, retention or `grant`, and leave real ones out; the receiver cannot tell
  them from what the chat's members sent. A `grant` of `true` it invents gives a review label or removal effect on the
  receiving device, and on each device that device later sends that history to. An attachment key opens only the one
  file it names, never the rest of that epoch's media.
- A delivery's `from` is only as good as the sending leaf's device tag, which reads against the `tag_signature_key` in a
  roster entry that any device can rewrite. A stolen linked device can make its deliveries read as another sibling's,
  so which device a message was imported from, as a client may show it, is only as trustworthy as the roster.
