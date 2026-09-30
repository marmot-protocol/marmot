# Multi-device

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

This idea covers using one Marmot account on several devices: signing in on a new device, linking it to the devices you
already have, getting invites on every device, and managing or removing devices later. It describes the experience and
the direction we have agreed on. The protocol details come later, surface by surface.

The goal is for adding a device to feel like signing in to a big-provider account and confirming on a phone you already
have, without a server that controls the device list.

[Security and sync choices](./multi-device-security.md) explores refinements to this baseline: selective chats and
history, linked-device Welcome delivery, warning policy, trusted KeyPackage continuity, and a threat model. Those
options remain open for discussion; the figures below illustrate the baseline, not settled UI for the refinements.

## At a glance

- **Every device is its own MLS member.** Each device has its own leaf, keys, and local state. MLS state is never copied
  between devices, and no device is primary.
- **Your devices know about each other through a device group.** Once you link a second device, your devices share a
  hidden Marmot group that only they belong to. It holds the device list, heartbeats, and small coordination messages.
- **Observed new sign-ins ask for verification.** When your devices receive and validate evidence of a new
  installation, they ask "Was this you?" You compare a short code on both screens before approving. Publication alone
  does not guarantee observation; relays can withhold evidence and a replaced known slot needs continuity checks.
- **Invites reach every device.** Inviters add all of your fresh devices, and your devices fill in any that were missed.
- **Any of your devices can remove any other.** Removal takes the device out of your chats and the device group and
  retires its KeyPackage.
- **Your nsec still controls account identity.** Anyone holding it can act as you. Observed sign-ins can trigger alerts,
  but detection is not guaranteed. The nsec does not directly decrypt old chats; tricking a sibling into enrollment or
  history release is a separate risk discussed in the companion.

## Words used here

| Term | Meaning |
| --- | --- |
| Account | One Nostr public key. What other people see as "Alice". |
| Device | One installation of a Marmot client signed in to the account. Reinstalling the app on the same phone creates a new device. |
| Leaf | One device's membership in one MLS group. A device in 15 chats has 15 leaves. |
| Slot | The KeyPackage publication slot a device publishes into. Each installation uses exactly one. Its id is random, chosen by the installation, and kept for that installation's lifetime. A reinstall picks a new, unrelated slot. |
| Device group | The hidden MLS group containing only the account's linked devices. |
| Roster | The device group's list of linked devices. |
| Sibling | Another device on the same account. |
| Label | The name Alice gives a device when she links it, such as "Laptop". Kept only in the roster, never in KeyPackages or chats. |

## What this does and does not protect

- **Compromise of the nsec cannot be repaired by linking.** Whoever holds it can install a client, publish KeyPackages,
  be added to new chats by other people's inviters, and act as the account. Nostr has no key rotation, and nothing here
  tries to add one.
- **Approval controls your own device group, not your key.** It decides which installations your devices treat as
  known: which ones are added to your existing chats, receive history, and take part in the device group.
