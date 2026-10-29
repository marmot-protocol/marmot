# Device group

Status: draft.

An account signed in on several devices keeps a hidden Marmot group that holds only those devices: its device group.
The device group carries the account's device roster as group state, so every device agrees on which devices are
linked, which sign-ins were rejected, and in which order those decisions were made. It never appears as a chat.

The non-normative direction is described in [../ideas/multi-device.md](../ideas/multi-device.md). This document covers
the device group itself: what makes a group one, how it is created, when a device trusts it, how clients keep it out
of sight, how each device announces the KeyPackages it publishes, and how devices hand each other private KeyPackages.
Linking, adding a sibling to a chat, and removal are not specified yet.

## Surfaces

- App component: [marmot.account.device-roster.v1](../app-components/device-roster-v1.md) (`0x800e`), which owns the
  roster's bytes, its update operations and their validation. Requiring it marks a group as a device group.
- App component: [marmot.member.device-tag.v1](../app-components/device-tag-v1.md) (`0x800f`), the LeafNode tag that
  tells the account's devices which of its leaves in any group belongs to which device.
- App component: [marmot.group.account-devices.v1](../app-components/account-devices-v1.md) (`0x800d`), which a device
  group requires under the ordinary creation rule.
- Protocol core: [../protocol-core/group-setup.md](../protocol-core/group-setup.md) and
  [../protocol-core/joining.md](../protocol-core/joining.md).
- Foundation: [../foundation/key-packages.md](../foundation/key-packages.md), whose publication slots each device's
  roster entry announces into.
- Marmot app events: kind `459` (private KeyPackage request) and kind `460` (private KeyPackage hand-off), sent only in
  a device group ([Private KeyPackages](#private-keypackages)). Their kinds are registered in
  [../foundation/registries.md](../foundation/registries.md).

## What a device group is

A device group is a group whose GroupContext `app_components` required list contains `0x800e`. Its members are the
devices of one account and no others ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md),
"Requirement").

An account has no device group while it has one device. The device group is created when a second device is linked.

The marker never makes a group trusted. Anyone holding the account's signing key can create a group that requires
`0x800e` and send a Welcome for it to the account. A device acts on a group as its device group only under the trust
rule below.

## Creating the device group

The device that approves a link creates the device group, if its account has none, and adds the newly linked device in
the founding Add:

- The founding state requires `0x800e` and carries a roster with an entry for the creating device and one for the
  linked device.
- The group runs under the ordinary group rules. The creating device's account is its only admin: the creator passes
  no other initial admin. Whether the founding state requires `0x800d` follows the ordinary creation rule
  ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)).
- The founding Add contains exactly one KeyPackage: the one the link confirmed, identified by its `KeyPackageRef`. A
  client MUST NOT found a device group with any other KeyPackage, and MUST NOT select one from the account's
  publications. This is narrower than the founding exemption in
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md) ("Sender rules"), which lets a
  creator add its own account's published KeyPackages to a new group. A device group never relies on that exemption.

A Commit that adds a device to the device group or removes one also writes that device's roster entry, so each change of
membership and its record are one decision. Such a Commit carries an AppDataUpdate, so it is `privileged` in branch
selection ([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate branches").

These are sender rules. A receiver cannot tell where a KeyPackage came from, so it does not reject a Commit or a
Welcome for breaking them.

## Trust

A device treats a group as its device group only if:

- it created the group itself, as above; or
- it joined the group through a Welcome for the group that a confirmed link named.

A device MUST NOT join a group that requires `0x800e` through any other Welcome, and decides that before it joins.

A device records which group it trusts as its device group when it creates or joins it, and does not infer it later
from group state.

## Keeping it out of sight

A device group is not a chat:

- Clients MUST NOT show a device group, or any group that requires `0x800e`, in chat lists, chat counts, unread counts,
  or notifications, and MUST NOT offer it as a destination for messages.
- A client shows the roster of its own device group only to its own user, for example on a Devices screen. It never
  shows another account's devices.

## Matching leaves to devices

Every leaf of the account in a group carries the same credential identity, so the group alone does not say which leaf
belongs to which device. Each linked device tags its leaves instead
([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md)), and a device that holds the roster reads
those tags in the groups it is in. Nothing about other groups is written to the device group, so joining a group,
leaving one, or replacing a leaf there never commits to it.

- Each device makes its own tag signature key pair and keeps the private key to itself.
- The device that creates the device group chooses the roster's `leaf_tag_key`, and its founding entry carries its
  `tag_signature_key` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)).
