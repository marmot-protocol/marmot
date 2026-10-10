# Multi-device

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

This idea covers using one Marmot account on several devices: signing in on a new device, linking it to the devices you
already have, getting invites on every device, and managing or removing devices later. It describes the experience and
the direction we have agreed on. The protocol details come later, surface by surface.

The goal is for adding a device to feel like signing in to a big-provider account and confirming on a phone you already
have, without a server that controls the device list.

## At a glance

- **Every device is its own MLS member.** Each device has its own leaf, keys, and local state. MLS state is never copied
  between devices, and no device is primary.
- **Your devices know about each other through a device group.** Once you link a second device, your devices share a
  hidden Marmot group that only they belong to. The device list (the roster) is group state there, changed only by
  commits, so every device agrees on it and on the order of decisions. Heartbeats and small coordination messages
  travel as ordinary messages.
- **Linked devices vouch for each other privately.** Each device tells its siblings, inside the device group, which
  KeyPackage it put in its public slot, and hands them private single-use KeyPackages. Siblings add each other to chats
  with those, never with whatever relays show for the slot.
- **A new sign-in is noticed, then approved.** When a new device publishes a KeyPackage under your key, your other
  devices ask "Was this you?" You approve by checking that the same five emojis appear on both screens, and confirming
  on each.
- **Invites reach every device.** Inviters add all of your fresh devices, and your devices fill in any that were missed.
- **Any of your devices can remove any other.** Removal takes the device out of your chats and the device group and
  retires its KeyPackage.
- **Your nsec is still everything.** Anyone holding it can act as you. This design makes a new installation visible; it
  cannot stop one.

## Words used here

| Term | Meaning |
| --- | --- |
| Account | One Nostr public key. What other people see as "Alice". |
| Device | One installation of a Marmot client signed in to the account. Reinstalling the app on the same phone creates a new device. |
| Leaf | One device's membership in one MLS group. A device in 15 chats has 15 leaves. |
| Slot | The KeyPackage publication slot a device publishes into. Each installation uses exactly one. Its id is random, chosen by the installation, and kept for that installation's lifetime. A reinstall picks a new, unrelated slot. |
| Public KeyPackage | The KeyPackage in a device's slot on relays. Other people's inviters use it, and a new device uses it once to join the device group. |
| Private KeyPackage | A single-use KeyPackage a device hands to a sibling inside the device group. It never goes to relays. |
| Allocation | The private KeyPackages one device has handed to one particular sibling. |
| Slot announcement | A roster update in which a device records which KeyPackage it put in its slot. |
| Device group | The hidden MLS group containing only the account's linked devices. |
| Roster | The device group's record of linked devices, their settings and current KeyPackages, and rejected sign-ins. It is group state, changed only by commits. |
| Sibling | Another device on the same account. |
| Label | The name Alice gives a device when she links it, such as "Laptop". Kept only in the roster, never in KeyPackages or chats. |

## What this does and does not protect

- **Compromise of the nsec is out of scope.** Whoever holds it can install a client, publish KeyPackages, be added to
  new chats by other people's inviters, and act as the account. Nostr has no key rotation, and nothing here tries to add
  one.
- **Approval controls your own device group, not your key.** It decides which installations your devices treat as
  known: which ones are added to your existing chats, receive history, and take part in the device group. Because
  siblings only add each other with private KeyPackages handed over inside the device group, someone with the nsec
  can't get into your existing chats by replacing a linked device's public KeyPackage.
- **Detection is the mitigation.** A KeyPackage in a slot your devices don't know about produces a visible prompt once
  they see it. Either you skipped linking, or someone else has your key and you now know. A KeyPackage in a known slot
  that its device never announced produces a warning the same way. Detection is not guaranteed: a relay can hide a
  KeyPackage from your devices while showing it to other people.
- **A stolen linked device is inside the circle.** Any device can remove any other, and no device is primary. Someone
  holding Alice's unlocked, linked phone can read what that phone can read, and can remove her other devices before
  she removes it. App lock is what stands in the way. Nothing in this design lets one device overrule another.
- **Removed devices stay removed.** A removed leaf cannot rejoin a chat through its old MLS state. Coming back needs a
  new KeyPackage, which your devices see. One gap: deleting a removed device's slot doesn't make every relay forget it,
  so an inviter can still pick up a cached copy until it expires (Scene 7).
- **Device count is not private.** Chat members see every leaf, and each carries the account's key. Showing Alice as one
  member is a display choice, not a privacy property. Public KeyPackages also show roughly how many installations an
  account has. Hiding devices entirely would need a shared-leaf design, which needs stricter message ordering than
  relays give us.
- **A lost or stolen device that holds the raw nsec is a key compromise.** Removing it cleans up your device list, but
  it does not protect the key. Signers that keep the key off the device avoid this, but the device still has its own
  session with the signer. Removing the device doesn't end that session; Alice revokes it in the signer.

