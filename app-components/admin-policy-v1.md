# marmot.group.admin-policy.v1

Status: adopted.

## Registry

- Component id: `0x8003`
- Name: `marmot.group.admin-policy.v1`
- Location: GroupContext `app_data_dictionary`
- Default requirement: required for every Marmot group

## State

```text
struct {
  opaque xonly_pubkey[32];
} MarmotAdminKeyV1;

struct {
  MarmotAdminKeyV1 admins<V>;
} MarmotAdminPolicyV1;
```

`admins` is a sorted list of unique 32-byte x-only secp256k1 public keys.

Each admin key is a Marmot account identity: the same raw 32-byte x-only Nostr public key carried as a member's MLS
`BasicCredential` identity (see [../foundation/identity.md](../foundation/identity.md)). It is not a separate
authorization key.

## Active admins

An account is an active admin when its key is in `admins` and the account has at least one current member leaf in the
group. Admin authority is evaluated by matching a member's MLS-authenticated account identity against the active
admins; a multi-device account shares one admin entry across all of its leaves. Every Marmot document that authorizes
an action against the admin policy uses this term with this definition.

A commit that removes an account's last member leaf MUST also remove that account's key from `admins` in the same
commit. An admin-policy state that lists an account with no member leaf is invalid in the resulting epoch, so in valid
group state every key in `admins` names an active admin.

This coupling rule and the SelfRemove flow below are two different departure paths, not two orderings of one
transition. The coupling rule binds commits that remove a listed account's last leaf — for example, an admin removing
another listed account's last device with a Remove proposal. SelfRemove never triggers the coupling rule: a SelfRemove
proposal whose sender is still an active admin is invalid at the sender check, so a departing admin's admin-policy
update always lands in an earlier commit, and the account is no longer listed in `admins` by the time its SelfRemove
commits.

## Update

The update payload is a full replacement state:

```text
MarmotAdminPolicyV1 MarmotAdminPolicyUpdateV1;
```

## Validation

An admin policy state is valid if:

- the component entry is present in the resulting epoch's `app_data_dictionary`
- component id `0x8003` is present in the resulting epoch's GroupContext `app_components` required-component list
- every admin key is exactly 32 bytes
- the admin list is sorted lexicographically by key bytes
- the admin list has no duplicates
- the admin list is not empty
- every admin key corresponds to an account with at least one member leaf in the resulting epoch's group state

v1 sets no smaller independent admin-count ceiling: every distinct current account may legitimately be an admin, and
the uniqueness and membership checks bound the list by the resulting group's distinct account count.

The last check is cross-component: it validates this component against the resulting epoch's member leaves rather than
against the component bytes alone. Commit validity already spans components, so a commit whose resulting epoch lists an
admin key with no member leaf is invalid.

The required-component and membership checks are properties of the resulting epoch, not only of commits that carry
admin-policy bytes. They run on every Commit, including one that changes `app_components`, the member leaf set, or this
component's state. When a Commit carries no admin-policy update, the resulting epoch's admin set is the candidate parent
state's admin set carried forward, and the checks are evaluated against that carried-forward set. A Commit that omits
`0x8003` from resulting `app_components`, removes the dictionary entry, or removes a listed account's last member leaf
without also updating this component is invalid whether or not it re-serializes this component's bytes.

## Authorization

Only an active admin MAY send a standalone admin policy update proposal.

Only an active admin MAY commit an admin policy update.

Commit authorization, including removal authorization, follows the shared candidate-parent rule in
[README.md](./README.md) ("Authorization Evaluation"). An update that removes the committer from `admins` is valid only
if at least one other active admin remains.

## Admin-Gated Actions

Every v1 group-level Marmot component update requires an active admin to commit unless the owning component document
explicitly defines a looser rule. No v1 group-level component currently defines one. This rule follows the component
class rather than an enumerated list, so adding a registered component does not silently make its updates ungoverned.

The following non-component operations also require an active admin to commit:

- invite a new member;
- remove another member;
- change the GroupContext `app_components` list of required Marmot components; and
- change the GroupContext `required_capabilities` extension through an MLS `GroupContextExtensions` proposal.

The experimental [`marmot.same-account-membership.v1`](./same-account-membership-v1.md) component is the narrow
exception for its exactly-one-Add and one-to-four-sibling-Remove Commit shapes. Its rules apply equally to admins and
non-admins when `0x800d` is required. It authorizes neither standalone proposals nor mixed Commit shapes.

Existing members authorize an Add Commit against its candidate parent state. A Welcome receiver cannot perform that
same parent-state check; it instead applies the distinct join-time resulting-state check defined in
[../protocol-core/joining.md](../protocol-core/joining.md). The receiver identifies the inviter from the MLS GroupInfo
signer leaf and rejects the Welcome unless that leaf's MLS-authenticated Marmot account identity is an active admin in
the joined group state. This component is the default membership-add authority for v1 groups. A Welcome receiver
rejects another authority unless an enabled component explicitly defines a separate join-time check; experimental
component `0x800d` defines that check for same-account admission. The resulting-state check's trust model is described
in [../protocol-core/joining.md](../protocol-core/joining.md), "Welcome-bootstrap trust."

SelfRemove is special:

- a non-admin member MAY self-remove
- a SelfRemove proposal whose sender is an active admin in its authenticated source-epoch state is invalid
- a departing admin first commits an admin-policy update that removes it from `admins` (valid only if at least one
  other active admin remains), then uses SelfRemove
- any remaining authorized member MAY commit a SelfRemove proposal
- the committer of a SelfRemove proposal MUST NOT be the leaving member

[../protocol-core/member-departure.md](../protocol-core/member-departure.md) owns the full SelfRemove flow.

## Removal

This component is the sole admin authority for v1 groups and MUST remain present and required for the lifetime of a
Marmot group. An AppDataUpdate `remove` operation targeting this component is invalid, so no member, including an
active admin, is authorized to commit one. Deleting or abandoning a local group is not a component removal and does not
require a group-state commit.

The terminal disband Commit defined by
[group-lifecycle-v1.md](./group-lifecycle-v1.md) is the only coupled operation
that may remove every other admin/member at once. Its resulting admin list MUST
contain exactly the authenticated committer's account so the final mechanical
MLS state still satisfies the nonempty-admin and admin/leaf invariants before
live MLS state is deleted.

If every active admin loses access to all of its signing devices or keys, v1 has no in-band succession, override, or
automatic-promotion mechanism. The group remains cryptographically valid, and ordinary application messages and
non-admin SelfRemove may continue, but admin-gated membership and settings changes are permanently frozen. Members must
create a new group to recover governance; local or out-of-band policy MUST NOT elevate another account inside the frozen
group.

## Migration

This component carries the `admin_pubkeys` field from the MIP-01 `marmot_group_data` extension (see
[../mip-coverage.md](../mip-coverage.md)). v1 is the first versioned form; a breaking change gets a new component id and
file.