- A device that joins the device group sets the `tag_signature_key` in its own roster entry with its first Commit
  there, its post-join self-update ([../protocol-core/joining.md](../protocol-core/joining.md), receiving flow, step
  14), which it SHOULD make as soon as it has joined. That Commit also replaces its leaf in the device group with one
  tagged under that key ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags").
  Until then its leaf there is unclaimed, like any untagged leaf. A group where it made its post-join self-update
  before then gets a tagged leaf later.

What the devices do with what they find (adding a sibling to a group it is missing from, removing a removed device's
leaves, warning about a leaf no device claims) is not specified yet.

## Slot announcements

A device in a device group names each KeyPackage in its own roster entry before that KeyPackage reaches its slot
([../foundation/key-packages.md](../foundation/key-packages.md), "Devices and publication slots"). The entry's
`announced_key_package` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md)) holds the
`KeyPackageRef` of the KeyPackage the device publishes there. Its siblings can then tell a refresh, which the roster
names, from a publication in the slot that the device did not make.

- Before a device publishes a KeyPackage to its slot, whether a new one or the current one again, it MUST check that its
  own entry in its device group's current roster names that KeyPackage. If the entry names another or none, the device
  first commits an AppDataUpdate that sets its own entry, with every other field unchanged and `announced_key_package`
  naming the KeyPackage.
- The device publishes only once that Commit is part of the group state it holds. A Commit that fails, or that a
  branch selection drops, leaves the entry as it was, so the device announces again before it publishes.
- A device that cannot announce, for example because the device group's relays are unreachable, does not publish. It
  MUST NOT publish an unannounced KeyPackage after a timeout; its slot ages instead
  ([../foundation/key-packages.md](../foundation/key-packages.md), "Refreshing a slot"). While a refresh that section
  calls for is held back this way, a client SHOULD tell its user, so that a device whose device group stays unwritable
  does not quietly become one that new chats cannot add.