- **Detection is a mitigation with limits.** An observed, validated new slot prompts for verification. Relays can hide
  it, and an attacker with signing access can overwrite a known slot. The companion discusses
  [trusted continuity](./multi-device-security.md#existing-signatures-and-the-missing-continuity-guarantee) for that case.
- **Removal blocks use of old membership after the removal is accepted.** A removed leaf cannot rejoin through its
  old MLS state. Coming back needs a new add authorized by a chat admin or sibling, not necessarily Alice's approval;
  observed publications can alert siblings, but a stolen
  account key still permits new valid packages. Last-resort initialization keys also remain an exposure to review.
- **Device count is not private.** Chat members see every leaf, and each carries the account's key. Showing Alice as one
  member is a display choice, not a privacy property. Public KeyPackages also show roughly how many installations an
  account has. Hiding devices entirely would need a shared-leaf design, which needs stricter message ordering than
  relays give us.
- **A lost or stolen device that holds the raw nsec risks key compromise.** Removing it cleans up your device list, but
  does not revoke a stolen key. An external signer reduces raw-key exposure; its grants and the device's stored
  messages and MLS secrets still need attention.

## Scene 1: Alice's first device

![Alice's iPhone publishes one KeyPackage in slot A and watches her account's slots. No device group exists
yet.](multi-device/scene-1-first-device.svg)

**What Alice sees:** nothing about devices. She signs in and uses Marmot.

**Underneath:** the iPhone picks a random slot id and publishes its KeyPackage there. It republishes into that same slot
after its KeyPackage is used for a Welcome, when something it advertises changes, and on a regular refresh while the
app runs, so the slot's age shows the installation still exists. It also watches the account's other slots, so it
notices when a new one appears.

The KeyPackage carries a client tag (for example "White Noise") and nothing else about the device: no model, platform,
or label.

Slots are not deterministic. Nothing ties a slot id to the hardware, the account key, or an earlier install. If Alice
deletes the app and installs it again on the same iPhone, the new installation picks a new slot and has no link to the
old one. To her other devices it is a new device, and the old slot is simply a device that stopped republishing.

**Decision:** the device group is created only when a second device is linked. With one device there is nothing to
coordinate. It also keeps "two device groups for one account" rare (Scene 3).

## Scene 2: Signing in on a new device

![The new laptop publishes its KeyPackage, sees another device whose KeyPackage was refreshed two hours ago, asks
whether Alice still has it, and shows a four-word code after she answers yes.](multi-device/scene-2-new-sign-in.svg)

**What Alice sees:**

1. She signs in on her laptop with her nsec or a signer.
2. The laptop says she's already signed in on another device (last seen 2 hours ago) and asks whether she still has it.
3. **Yes:** the laptop shows a short code and asks her to open Marmot on a device she's already signed in on.
4. **No, start fresh:** Scene 3.

**Underneath:** the laptop publishes its KeyPackage right away. That is what lets the iPhone notice it. The laptop
learns there is another device from the account's other fresh slots.

**What "last seen" means here:** the only public sign of another device is when it last republished its KeyPackage.
Group messages are signed with throwaway keys, so they can't be tied to Alice or to a device. "Last seen 2 hours ago"
only means "that installation refreshed its KeyPackage 2 hours ago." That is as precise as the republish schedule
allows, and the app has to be running to republish, so a phone that is rarely opened looks older than it is. It shows
the installation still exists, not that Alice is using it. Once a device is linked, heartbeats in the device group give
its siblings better liveness (the "last active" on the Devices screen in Scene 7), but a new sign-in outside the device
group only ever sees KeyPackage refreshes.

**The code:** four words from a fixed 2,048-word list (about 44 bits), computed from the laptop's own KeyPackage. The iPhone sees that KeyPackage on
relays and can compute the same code, so displaying the code needs no extra messages. Comparing the screens is intended
to identify the candidate Alice approves. Its security depends on the session binding, grinding analysis and
private-key possession exchange left open in Scene 4 and the companion; the code alone does not establish those.

**Trade-offs:**

- Publishing before approval means inviters can add the laptop to *new* chats before Alice approves it. That is
  consistent with the threat model: approval governs Alice's own devices, not who can be invited.
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
**When devices from two device groups are linked, the approving device's group absorbs the other one.** The absorbed
devices join the approver's group and then leave and delete their old group. Alice's own approval decides which group
survives.

**Trade-offs:**

- Starting fresh never recovers old chats by itself. That needs backups or disaster recovery, which is separate work.
- The merge touches every chat both groups' devices are in. The mechanics need care (see open questions).
- A ghost leaf from a lost device stays in old chats until it is removed by Alice's devices, by inactivity rules, or by
  a chat admin.

## Scene 4: The existing device approves

![Baseline flow: Alice's iPhone shows a New sign-in prompt with the client name, the same code as the laptop, a field
to name the device, two toggles, and Link device, This wasn't me, and Not now.](multi-device/scene-4-approve.svg)

**What Alice sees:** her iPhone notifies her of a new sign-in: the client, when it appeared, and the code. That is all
the iPhone can know, because KeyPackages carry only a client tag. She checks the code against the laptop and chooses:

- **Link device.** She names the device (the label, such as "Laptop") and sets two toggles: **Add to all my chats** and
  **Bring chat history**. Both default to on in this baseline illustration; the companion leaves the defaults open
  when introducing selective sync. The label lives only in the roster. The new device can share its model
  and platform privately in the device group once it is linked.
- **This wasn't me:** Scene 8.
- **Not now:** the sign-in stays listed under Unrecognized sign-ins on the Devices screen (Scene 7).

**Underneath:** the iPhone noticed a KeyPackage in a slot that isn't in its roster.

**What triggers a prompt:**

- a KeyPackage under the account in a slot outside the roster (the main signal, and the normal way linking starts);
- a Welcome sent to the account for a KeyPackage no roster device owns. Every device can open gift wraps addressed to
  the account, so any of them can notice this.

A new client tag is supporting, self-reported information. By itself it does not trigger a security prompt or prove a
new installation.

These signals need validated evidence before a security alert; a Welcome reference alone is not proof of a valid
account publication. The proposed [warning policy](./multi-device-security.md#warning-policy-for-discussion) adds
known-slot replacement and returning-device cases, and distinguishes signing-access compromise from raw-key theft.

**Matching codes:** the laptop's KeyPackage is public, so someone who has Alice's key could try generating KeyPackages
until one produces the same code. The four-word design needs a grinding analysis and a bounded approval session before
its security claim is settled. If two pending sign-ins show the same code, Alice's devices treat that as an anomaly and
don't offer Link for either. Package replacement during approval also stops that attempt. A matching public code alone
does not prove possession of the private Welcome initialization key; the companion leaves that exchange open.

**Rules of thumb:**

- **Approval from any one device is enough.** Alice's other devices change their prompt to "Laptop was added by iPhone"
  rather than silently dropping it. A device linked later doesn't prompt about devices already in the roster.
- **Conflicting answers:** the first decision recorded in the device group wins. A later "This wasn't me" from another
  device initiates removal, raises the persistent signing-access warning, and cancels unfinished transfers. There are
  no seniority rules. How decisions are ordered during partitions remains an open question in the companion.
- **Latency:** a phone may only notice a new slot when the app is opened. The laptop's "open Marmot on a device you're
  already signed in on" instruction covers that without needing push.

## Scene 5: The new device joins Alice's chats

![After approval the iPhone forms a device group with the laptop and sends one Welcome per chat, all to the laptop's
single last-resort KeyPackage. The laptop shows its progress and lists chats waiting on members' app
updates.](multi-device/scene-5-join-chats.svg)

**What Alice sees:** the laptop says it's linked and shows progress through her chats, such as "12 of 15". Chats it
can't join yet are listed with the reason ("3 chats need members to update their app"). History follows if she left
that toggle on.

**Underneath:**

1. The approving iPhone creates the device group (if this is the first link) and adds the laptop to it.
2. **The approving device does the adding.** It's online and in Alice's hand, so it adds the laptop to every chat it's
   in right away instead of waiting on a designated sibling.
3. All of those adds use the laptop's single KeyPackage. Marmot KeyPackages are last-resort KeyPackages, so one can be
   used for many Welcomes. After joining each chat, the laptop self-updates its leaf there, which replaces the key
   material that came from the shared KeyPackage.
4. Chats the approving device isn't in are covered by **gap filling**: a sibling that is in the chat adds the missing
   device.
5. History transfer runs afterwards, separately from the Welcome; see the proposed
   [history flow](./multi-device-security.md#how-old-messages-reach-a-new-device) and open questions.

The adopted Welcome carrier is an account-addressed gift wrap. Carrying later chat Welcomes inside the device group
after bootstrap is a [proposed alternative](./multi-device-security.md#welcome-delivery-bootstrap-first-then-private-coordination),
not a change made by this walkthrough. Likewise, [selective sync](./multi-device-security.md#selective-chats-history-and-future-invites)
would constrain both the approving device's adds and sibling gap filling; exclusion cannot be treated as a missing leaf.

**Trade-offs:**

- A device that isn't an admin adding a sibling is a new kind of commit. Every member of a chat has to understand it,
  so a chat turns it on with a group app component that every member must support. Chats without it wait, and the UI
  says why.
- Reusing one KeyPackage for many Welcomes means those Welcomes share key material until the laptop self-updates in
  each chat. This is the known last-resort trade-off, now applied to a burst of joins.
- Gap filling needs a rule so that two siblings don't both add the same device at the same time.

## Scene 6: Everyday life with several devices

![Bob's client sends one Welcome for each of Alice's fresh devices. Alice accepts on her iPhone, the decision is shared
through the device group, and her laptop joins too. Bob sees Alice as one member with two
devices.](multi-device/scene-6-invites.svg)

**What Alice sees:**

- **Invites arrive on every device.** She accepts on whichever device she's holding, and the others follow.
- **Declining works the same way**, except every device leaves the chat. Each device already has a leaf in the chat
  once its Welcome arrives, so a decline that only applied to one device would leave ghost members behind.
- **Chats she creates** include her other devices from the start.
- **A device that was missed** is added quietly by gap filling.

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
| Your devices | label, client and platform (shared inside the device group), when linked and by which device, last active (from device-group heartbeats) | rename, keep while inactive, remove |
| Unrecognized sign-ins | client and when it appeared, for new slots not yet linked or rejected | link, this wasn't me |

These baseline sections would need additional status and actions for paused known-slot replacements and outstanding
chat removals if the companion's warning refinements are adopted. Their placement is part of the open warning-UI design.

**Removing a device from another device**, for example a lost laptop:

1. The laptop is removed from every chat Alice's devices are in, and from the device group.
2. **Its slot is deleted.** Alice's device holds the key, so it can do this. Otherwise inviters would keep adding a dead
   device to new chats.
3. **The roster remembers the removed slot.** If that installation, still holding its old state, publishes into its
   old slot again, Alice's devices show a stronger warning: "A device you removed is trying to come back."
4. The next time the removed laptop opens, it says it was removed and offers to sign in again.

A limit on point 3: a reinstalled app creates a new slot, so it looks like any other new sign-in (Scene 4), not a
returning device. That's fine, since it goes through normal approval. The stronger warning only catches the case where
the removed installation itself keeps running.

**Inactive devices:**

- **After 30 days:** the device's KeyPackage is past the freshness window, so inviters stop adding it to new chats, and
  the Devices screen asks "Remove it?"
- **After 90 days:** it is removed automatically, unless Alice marked it "keep while inactive".

**Signing out on this device** removes that device completely. In order:

1. It leaves the device group. This goes first so siblings don't see it missing from a chat and add it back.
2. It leaves every chat it is in.
3. It deletes the KeyPackage in its own slot, and only its own.
4. It deletes all of its local data.

Leaving a chat needs another member to commit the departure, so the device publishes its departures and then wipes. If
it can't reach relays, the leftovers are cleaned up by its siblings or by the inactivity rules.

Signing out on the **last** device follows the same steps. The only difference is that when an account's last leaf
leaves a chat, the account is no longer in that chat. The warning says so: signing back in won't bring those chats
back.

Locking the app with a PIN, face, or fingerprint is not signing out. It protects local access and changes nothing on
the network.

**Admin chats:** if Alice is a chat admin, every one of her devices is an admin there, because admin rights belong to
the account. One of her devices needs to be able to leave while a sibling stays. Today an admin can't leave by itself,
so this rule has to relax while at least one other leaf of the same account remains. The last device of an admin
account still has to give up admin first, as today.

## Scene 8: "This wasn't me"

![Baseline raw-key compromise example: Alice's devices reject the sign-in, keep it out of existing chats and history,
and request removal from shared chats; cleanup can remain incomplete. The key holder can still receive new invites,
send as Alice, remove her devices and publish KeyPackages.](multi-device/scene-8-not-me.svg)

The illustration assumes raw-nsec theft. A real warning would describe possible signing-access compromise without
claiming which secret was stolen.

**What Alice sees:** a full-screen warning that her account's signing access may be compromised, through a private key
or authorized signer. The figure shows the raw-key compromise case. The app explains signer-access revocation where
applicable; if the raw nsec was stolen, moving to a new account is the complete identity remedy.

**What her devices do:** they reject this sign-in, suppress repeats of the same evidence, cancel pending adds and
history transfers, and request removal of its leaves from shared chats. Incomplete removals remain visible. A later
suspicious replacement in the same slot remains a warning case, and history already delivered cannot be recalled.

**What they can't do:** stop the key holder. Someone with the nsec can be invited to new chats, send as Alice, remove her
devices, and publish more KeyPackages. The warning must not promise more protection than that.

## Numbers

| Number | Value |
| --- | --- |
| Leaves per account in one chat | at most 10 |
| KeyPackages an inviter adds per account | at most 10 |
| Freshness window for inviters | 30 days |
| KeyPackage lifetime | 30 days |
| KeyPackage republish | after it is used, when what it advertises changes, and on a regular refresh |
| Inactive device prompt | 30 days |
| Inactive device removal | 90 days, unless kept |
| Link code | 4 words from a 2,048-word list |

## Open questions

These are the pieces we know are unsettled.

1. **Device group merge mechanics.** The rule is "the approving device's group absorbs the other one." The likely shape
   is that devices compare which chats each is missing and add each other through the device group. The details need
   working out alongside an implementation.
2. **Matching leaves to devices.** Gap filling and sibling removal need a device to know which of the account's leaves in
   a chat belongs to which sibling. Labels don't help, because they never appear in chats. Proposal: each device
   announces in the device group which chats it has joined and its leaf position in each. Siblings keep that map
   privately, and other chat members see nothing new.
3. **Refresh interval.** Republishing only when used would let an idle but alive device go stale after 30 days. A
   regular refresh well inside the window (for example weekly while the app runs) avoids that. The interval needs
   choosing.
4. **Device group messages and rules.** A set of app event kinds sent inside the device group: roster add, update, and
   remove; heartbeats; invite accept and decline; gap-fill claims; link approval; leaf announcements; and anomaly
   alerts. The sender is already identified by its leaf in the device group, so these need no device identifier tag.
   Also the marker that hides the device group from chat lists. Different clients on one account have to understand
   all of these the same way.
5. **The chat readiness component.** Which group app component marks a chat as ready for multi-device, and what exactly
   it turns on: sibling adds, sibling removal, an admin's device leaving, and the leaf cap.
6. **The client tag.** The new sign-in prompt displays a client tag on KeyPackages, but the Nostr transport doesn't
   define one yet. Slot detection does not depend on that self-reported tag.
7. **Code details.** Exactly how the four words are derived from the KeyPackage, and which word list to use.
8. **History, state sync, and backups.** The companion's [initial history sketch](./multi-device-security.md#how-old-messages-reach-a-new-device)
   leaves the complete transfer and recovery design open: chunked history, small-state sync (read markers, pins,
   notification state), and backups that are never encrypted to the nsec alone.
9. **Disaster recovery.** Recovering when every device is lost is out of scope here, but we need a rough direction
   early so that it doesn't force changes to this design later.
10. **Security and selective sync refinements.** The companion's
    [question register](./multi-device-security.md#questions-to-settle-before-spec-work) covers continuity keys and
    bidirectional signatures, private-key possession, Welcome carriers, per-chat consent, warning rules, privacy,
    decision ordering, history provenance and adversary cases. These need resolution before their rules enter the spec.

## Path into the spec

Parts of this can become spec text before others are settled:

1. **Several leaves per account.** Rules that are already valid today but need writing down: removing a person removes
   all of their leaves, your own leaf being removed means this device was removed even when a sibling stays, each
   installation uses exactly one random slot for its lifetime, KeyPackages carry a client tag and nothing more about
   the device, signing out deletes only your own slot, and inviters add up to 10 fresh KeyPackages per account. None of
   this needs new commit types.
2. **Same-account operations.** The chat readiness app component, sibling adds, sibling removal, an admin's device
   leaving while a sibling remains, and the 10-leaf cap.
3. **The device group.** Roster, messages, linking, gap filling, anomaly signals, and merging.
4. **Account sync.** History, small-state sync, and backups.

## What this replaces

An earlier draft had a new device join each chat through an MLS External Commit. It needed a pairing payload carrying
per-chat secrets and an admin-signed authorization. That draft was never adopted or implemented, and it has been
removed from the spec along with the ids it reserved.
