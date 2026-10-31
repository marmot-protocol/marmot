# Account sync

Status: draft.

An account's devices keep some state the same everywhere: which messages the user has read, and per-chat settings such
as pins, mutes and archived chats. The account's devices exchange it inside their device group
([device-group.md](./device-group.md)), so it never reaches a chat, a relay or another account.

The non-normative direction is described in [../ideas/account-sync.md](../ideas/account-sync.md). This document covers
small state, the history keys that chat history is sealed to, and the recovery key that backups are sealed to. History
transfer, writing and restoring backups, and invite decisions are not specified yet.

## Surfaces

- Feature: [device-group.md](./device-group.md), which defines the device group, when a device trusts one, and its
  roster.
- App component: [../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), whose device entries
  carry each device's history key ([History keys](#history-keys)) and whose account entry carries the account's
  recovery key and backup writer ([The account's recovery key](#the-accounts-recovery-key)).
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

### History bundles

A device sends history as bundles. A bundle holds one stretch of one chat's history, as the sending device holds it,
for one receiving device.

**Stretches.** Chat order is the order of read positions ([Items](#items)): the epoch a message was sent in, then its
`created_at`, then its `id`. A position names one message by those three values, encoded as a read position's value:
`{"epoch":e,"at":t,"id":"<id>"}`. A stretch is every message from one position to another in chat order, both
included. A position may name a message the receiver does not hold, or one the bundle leaves out.

**What a bundle carries.** Every Marmot app event ([../foundation/application-messages.md](../foundation/application-messages.md))
delivered in the chat that the sender holds in the stretch, as the inner event it received or sent, except:

- an event whose retention ([../app-components/message-retention-v1.md](../app-components/message-retention-v1.md)) has
  expired;
- an event that branch selection withdrew ([../protocol-core/convergence.md](../protocol-core/convergence.md)), or that
  the sender sent and no relay accepted;
- a message deleted by its author or removed by an admin, and every event that targets one, such as a reaction, an
  edit or a report. The deletion or removal itself is carried, so a later bundle from a sibling that missed it does not
  bring the message back.

A bundle never carries MLS state, an epoch secret, or an epoch's media exporter secret.

**Encoding.** A bundle is one UTF-8 JSON object, and no object in it repeats a member name. Every number in it is a
decimal integer from 0 to 9007199254740991, without leading zeros. Its encoding is at most 8,388,608 bytes long. The
sender writes it without whitespace, with its members in the order shown.

| Member   | Value |
| -------- | ----- |
| `v`      | `1` |
| `chat`   | the chat's MLS group id: its raw bytes, every one, as lowercase hexadecimal with no prefix, so at most 512 characters |
| `from`   | the position the stretch starts at |
| `to`     | the position the stretch ends at, at or after `from` |
| `events` | the events, each one object below, in chat order |

| Member      | Value |
| ----------- | ----- |
| `event`     | the inner event, as a JSON object with exactly the members [../foundation/application-messages.md](../foundation/application-messages.md) gives it |
| `epoch`     | the MLS epoch the event was sent in |
| `retention` | the event's retention in seconds, from the retention decision the sender holds for it; absent when the sender holds none |
| `grant`     | for a review label (kind `1985`) or an admin removal (kind `4891`) only: `true` when the sender found that the event's author had the authority the kind needs at the event's epoch, `false` when it found they did not; absent when the sender has not decided |
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
  wrong kind of value (`null` included), a number is out of range, hexadecimal is not lowercase or not the length shown,
  or `keys` is empty. It does not check whitespace or member order, which only the sender's rule fixes;
- checks each event on its own, and drops one whose `id` does not match its content
  ([../foundation/application-messages.md](../foundation/application-messages.md)), whose position is outside the
  bundle's stretch, that has `grant` on another kind, or whose retention has expired;
- adds every other event it does not already hold, and leaves every event it holds as it is, so an import never undoes a
  newer update. An edit, reaction or deletion that arrived before its target takes effect once the target arrives;
- takes `grant` as the event's authority and keeps it, and gives an event without one no authority until a copy of the
  event reaches it live, when it judges that copy's authority as for any live event;
- has each event expire at its `created_at` plus its `retention`, as message retention does for live messages.

The receiver cannot check that an event's author was a member of the chat at its epoch, or held any authority there.
Imported history is as trustworthy as the sibling that sent it ([Security considerations](#security-considerations)).
A client MAY show which device a message was imported from.

Importing history is not reading it. It never moves the device's read position, so the device never sends a read
position for a message only because it was imported. A client SHOULD NOT count imported messages as unread.

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
a backup. It MUST NOT store the words, the entropy or the private half, and MUST NOT send them anywhere.

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
4. Once the update is committed, or the public half kept, it forgets the words, the entropy and the private half. If
   it cannot commit the update, because the account entry is no longer the one it read or the device group cannot
   take a commit from it yet, it keeps them in memory, never on disk, for the user to try again.

A device that trusts no device group ([device-group.md](./device-group.md), "Trust") keeps the public half itself,
across restarts, as the account's recovery key; new words replace it, and none of the rules below for roster updates
apply until the device trusts a device group. When it creates a device group, the founding roster's account entry holds
that key and names this device as `backup_writer`. When it joins one instead, the roster's account entry stands,
whatever it holds, since a roster with no key may be one whose backups the user turned off. Either way, once the device
trusts the device group it forgets the key it kept, and the roster's account entry is the account's recovery key from
then on.

An update that sets the account entry replaces it whole, so it is computed from the entry as the device read it. A
device MUST NOT commit it on a roster whose account entry is not the one it read, including when it commits the update
again after branch selection dropped it ([../protocol-core/convergence.md](../protocol-core/convergence.md)). Otherwise
an update from a stale read would undo newer words another device wrote.

A device turns backups off with an update that sets the account entry to hold neither `recovery_public_key` nor
`backup_writer`, under the same rule. No device writes backups while they are off, and turning them on again takes new
words, in the four steps above. Backups already written stay until they are deleted. A device that trusts no device
group turns backups off by forgetting the key it keeps.

A device commits an update that sets the account entry again only when branch selection drops it, under the rule above,
and never because the roster does not hold what the user chose: a roster with no key looks the same before backups were
turned on and after they were turned off again, so committing a change again on what the roster holds could undo another
device's turn-off. A device shows backups as the roster's account entry holds them now. A device keeps each update it
makes to the account entry, with the entry it was computed from, across restarts, until branch selection can no longer
drop it. While one is not yet confirmed, or was dropped and is neither committed again nor refused, the device makes no
other change to the account entry. An update whose publication fails is published again or discarded as
[../protocol-core/publish-lifecycle.md](../protocol-core/publish-lifecycle.md) allows; that is not committing it again,
and a discarded update is lost as a refused one is.

Two limitations are known. After a fork, the rule above may commit an earlier change again and refuse a later one, so a
dropped change can stay lost: a device shows the account entry of the branch selected now, even while branch selection
could still pick another, and the user makes a lost change again. And the rule against committing on an entry that is
not the one the device read compares values: when branch selection drops an update turning backups on, and the winning
branch turns backups on with other words and off again before the device reads it, the entry holds no key, as it did
when the device read it, and the update is committed again.

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
  receiving device only. An attachment key opens only the one file it names, never the rest of that epoch's media.
