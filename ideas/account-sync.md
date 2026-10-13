# Account sync

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

This idea covers what follows Alice from device to device: the history of her chats when she links a new device, small
state such as read positions and mutes, and backups for when every device is gone. It builds on
[multi-device.md](./multi-device.md), which covers linking, the device group, and the roster.

## At a glance

- **History comes from a sibling.** Old messages on relays are encrypted for epochs a new device was never part of, so
  it can't read them. Only a device that was there can hand over what it saw.
- **History is content, never membership.** It carries messages, reactions, and attachment keys. It never carries MLS
  state, so it can't let a device act as a member of the past.
- **It is meant for one device.** Each history bundle is sealed to the receiving device, even though it travels
  through the device group.
- **Small state follows Alice.** Read positions, pins, mutes, and archived chats match across her devices.
- **Backups are for losing everything.** With two or more devices, the others already have her history. A backup is
  protected by a recovery key, not her nsec, and restores content, not chat membership.

## Words used here

| Term | Meaning |
| --- | --- |
| History | The messages one device has for one chat: text, tags, reactions, edits and deletions already applied, and attachment keys. |
| History bundle | One chat's history, packed and encrypted for a single receiving device. |
| History key | A public key a device puts in its roster entry so siblings can seal history to it. |
| Manifest | The small list that describes a large bundle: its chunks, where each is stored, and each chunk's hash. |
| Small state | Per-chat settings and positions that follow Alice: read position, pins, mutes, archived chats. |
| Backup | An encrypted archive of history and small state, written by one of Alice's devices. |
| Backup writer | The one device the roster names to write backups. |
| Archive key | The random key backups are encrypted with. Every linked device has it. |
| Recovery key | 12 words that unlock the archive key when no linked device is left. Separate from the nsec. |

