# Welcomes

Status: adopted.

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

The GroupInfo encrypted in every Marmot Welcome MUST include the `ratchet_tree` extension. Marmot does not support
out-of-band ratchet tree distribution for the Welcome join path. A joiner MUST reject a Welcome whose GroupInfo does
not carry the ratchet tree.

## Delivery

The active transport binding owns the Welcome delivery envelope, recipient addressing, and transport-specific metadata.
Protocol core requires that the receiver can recover the serialized MLSMessage whose wire format is `mls_welcome` and
can identify which local KeyPackage was consumed.

The Welcome delivery envelope MUST NOT by itself choose group state. It supplies bytes and delivery evidence. MLS and
Marmot validation decide whether the receiver joins.

## Receiving flow

After unwrapping a Welcome, the receiver:

1. verifies that the Welcome is addressed to its account identity;
2. verifies that the referenced KeyPackage belongs to this account/device;
3. decodes the transport-carried content as an MLSMessage with `mls_welcome` wire format;
4. processes the MLS Welcome, taking the group's ratchet tree from the GroupInfo `ratchet_tree` extension;
5. validates every resulting member identity and account identity proof;
6. identifies the Welcome author from the MLS GroupInfo signer leaf and validates that author's Marmot account identity;
7. validates the resulting Marmot group state and required components;
8. authorizes the Welcome through exactly one path: when its KeyPackageRef matches an active approved same-account
   intent, the pairing-intent and exact-sponsor-leaf checks in [multi-device.md](../features/multi-device.md) are
   mandatory even if the sponsor is an active admin; otherwise the ordinary active-admin check in
   [admin-policy-v1.md](../app-components/admin-policy-v1.md) applies;
9. checks whether the client already retains the resulting MLS group id; outside a separately verified repair or rejoin
   path, it rejects a match without modifying the existing state or the referenced KeyPackage material;
10. stores the group state and routing information;
11. rotates the consumed published KeyPackage when appropriate;
12. deletes consumed `init_key` material according to the KeyPackage lifecycle rules;
13. sends any feature-required first post-join acknowledgement;
14. catches up on outstanding Commits as best it can; and
15. performs a self-update as soon as practical.

Steps 4 through 9 are one tentative validation operation. They MUST NOT durably create or replace group state, consume
or rotate the referenced KeyPackage, or delete its `init_key` material unless every check through step 9 succeeds. If
the MLS Welcome-processing operation consumes KeyPackage material before exposing the resulting group id and state,
the receiver MUST stage that mutation or provide equivalent rollback so rejection restores the exact pre-processing
KeyPackage state. Durable group storage and KeyPackage rotation begin only at steps 10 through 12.

A new member SHOULD perform the post-join self-update before sending application payloads when feasible, except that a
feature MAY require one authenticated acknowledgement from the original added leaf first. It SHOULD then update
promptly. This carries forward the MIP-02 post-join rotation guidance; this spec keeps it as a
`SHOULD` because a member who never rotates is a forward-secrecy weakness for itself, not a correctness break for the
group. The concrete recommended completion window is operational, not interop-visible, so it lives in
[../implementation-model.md](../implementation-model.md) rather than here.

The group-id check in step 9 makes this receiving flow a first join for a locally unknown MLS group id. If the resulting
MLS group id matches a group copy the client already retains, the Welcome MUST NOT silently replace or merge into that
group's canonical state. The receiver rejects it through this flow without rotating or deleting the referenced
KeyPackage. Marmot v1 defines no in-place repair-by-Welcome procedure. To rejoin, the client first explicitly discards
the retained active cryptographic state, then processes a fresh valid Welcome through this first-join flow. It MAY
preserve local history and a removal tombstone outside the replaced active state.

Before the group-id rejection and before MLS Welcome processing, a receiver MAY recognize a duplicate same-account
Welcome by its plaintext KeyPackageRef and the durable enrollment record defined in
[multi-device.md](../features/multi-device.md). An exact serialized-Welcome digest match republishes the feature
acknowledgement without consuming `init_key` material or modifying group state. This is duplicate recovery, not an
in-place repair or rejoin. A mismatch, absent record, discarded group, or removed enrollment never recreates state.

## Welcome-bootstrap trust

The ordinary join-time authorization check validates the Welcome author against the admin set of the joined group
state itself. In a forked group that admin set is author-controlled: an existing non-admin member can
fork with a single commit that both adds the joiner and rewrites the admin policy to list itself, and the check passes
against the fork's own admin set. The check therefore guarantees that the Welcome author is an admin of the group state
the joiner received — it does not prove that this group is the one the joiner intended to join.

This version deliberately defines no in-band cryptographic anchor for first-contact group authenticity: every value a
first-time joiner can check arrives in the Welcome, and a forger authors all of it.

The first-contact trust root is therefore the Welcome author. A joiner MUST authenticate the Welcome author's account
identity — this is step 6 of the receiving flow — and a client SHOULD present that identity to the joining user
before or at join, so accepting an invite is an explicit decision about who the inviter is.

For same-account enrollment, the interactively paired sponsor is the trust root. The approved intent binds its exact
MLS leaf signature key, group id, and fresh KeyPackageRef; the sponsor-signed GroupInfo authenticates the resulting
branch. It does not independently prove the candidate parent, Add-only Commit shape, or global finality. Existing
members validate the Commit, and a compromised sponsor can lie about the branch it delivers.

A client MAY treat a newly joined group as unverified until an MLS application message from an account other than the
Welcome author authenticates on the group's branch. That message proves only that the other account participated on
the received branch. It does not prove that the branch is the intended continuation: a forger can add genuine
KeyPackages to a fork, and a genuine re-added member can later speak on it. Any unverified-group presentation is
application-defined; this signal is an activity heuristic, not a group-authenticity proof.

## Failure behavior

If Welcome processing or any tentative validation through step 9 fails, the receiver MUST leave the referenced
KeyPackage and its `init_key` material exactly as they were before processing. The inviter MAY retry or choose another
KeyPackage.

A receiver rejects the Welcome if:

- transport unwrapping fails;
- the Welcome is not addressed to the local account identity;
- the MLSMessage is not an MLS Welcome;
- the referenced KeyPackage is not local to this account/device;
- the GroupInfo does not include the `ratchet_tree` extension;
- any resulting member leaf is missing a valid account identity proof;
- the Welcome author cannot be identified as a member leaf in the resulting group;
- the resulting group state lacks required Marmot state;
- the resulting MLS group id matches retained active cryptographic state;
- neither the ordinary active-admin path nor an enabled component's exact alternate join-time authorization succeeds;
- the group requires a capability this client does not support.
