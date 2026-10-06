# marmot.group.invite-links.v1

Status: proposed; not adopted. The allocations below are draft allocations for review.

## Registry and presence

- Component id: `0x800e`.
- Name: `marmot.group.invite-links.v1`.
- Location: GroupContext `app_data_dictionary` only.
- Optional feature; not required by baseline Marmot.

Enabling the feature MUST add this component and require its id in `app_components` in the same authorized Commit.
Every resulting member MUST advertise support. Existing groups without it have no enabled invite links.
This v1 feature may be enabled only in ciphersuite `0x0001` groups with an MLS group id of one through 255 bytes;
a resulting state with this component outside those bounds is invalid.
An unsupported required component fails normal capability negotiation; implementations MUST NOT silently omit it.
This component defines no LeafNode, KeyPackage, GroupInfo, AppEphemeral, or SafeAAD data.
Its [request records](../foundation/invite-link-records.md) use the draft-10 Safe Application Interface for
component-scoped signing with the originating leaf key; that does not require SafeAAD negotiation.

## State bytes

Use the [Marmot binary profile](../foundation/canonical-encoding.md), including shortest QUIC vector lengths.

```text
struct {
  opaque link_id[32];
  opaque inbox_pubkey[32];
  opaque bearer_hash[32];
  opaque preview_hash[32];
  uint64 expires_at;
  uint8 approval_mode;
} InviteLinkV1;

struct {
  InviteLinkV1 links<0..1096>;
} InviteLinksV1;
```

Each entry is 137 bytes. There are at most eight entries, sorted by `link_id` bytes with no duplicates.
`link_id` is a fresh independently random identifier for one immutable invitation generation. It is not a group id,
account identity, device identity, or a derivation of any of them. `inbox_pubkey` is a valid x-only secp256k1 public key
for a fresh independently generated inbox key, unique among this component's entries.
The hashes are SHA-256 outputs. `bearer_hash = SHA-256(bearer)` for the invitation's independently random 32-byte
bearer. `preview_hash` hashes the exact plaintext specified in the
[Nostr preview binding](../transports/nostr-invite-links.md#preview-descriptor).
No private key, bearer, preview key, relay hint, or requester identity is stored in this component.

`expires_at` is zero for no expiry or a Unix time in seconds in `1..9007199254740991`.
`approval_mode` is zero for manual approval or one for automatic admission. Other values are invalid.
A component decoder MUST consume the whole input and reject malformed keys, bad vector lengths, duplicates,
unsorted entries, invalid values, and trailing bytes without repairing them.

## Updates, authorization, and removal

AppDataUpdate bytes are exactly a full `InviteLinksV1` replacement, without a generic payload version field.
Standalone proposal and Commit authorization follow
[candidate-state and candidate-parent authorization](README.md#authorization-evaluation): only an active admin may
propose or commit the change. Inline AppDataUpdate is the default. A control message does not mutate this state.
An empty replacement disables all links while retaining feature negotiation.

For an id present in both parent and resulting state, its complete entry MUST be byte-identical. Changing mode,
preview, bearer, inbox, or expiry creates a fresh id and inbox. This prevents a copied code from silently acquiring
different semantics. A removed id is revoked. The secret-distribution flow MUST NOT reuse a retired id or inbox.

For a nonterminal resulting group, if the Commit demotes any candidate-parent active-admin account or contains a
resolved Remove of an active-admin leaf (even if another leaf of that account remains), none of the parent's link ids
or inbox keys may remain in the resulting component. An admin who kept an inbox key can still read old ciphertext;
rotation protects requests sent with the new codes. Holders of an old code may still disclose their account and
package to a former admin who retains its inbox key, even if the new group policy rejects the request.
Promoting an admin does not require rotating links.

If the Commit demotes its own committer's account, the resulting invite-links vector MUST be empty. The departing
committer MUST NOT create replacement generations while stepping down. A remaining admin creates fresh links in a
later authorized Commit and distributes secrets only to the resulting current admins. The demoted device MUST stop
using and delete cached invitation secrets after any required handoff; deletion cannot erase ciphertext or copies
already retained elsewhere.

The adopted [member-departure flow](../protocol-core/member-departure.md) is unchanged: an active admin cannot send
SelfRemove. It first completes an admin-policy demotion with at least one other active admin remaining. That
admin-authorized demotion Commit retires the old invitation generations. A subsequent non-admin SelfRemove-only
Commit does not change this component or trigger rotation. The last admin first promotes a successor; enabling
this feature adds no new departure exception or extra Commit. When links are nonempty, the demotion Commit
also carries the invite-links AppDataUpdate that retires them.

Fresh-id/key generation and never reusing retired values are producer obligations. The current component cannot
prove a complete history of retired ids at a first join or after history expiry; reintroducing an old entry is not a
history-dependent Commit rejection. Honest admins MUST NOT reintroduce it. A client that retains selected-history
evidence of its retirement MUST NOT reopen revoked requests or automatically admit new requests under that id if it
reappears. Treat it as a retired invitation needing a fresh generation, without altering MLS branch selection.
Revocation's future privacy depends on current admins following the fresh-key rule; a malicious current admin can
always disclose new material too.

These invariants are checked against the complete resulting state, independently of proposal order.
Clock time MUST NOT affect component-update validity or convergence. Expiry is an admission gate specified by the
[feature flow](../features/group-invite-links.md#expiry-revocation-and-withdrawal), not an automatic state mutation.

Once enabled, the component MUST remain present and required. An AppDataUpdate remove operation is invalid.
Disbanding follows the adopted lifecycle's restricted Commit shape: this component MUST NOT be modified in that
Commit, and retained entries are inert once the group is disbanded.

## Versioning and migration

This is the first proposed component version. No earlier invite-code bytes are interoperable with it.
Breaking state, authorization, or update changes require a new component id and document.
Group activation follows normal required-capability updates and publish-before-apply; enabling links does not grant
any membership. Link ids are not assigned a new meaning when a group is recreated.

## Conformance cases

Accept an empty vector and one correctly encoded entry. Reject nine entries, duplicate ids, duplicate inboxes,
longer-than-minimal lengths, invalid keys, trailing bytes, and a changed entry under an existing id.
Reject a non-admin update and an admin-removal Commit that retains an old invitation generation.
Reject an active admin's SelfRemove under the adopted sender check. Accept demotion with retirement followed by a
non-admin SelfRemove-only Commit that leaves this component unchanged. A sole admin must promote a successor first.
Reject a self-demotion Commit that adds replacement links, even when
another admin remains. Accept a later fresh-generation Commit from an admin who stays.
Do not reopen revoked requests if an authorized malicious admin reintroduces a known retired generation.
Accept disabling links through an empty replacement. Reject component removal after enablement.
Accept a structurally valid expired entry during replay; reject automatic admission using it under the feature gate.