## Scene 1: Alice's first device

![Alice's iPhone publishes one KeyPackage in slot A and watches her account's slots. No device group exists
yet.](multi-device/scene-1-first-device.svg)

**What Alice sees:** nothing about devices. She signs in and uses Marmot.

**Underneath:** the iPhone picks a random slot id and publishes its KeyPackage there. It republishes into that same slot
after its KeyPackage is used for a Welcome, when something it advertises changes, and weekly while the app runs, so
the slot's age shows the installation still exists. It also watches the account's other slots, so it
notices when a new one appears, and its own slot. A KeyPackage in its own slot that it didn't publish means someone
else is signing as Alice. With no siblings yet, that self-check is the only protection a single device has.

The KeyPackage event carries the standard Nostr `client` tag (for example `["client", "whitenoise"]`) and nothing else
about the device: no model, platform, or label. The tag goes on KeyPackage events only, never on gift wraps or group
messages.

Slots are not deterministic. Nothing ties a slot id to the hardware, the account key, or an earlier install. If Alice
deletes the app and installs it again on the same iPhone, the new installation picks a new slot and has no link to the
old one. To her other devices it is a new device, and the old slot is simply a device that stopped republishing.

**Decision:** the device group is created only when a second device is linked. With one device there is nothing to
coordinate. It also keeps "two device groups for one account" rare (Scene 3).

## Scene 2: Signing in on a new device

![The new laptop publishes its KeyPackage, sees another device whose KeyPackage was refreshed two hours ago, and asks
whether Alice still has it. On Yes it sends a pairing request and waits; five emojis appear once the other device
answers.](multi-device/scene-2-new-sign-in.svg)

**What Alice sees:**

1. She signs in on her laptop with her nsec or a signer.
2. The laptop says she's already signed in on another device (last seen 2 hours ago) and asks whether she still has it.
3. **Yes:** the laptop asks her to open Marmot on a device she's already signed in on. When that device answers, both
   screens show the same five emojis (Scene 4).
4. **No, start fresh:** Scene 3.

**Underneath:** the laptop publishes its KeyPackage right away. That is what lets the iPhone notice it. The laptop
learns there is another device from the account's other fresh slots. On **Yes**, it also sends a pairing request that
names its KeyPackage and starts the exchange that produces the five emojis.

**What "last seen" means here:** the only public sign of another device is when it last republished its KeyPackage.
Group messages are signed with throwaway keys, so they can't be tied to Alice or to a device. "Last seen 2 hours ago"
only means "that installation refreshed its KeyPackage 2 hours ago." That is as precise as the republish schedule
allows, and the app has to be running to republish, so a phone that is rarely opened looks older than it is. It shows
the installation still exists, not that Alice is using it. Once a device is linked, heartbeats in the device group give
its siblings better liveness (the "last active" on the Devices screen in Scene 7), but a new sign-in outside the device
group only ever sees KeyPackage refreshes.

**The code:** five emojis from a fixed, ordered set of 512 (45 bits), new for every session. Alice compares the
pictures in order, without reading or translating a word list. For example: 🐢 🍎 🚲 🌙 🔑. The
[candidate alphabet](multi-device/emoji-candidates.md) keeps Matrix's 64 verification emojis, adds 447 Unicode
candidates and includes the custom Marmot artwork already bundled in White Noise. Its recognition testing is still
open; it is a proposal, not an approved verification set.
They come from a short exchange between the two devices, not from anything published:

1. The laptop's pairing request locks in a fresh one-time key without revealing it.
2. The other device answers with its own fresh one-time key.
3. The laptop reveals its key, and the other device checks it is the one the laptop locked in.
4. Both devices derive the same five emojis from the exchange, bound to the session, the account, the laptop's
   exact KeyPackage, the other device's identity and the agreed alphabet and display format.