- The founding roster announces the KeyPackage the link confirmed and the creating device's current one
  ([Creating the device group](#creating-the-device-group)), so neither device owes a Commit before it next publishes.
- A device with no device group publishes as before.

The roster keeps one announcement per device. Between an announcement and its publication, and while some relays still
serve the previous publication, a sibling can find a KeyPackage in a device's slot that the roster no longer names. A
sibling's response to a KeyPackage the roster does not announce is not specified yet.

A device that finds a publication in its own slot that it did not make replaces it
([../foundation/key-packages.md](../foundation/key-packages.md), "A publication the device did not make"), announcing
the replacement first as above.

## Private KeyPackages

Devices in a device group add each other to chats only with private KeyPackages: single-use KeyPackages that one device
hands to one sibling inside the device group. A private KeyPackage never reaches a slot or any other publication. How a
sibling uses one to add a device to a chat is not specified yet.

### Issuing

A private KeyPackage is a KeyPackage of the device that issues it
([../foundation/key-packages.md](../foundation/key-packages.md)), with the lifetime and capabilities that device gives
the KeyPackages it publishes. It MUST NOT be last-resort, so a Welcome consumes it once. It carries the issuer's device
tag ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Producing tags"), so a device issues
private KeyPackages only once it can tag.

- The issuer records which sibling, by slot, it handed each one to. It keeps the private key material until a Welcome
  consumes the KeyPackage or until its `Lifetime.not_after`, whichever comes first.
- Only a sibling's add may consume a private KeyPackage. A device MUST NOT join a group through any other Welcome that
  consumes one, and keeps the KeyPackage when it refuses such a Welcome.
- Halfway is `not_before + (not_after - not_before) / 2` in integer seconds, from the KeyPackage's `Lifetime`.
- A device's stock with a sibling is the private KeyPackages it handed that sibling that no Welcome has consumed, that
  have not reached halfway, and that no later request from that sibling has superseded. When the stock falls below 5,
  the device issues enough new ones to bring it to 10 and hands them over.
- A device tops up its siblings before it asks for its own, so a device back after a long gap serves the others first.
- A device MAY cap how many unexpired private KeyPackages it keeps for one sibling, and issue fewer than a request asks
  for once it reaches that cap. It MUST NOT delete one before `not_after` to make room.
- At `not_after`, the issuer deletes the private key material and the holder deletes the KeyPackage.

### Messages

| Kind  | Message  | Sent by                                   |
| ----- | -------- | ----------------------------------------- |
| `459` | Request  | a device that wants private KeyPackages   |
| `460` | Hand-off | the device that issued them               |

Both are Marmot app events ([../foundation/application-messages.md](../foundation/application-messages.md)) sent as MLS
application messages in the device group. Both name the sender's slot (`from`) and the addressee's slot (`to`), each a
`SlotId` ([../app-components/device-roster-v1.md](../app-components/device-roster-v1.md), "State").

A request's content is one UTF-8 JSON object with exactly these members, written in this order without whitespace.
Slots are lowercase hexadecimal, 64 characters, and `want` is a decimal integer without leading zeros.

| Member | Value |
| ------ | ----- |
| `v`    | `1` |
| `from` | the requesting device's slot |
| `to`   | the slot of the device asked |
| `want` | how many new private KeyPackages it asks for, from 1 to 100 |

A hand-off's content is the standard base64 encoding, with padding
([RFC 4648, section 4](https://www.rfc-editor.org/rfc/rfc4648#section-4)), of:

```text
struct {
  uint8 version;
  SlotId from;
  SlotId to;
  MLSMessage key_packages<V>;
} PrivateKeyPackageHandOffV1;
```

`version` is `1`. `key_packages` holds 1 to 20 MLSMessages, each with `wire_format` `mls_key_package`. An answer of
more than 20 goes out as several hand-offs.

### Sending

- A device asks a sibling for private KeyPackages when it holds no usable one from that sibling, or when it needs more
  than it holds. A usable one has not reached halfway. While the need lasts, it sends the request again at most once an
  hour.
- A device answers a request by issuing `want` new private KeyPackages to the requester and handing them over. The ones
  it handed the requester before stop counting toward the stock, since they may have been lost, but keep their key
  material until a Welcome consumes them or they expire. A device answers each request, by its Marmot app event `id`,
  once.
- There are no receipts. A lost hand-off is repaired by the requester's next request.

### Receiving

A device reads a request or a hand-off only from the device group it trusts ([Trust](#trust)), and ignores both kinds
in any other group. It drops one unless:

- `to` is its own slot;
- `from` is another device in its current roster;
- the leaf that sent it carries a device tag that reads as `from`'s
  ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md), "Reading tags"): it opens under the
  roster's `leaf_tag_key`, names `from`, and verifies under the `tag_signature_key` in `from`'s roster entry.

A device whose leaf in the device group carries no tag yet, such as a new device before its post-join self-update, has
its requests and hand-offs dropped and not counted. It sends them again once it has tagged its leaf.

It drops a whole hand-off unless every KeyPackage in it:

- is a valid KeyPackage ([../foundation/key-packages.md](../foundation/key-packages.md)) of its own account;
- is not last-resort;
- has not reached its `Lifetime.not_after`;
- carries a device tag that reads as `from`'s, as above.

The tag checks are the device group's rules for accepting a request or a hand-off, not validity rules: a KeyPackage or
leaf without a tag stays valid everywhere else ([../app-components/device-tag-v1.md](../app-components/device-tag-v1.md),
"Validity"). The receiver keeps the KeyPackages it accepts by `from` until it uses one, discards them, or they expire.

## Security considerations

- Every device in the device group is the same account, and that account is the group's only admin, so any device can
  add or remove another and edit any roster entry. A stolen linked device can do the same until it is removed.
- The trust rule is what keeps someone holding the account's signing key from pulling a device into a device group they
  control. Requiring `0x800e` is a marker for hiding the group, not evidence that the account's devices created it.
- Only the account's devices, including removed ones, can read device tags. Other members of a group see opaque bytes
  that differ in every KeyPackage. A tag's presence shows that the account has linked devices, which its KeyPackage
  publications already show.
- An announcement is evidence only among devices that trust the same device group. Someone holding the account's
  signing key can publish into any slot, but cannot write the roster of a device group they are not in.
- Private KeyPackages are why holding the account's signing key never lets someone join a chat as a sibling: siblings
  add each other only with KeyPackages handed over inside a device group that person is not in.
- Device tags tie a request or hand-off, and each handed-over KeyPackage, to its `from` slot. One device in the device
  group therefore cannot file its KeyPackages under a sibling's slot, or make a request in a sibling's name that resets
  what was handed that sibling. Someone holding only the account's signing key has neither `leaf_tag_key` nor a tag
  signature key.