Device, sibling, device group, and roster mean what they mean in [multi-device.md](./multi-device.md#words-used-here).

## What this does and does not protect

- **No MLS state ever moves.** History, small state, and backups never include leaf keys, epoch secrets, or anything
  else that would let a device rejoin or read a chat through old state.
- **Imported history is as trustworthy as the device that sent it.** Marmot messages are authenticated by MLS when they
  are delivered; there is no signature a receiving device could re-check later. A stolen linked device could invent
  history. That falls under the stolen-linked-device limit in multi-device.
- **History already sent can't be recalled.** Removing a device later doesn't take back what it received.
- **Disappearing messages stay advisory.** Expired messages are never sent, and the rest keep their original expiry.
  As with retention today, this relies on Alice's own devices behaving, not on any enforcement.
- **A stolen nsec doesn't open a backup.** The recovery key does. A stolen linked device holds the archive key, but it
  can already read everything that key protects.
- **Lose the recovery key and every device, and the backup is gone.** Nobody can read it, Alice included.
- **A backup never restores membership.** Getting back into a chat needs a fresh add from someone still in it, so a
  stolen backup is never a way in.
- **Attachments depend on their storage.** History carries the keys to attachments, not the files. If a Blossom server
  has dropped a file, it is gone on the new device too.

## Scene 1: What history is

When the laptop joins Book club, the iPhone sends it a record of what the iPhone has for that chat: each message's
sender, time, text and tags, its reactions, and any edits and deletions already applied.

**Attachments travel as keys, not files.** In Marmot, an attachment's key comes from the MLS epoch its message was sent
in ([../features/encrypted-media.md](../features/encrypted-media.md)). The laptop can't derive keys for epochs before
it joined, so the record carries each attachment's key, locator, and hashes. The laptop fetches the encrypted file from
the Blossom server when Alice opens it, the same way it fetches any new attachment.

**Disappearing messages:** expired messages are never sent. The rest arrive with their original expiry
([../app-components/message-retention-v1.md](../app-components/message-retention-v1.md)) and vanish on the laptop at
the same moment as everywhere else.

**Never included:** MLS state, epoch secrets, pending operations, or anything that would let the laptop act as a member
of the past. History is read-only content.

## Scene 2: Who sends it

**The device that adds the laptop to a chat also sends that chat's history.** At link time that is the approving
iPhone. Later it is whichever sibling fills a gap. There is exactly one adder per chat, so nothing needs coordinating.

**Filling in older history.** Say Alice got her iPhone last month, but her iPad has two years of Book club. The iPhone
can only give a month, so the laptop shows "History from March". Then:

1. The laptop records in the device group which date its history for Book club starts from.
2. Any sibling with older messages for that chat replies with a short offer saying how far back it goes.
3. The laptop accepts the offer that reaches furthest back. Only that sibling sends the missing range.
4. The laptop updates its start date. Any offer that still reaches further back can be accepted the same way, though
   one round is usually enough.

Offers are tiny, and only the accepted one moves data, so two siblings never send overlapping history. Nothing waits
on the device with the most history, so a sleeping iPad never blocks the link. This works because a device's history
for a chat runs unbroken from when it joined, apart from deleted or expired messages that nobody sends anyway.

## Scene 3: How much

**Everything the sending device has.** Text is small, and attachments travel as keys, so even years of history is a
modest transfer. The cost that remains is the laptop fetching attachment files later, one at a time, as Alice scrolls.

"Bring chat history" stays a single on/off setting per device, as in multi-device.

## Scene 4: How it moves

History is meant for the laptop alone. Other siblings may not be in that chat, and the setting may be off for some of
them.

1. When it is linked, the laptop puts a **history key** in its roster entry.
2. The iPhone packs Book club's history into a bundle and encrypts it with a fresh random key.
3. **A small bundle goes straight through the device group**, if it fits in one message of about 32 KiB once sealed.
   That stays well under the event sizes relays commonly accept.
4. **A large bundle is split into chunks of about 8 MiB.** Each chunk is uploaded to a Blossom server as its own
   opaque encrypted blob. A small **manifest** listing every chunk, where it is, and its hash goes through the device
   group instead.
5. The bundle's key, and the manifest if there is one, go through the device group **sealed to the laptop's history
   key**. Other siblings can see that a transfer happened, but can't read it.
6. The laptop fetches, checks each chunk against the manifest, imports, and confirms chunk by chunk. The iPhone deletes
   each Blossom blob once it is confirmed.

**Interruptions:** the laptop resumes by fetching only the chunks it hasn't confirmed. If the iPhone is the one
interrupted, it re-uploads only the missing chunks, or builds a fresh bundle if its copy is gone.

**Where history stops and live chat starts.** A bundle covers everything up to the point the laptop joined. Anything
after that reaches the laptop live, as a member. An edit, reaction, or deletion that arrives live and refers to an
imported message applies to it normally.

**What Alice sees:** progress per chat on the laptop, such as "Book club: history imported", next to the joining
progress from multi-device Scene 5.

## Scene 5: Trusting imported history

The laptop marks imported messages internally. The UI shows a subtle divider, such as "Imported from iPhone", where its
own live history begins.

Within Alice's own devices, the trust is the point: she linked the sending device herself. The limit is the one
multi-device already states. A stolen linked device is inside the circle, and it could send invented history along
with real history.

## Scene 6: Small state that follows Alice

What matches across her devices:

- **Read position per chat.** Read it on her phone, and the laptop doesn't show it as unread.
- **Pins.**
- **Mute and notification settings per chat.**
- **Archived or hidden chats.**

**Not drafts.** A draft belongs to the device it was typed on.

These change often, so they travel as **device-group messages, not roster commits**. Each kind has a merge rule that
makes arrival order irrelevant:

- **Read position:** the furthest point wins. Positions only move forward.
- **Pins, mutes, and archive:** the highest version wins. Each change to an item, such as muting Book club, carries a
  version one higher than the highest the sending device has seen for that item. If two devices that couldn't see each
  other pick the same version, the device whose leaf signature key sorts first wins. Every device picks the same winner,
  and no device's clock matters.

A newly linked device gets a snapshot of the current small state along with its history.

## Scene 7: Backups

With two or more devices, Alice rarely needs a backup: losing one leaves the others with everything. Backups are for
losing all of them.

**Turning backups on:**

1. The app generates a **recovery key**: 12 words from the BIP-39 English word list, about 128 bits. Alice never picks
   it. A chosen password would be too weak to protect a file anyone can download and attack offline.
2. The app says plainly that if she loses these words and every device, nobody can open the backup. She confirms she
   has saved them by typing two of them back.
3. Backups are encrypted with a random **archive key**, and the recovery key only wraps that archive key. The archive
   key sits in the roster, so every linked device has it.

**Writing a backup:**

- **One named writer.** The roster names a backup writer: by default the device where Alice turned backups on. She can
  change it on the Devices screen.
- **Takeover.** If the writer's latest backup is more than 7 days old, any other device takes over with one roster
  commit. Convergence settles it if two try at once.
- **Daily**, when the device finds it convenient, for example on Wi-Fi and charging for a phone.
- **Two generations.** Each new full backup replaces the previous one only after it is confirmed uploaded, so there is
  never a moment without a usable backup. It goes to a Blossom server or to storage Alice chooses, and the roster
  records where the latest one is. It never contains MLS state.
- **Coverage.** A backup holds what the writer has. If the writer isn't in some chat, the Devices screen says so, for
  example "Backup covers 14 of 15 chats."

**Replacing the recovery key:** from any linked device, Alice gets new words. Only the wrapping of the archive key
changes, and the next backup uses it. Her old words stop working once the old backups are replaced. If she has lost
her words but still has a device, this is all she needs to do.

**Restoring:** on a new device, she signs in with her nsec, chooses **No, start fresh** (multi-device Scene 3), then
**Restore from backup**, and enters her 12 words. Her old chats appear **read-only**, each with "Ask someone in this
chat to add you back."

**Why read-only:** a backup can't put her back into chats. Membership needs a fresh add from someone still in each
chat. That boundary is what keeps a stolen backup from becoming a way in.

**What the lost devices leave behind:** their old leaves stay in those chats as ghosts until a chat admin removes them,
the same as any lost device in multi-device.

## Scene 8: When every device is lost

**Disaster recovery is backups plus re-invites.** A backup restores what Alice had. Other people add her back to the
chats she wants to rejoin.

**Planned later: asking to be added back.** A restored device sends a gift-wrapped "please add me back" to the admins of
each chat in its backup. It names the chat and points to Alice's current KeyPackages. The admins see an ordinary
"Alice asks to be added back" prompt and use the normal add flow.

- **What it reveals:** only that Alice lost her devices and is back, and only to people already in the chat with her.
- **Forged requests:** someone with her nsec could send them too. That is no new exposure, since they could already be
  invited, and admins decide either way.
- **No spam:** one request per chat per restore, with no automatic retries.

It needs nothing beyond gift wraps and the existing add, so it can come after the rest without changing it.

## Numbers

| Number | Value |
| --- | --- |
| History bundle sent inline | up to about 32 KiB once sealed |
| Blossom chunk size for larger bundles | about 8 MiB |
| Backup frequency | daily |
| Backup writer takeover | when the latest backup is more than 7 days old |
| Backups kept | 2; a new one replaces the old only once confirmed |
| Recovery key | 12 words from the BIP-39 English word list, about 128 bits |

## Left for later

- **Asking to be added back** (Scene 8), as a planned feature.
- **Incremental backups**, as an optimization over daily full backups.
- **Backups that cover every device's chats**, by combining contributions from several devices instead of only the
  writer's.
- **A "recent only" history option**, if transfer size turns out to matter.

## Path into the spec

1. **Roster additions.** Each device's history key, the backup writer, the archive key, and the latest-backup record
   join the roster component defined with the multi-device device group.
2. **History transfer.** A feature document for account sync, with device-group message kinds for transfer offers,
   older-history offers, sealed bundle keys, manifests, and confirmations, plus the bundle format. Large bundles reuse
   encrypted-media locators and Blossom storage.
3. **Small-state sync.** The device-group message kinds, their versions, and their merge rules.
4. **Backups.** The archive format, how the recovery key wraps the archive key, and the restore flow.
5. **Re-add requests**, when they are picked up.
