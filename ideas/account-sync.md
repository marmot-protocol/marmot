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
- **Backups cover what siblings can't.** Most of the time her other devices already have her history. A backup covers
  losing every device, or losing the only device in some chat. It is protected by a recovery key, not her nsec, and
  restores content, not chat membership.

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
| Recovery key | 12 words that derive the key pair backups are sealed to. Devices keep only its public half. Separate from the nsec. |
| Archive key | A fresh random key for one backup, sealed to the recovery key's public half. |
| Backup pointer | A small record, encrypted to Alice's own account, listing her kept backups: where each is, which words it needs, and which stretches of each chat it holds. |

Device, sibling, device group, and roster mean what they mean in [multi-device.md](./multi-device.md#words-used-here).

## What this does and does not protect

- **No MLS state ever moves.** History, small state, and backups never include leaf keys, epoch secrets, or anything
  else that would let a device rejoin or read a chat through old state.
- **Imported history is as trustworthy as the device that sent it.** Marmot messages are authenticated by MLS when they
  are delivered; there is no signature a receiving device could re-check later. A stolen linked device could invent
  history. That falls under the stolen-linked-device limit in multi-device.
- **History already sent can't be recalled.** Removing a device later doesn't take back what it received.
- **Disappearing messages stay advisory.** Expired messages are never sent, and the rest keep their original expiry.
  As with retention today, this relies on Alice's own devices behaving, not on any enforcement. A backup kept only
  because it is the last one holding some chat (Scene 7) can hold messages past their expiry until it is replaced.
- **A stolen nsec can find and replace the backup pointer, but can't open a backup.** The pointer is signed by and
  encrypted to the account, so the nsec can list it, read it, and publish a new one. Reading it shows where the backups
  are and which chats and stretches each holds, but not their content. Only the 12 words open a backup. A replaced
  pointer could steer a restore to a fake backup that opens normally, but only if its maker also has the recovery key's
  public half: a current or former linked device, the same circle as a stolen device.
- **Linked devices can write backups but not read them.** They hold only the public half of the recovery key. A sibling
  can't open the writer's backup to read chats it was never sent, and a removed device can't read backups written
  after it left.
- **Replacing the words doesn't take back old copies.** Someone who already has an old backup and the old words can
  still read that old backup. New backups are sealed to the new words only.
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

**Filling in what's missing.** Say Alice got her iPhone last month, but her iPad has two years of Book club. The
iPhone can only give a month, so the laptop shows "History from March". A device's history can also have holes in the
middle: a device that was offline too long can miss messages for good
([../protocol-core/retained-history.md](../protocol-core/retained-history.md)), while a sibling has them. So:

1. The laptop records in the device group which stretches of Book club it has, marked by the messages at each end in
   chat order, not by calendar dates. "History from March" is only what Alice sees.
2. Any sibling with messages outside those stretches, earlier ones or ones in a gap, replies with a short offer naming
   the stretch it can fill.
3. For each missing stretch, the laptop accepts the offer that covers the most of it. Only that sibling sends, and
   only the part still missing.
4. The laptop updates its stretches. Any offer that still covers something missing can be accepted the same way,
   though one round is usually enough.

Offers are tiny, and only accepted ones move data, so two siblings never send the same messages. Nothing waits on the
device with the most history, so a sleeping iPad never blocks the link. If no device has a missing stretch, the laptop
marks it as a gap in the chat rather than claiming the history is complete.

**Keeping history whole later.** The same offers run whenever any device knows it has lost messages in a chat it is
already in, for example after being offline longer than the retention window allows. It records its stretches for
that chat, and siblings offer what it is missing. This is triggered by a known loss, not by continuous comparison, so
it costs nothing while devices are keeping up. **Bring chat history** doesn't block it: that setting is about history
from before a device was linked, and these are messages from while it was a member.

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

**If the sealed key or manifest is lost** on the way, the laptop's recorded stretches for that chat don't change, so
the iPhone's offer is still open and it sends again. This is the same "no visible effect, send again" rule multi-device
uses for lost device-group messages, so no receipts are needed.

**Where history stops and live chat starts.** A bundle covers everything up to the point the laptop joined. Anything
after that reaches the laptop live, as a member. An edit, reaction, or deletion can arrive live before the history it
refers to has finished importing. The laptop keeps such updates until that chat's import is done and then applies them,
rather than dropping them as it would an update for a message that never arrives. Importing never overwrites a newer
live update.

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
- **Invite decisions.** Accepting or declining an invite is an account-wide decision (multi-device Scene 6). They use
  versions like pins and mutes, with one extra rule ahead of the tie-break: at an equal version, a decline beats an
  accept. An accepted device can still be removed later, but a decline can't be partly undone. A decline is final for
  that invite: every device leaves, so a later accept has nothing to act on, and joining again needs a new invite.

**Not drafts.** A draft belongs to the device it was typed on.

These change often, so they travel as **device-group messages, not roster commits**. Read positions, pins, mutes and
archive are specified in [../features/account-sync.md](../features/account-sync.md): the furthest read position wins,
the highest version wins for the others, and every device breaks a tie the same way, whatever order changes arrive in.
A newly linked device, and one coming back after a long gap, asks a sibling for a snapshot of every item. This works
whether or not history is on for that device.

## Scene 7: Backups

With two or more devices, Alice rarely needs a backup for most chats: losing one leaves the others with everything.
Backups matter when she loses all of them, and for any chat only one device was in. That can happen, since a device
linked with **Add to all my chats** off isn't in her older chats.

**Turning backups on:**

1. The app generates a **recovery key**: 12 words from the BIP-39 English word list, about 128 bits. Alice never picks
   it. A chosen password would be too weak to protect a file anyone can download and attack offline.
2. The app says plainly that if she loses these words and every device, nobody can open the backup. She confirms she
   has saved them by typing two of them back.
3. The words derive a key pair. The device keeps only its **public half**, then forgets the words and the private
   half. No device can open a backup; only the words can. The public half lives in the roster. With only one device
   there is no device group yet, so that device keeps it locally and copies it into the roster when a group starts.

**Writing a backup:**

- **One named writer.** The roster names a backup writer: by default the device where Alice turned backups on. She can
  change it on the Devices screen.
- **Takeover.** If the writer's latest backup is more than 7 days old, any other device takes over with one roster
  commit. Convergence settles it if two try at once.
- **Daily**, when the device finds it convenient, for example on Wi-Fi and charging for a phone.
- **A fresh key each time.** Each backup is encrypted with a new random **archive key**, sealed to the recovery key's
  public half. No archive key outlives its backup, so there is nothing to rotate when a device is removed.
- **Two generations.** A new backup is uploaded alongside the existing one. Once it is confirmed, the older of the two
  previous backups is deleted, so the latest two are always kept, plus any kept so no history is lost (below). Backups
  go to a Blossom server or to storage Alice chooses, and never contain MLS state or attachment files.
- **Expired messages are left out.** A backup drops disappearing messages that have expired by the time it is written,
  and a restore drops any that have expired since.
- **Never quietly losing history.** Backups are compared by the stretches of each chat they hold (Scene 2), not just by
  which chats they include. No device can open an old backup to see what is in it, so the writer records each backup's
  stretches in the backup pointer when it writes the backup, and later writers compare against that. If a new backup
  lacks messages an older one has, the last backup holding them is kept and the pointer keeps listing it. That covers a
  whole missing chat, after a takeover by a device that isn't in Book club, and older messages in a chat, after a
  takeover by a device that joined Book club with history off. The Devices screen says "Older Book club messages are
  only in a backup from June 3." It is deleted only if Alice chooses to, or once newer backups hold those messages
  again. Expired messages don't count.
- **The backup pointer.** After each backup, the writer updates a small record that Alice's account publishes, encrypted
  to herself, listing every backup still kept: where it is, which recovery words it needs, and which stretches of each
  chat it holds. It is an addressable event signed by her account, not a gift wrap: each new pointer replaces the last,
  and a device finds it with one query to her relays.
  - **Its address comes from the recovery key's public half**, so a restoring device that has the words finds it with
    one query, and it never collides with another app's data. This is a deliberate exception to KeyPackage slots,
    whose address is random: the pointer has to be found again from the words. The address doesn't hide it from
    someone with the nsec, who can list the account's app-data events and decrypt them.
  - **It is ordinary private app data.** It uses NIP-78's general app-data event, and what the record is, a Marmot
    backup pointer, is stated only inside the encryption. NIP-78 describes that kind as one app's own storage and
    points shared formats to dedicated kinds. We use it anyway, as cover: a dedicated kind would tell every relay that
    this account has Marmot backups. Any Marmot client can still read it, because the Nostr transport spec defines how
    the address is derived and what the encrypted content looks like. Neither choice hides the pointer from someone
    with the nsec.
  - **What a relay still sees:** the author, the kind, when it was updated, and an address that looks random. That is
    the same as any app saving its settings, so it says nothing about Marmot or backups. A relay that follows NIP-78's
    advice to serve these events only to their author adds to that; a restoring device can authenticate as Alice,
    because it has her nsec or signer.
- **Coverage.** A backup holds what the writer has. If the writer isn't in some chat, or lacks some of its history,
  the Devices screen says so, for example "Backup covers 14 of 15 chats."
- **When two device groups merge** (multi-device Scene 3), the surviving group's backup settings and recovery words
  are used for new backups. The absorbed group's backups are kept under the rule above, and they stay sealed to that
  group's words: no device can re-seal them. So Alice is told to keep those words until the surviving group's backups
  hold the same messages. The pointer lists those backups with a note that they need the other words, and a restore
  asks for whichever words each backup needs.

**Replacing the recovery key:** from any linked device, Alice gets new words. The roster's public half changes and the
next backup is sealed to the new words. Older backups stay sealed to the old words, and no device can re-seal them. So
before they are deleted, Alice sees which chats or older messages exist only in them, and confirms. If she still has
her old words, she can keep those backups instead, and the pointer lists them as needing the old words. If she has lost
her words but still has a device, replacing them is all she needs to do. Anyone who already copied an old backup and
also has the old words can still read that old copy; nothing can take it back.

**Restoring:** on a new device, she signs in with her nsec and chooses **No, start fresh** (multi-device Scene 3), then
**Restore from backup**, and enters her 12 words. The app works out the pointer's address from them, finds the pointer,
and imports **every backup it lists**, not only the latest, so an older backup kept for its history is used too. If a
listed backup needs other words, the app asks for them. If the pointer is missing, she can point the app at where her
backups are. Her
old chats appear **read-only**, each with "Ask someone in this chat to add you back."

A restore is a copy of what her kept backups held. Messages sent after the latest one are only recoverable from a
device that has them.

**Keeping the same words:** the restoring device keeps the recovery key's public half before it forgets the words.
When it later links another device and a device group starts, it puts that public half in the roster, so the next
backup is sealed to the same words.

**When she is added back:** whoever adds her, the restored transcript and the new membership become the same chat. The
restored messages stay and the chat becomes writable.

**If one of her devices is still alive after all:** Scene 3 of multi-device has two endings, and this is the other one.
A surviving iPad links the restored phone and adds it to the old chats. On top of the above, the iPad sends only the
stretches the backup doesn't have, including everything after the last backup.

**Why read-only:** a backup can't put her back into chats. Membership needs a fresh add from someone still in each
chat. That boundary is what keeps a stolen backup from becoming a way in.

**What the lost devices leave behind:** their old leaves stay in those chats as ghosts until a chat admin removes them,
the same as any lost device in multi-device.

## Scene 8: When every device is lost

**Disaster recovery is backups plus re-invites.** Her kept backups restore a copy of what she had when they were
written. Other people add her back to the chats she wants to rejoin. Their add starts her membership at that moment:
messages between the latest backup and the add stay missing, because history only comes from her own devices.

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
| Backups kept | the latest 2, plus any that are the last to hold some messages; replacing the words deletes old ones only after Alice confirms |
| Recovery key | 12 words from the BIP-39 English word list, about 128 bits |

## Left for later

- **Asking to be added back** (Scene 8), as a planned feature.
- **Incremental backups**, as an optimization over daily full backups.
- **Backups that cover every device's chats**, by combining contributions from several devices instead of only the
  writer's.
- **A "recent only" history option**, if transfer size turns out to matter.
- **Attachment files in backups**, as separate work. Backups carry attachment keys only, so old media depends on its
  Blossom servers keeping the files.
- **Account-wide settings that aren't per chat**, such as who may invite her. Most account data, such as contacts and
  mute lists, is already Nostr events that sync through relays.

## Path into the spec

1. **Roster additions.** Each device's history key, the backup writer, and the recovery key's public half join the
   roster component defined with the multi-device device group.
2. **History transfer.** A feature document for account sync, with device-group message kinds for transfer offers,
   older-history offers, sealed bundle keys, manifests, and confirmations, plus the bundle format. Large bundles reuse
   encrypted-media locators and Blossom storage.
3. **Small-state sync.** Specified in [../features/account-sync.md](../features/account-sync.md).
4. **Backups.** The archive format, how the 12 words derive the recovery key pair, how an archive key is sealed to it,
   the backup pointer's address derivation and encrypted content in the Nostr transport, and the restore flow.
5. **Re-add requests**, when they are picked up.
