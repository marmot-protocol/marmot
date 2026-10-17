# Identity, credentials, and capabilities

Status: adopted.

Marmot account identity is a Nostr public key.

The protocol identity is the raw 32-byte x-only secp256k1 public key. Human formats such as `npub` are presentation
formats and do not appear in Marmot protocol bytes unless a document says so.

## Accounts and members

A Marmot account is identified by one Nostr public key.

An MLS leaf represents one account-device membership in one group. Multiple MLS leaves MAY have the same Marmot account
identity when the account has multiple devices in the group.

Group policy MAY talk about accounts or leaves. A rule that targets an account applies to every current leaf whose
credential identity is that account. A rule that targets a leaf applies only to that leaf.

## Devices

A device is one installation of a Marmot client signed in to an account. The word means the client installation, not
the hardware: two different Marmot clients signed in to the same account on one phone are two devices, and reinstalling
a client creates a new device even on the same hardware.

Each device holds its own MLS state: its own leaves, its own KeyPackages, and their private key material. A client
MUST NOT copy MLS group state, leaf secrets, or KeyPackage private key material to another device. Two devices acting
from one leaf's state would reuse that leaf's secrets.

No device has protocol authority over another device of the same account. Rules that target the account, such as admin
rights, apply equally to the leaves of every device. KeyPackage publication per device is defined in
[key-packages.md](./key-packages.md) ("Devices and publication slots").

## MLS credential identity

Marmot uses the MLS credential identity to carry the Marmot account identity.

For a Marmot member leaf:

- the credential identity is exactly 32 bytes;
- those bytes are the member account's Nostr public key;
- clients MUST reject credentials whose identity is not a valid x-only secp256k1 public key.

The MLS signature key for a leaf is not the Marmot account identity. It proves the MLS leaf. The credential identity
says which Marmot account that leaf belongs to.

## Account identity proof

Every Marmot member LeafNode MUST carry `marmot.member.account-identity-proof.v2`, a LeafNode application component
that proves the account named by the `BasicCredential` authorized the leaf's MLS signature public key.

Clients MUST reject a member leaf or KeyPackage if the proof is missing, malformed, does not match the credential
identity, does not match the MLS leaf signature key, or does not verify under the account identity.

The component bytes, local Nostr signing event, capability rules, and validation requirements are defined in
[../app-components/account-identity-proof-v2.md](../app-components/account-identity-proof-v2.md).

## KeyPackages

KeyPackage meaning, discovery requirements, and lifecycle are defined in [key-packages.md](./key-packages.md).

## Capability negotiation

To ensure interoperability, capability negotiation is part of the Marmot protocol.

Different clients MAY support different features. The creator chooses which supported features the group requires; the
required set need not be the largest set every intended member could support. A group MUST NOT require a feature that
an intended initial member cannot process, and later members MUST support the group's required feature set before they
can join.

Marmot uses MLS capabilities for this:

- each KeyPackage advertises the MLS extensions, app components, and proposal types the client supports;
- group state records the features every current and future member MUST support;
- adding a member fails if the new member's KeyPackage does not cover the group's required features;
- group state cannot be mutated into a state that not all members support.

Feature docs MUST say which capability they require. This can be an MLS extension type, an MLS proposal type, a Marmot
app component id, or a combination named by the feature. Marmot-owned ids are registered in
[registries.md](./registries.md).

Optional features SHOULD NOT block basic messaging. If a feature is not supported by every member, the group can still
exist without that feature. When all current members later support it, the group MAY upgrade its required feature set
through the required-capability change flow in
[../protocol-core/group-setup.md](../protocol-core/group-setup.md) ("Required capability changes").

## Delivery addressing is separate

Delivery addresses are not identities.

A group or conversation delivery address MUST NOT be derived from an account id, member id, public key, MLS group id,
KeyPackage id, message id, relay URL, or other stable identity material. For example, the Nostr group `h` tag is the
random `nostr_group_id`, not a value derived from any member key.

Account-level inbox addressing is the deliberate exception. A transport MAY address an account's own inbox by that
account's public key, because reaching a specific account is the purpose of an inbox. The active transport binding owns
the concrete inbox-addressing mechanism; the Nostr rule is defined in [../transports/nostr.md](../transports/nostr.md).

Examples of delivery addresses include a Nostr group `h` tag, an account inbox, a relay list, a topic, or an endpoint
set. The owning transport document defines how those addresses are generated, updated, validated, and used.

## Application content

Marmot app payloads use an unsigned Nostr event shape inside MLS. The shared shape is defined in
[application-messages.md](./application-messages.md).

The inner event's `pubkey` is the author's Marmot account identity. The receiver binding and mismatch outcome are
defined in [application-messages.md](./application-messages.md) ("Receiver authentication").
