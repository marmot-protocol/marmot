# Device pairing

Status: draft.

Device pairing lets a new device and one of the account's existing devices authenticate each other before the new
device joins the account's device group. Each device shows a short code, and the user checks that the two codes match.
They match only if nobody sits between the two devices. The exchange ends in a confirmed link with three parts: the
new device's exact `KeyPackageRef`, which the existing device may add; the id of the group it will add it to; and the
MLS signature key of the existing device's leaf in that group. The new device accepts a Welcome under this link only
into that group, and only from that leaf.

The exchange is Matrix's short authentication string (SAS) verification: `m.sas.v1` with the `curve25519-hkdf-sha256`
key agreement and the `hkdf-hmac-sha256.v2` MAC method
([Matrix client-server API, "Short Authentication String (SAS) verification"](https://spec.matrix.org/latest/client-server-api/#short-authentication-string-sas-verification)).
This document transcribes it into Marmot encodings; it does not use Matrix's event protocol. Of Matrix's two code
methods it uses only emoji, with Matrix's own emoji table (Appendix A).

The non-normative design, including what users see, is in [../ideas/multi-device.md](../ideas/multi-device.md)
(Scenes 2 and 4). This document covers only the exchange. What a device does with a confirmed link, such as creating
the device group, adding the new device to it, or deciding which Welcome makes a group its device group, follows the
device group's own rules ([device-group.md](./device-group.md)).

## Surfaces

- Messages: five rumor kinds, `452` to `456` ("Messages" below), registered in
  [../foundation/registries.md](../foundation/registries.md).
- Transport: the Nostr binding carries each message as a NIP-59 gift wrap from the account to itself
  ([../transports/nostr.md](../transports/nostr.md), "Pairing delivery").
- Foundation: the Marmot binary profile ([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)) for
  every derivation input, and `KeyPackageRef` and publication slots
  ([../foundation/key-packages.md](../foundation/key-packages.md)).
- Group state: none. Pairing changes no group state and requires no app component.

## Threat model

Every device of the account can read and send pairing messages. So can anyone else who holds the account's signing
key. Such an attacker can:

- read every pairing message, and drop, delay, replay or inject any of them;
- run its own sessions from its own installation, or answer a new device while posing as an existing one;
- block linking for as long as it holds the key, by sending competing requests ("Competing requests"), a denial of
  service this design accepts;
- succeed if the user confirms a code they did not compare.

It cannot:

- sit between the devices unseen. Each side fixes its key before it sees the other's, so an attacker gets one blind
  guess per session, with a 1 in 2^42 chance. A wrong guess shows up as different codes, or as a code on only one
  screen;
- swap the new device's KeyPackage. Its `KeyPackageRef` is in the commitment, the code and the new device's
  confirmation;
- pull the new device into a group it controls. The existing device's confirmation covers the group id and its own
  leaf's signature key, and the new device accepts a Welcome only into that group and only from that leaf. Reading the
  group id lets the attacker found a group under it, but not sign as that leaf;
- reuse a code. Every session has fresh keys and expires.

Holding the account key never authenticates a device. Only the code compared on both screens does.

## Roles

The **new device** is the device whose user asks to link it to the account's other devices. It has published a
KeyPackage into its own publication slot and has no device group ([device-group.md](./device-group.md)), or has one and
is moving to another ([device-group.md](./device-group.md), "Moving to another device group"). It starts the session,
commits to its key first and reveals it last. In Matrix's terms, it is the accepting device.

An **existing device** is any other device of the account, whether or not it has a device group yet. Every existing
device sees every request. The new device takes the first answer, and the session continues with that device alone. A
device running a session as a new device answers no request, so if its user starts linking on two devices at once,
neither links and both sessions expire.

## Messages

| Kind  | Message | Sent by           |
| ----- | ------- | ----------------- |
| `452` | Request | the new device    |
| `453` | Answer  | an existing device |
| `454` | Reveal  | the new device    |
| `455` | Confirm | either side       |
| `456` | Cancel  | either side       |

Each message's content is one UTF-8 JSON object with exactly the members its table shows. Every byte string is
lowercase hexadecimal of the exact length shown. A sender writes the members in the order shown, without whitespace.

A reader MUST reject content longer than 1024 bytes; content that is not a JSON object; an unknown, duplicate or missing
member; a member of the wrong type; and hex that is not lowercase or not of the exact length. It MUST ignore a message
whose `v` is not `1`, before reading any other member. The commitment, code and confirmations never cover the JSON
bytes; they use the binary encodings in "Derivations".

### Request

| Member              | Value |
| ------------------- | ----- |
| `v`                 | `1` |
| `session`           | 32 random bytes the new device chose for this session |
| `key_package_event` | 32 bytes: the transport id of the new device's KeyPackage publication, a Nostr event id in the Nostr binding |
| `key_package_ref`   | 1 to 64 bytes: that KeyPackage's `KeyPackageRef` |
| `commitment`        | 32 bytes: the commitment to the new device's key ("Commitment") |

### Answer

| Member | Value |
| ------ | ----- |
| `v`    | `1` |
| `session` | 32 bytes: the request's session |
| `slot` | 32 bytes: the answering device's publication slot id |
| `key`  | 32 bytes: the answering device's X25519 public key for this session |

### Reveal

| Member        | Value |
| ------------- | ----- |
| `v`           | `1` |
| `session`     | 32 bytes |
| `answer_slot` | 32 bytes: the `slot` of the answer the new device took |
| `key`         | 32 bytes: the new device's X25519 public key for this session |

### Confirm

| Member          | Value |
| --------------- | ----- |
| `v`             | `1` |
| `session`       | 32 bytes |
| `from`          | `"new_device"` or `"existing_device"` |
| `device_group`  | 1 to 255 bytes: the MLS group id of the group the existing device adds the new device to. Present if and only if `from` is `"existing_device"`; never `null` |
| `signature_key` | 1 to 133 bytes: the MLS signature public key of the existing device's own leaf in that group, which is the key it creates the group with if the group does not exist yet. Present if and only if `from` is `"existing_device"`; never `null` |
| `mac`           | 32 bytes: the sender's confirmation ("Confirmations") |

133 bytes is the longest MLS signature public key, a P-521 point. With the longest group id, the existing device's
Confirm stays within the 1024-byte limit.

### Cancel

| Member    | Value |
| --------- | ----- |
| `v`       | `1` |
| `session` | 32 bytes |
| `reason`  | 1 to 32 bytes of lowercase ASCII letters, digits and `_` |

Defined reasons: `user`, `timeout`, `mismatched_commitment`, `mismatched_code`, `mismatched_confirm`,
`unexpected_message`, `competing_requests`, `rate_limited` and `cannot_link`. A reader MUST accept any other reason
in that format, and treats it as an unknown reason.

## Derivations

Every structure below uses the Marmot binary profile
([../foundation/canonical-encoding.md](../foundation/canonical-encoding.md)). `account` is the account's 32-byte
identity. HKDF is HKDF-SHA256 ([RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)) with the shared secret as input
keying material and no salt, as in Matrix, so RFC 5869 uses 32 zero bytes as the salt.

### Keys

Each side generates a fresh X25519 key pair ([RFC 7748](https://www.rfc-editor.org/rfc/rfc7748)) for each session and
never reuses it. The shared secret is X25519 of a side's own private key and the other side's public key. A side MUST
end the session if the shared secret is 32 zero bytes, which a low-order public key produces (RFC 7748, section 6.1).

### Commitment

```text
struct {
    opaque label<V> = "marmot-pairing-v1-commitment";
    opaque new_device_key[32];
    opaque session_id[32];
    opaque account[32];
    opaque key_package_event_id[32];
    opaque key_package_ref<1..64>;
} PairingCommitmentInput;

commitment = SHA-256(PairingCommitmentInput)
```

This is Matrix's commitment, a hash of the committing device's key and the start message, with the start message
replaced by the fields the request binds.

### Code

```text
struct {
    opaque label<V> = "marmot-pairing-v1-sas";
    opaque session_id[32];
    opaque account[32];
    opaque key_package_ref<1..64>;
    opaque new_device_key[32];
    opaque existing_device_slot[32];
    opaque existing_device_key[32];
} PairingSasInfo;

sas_bytes = HKDF(info = PairingSasInfo, length = 6)
```

`existing_device_slot` is the `slot` of the answer the new device took. The code is seven emoji, by Matrix's emoji
method: the first 42 bits of `sas_bytes`, most significant bit first, split into seven 6-bit numbers. Each number is an
index into the table in Appendix A. A device shows each emoji with its English description, or a translation of it,
and gives that text to screen readers. Matrix's decimal method is not used.

### Confirmations

```text
enum { new_device(1), existing_device(2), (255) } PairingConfirmSender;
enum { key_package_ref(1), device_group(2), (255) } PairingConfirmItem;

struct {
    opaque label<V> = "marmot-pairing-v1-mac";
    PairingConfirmSender sender;
    opaque session_id[32];
    opaque account[32];
    opaque key_package_ref<1..64>;
    opaque existing_device_slot[32];
    PairingConfirmItem item;
} PairingMacInfo;

mac_key = HKDF(info = PairingMacInfo, length = 32)
mac     = HMAC-SHA256(mac_key, opaque value<V>)

struct {
    opaque group_id<V>;
    opaque signature_key<V>;
} PairingDeviceGroup;
```

- The new device's confirmation has `sender = new_device`, `item = key_package_ref`, and `value` is its own
  `KeyPackageRef` from the request.
- The existing device's confirmation has `sender = existing_device`, `item = device_group`, and `value` is the
  `PairingDeviceGroup` of the `device_group` and `signature_key` it sends.

A receiver MUST compare MACs in constant time.

## Session rules

### New device

1. It sends a Request. It shows no code until it has taken an answer.
2. It takes the first Answer for its session and ignores every later one. If the shared secret is invalid ("Keys"), it
   sends Cancel `unexpected_message` and ends the session. Otherwise it sends a Reveal naming that answer's `slot`,
   derives the code, and shows it.
3. Its user decides once, at any time while the code is on screen. If the codes differ, it sends Cancel
   `mismatched_code` and ends the session. If they match, it holds its Confirm until the existing device's Confirm
   has been verified.
4. When the existing device's Confirm arrives, it checks the MAC over the named `device_group` and `signature_key`. If
   the check fails, it sends Cancel `mismatched_confirm` and ends the session.
5. Once its user has confirmed and the existing device's Confirm has been verified, it sends its Confirm, and the link
   is confirmed. It MUST NOT send its Confirm before then. Until the link ends ([device-group.md](./device-group.md),
   "Joining"), the new device MUST NOT join any Welcome into the group the existing device's Confirm named, or any
   Welcome that adds the KeyPackage the link confirmed, except the link's Welcome: one into that group, whose sender has
   the signature key that Confirm named, that adds that KeyPackage, and whose group requires `0x800e`. The sender is the
   leaf at the `signer` index of the Welcome's `GroupInfo`, whose signature key verifies that `GroupInfo`. It refuses
   every other such Welcome before joining, so none takes the group id or uses up the KeyPackage. Any other Welcome
   never makes its group the device group, and a group that requires `0x800e` is joined only through the Welcome a
   confirmed link named ([device-group.md](./device-group.md), "Trust").

### Existing device

1. It ignores a Request whose timestamp is 600 seconds or more in the past, or more than 300 seconds in the future, as
   Matrix's request rule does. In the Nostr binding the timestamp is the rumor's `created_at`.
2. Before it answers, it fetches the KeyPackage publication the request names and validates it under
   [../foundation/key-packages.md](../foundation/key-packages.md) and the transport binding. The publication MUST be the
   account's, and its decoded `KeyPackageRef` MUST equal the request's `key_package_ref`. A device that would not link
   that KeyPackage does not answer. It sends Cancel `cannot_link` only as the device group's rules say
   ([device-group.md](./device-group.md), "Before answering").
3. It sends an Answer with a fresh key and its own slot id, subject to "Competing requests" and "Rate limit".
4. A Reveal whose `answer_slot` is not its own slot means the new device took another answer. The device ends the
   session, whether or not it answered, and sends nothing. On a Reveal naming its own slot, for a session it answered:
   - if the commitment computed from the revealed key and the request does not equal the request's `commitment`, it
     sends Cancel `mismatched_commitment` and ends the session;
   - if the shared secret is invalid, it sends Cancel `unexpected_message` and ends the session;
   - otherwise it derives the code and shows it.
5. Its user decides once. If the codes match, the device sends its Confirm with the id of the group it will add the new
   device to and the signature key of its own leaf in it. Which group that is, the device group's rules decide
   ([device-group.md](./device-group.md), "Approving"). For a group it has not created yet, that is the key it will
   create the group with. It keeps that key on its leaf there through the Commit that adds the new device, so that key
   signs the Welcome's `GroupInfo`. If the codes differ, it sends Cancel `mismatched_code` and ends the session.
6. It ignores a new device's Confirm that arrives before it has sent its own. When the new device's Confirm arrives
   after that, it checks the MAC over the request's `key_package_ref`. If the check fails, it sends Cancel
   `mismatched_confirm` and ends the session.
7. When the new device's Confirm has been verified, the link is confirmed. The device MAY then add the KeyPackage with
   exactly the confirmed `KeyPackageRef`, and no other, to the group its Confirm named, from the leaf whose signature
   key its Confirm named, so that leaf signs the Welcome's `GroupInfo`. It MUST NOT add it before then.

### Confirmation order

The confirmations are sent in a fixed order: the existing device's first, then the new device's. By the time the
existing device confirms the link, the new device has already verified the group it will join. Either user may confirm
at any time; only the sending waits. Matrix allows its MACs in either order and ends with `m.key.verification.done`;
this exchange fixes the order instead and has no closing message.

- If the existing device's Confirm is lost, the new device never sends its own. Both sessions expire and nothing is
  added.
- If the new device's Confirm is lost, the existing device's session expires: it adds nothing and sends Cancel
  `timeout`. The new device withdraws its link when that Cancel arrives. If the Cancel is lost too, no Welcome arrives
  under the link.

"Expiry" does not apply to a confirmed link, which owes no Cancel `timeout`. How long a new device waits for its Welcome
is part of joining the device group ([device-group.md](./device-group.md), "Joining"), not of this exchange. An existing
device acts on its link as soon as the link is confirmed, and need not keep the session past the time it would otherwise
have expired.

### Competing requests

A request is live from the time a device receives it until it expires or its session ends. While more than one request
is live, an existing device MUST NOT answer any of them and MUST NOT send a Confirm in any session. Its user is not
offered a choice between them. A session already showing a code waits; it may continue once the other request is no
longer live. A device MAY send Cancel `competing_requests` in sessions it answered.

A device MAY bound how many requests it tracks. A request it has no room to track still counts as live until it
would have expired.

### Rate limit

An existing device sends at most 10 Answers in any 3600-second window. Once it has sent 10, it sends no further Answer
until the oldest of them is 3600 seconds old. A device MAY send Cancel `rate_limited` for a request it does not answer
for this reason. Only Answers count; requests that are ignored or never answered do not.

### Expiry

| Limit | Value |
| ----- | ----- |
| A request with no answer taken | 600 seconds after it was sent, or, at an existing device, after the earlier of its timestamp and its arrival |
| A session with an answer | 600 seconds after the answer was sent or taken |

When a session expires, a device ends it, stops showing its code, and sends Cancel `timeout` if it had sent an Answer
or a Request.

### Every session

- A device makes one decision per session. It never shows a session's code again after a decision, a cancel or expiry.
- A device ignores a message only its own role sends, a message for a step the session has passed, such as a second
  Reveal or a replayed Request, and a message for a session it does not hold, other than a Cancel for the session of a
  link it keeps. A Confirm whose `from` is the receiver's own role is one only its own role sends: its own Confirm,
  returned by its inbox relays ([../transports/nostr.md](../transports/nostr.md), "Pairing delivery").
- A Cancel ends the session at its receiver, whatever its reason, and the receiver sends nothing back. At a new device
  it also ends the session's confirmed link, even after a restart, unless the device has already joined through the
  link's Welcome; a Cancel after that join changes nothing. An existing device that has confirmed the link ignores it.
- A device keeps its private key, the shared secret, the code and the MAC keys in memory only, for the life of the
  session, and erases them when it ends. It MUST NOT write any of them to persistent storage or logs. The confirmed link
  is not one of these secrets: a new device keeps it across restarts until the link ends
  ([device-group.md](./device-group.md), "Joining").

## Security considerations

- **One guess per session.** The new device commits to its key before it sees the existing device's key, and the
  existing device sends its key before it sees the new device's. An attacker that takes either role must fix its key
  before it learns the other, so it can match the code only by chance. This is Matrix's argument, inherited from ZRTP's
  hash commitment.
- **Careless approval.** Nothing catches a user who confirms without comparing. Clients SHOULD make the comparison the
  main thing on screen, and MUST NOT ask the user to type the code or read it to anyone.
- **A code on one screen only.** An attacker that answers first, posing as an existing device, gets a code onto the new
  device's screen. The user's real devices then show none, because the Reveal names another slot.
- **Competing requests** cost an attacker nothing to send. They block linking but never cause a link.
- **A Welcome from another leaf.** Anyone holding the account key can read the group id in the existing device's
  Confirm and found a group under it, adding the new device's published KeyPackage. The new device refuses that
  Welcome, because its sender is not the leaf the Confirm named. It refuses before joining, so a forged Welcome that
  arrives first leaves the KeyPackage and the group id for the real one.
- **A forged Cancel** from anyone holding the account key can end any session, and can withdraw a new device's link
  after the existing device has confirmed it. The existing device may then add a device that refuses the Welcome. This
  is denial of service only: the added leaf is the new device's own KeyPackage, so the attacker adds no member of its
  own, and the user can remove the leaf.
- **The rate limit** bounds how often an attacker can put a prompt in front of the user. It does not bound guesses,
  because each session already allows only one.
- **Metadata.** Relays see gift wraps addressed to the account, as for Welcomes. A burst of five or more within
  minutes suggests a pairing session. Relays also see each gift wrap's size: NIP-44 padding rounds it up, but the sizes
  may still reveal which kind of message each one carries.

## Test vector

This vector covers the derivations and the message content. Its inputs are test material only.

```text
account                = 246dcea7bb990ddcb9d99d168ba8b5caabbff19fd7777447d7170cc002222723
session_id             = 57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738
key_package_event_id   = b14e210763b9624f3779a7cbec5dac11d70295378309adea4e641ad64e4a8bbe
key_package_ref        = f902a495dfe13081eeacb9a3e9810b3263036d203763a39cb43743fd859408be
existing_device_slot   = f1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b7
device_group_id        = 302cb48c526eec0acf5e92392604784d
signature_key          = c3286faa8aec5c128744235ee3092a1effc4a48b11ad56070e373556b9dfad33
new_device_secret      = 0dcf2a8012fdf56921abc17e50febc867232cb93386da5b1fef152d9858666eb
existing_device_secret = 897378a3d00765ba889939c4b56522c8159ac5ff7f30394e7ad3ed5c9298be43

new_device_key         = 8655170bbf46c3f293a1b8e0ed2e9b3a4ff77aaaa524eb2311e10cd90dcee45e
existing_device_key    = 82824d142a96277f81727318ddda32774ccaf2727b48a0d7fe7d42164f27eb7c
commitment             = 17b6195891fd8bb85ff47fbffeff42434ed20442b46db183e653add66fc1764e
shared_secret          = 025c75560bdfec692c645d2ebfe9e665e33cfe16ccd79f3ec90c56b85a2f830c
sas_bytes              = 38b17be5d13a
emoji                  = 14 11 5 59 57 29 4 (Butterfly, Turtle, Pig, Bell, Guitar, Heart, Unicorn)
new_device_mac         = c1c0251409411eda04366529b6e42c212dd441615740d317176d5b437d04b977
existing_device_mac    = 939e0e9477fd499c405bd581c44c984a3012b58eea331666a0cb2651497f7c0e
```

`PairingSasInfo`, the new device's and the existing device's `PairingMacInfo`, then the existing device's
`PairingDeviceGroup`:

```text
156d61726d6f742d70616972696e672d76312d73617357729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738246dcea7bb990ddcb9d99d168ba8b5caabbff19fd7777447d7170cc00222272320f902a495dfe13081eeacb9a3e9810b3263036d203763a39cb43743fd859408be8655170bbf46c3f293a1b8e0ed2e9b3a4ff77aaaa524eb2311e10cd90dcee45ef1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b782824d142a96277f81727318ddda32774ccaf2727b48a0d7fe7d42164f27eb7c

156d61726d6f742d70616972696e672d76312d6d61630157729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738246dcea7bb990ddcb9d99d168ba8b5caabbff19fd7777447d7170cc00222272320f902a495dfe13081eeacb9a3e9810b3263036d203763a39cb43743fd859408bef1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b701

156d61726d6f742d70616972696e672d76312d6d61630257729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738246dcea7bb990ddcb9d99d168ba8b5caabbff19fd7777447d7170cc00222272320f902a495dfe13081eeacb9a3e9810b3263036d203763a39cb43743fd859408bef1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b702

10302cb48c526eec0acf5e92392604784d20c3286faa8aec5c128744235ee3092a1effc4a48b11ad56070e373556b9dfad33
```

The content of the Request, Answer, Reveal and the two Confirms:

```text
{"v":1,"session":"57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738","key_package_event":"b14e210763b9624f3779a7cbec5dac11d70295378309adea4e641ad64e4a8bbe","key_package_ref":"f902a495dfe13081eeacb9a3e9810b3263036d203763a39cb43743fd859408be","commitment":"17b6195891fd8bb85ff47fbffeff42434ed20442b46db183e653add66fc1764e"}
{"v":1,"session":"57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738","slot":"f1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b7","key":"82824d142a96277f81727318ddda32774ccaf2727b48a0d7fe7d42164f27eb7c"}
{"v":1,"session":"57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738","answer_slot":"f1e8d7ff4ec5a09e46a51cc9a316cf243f9ea0cb0dc02eacc0991b035efa02b7","key":"8655170bbf46c3f293a1b8e0ed2e9b3a4ff77aaaa524eb2311e10cd90dcee45e"}
{"v":1,"session":"57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738","from":"new_device","mac":"c1c0251409411eda04366529b6e42c212dd441615740d317176d5b437d04b977"}
{"v":1,"session":"57729aa88f3b59e101e00eab5a3eaacb091602a0d51437c56a1e986652975738","from":"existing_device","device_group":"302cb48c526eec0acf5e92392604784d","signature_key":"c3286faa8aec5c128744235ee3092a1effc4a48b11ad56070e373556b9dfad33","mac":"939e0e9477fd499c405bd581c44c984a3012b58eea331666a0cb2651497f7c0e"}
```

A second vector uses a 64-byte `KeyPackageRef`, a 255-byte group id and a 133-byte signature key, whose length
prefixes take two bytes. Its `device_group_id` and `signature_key` are the 32 bytes shown, repeated and truncated to
255 and 133 bytes:

```text
account                = 10c8a4e42fed96611d9d09ccea39a1979e78026b429bafaf2c99b7919124388e
session_id             = 18d4e1ffec9c4c0efc4efbf395be56229030312fb4e4c458670898b2e2326b03
key_package_event_id   = 1c3f48efd41e4df6d61b6062c8d516fb223442350f80b7475091c00f51947615
key_package_ref        = d791758d5dd7c744aa44d9e8a3e7c45e2e4ed07bc928ab99768889637b539468
                         12ae2a0dca55d03aad3f35c2c9232a46b2e0f9ce4a0a4c0546d11bb20461dce3
existing_device_slot   = 43cf92ec8e2aab90ba226b8febc33a8fc65b6c89672588e7022233a3642f3589
device_group_id        = 1b27ff8782165e200c664fe505bb90cb3264611312917a4ecbc6d0b542d96750 (repeated)
signature_key          = 4cc82df86a0d2ce7d93dd9a0f804dbdc8e5cb3b60558f6f42c849794a19bd1a9 (repeated)
new_device_secret      = 4d30860f481a8db89eaa7b24818f2f065b3703a49dba1f98be7986febfddc649
existing_device_secret = dcf3ba787981200bd609928b3c10b3385d3b46286c0db9e7d761db8bd0d97c7b

commitment             = d7396351e1eb534f7620a17c771bb40d885d42e8acfa47cb1aa4c03561fa68c5
sas_bytes              = 2e3888256ef4
emoji                  = 11 35 34 8 9 22 59
new_device_mac         = 4f1e1c74100a03966a1636442e1a1109a8387cf80547ed9b9d7b03aa7fe133e0
existing_device_mac    = 9f3e619fc8dd6c719d9153f00bc6084f3302e68de3d427026f6a8595ab5e26fb
```

## Appendix A: Emoji table

This table is Matrix's SAS emoji table, `data-definitions/sas-emoji.json` from
[matrix-org/matrix-spec](https://github.com/matrix-org/matrix-spec/blob/7aaeac07608f97942eff88634a56b630a745ce56/data-definitions/sas-emoji.json)
at commit `7aaeac07608f97942eff88634a56b630a745ce56`. The entries are unchanged; this copy is a Markdown table and
leaves out the source file's translations. Clients that translate the descriptions SHOULD take them from that file.

SHA-256 over one line per entry, `number TAB emoji TAB description TAB unicode LF` in UTF-8, is
`2e6e8f1cdda84d2520dcbcc49152db6fc50c2a78546c36bd8991515eef48ba81`.

| Number | Emoji | Description | Unicode |
| --- | --- | --- | --- |
| 0 | 🐶 | Dog | U+1F436 |
| 1 | 🐱 | Cat | U+1F431 |
| 2 | 🦁 | Lion | U+1F981 |
| 3 | 🐎 | Horse | U+1F40E |
| 4 | 🦄 | Unicorn | U+1F984 |
| 5 | 🐷 | Pig | U+1F437 |
| 6 | 🐘 | Elephant | U+1F418 |
| 7 | 🐰 | Rabbit | U+1F430 |
| 8 | 🐼 | Panda | U+1F43C |
| 9 | 🐓 | Rooster | U+1F413 |
| 10 | 🐧 | Penguin | U+1F427 |
| 11 | 🐢 | Turtle | U+1F422 |
| 12 | 🐟 | Fish | U+1F41F |
| 13 | 🐙 | Octopus | U+1F419 |
| 14 | 🦋 | Butterfly | U+1F98B |
| 15 | 🌷 | Flower | U+1F337 |
| 16 | 🌳 | Tree | U+1F333 |
| 17 | 🌵 | Cactus | U+1F335 |
| 18 | 🍄 | Mushroom | U+1F344 |
| 19 | 🌏 | Globe | U+1F30F |
| 20 | 🌙 | Moon | U+1F319 |
| 21 | ☁️ | Cloud | U+2601U+FE0F |
| 22 | 🔥 | Fire | U+1F525 |
| 23 | 🍌 | Banana | U+1F34C |
| 24 | 🍎 | Apple | U+1F34E |
| 25 | 🍓 | Strawberry | U+1F353 |
| 26 | 🌽 | Corn | U+1F33D |
| 27 | 🍕 | Pizza | U+1F355 |
| 28 | 🎂 | Cake | U+1F382 |
| 29 | ❤️ | Heart | U+2764U+FE0F |
| 30 | 😀 | Smiley | U+1F600 |
| 31 | 🤖 | Robot | U+1F916 |
| 32 | 🎩 | Hat | U+1F3A9 |
| 33 | 👓 | Glasses | U+1F453 |
| 34 | 🔧 | Spanner | U+1F527 |
| 35 | 🎅 | Santa | U+1F385 |
| 36 | 👍 | Thumbs Up | U+1F44D |
| 37 | ☂️ | Umbrella | U+2602U+FE0F |
| 38 | ⌛ | Hourglass | U+231B |
| 39 | ⏰ | Clock | U+23F0 |
| 40 | 🎁 | Gift | U+1F381 |
| 41 | 💡 | Light Bulb | U+1F4A1 |
| 42 | 📕 | Book | U+1F4D5 |
| 43 | ✏️ | Pencil | U+270FU+FE0F |
| 44 | 📎 | Paperclip | U+1F4CE |
| 45 | ✂️ | Scissors | U+2702U+FE0F |
| 46 | 🔒 | Lock | U+1F512 |
| 47 | 🔑 | Key | U+1F511 |
| 48 | 🔨 | Hammer | U+1F528 |
| 49 | ☎️ | Telephone | U+260EU+FE0F |
| 50 | 🏁 | Flag | U+1F3C1 |
| 51 | 🚂 | Train | U+1F682 |
| 52 | 🚲 | Bicycle | U+1F6B2 |
| 53 | ✈️ | Aeroplane | U+2708U+FE0F |
| 54 | 🚀 | Rocket | U+1F680 |
| 55 | 🏆 | Trophy | U+1F3C6 |
| 56 | ⚽ | Ball | U+26BD |
| 57 | 🎸 | Guitar | U+1F3B8 |
| 58 | 🎺 | Trumpet | U+1F3BA |
| 59 | 🔔 | Bell | U+1F514 |
| 60 | ⚓ | Anchor | U+2693 |
| 61 | 🎧 | Headphones | U+1F3A7 |
| 62 | 📁 | Folder | U+1F4C1 |
| 63 | 📌 | Pin | U+1F4CC |
