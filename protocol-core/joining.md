# Welcomes

Status: adopted.

Security context: [protocol threat model](../security-considerations.md#t3-invitation-abuse-stale-packages-and-first-contact-group-substitution).

This document describes the member join flow built around MLS Welcomes.

## Surfaces

- Foundation identity and KeyPackages.
- MLS protocol: Add, Commit, Welcome, KeyPackageRef, and post-join Update.
- Protocol-core publish lifecycle.
- The active transport binding for Welcome delivery.
- The active transport routing state for post-join group traffic.

## Behavior

For Add commits after initial group creation, the inviter MUST wait for the Commit publish obligation to succeed
before sending the Welcome. Sending the Welcome first can activate the new member at an epoch existing members
have not seen yet.

Founding group creation is the exception, including both one-member creation and creation with initial invitees. There
are no existing peers that can be forked by a missing creation Commit. A one-member creation has an empty creation
publish obligation and ends at epoch 0. For founding creation with initial invitees, the creator first creates the
one-member epoch-0 group, then creates and locally merges one founding Add Commit from epoch 0 to epoch 1 containing the
initial invitees. That Add Commit has no group-message publication obligation because no pre-existing peer needs it.
The creator then attempts the independent per-invitee epoch-1 Welcome deliveries defined in
[publish-lifecycle.md](./publish-lifecycle.md).

## Ratchet tree source

Every Welcome delivery gives the joiner the group's ratchet tree from exactly one source:

- **inline**: the GroupInfo encrypted in the Welcome includes the `ratchet_tree` extension, and the delivery carries no
  ratchet tree reference; or
- **by reference**: the GroupInfo omits the `ratchet_tree` extension, and the delivery carries exactly one ratchet
  tree reference ([../features/ratchet-tree-reference.md](../features/ratchet-tree-reference.md)).

The inviter MUST use the inline source unless every KeyPackage the Commit adds advertises
`marmot.feature.ratchet_tree_reference.v1`. Marmot defines no other out-of-band tree distribution. A joiner MUST
reject a delivery that offers both sources or neither.

The reference never chooses group state. MLS Welcome processing binds whichever tree the joiner supplies to the
GroupInfo: it verifies the GroupInfo signature against the signer's leaf in that tree and the tree hash against the
GroupContext `tree_hash`.

## Delivery

The active transport binding owns the Welcome delivery envelope, recipient addressing, and transport-specific metadata
for a Welcome that consumes a published KeyPackage. A KeyPackage that was never published has no publication for a
binding to name, so the feature that hands it over owns its delivery: the device group's sibling Welcome
([../features/device-group.md](../features/device-group.md), "Sibling Welcomes"). Protocol core requires that the
receiver can recover the serialized MLSMessage whose wire format is `mls_welcome`, can identify which local
KeyPackage was consumed, and can recover the delivery's ratchet tree reference when it carries one.

Each delivery names exactly one consumed KeyPackage: a binding's delivery by the binding's reference to the
KeyPackage's publication, a sibling Welcome by the KeyPackage's `KeyPackageRef`. An inviter whose Commit added several
KeyPackages, including several of one account's
([../foundation/key-packages.md](../foundation/key-packages.md), "Selection and lifecycle"), MUST make one delivery for
each of them, so that every added device receives a delivery naming its own KeyPackage.

The Welcome in a delivery SHOULD contain only the `EncryptedGroupSecrets` entry for the KeyPackage the delivery names,
and MUST when the delivery carries a ratchet tree reference. Each entry is encrypted to its own KeyPackage with the
encrypted GroupInfo as context, not the list of entries (RFC 9420 §12.4.3.1), so a Welcome with one entry is complete
for its recipient, does not grow with the number of invitees, and does not show a recipient the other invitees'
KeyPackage references. A receiver MUST accept an inline Welcome with one entry or with several.

An account's devices can share delivery addressing, so a device can receive a delivery that names another device's
KeyPackage. That delivery fails step 2 of the receiving flow below for this device, but it is not a failed join: the
device leaves its own KeyPackage state unchanged and does not report a failed invite. It MUST NOT let such a delivery
prevent processing of a delivery that names its own KeyPackage.

The Welcome delivery envelope MUST NOT by itself choose group state. It supplies bytes and delivery evidence. MLS and
Marmot validation decide whether the receiver joins.

## Receiving flow

After unwrapping a Welcome, the receiver:

1. verifies that the Welcome is addressed to its account identity;
2. verifies that the referenced KeyPackage belongs to this account/device;
3. decodes the transport-carried content as an MLSMessage with `mls_welcome` wire format;
4. processes the MLS Welcome, taking the group's ratchet tree from its one source ("Ratchet tree source" above): the
   GroupInfo `ratchet_tree` extension, or the tree obtained and checked under the reference's fetch rules
   ([../features/ratchet-tree-reference.md](../features/ratchet-tree-reference.md), "Fetching and verification");
5. validates every resulting member identity and account identity proof;
6. identifies the Welcome author from the MLS GroupInfo signer leaf and validates that author's Marmot account identity;
7. validates the resulting Marmot group state and required components;
8. rejects the Welcome unless the author is authorized to add in the resulting group state: either the author is an
   active admin there, per the admin-policy component
   ([../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md)), or the author's account identity
   equals the receiver's own account identity and the resulting state requires `marmot.group.account-devices.v1`
   ([../app-components/account-devices-v1.md](../app-components/account-devices-v1.md));
9. checks whether the client already retains the resulting MLS group id; outside a separately verified repair or rejoin
   path, it rejects a match without modifying the existing state or the referenced KeyPackage material;
10. stores the group state and routing information;
11. rotates the consumed published KeyPackage when appropriate;
12. deletes consumed `init_key` material according to the KeyPackage lifecycle rules;
13. catches up on outstanding Commits as best it can;
14. performs a self-update as soon as practical.

Steps 4 through 9 are one tentative validation operation, which also runs any check a feature requires before a
Welcome is joined, such as a new device's check of the Welcome's group and sender under a confirmed device link
([../features/device-pairing.md](../features/device-pairing.md), "New device", step 5). The operation MUST NOT durably
create or replace group state, consume or rotate the referenced KeyPackage, or delete its `init_key` material unless
every one of its checks succeeds. If the MLS Welcome-processing operation consumes KeyPackage material before exposing
the resulting group id and state, the receiver MUST stage that mutation or provide equivalent rollback so rejection
restores the exact pre-processing KeyPackage state. Durable group storage and KeyPackage rotation begin only at steps 10
through 12.

Obtaining a referenced tree is part of that tentative operation. A tree that no locator serves is not a rejection: the
receiver keeps the delivery, leaves its KeyPackage state unchanged, and retries under the reference's failure rules
([../features/ratchet-tree-reference.md](../features/ratchet-tree-reference.md), "Failures"). A delivery's sender
authenticates the reference it carries, not the Welcome inside it, so every failure of the reference depends on the
delivery and rejects that delivery only ("Failure behavior").

A new member SHOULD perform the post-join self-update before sending application payloads when feasible, and SHOULD do
so promptly after joining. This carries forward the MIP-02 post-join rotation guidance; this spec keeps it as a
`SHOULD` because a member who never rotates is a forward-secrecy weakness for itself, not a correctness break for the
group. The concrete recommended completion window is operational, not interop-visible, so it lives in
[../implementation-model.md](../implementation-model.md) rather than here.

The group-id check in step 9 makes this receiving flow a first join for a locally unknown MLS group id. If the resulting
MLS group id matches a group copy the client already retains, the Welcome MUST NOT silently replace or merge into that
group's canonical state. The receiver rejects it through this flow without rotating or deleting the referenced
KeyPackage. Marmot v1 defines no in-place repair-by-Welcome procedure. To rejoin, the client first explicitly discards
the retained active cryptographic state, then processes a fresh valid Welcome through this first-join flow. It MAY
preserve local history and a removal tombstone outside the replaced active state.

## Welcome-bootstrap trust

The join-time authorization check (step 8 of the receiving flow) validates the Welcome author against the joined group
state itself: its admin set, or, when the author is the joiner's own account, its required-component list. In a forked
group both are author-controlled: an existing non-admin member can fork with a single commit that both adds the joiner
and rewrites the admin policy to list itself, and the check passes against the fork's own admin set. The check
therefore guarantees that the Welcome author is an admin of the group state the joiner received, or the joiner's own
account in a state that requires `marmot.group.account-devices.v1` — it does not prove that this group is the one the
joiner intended to join.

This version deliberately defines no in-band cryptographic anchor for first-contact group authenticity: every value a
first-time joiner can check arrives in the Welcome, and a forger authors all of it.

The first-contact trust root is therefore the Welcome author. A joiner MUST authenticate the Welcome author's account
identity — this is step 6 of the receiving flow — and a client SHOULD present that identity to the joining user
before or at join, so accepting an invite is an explicit decision about who the inviter is.

A Welcome whose author is the joiner's own account, accepted under
[../app-components/account-devices-v1.md](../app-components/account-devices-v1.md), adds no new forger. Whoever authors
it holds a leaf of the joiner's account or the account's signing key, and the signing key alone is already enough to
create a group in which the account is an admin and to add the joiner under the admin path. Presenting the author of
such a Welcome tells the user only that one of the account's own devices, or someone holding the account's key, decided
the join.

A client MAY treat a newly joined group as unverified until an MLS application message from an account other than the
Welcome author authenticates on the group's branch. That message proves only that the other account participated on
the received branch. It does not prove that the branch is the intended continuation: a forger can add genuine
KeyPackages to a fork, and a genuine re-added member can later speak on it. Any unverified-group presentation is
application-defined; this signal is an activity heuristic, not a group-authenticity proof.

## Failure behavior

If Welcome processing or any tentative validation through step 9 fails, the receiver MUST leave the referenced
KeyPackage and its `init_key` material exactly as they were before processing. The inviter MAY retry or choose another
KeyPackage.

A receiver MUST NOT let its refusal of one delivery stop it from processing another delivery of the same Welcome,
unless that other delivery would necessarily be refused the same way. Only a refusal that follows from the Welcome
message alone meets that condition. A refusal that depends on anything else, such as the delivery's sender or
timestamps, a ratchet tree reference it carries, or local state that can change, rejects only that delivery. Remembering
refusals per delivery always satisfies this rule. The rule covers refusals by the checks of the receiving flow. A user's
decision about the invitation itself, such as declining it after seeing its MLS-authenticated author, MAY apply to every
delivery of the same Welcome.

A receiver rejects the Welcome if:

- transport unwrapping fails;
- the Welcome is not addressed to the local account identity;
- the MLSMessage is not an MLS Welcome;
- the referenced KeyPackage is not local to this account/device;
- the delivery offers both ratchet tree sources or neither ("Ratchet tree source" above), or carries a reference with
  a Welcome of more than one `EncryptedGroupSecrets` entry;
- bytes that match a ratchet tree reference's hash fail its decryption, padding or decoding checks, or MLS does not
  accept the tree they carry ([../features/ratchet-tree-reference.md](../features/ratchet-tree-reference.md),
  "Failures");
- any resulting member leaf is missing a valid account identity proof;
- the Welcome author cannot be identified as a member leaf in the resulting group;
- the resulting group state lacks required Marmot state;
- the resulting MLS group id matches retained active cryptographic state;
- the Welcome author's MLS-authenticated account identity is not an active admin in the resulting group state (see
  [../app-components/admin-policy-v1.md](../app-components/admin-policy-v1.md)), and it is not the receiver's own
  account identity in a resulting state that requires `marmot.group.account-devices.v1` (see
  [../app-components/account-devices-v1.md](../app-components/account-devices-v1.md));
- the group requires a capability this client does not support.