Each side commits to its key before it sees the other's, so nobody can steer the result, including someone sitting
in the middle. This is the same idea as [Matrix's emoji verification](https://spec.matrix.org/latest/client-server-api/#short-authentication-string-sas-verification).
We would reuse a reviewed exchange and review the Marmot bindings and display format before they become spec text.

**Why emojis:** visual fingerprints are already used in Matrix device verification and
[Telegram calls](https://core.telegram.org/api/end-to-end/video-calls#key-verification). The pictures need no translated
word list for visual comparison. Instructions, screen-reader labels and warnings still need localization.

**Start with Matrix, then extend it.** Matrix's [SAS table](https://spec.matrix.org/latest/client-server-api/#sas-method-emoji)
has 64 symbols and uses seven of them for a 42-bit comparison. Its
[source table](https://github.com/matrix-org/matrix-spec/blob/main/data-definitions/sas-emoji.json) supplies the
characters, descriptions and translated labels. Five of those symbols alone would carry only 30 bits. Reusing that
set therefore means adding symbols, rather than shortening Matrix's display unchanged.

The candidate list starts with all 64 Matrix symbols, in their original order, then adds animals, food, places,
activities, objects and a few body parts. It excludes skin-tone and gender variants, national flags, color-only
variants such as red versus green apples, clock faces and many close alternatives. This reduces obvious confusion; it does not prove that
all 512 pictures are distinguishable. For example, animal silhouettes and similar tools still need testing at phone
size. The [candidate appendix](multi-device/emoji-candidates.md) records sources, attribution and the remaining checks.

Clients use a fixed copy agreed through the eventual linking spec, never a list fetched during pairing. Translated
labels do not change the mapping. They use consistent artwork rather than relying on every platform's emoji font.
Reusing Matrix's characters does not copy an artwork pack or make Marmot's exchange Matrix-compatible.

**The Marmot is a fixed picture, not a chat override.** The alphabet includes
[White Noise's Marmot emoji](multi-device/marmot.png), replacing the beaver candidate to keep 512 entries. Clients
bundle the agreed artwork and ignore user emoji files, received emoji tags and remote image substitutions when
drawing verification symbols. An unsupported entry prevents linking; it never silently becomes a beaver or a blank.
The agreed alphabet covers the artwork identity as well as the symbol order.

**Keeping the comparison reliable:**

- **Keep the security margin.** The previous four words from a 2,048-word list carried 44 bits. Five independently
  distributed symbols from 512 carry 45 bits, with repeats allowed. Five symbols need at least 446 choices to reach
  44 bits; using 512 gives an exact nine bits per symbol. The derivation and binding remain work for the reviewed
  linking exchange, owned by the device-group spec. Alphabet agreement is part of that exchange, so a client cannot
  silently downgrade to the smaller Matrix set. If recognition testing cannot support 512 choices, eight symbols
  from Matrix's original 64-symbol set remain an alternative with 48 bits.
- **One shared set and order.** Both clients use the same fixed set and mapping. Pick recognizable symbols without
  lookalikes or distinctions that depend only on color, skin tone or gender. Use consistent artwork and positions
  across clients and writing directions, so platform fonts or right-to-left layout cannot change the comparison.
  Alice checks every position, including repeats. A mismatch cancels the link; retrying starts a fresh session.
- **An accessible alternative.** Offer screen-reader labels with each symbol's position, and a numeric representation
  of the same full 45-bit value on both devices for people who cannot compare pictures. Changing presentation keeps
  the same session and confirmation rules. If a client cannot display a symbol reliably, it offers that alternative
  rather than silently dropping or replacing the symbol.

Show each glyph at least 32 logical pixels across, with enough spacing to compare every position and an option to
enlarge it. The [small-size visual review](multi-device/emoji-visual-review.md) replaced 24 weak candidates; it does
not establish a human recognition success rate.

Before adopting the set in the spec, test single-symbol mismatches, repeats and recognition on phones and desktops,
in light and dark themes, with screen readers and different writing directions. Check the full alphabet for missing
or confusable artwork; replace a confusable candidate before fixing the mapping. Emojis still need careful comparison;
they do not make approval automatic.

**How the messages travel:** as gift wraps addressed to Alice's own account, because the laptop isn't in the device
group yet. Anyone with her nsec can read them too. That is fine: the exchange assumes someone can read and replace
every message, and comparing the two screens is what catches it.

**Trade-offs:**

- Publishing before approval means inviters can add the laptop to *new* chats before Alice approves it. That is
  consistent with the threat model: approval governs Alice's own devices, not who can be invited.
- Linking needs messages in both directions while both devices are open, rather than a code either side can compute
  alone. In return, the code is new every time and there is nothing to search for ahead of time.
- The code replaces a separate local pairing step (Bluetooth, local network). One flow works whether the devices are
  side by side or in different countries, and needs no radio permissions. A local link may come back later as a faster
  carrier for moving large history.

## Scene 3: "I don't have my old device"

![Before: device group 1 has a lost iPhone and a sleeping iPad; device group 2 has the laptop and a desktop. After Alice
approves on the iPad, group 1 absorbs the laptop and desktop and group 2 is deleted.](multi-device/scene-3-start-fresh.svg)

**What Alice sees:** after choosing **No, start fresh**, the laptop works on its own. It is only in chats she is invited
to from now on, and it says so: her old chats aren't available here, and people can re-invite her.

**Underneath:** the laptop has no device group. If one of her old devices is still alive, say an iPad in a drawer, it
sees the laptop's slot as a new sign-in and prompts when it next runs. If Alice links it there, the laptop joins the old
device group and is added to her old chats.

Two device groups for one account only exist when both sides have linked more devices on their own, as in the figure.
**When devices from two device groups are linked, the approving device's group absorbs the other one.** Alice's own
approval decides which group survives.

**Merging, step by step:** say the iPad (group 1) links the laptop (group 2: laptop and desktop).

1. **The prompt shows everything that comes along.** The laptop's confirmation from the code exchange (Scene 4) covers
   its whole roster, not just itself, so nobody in between can slip a device into the list. The iPad's prompt says
   "Linking Laptop also brings Desktop", with each device's label, when it was linked and when it was last active,
   and a checkbox for each.
2. **The laptop joins first**, like any new device.
3. **The laptop brings the desktop in.** It already holds the desktop's private KeyPackages from their old group, so it
   adds the desktop to the surviving group with one of them, in a commit that also writes the desktop's roster entry.
   The desktop's Welcome travels through the old group, which the desktop is still in. No public KeyPackage is used.
4. **The two rosters combine.** Each device keeps its own settings. Rejections from both sides are kept: a slot
   rejected in either group stays rejected, and a device linked on one side but rejected on the other stays out, with
   Alice told why.
5. **Chats catch up.** Gap filling runs in both directions, using allocations and respecting each device's settings.
6. **The old group closes** once every device it brought along has joined the new one. It stays around for any that
   are offline until they come back.

A device Alice unchecks isn't brought in. It shows up under Unrecognized sign-ins in the surviving group, where she can
link it later with its own code or reject it.

**Which side approves:** in a merge, both devices see each other as a new sign-in. Whichever device Alice taps **Link**
on is the approver, and its group survives. The other device shows **They match**. If two merges are started at once,
neither is offered Link until one is finished or cancelled, the same rule as two pairing requests at once.

**Trade-offs:**

- Starting fresh never recovers old chats by itself. That needs backups or disaster recovery, which is separate work.
- The merge touches every chat both groups' devices are in, so it can take a while to finish. Progress is shown the
  same way as a single link (Scene 5).
- A ghost leaf from a lost device stays in old chats until it is removed by Alice's devices, by inactivity rules, or by
  a chat admin.

## Scene 4: The existing device approves

![Alice's iPhone shows a New sign-in prompt with the client name, the same five-emoji code as the laptop, a field
to name the device, two toggles, and Link device, This wasn't me, and Not now. The laptop shows the same emojis and a
They match button.](multi-device/scene-4-approve.svg)

**What Alice sees:** her iPhone notifies her of a new sign-in: the client, when it appeared, and the code. That is all
the iPhone can know, because KeyPackages carry only a client tag. She checks that the laptop shows the same five emojis
and confirms on both devices: **They match** on the laptop, and one of these on the iPhone:

- **Link device.** She names the device (the label, such as "Laptop") and sets two toggles, both on by default:
  - **Add to all my chats** covers the chats her devices are already in. Chats she joins after linking reach every
    device either way, because inviters add all of her fresh devices (Scene 6).
  - **Bring chat history** covers the history of those chats.

  The label and both settings live in the roster, so every sibling follows them, not just the approving one. The new
  device can share its model and platform privately in the device group once it is linked.
- **This wasn't me:** Scene 8.
- **Not now:** the sign-in stays listed under Unrecognized sign-ins on the Devices screen (Scene 7). Linking it later
  starts a fresh exchange from either device, with new emojis. No code stays valid while a sign-in waits.

**Underneath:** the iPhone noticed a KeyPackage in a slot that isn't in its roster, and the laptop's pairing request
naming it. Once Alice confirms on both screens, each device sends a short confirmation tied to the exchange:

- **The laptop's covers its exact KeyPackage.** Link applies to that KeyPackage, not to whatever the slot holds later.
- **The iPhone's covers the device group** it is about to add the laptop to. The laptop accepts a Welcome only for that
  group. A group that merely carries the hidden device-group marker can't pull the laptop in. Exactly what the laptop
  checks belongs to the device group's spec (Path into the spec, item 3).

The tap on the laptop is not a formality. Someone with the nsec could pose as Alice's existing device and try to pull
the laptop into a device group they control. Without the laptop's own confirmation, nothing would stop that.

**What triggers a prompt:**

- a KeyPackage under the account in a slot outside the roster (the main signal, and the normal way linking starts);
- a Welcome sent to the account for a KeyPackage no roster device announced. Every device can open gift wraps addressed
  to the account, so any of them can notice this.

A KeyPackage in a linked device's slot that the device never announced is not a sign-in to approve. Someone else
replaced it, so it goes straight to the warning in Scene 8.

**Only checked evidence counts.** Before anything raises a prompt, a device validates what it saw under the existing
KeyPackage and Nostr transport rules; this idea adds no checks of its own. A Welcome that names an unfamiliar KeyPackage
counts only once that KeyPackage has been fetched and validated the same way. Malformed or unverifiable input is
dropped, never treated as a sign that Alice's key was stolen, so nobody can set off a stream of warnings by sending
junk. The client tag is shown in the prompt, but it is self-reported, so a new one never triggers a prompt by itself.

**Why the code can't be faked:**

- **Nothing to search for ahead of time.** The emojis depend on a key the iPhone picks during the session.
- **Sitting in the middle shows.** Someone who swaps in their own one-time keys has to lock them in before seeing the
  real ones, so the two halves produce different emojis and the screens don't match.
- **One guess per session.** With a uniform 45-bit sequence and the exchange's commitment rules, a single
  guess succeeds about once in 35 trillion attempts. Sessions expire 10 minutes after the other device answers, and
  the number of attempts is limited.
- **Two requests at once.** If two pairing requests arrive together, Alice's devices treat that as an anomaly and don't
  offer Link for either.

**Rules of thumb:**

- **Approval from any one device is enough.** Alice's other devices change their prompt to "Laptop was added by iPhone"
  rather than silently dropping it. A device linked later doesn't prompt about devices already in the roster.
- **Every decision is a commit.** Linking, rejecting, changing a device's settings and removing a device each change the
  roster through a commit in the device group, so MLS puts them in one order that every device agrees on.
- **Conflicting answers:** if the iPhone links the laptop while the iPad says "This wasn't me", both make commits from
  the same starting point and Marmot's normal convergence rules pick one. If the link wins, the iPad's answer becomes
  an ordinary removal of the laptop. If the rejection wins, the link never happened and the laptop is told. There are
  no seniority rules.
- **Latency:** a phone may only notice a new slot when the app is opened. The laptop's "open Marmot on a device you're
  already signed in on" instruction covers that without needing push.
- **Careless approval:** if Alice taps Link without comparing, nothing catches it. The prompt makes the comparison the
  main thing on screen, and the app never asks her to type the emojis or send the sequence to anyone.

## Scene 5: The new device joins Alice's chats

![After approval the iPhone forms a device group with the laptop. The laptop hands the iPhone private KeyPackages, and
the iPhone sends one Welcome per chat through the device group, each to its own KeyPackage. The laptop shows its
progress and lists chats waiting on members' app updates.](multi-device/scene-5-join-chats.svg)

**What Alice sees:** the laptop says it's linked and shows progress through her chats, such as "12 of 15". Chats it
can't join yet are listed with the reason ("3 chats need members to update their app"). History follows if she left
that toggle on.

**Underneath:**

1. The approving iPhone creates the device group (if this is the first link). In **one commit** it adds the laptop,
   using the exact public KeyPackage Alice approved, and writes the laptop's roster entry with its label and settings.
   That commit is the approval. The Welcome goes out as an ordinary gift wrap, because the laptop isn't in the device
   group yet. This is the only time a sibling uses the laptop's public KeyPackage.
2. The laptop records its slot announcement in the roster and sends the iPhone a burst of private KeyPackages. The
   iPhone asks for one per chat it's about to add the laptop to. The laptop is open in Alice's hand, so it answers
   right away.
3. **Nothing irreversible happens until the link has settled.** Devices wait until the approving commit has settled
   under Marmot's normal convergence rules, about a second with no competing input, before adding the laptop to chats
   or sending history. That covers the ordinary race with another device's answer. If a late branch still reverses
   the link, the devices remove the laptop and tell Alice what was already shared.
4. **The approving device does the adding.** It's online and in Alice's hand, so it adds the laptop to every chat it's
   in right away instead of waiting on a designated sibling. Each add uses its own private KeyPackage. If **Add to all
   my chats** is off, it skips this step.
5. **Welcomes go through the device group.** Each one is still encrypted to its own KeyPackage, so only the laptop can
   open it. The device group is just the envelope, and nothing about these joins appears on relays as a gift wrap.
6. The laptop processes each Welcome and deletes that KeyPackage's private key straight away, as single-use
   KeyPackages require.
7. Chats the approving device isn't in are covered by **gap filling**: a sibling that is in the chat adds the missing
   device, using its own allocation of the laptop's private KeyPackages (Scene 6).
8. History transfer runs afterwards and is a separate document (see Open questions). The history setting applies to
   every sibling, so a sibling that fills a chat also sends that chat's history if the setting is on. History is
   encrypted for the laptop alone, even though it travels through the device group, because not every sibling is in
   every chat.

**Why not use the public KeyPackage for all of this:**

- **Anyone with the nsec can replace it.** The slot id is public, and an addressable event can be overwritten by any
  valid event in the same slot. If siblings looked up the laptop's slot when adding it, someone with Alice's key could
  publish their own KeyPackage there and be added to her existing chats with no approval at all.
- **It can't serve a burst of Welcomes.** After the laptop processes its first Welcome it republishes its slot, and
  once that replacement is published the old KeyPackage's private key has to be deleted. Any Welcomes still in flight
  for it can no longer be opened. Keeping the key longer instead means one stolen key opens every one of those
  Welcomes.

**Trade-offs:**

- A device that isn't an admin adding a sibling is a new kind of commit. Every member of a chat has to understand it,
  so a chat turns it on with a group app component that every member must support. Chats without it wait, and the UI
  says why.
- Each device holds the private keys for KeyPackages it has handed out until they are used or replaced. This is a
  small amount of state, and it is the price of never sharing one key across Welcomes.
- Two siblings can both try to fill the same gap. A short claim in the device group makes that rare. If both adds land
  anyway, the extra leaf is removed. The 10-leaf limit is counted on each chat's actual membership after each commit,
  never across competing branches added together.

## Scene 6: Everyday life with several devices

![Bob's client sends one Welcome for each of Alice's fresh devices. Alice accepts on her iPhone, the decision is shared
through the device group, and her laptop joins too. Bob sees Alice as one member with two
devices.](multi-device/scene-6-invites.svg)

**What Alice sees:**

- **Invites arrive on every device.** She accepts on whichever device she's holding, and the others follow.
- **Declining works the same way**, except every device leaves the chat. Each device already has a leaf in the chat
  once its Welcome arrives, so a decline that only applied to one device would leave ghost members behind.
- **Chats she creates** include her other devices from the start.
- **A device that was missed** is added quietly by gap filling, unless its settings say otherwise.

**What other people see:** Alice appears as one member. The member list shows how many devices she has in that chat.
There is no "Alice added a device" notice.

**Underneath:**

- **Inviters add every valid, fresh, compatible KeyPackage for the account, up to a cap.** This is an ordinary admin
  commit with several adds and needs no new authorization rule.
  - **Valid** includes supporting what the chat requires, which keeps non-chat clients on the same account out of chat
    groups.
  - **Fresh** means republished recently, which keeps uninstalled or dead devices out of new chats.
  - **Capped at 10 per account**, because a broken or malicious client can publish hundreds of KeyPackages under one
    account. A chat also allows at most 10 leaves per account.
- An inviter that still picks a single KeyPackage keeps working. Alice's other devices join through gap filling.
- **Alice's own devices never use these public KeyPackages for each other.** Gap filling and chats Alice creates use
  private KeyPackages, with the Welcome sent through the device group:
  - **Allocations.** Each device keeps every sibling stocked with about 10 private KeyPackages, topping up as they are
    used. Siblings can add it to chats while it is offline.
  - **When an allocation runs out, the sibling waits** until the device comes online and tops it up. It doesn't fall
    back to the public KeyPackage. A sibling that needs more than it holds, for example to fill 30 chats at once, asks
    for a burst the same way the approving device does at link time.
- **Gap filling follows the roster.** Before adding a sibling to a chat, a device checks that sibling's settings. If
  **Add to all my chats** is off, it leaves alone the chats Alice's devices were already in when that sibling was
  linked. A device that was offline during the link reads the same settings when it comes back, so it doesn't undo
  Alice's choice.
- **Refreshing a slot.** A linked device records its new KeyPackage in the roster before publishing it. A sibling that
  sees a new KeyPackage in a known slot catches up on the device group before deciding. If the roster has it, it is a
  quiet refresh. If not, someone else replaced it (Scene 8). The device itself also notices a KeyPackage it didn't
  publish in its own slot, and republishes its own. Keeping this in the roster rather than in a message means a device
  linked later can read every sibling's current KeyPackage straight away.
- **Checking chats for unknown leaves.** Each device compares the account's leaves in every chat it is in with the
  siblings' leaf map (see Under the hood). A leaf for Alice's account that no sibling claims is flagged and goes to the
  warning in Scene 8. This catches a replaced KeyPackage that an outside inviter used, and extra leaves a stolen device
  added before it was removed.

**Trade-offs:** device counts are visible to chat members and, roughly, to anyone reading relays. We accept that and
show it plainly rather than hiding it behind a notice.

## Scene 7: Managing and removing devices

![Alice's Devices screen lists this device, her linked devices with last activity, and unrecognized sign-ins. Removing
the laptop takes it out of every chat and the device group and deletes its slot. A timeline shows inactive devices
going stale with a prompt at 30 days, and removal at 90 days unless kept.](multi-device/scene-7-devices.svg)

**The Devices screen**, built from the roster:

| Section | Shows | Actions |
| --- | --- | --- |
| This device | name, client and platform | rename, sign out |
| Your devices | label, client and platform (shared inside the device group), when linked and by which device, last active (from device-group heartbeats), settings | rename, add to all my chats, bring chat history, keep while inactive, remove |
| Unrecognized sign-ins | client and when it appeared, for new slots not yet linked or rejected | link, this wasn't me |

**Changing a device's settings later** is one commit, and every sibling follows it. Turning **Add to all my chats** on
makes siblings add the device to the old chats it is missing, with history if that setting is on. Turning it off
doesn't take the device out of chats it is already in. Removing the device, or leaving a chat, does that.

**Removing a device from another device**, for example a lost laptop:

1. The laptop is removed from every chat Alice's devices are in, and from the device group.
2. **Its slot is deleted.** Alice's device holds the key, so it can do this. Otherwise inviters would keep adding a dead
   device to new chats. Siblings also discard the private KeyPackages it handed them. Deletion is cleanup, not
   revocation: a relay that ignores it can keep serving the old KeyPackage until it expires, and the lost laptop still
   holds that KeyPackage's private key. If an inviter adds it from such a copy, Alice's devices are invited to the same
   chat, see a leaf for a removed device, and remove it.
3. **The roster remembers the removed slot.** If that installation, still holding its old state, publishes into its
   old slot again, Alice's devices show a stronger warning: "A device you removed is trying to come back."
4. **Siblings check for leftovers.** A stolen device could have added extra leaves before it was removed, so siblings
   check every chat they are in for account leaves that no remaining device claims, and remove them.
5. **If the laptop used a signer,** the app tells Alice to revoke that device's session in the signer. Removal alone
   doesn't end it, and the app doesn't claim the device is fully cut off until she has.
6. The next time the removed laptop opens, it says it was removed and offers to sign in again.

A limit on points 1 and 4: siblings can only clean up chats they are in. If the laptop was in a chat none of Alice's
remaining devices is in, its leaf stays there until a chat admin removes it. The roster's leaf map still records that
chat, so the Devices screen can list it and Alice can ask an admin there.

A limit on point 3: a reinstalled app creates a new slot, so it looks like any other new sign-in (Scene 4), not a
returning device. That's fine, since it goes through normal approval. The stronger warning only catches the case where
the removed installation itself keeps running.

**Inactive devices:**

- **After 30 days:** the device's KeyPackage is past the freshness window, so inviters stop adding it to new chats, and
  the Devices screen asks "Remove it?"
- **After 90 days:** it is removed automatically, unless Alice marked it "keep while inactive".

Inactivity is judged from device-group heartbeats as the siblings see them, never from one device's clock alone. At
the 30-day mark, siblings record in the roster that the device is inactive. The 60 days from there to removal are its
grace period: if it shows up at any point before 90 days, the mark is cleared and nothing is removed. A device that
was alive but cut off for that long can still be removed this way: this is a cleanup rule Alice agrees to, not a
finding that the device was lost.

**Signing out on this device** removes that device completely. In order:

1. It records in the roster that it is leaving. This goes first so siblings stop adding it to chats.
2. Its siblings remove it from every chat and from the device group, exactly as in a removal from another device.
   The signing-out device doesn't have to wait for that to finish.
3. It deletes the KeyPackage in its own slot, and only its own.
4. It deletes all of its local data.

Letting siblings do the removing means the departure still completes after the device has wiped itself.

Signing out on the **last** device has no siblings to do this, so it leaves each chat itself, which needs another
member of the chat to commit the departure. It publishes its departures, then wipes. Once an account's last leaf
leaves a chat, the account is no longer in that chat. The warning says so: signing back in won't bring those chats
back.

Locking the app with a PIN, face, or fingerprint is not signing out. It protects local access and changes nothing on
the network.

**Admin chats:** if Alice is a chat admin, every one of her devices is an admin there, because admin rights belong to
the account. Today an admin can't leave a chat by itself, but signing out doesn't need it to: a sibling removes the
departing device, and a sibling of an admin is an admin. So the self-leave rule doesn't have to relax. In chats with
the readiness component, an admin removing another leaf of their own account counts as removing another member. The
last device of an admin account still has to give up admin first, as today.

## Scene 8: "This wasn't me"

![A full-screen warning tells Alice someone else has her key. Her devices reject the sign-in, keep it out of existing
chats and history, and remove it from chats they share with it. The key holder can still be invited to new chats, send
as Alice, remove her devices, and publish KeyPackages.](multi-device/scene-8-not-me.svg)

**Two ways in:** Alice taps **This wasn't me** on a new sign-in, or her devices find a KeyPackage in a linked device's
slot that the device never announced. The second needs no tap. A linked device always announces before it publishes,
so there is no innocent explanation, and the warning appears on its own.

**What Alice sees:** a full-screen warning that her account's signing access may be compromised: either her nsec, or a
signer session. The figure shows the case where the nsec itself is stolen. The warning says plainly that for a stolen
nsec, the only complete fix is moving to a new account, and for a signer, which session to revoke. It doesn't claim to
know which one was taken.

**What her devices do:** they mark the slot rejected so no device prompts about it again, never add it to existing chats
or send it history, and remove its leaf from any chat they share with it. For a replaced KeyPackage in a linked
device's slot, they reject that KeyPackage, not the slot, and the roster keeps pointing at the device's own. If
other people's inviters have already added the replacement to a chat, Alice's devices see a leaf for her account that
no sibling announced, and remove it.

**What they can't do:** stop the key holder. Someone with the nsec can be invited to new chats, send as Alice, remove her
devices, and publish more KeyPackages. The warning must not promise more protection than that.

## Under the hood

These pieces sit behind the scenes above. They are settled in direction; their exact encodings come with the spec.

**The roster** is a group app component in the device group. It holds each device's slot, label, platform, link
details, settings, status, current public KeyPackage and leaf map, plus the account's rejected slots and KeyPackages.
Every member of the device group is the same account, and admin rights belong to the account, so any device can change
the roster and no new permission rule is needed.

**Device group messages** are app event kinds for things only needed in the moment: heartbeats, invite accept and
decline, gap-fill claims, private KeyPackage requests and hand-offs, Welcomes for sibling adds, and anomaly alerts. The
sender is already identified by its leaf in the device group, so messages need no device identifier tag. The rule for
roster versus message: anything a device linked later needs to know goes in the roster.

**Matching leaves to devices.** Gap filling, sibling removal and the unknown-leaf check need to know which of the
account's leaves in a chat belongs to which sibling. Labels don't help, because they never appear in chats. Each device
records in the roster which chats it has joined, identifying its leaf in each by the leaf's signature key rather than
its position, because positions are reused after a removal. It updates the entry when it rotates that key. Other chat
members see nothing new.

**Private KeyPackage upkeep.** Private KeyPackages expire like public ones. A device replaces a sibling's allocation
when it is halfway to expiry, and expired private KeyPackages are simply discarded. A device coming back after a long
gap first tops up its siblings' allocations, then asks for fresh allocations of theirs.

**The hidden-group marker** keeps the device group out of chat lists. It never makes a group trusted by itself: a
device treats a group as its device group only if it created it or joined it through a confirmed link or merge
(Scene 4).

## Numbers

| Number | Value |
| --- | --- |
| Leaves per account in one chat | at most 10 |
| KeyPackages an inviter adds per account | at most 10 |
| Freshness window for inviters | 30 days |
| KeyPackage lifetime | 30 days |
| KeyPackage republish | after it is used, when what it advertises changes, and weekly while the app runs |
| Inactive device prompt | 30 days |
| Inactive device removal | 90 days, unless kept; showing up any time before then cancels it |
| Private KeyPackages each device keeps per sibling | about 10, topped up as they are used and replaced halfway to expiry |
| Private KeyPackages at link time | one per chat the approving device is adding, requested through the device group |
| Link code | 5 emojis from a fixed, ordered set of 512 (45 bits), new for every session; candidate set needs recognition testing |
| Link session | expires 10 minutes after the existing device answers |

## Open questions

1. **History, state sync, and backups.** Needs its own idea document: chunked history transfer, small-state sync (read
   markers, pins, notification state), and backups that are never encrypted to the nsec alone.
2. **Emoji recognition.** Can the 512-symbol candidate set support reliable comparison at phone size, including
   grayscale and assistive use? The alphabet and artwork need review before this format enters the spec.
3. **Disaster recovery.** Recovering when every device is lost is out of scope here, but we need a rough direction
   early so that it doesn't force changes to this design later.

**Left for later:** picking which old chats a device joins, one by one. Nothing here blocks it. A "keep this device off
new chats" setting is not planned, because other people's inviters add every fresh device before Alice accepts, so a
private setting couldn't stop it.

## Path into the spec

Parts of this can become spec text before others are settled:

1. **Several leaves per account.** Rules that are already valid today but need writing down: removing a person removes
   all of their leaves, your own leaf being removed means this device was removed even when a sibling stays, each
   installation uses exactly one random slot for its lifetime, KeyPackage events carry the standard `client` tag and
   nothing more about the device, signing out deletes only your own slot, and inviters add up to 10 fresh KeyPackages
   per account. None of this needs new commit types.
2. **Same-account operations.** The chat readiness app component, sibling adds, sibling removal (including a device
   signing out while a sibling remains), and the 10-leaf cap.
3. **The device group.** The roster component, messages, linking, slot announcements, private KeyPackages and Welcome
   delivery, gap filling, anomaly signals, and merging.
4. **Account sync.** History, small-state sync, and backups.

Details to pick while writing the spec, rather than product questions:

- which reviewed short-code exchange to reuse, the exact pairing messages, how many attempts are allowed, and which
  reviewed derivation, alphabet agreement, rendering and accessible numeric representation to use;
- the chat readiness component's exact contents;
- the roster and device group message encodings;
- listing the `client` tag as allowed on KeyPackage events in the Nostr transport.

## What this replaces

An earlier draft had a new device join each chat through an MLS External Commit. It needed a pairing payload carrying
per-chat secrets and an admin-signed authorization. That draft was never adopted or implemented, and it has been
removed from the spec along with the ids it reserved.
