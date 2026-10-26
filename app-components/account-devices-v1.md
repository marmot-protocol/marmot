# marmot.group.account-devices.v1

Status: draft.

`marmot.group.account-devices.v1` lets a member add and remove leaves of its own account in a group without admin
authority. A device can then add another device of the same account to a group it is in, or remove one, for example
when that device signs out. A group turns this on by requiring the component.

An account can have several leaves in one group, one for each of its devices there
([../foundation/identity.md](../foundation/identity.md), "Accounts and members"). The non-normative direction this
component serves is described in [../ideas/multi-device.md](../ideas/multi-device.md).

## Registry

- Component id: `0x800d`
- Name: `marmot.group.account-devices.v1`
- Location: none. The component carries no data. Its id appears only in `app_components` lists.
- Default requirement: required in new groups when every initial member supports it
  ([../protocol-core/group-setup.md](../protocol-core/group-setup.md)); existing groups can activate it ("Activation in
  an existing group" below)

## Data

The component has no data at any location. A client advertises support by listing `0x800d` in the `app_components`
support list of its KeyPackages and LeafNodes, as for any component ([README.md](./README.md), "Negotiation"). A group
requires the component by listing `0x800d` in the GroupContext `app_components` required list. In this document, a
state "requires" the component when that list contains `0x800d`.

A client MUST NOT create an `app_data_dictionary` entry with component id `0x800d` at any location (GroupContext,
LeafNode, KeyPackage, or GroupInfo), and MUST NOT create AppEphemeral or SafeAAD bytes for it. The component defines
none of them.

Receivers check this only in groups that require the component. Every leaf in such a state advertises the component, so
every member that continues in it applies the same check:

- A Commit whose resulting state requires `0x800d` is invalid if that state carries an entry with id `0x800d` in its
  GroupContext or in any member LeafNode.
- A Commit whose candidate parent state requires `0x800d` is invalid if it contains an AppDataUpdate targeting
  `0x800d`.

Before a group requires the component, a client that supports it treats such an entry, and an AppDataUpdate for it,
as it treats those of any unknown component ([README.md](./README.md), "Unknown Data"), so that its validity decisions
match those of members that do not support the component. If the GroupContext carries such an entry, the activation
Commit removes it with an AppDataUpdate `remove`; a leaf that carries one has to be replaced before activation.

## Same-account operations

In a Commit, with the committer's account identity taken from the credential of the committer's leaf in the candidate
parent state:

- a **same-account Add** is an Add proposal, carried by value, whose KeyPackage credential identity equals the
  committer's account identity;
- a **same-account Remove** is a Remove proposal, carried by value, that targets a current leaf other than the
  committer's own leaf whose credential identity equals the committer's account identity.

A same-account Add is an Add like any other in every other respect. Its KeyPackage MUST be compatible with the group
once the Commit is applied, as [../foundation/key-packages.md](../foundation/key-packages.md) ("Selection and
lifecycle") defines for inviters, and receivers check the group's requirements on it as on any Add.

Both are leaf operations. A same-account Remove never removes the account's last leaf, because the committer's own leaf
stays, so it never triggers the admin coupling rule in [admin-policy-v1.md](./admin-policy-v1.md) ("Active admins") and
never changes the account's admin status. A leaf added by a same-account Add has the account's standing: if the account
is an active admin, the new leaf acts as an admin too.

## Authorization

When the candidate parent state requires `0x800d`, any current member MAY commit same-account Adds and same-account
Removes, whether or not its account is an active admin. Authorization is evaluated against the candidate parent state
([README.md](./README.md), "Authorization Evaluation").

For a committer that is not an active admin in the candidate parent state, this component authorizes one Commit
shape, the **same-account Commit**: a Commit that contains at least one same-account Add or same-account Remove and no
other proposal. A same-account Commit MUST NOT contain AppDataUpdate, GroupContextExtensions, Update, SelfRemove, or
any other proposal, and MUST NOT reference any proposal by `ProposalRef`. Its UpdatePath, which replaces the
committer's own LeafNode, is allowed as in any Commit. This shape sits beside the self-update and SelfRemove-only
Commits that [../protocol-core/group-messaging.md](../protocol-core/group-messaging.md) ("Commit authorization") allows
a non-admin; it does not restrict them, and it is not combined with them.

An active admin keeps every power [admin-policy-v1.md](./admin-policy-v1.md) gives it. Its Commit MAY combine
same-account Adds and Removes with any other operation it is authorized to commit.

This component grants no standalone proposal authority: same-account operations exist only by value in the committer's
own Commit.

When the candidate parent state does not require `0x800d`, this component authorizes nothing, even in the Commit that
activates it.

A non-admin Commit that contains a same-account operation but does not have the same-account Commit shape is
`authorization_failed` ([../foundation/errors.md](../foundation/errors.md)). Breaking the leaf limit below is a
resulting-state failure, not an authorization failure.

### Branch priority

A same-account Commit is `ordinary` in branch selection, even when its committer is also an active admin, because the
same-account rule authorizes it without admin authority. A Commit that also contains anything else, including another
non-admin shape such as a referenced SelfRemove, is `privileged`, because only an active admin may commit it
([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate branches").

## Leaf limit

This component defines one constant. Other documents refer to it by name.

| Constant                 | Value |
| ------------------------ | ----- |
| `max_leaves_per_account` | `20`  |

While the resulting state requires `0x800d`, no account may have more than `max_leaves_per_account` current leaves in
the group. This is a resulting-state invariant: it is checked against the complete resulting state of every Commit,
whoever commits it and whatever it contains, including the activation Commit and Commits by active admins. A Commit
whose resulting state breaks it is invalid and creates no candidate edge
([../protocol-core/convergence.md](../protocol-core/convergence.md), "Candidate branches").

A client that wants to add a device to an account that already has `max_leaves_per_account` leaves removes one of that
account's leaves in the same Commit or an earlier one. Leaves on competing branches are never counted together: each
candidate branch is checked on its own states, and convergence selects one branch.

The value can be raised in a later version. Every member enforces it, so a client that still enforces the old value
would reject a Commit that only the higher value allows; a higher value therefore needs a new component id, not an
in-place edit of this document.

## Welcome acceptance

A joiner cannot see the candidate parent state. It checks the Welcome author against the resulting state instead:
[../protocol-core/joining.md](../protocol-core/joining.md) (receiving flow, step 8) accepts a Welcome whose author's
account identity equals the joiner's own account identity when the resulting state requires `0x800d`. The limits of
that resulting-state check are described in [../protocol-core/joining.md](../protocol-core/joining.md),
"Welcome-bootstrap trust."

Delivery does not change. The committer of a same-account Add delivers its Welcomes as any inviter does
([../protocol-core/joining.md](../protocol-core/joining.md), "Delivery"). The Nostr binding's Welcome names the
published KeyPackage event it consumed ([../transports/nostr.md](../transports/nostr.md), "Welcome delivery"), so on
that binding a same-account Add uses a published KeyPackage. This document defines no delivery for a KeyPackage that
was never published.

## Sender rules

The rules in this section bind the committer of a same-account Add or Remove in a group that requires the component,
including a committer whose account is an active admin. A receiver cannot check where a KeyPackage came from, why a
leaf was removed, or why a requirement changed, so a receiver MUST NOT reject a Commit or a Welcome for breaking them. The validation rules above are
the only receiver checks this component adds.

- A client MUST NOT commit a same-account Add unless it has authenticated the KeyPackage as belonging to a device of its
  account that its user approved. A valid credential and account identity proof naming the account do not authenticate
  a device, and neither does publication under the account's key: anyone who holds the account's signing key can
  produce both. This document does not define how a client authenticates a device's KeyPackage. A client that has no
  such authentication does not commit same-account Adds.
- A committer MUST NOT drop or leave out a group requirement so that a device's KeyPackage qualifies for a
  same-account Add. A device that does not support what the group requires is not added until it does.
- The founding Add Commit of a new group is exempt from the first rule above. Its creator MAY add KeyPackages of its own
  account under the ordinary selection rules ([../foundation/key-packages.md](../foundation/key-packages.md)), as any
  inviter adds another account's. A KeyPackage published by someone holding the account's key can then join the new
  group, which is the risk every inviter of a new group already accepts; the rule above protects groups that already
  have members and history.
- A client SHOULD commit a same-account Remove only to carry out its user's decision to remove that device, or a request
  from the device being removed, such as signing out
  ([../protocol-core/member-departure.md](../protocol-core/member-departure.md), "Removal by another device of the same
  account").
- Before committing same-account operations without admin authority, a client checks that the current canonical state
  requires `0x800d`. Before any Commit in such a group, it checks that the resulting state stays within the leaf limit.

## Activation in an existing group

A group that predates this component activates it through the process in [README.md](./README.md) ("Enabling a
Component in an Existing Group"):

- There is no initial state. The activation Commit adds `0x800d` to the GroupContext `app_components` required list and
  installs no `app_data_dictionary` entry.
- Only an active admin MAY commit the activation, because it changes the required-component list
  ([admin-policy-v1.md](./admin-policy-v1.md), "Admin-Gated Actions").
- The activation Commit is valid only when every leaf in its resulting state advertises `0x800d` and the resulting state
  satisfies the leaf limit.
- Same-account authority starts with the Commit after activation, because authorization reads the candidate parent
  state. The activation Commit can still add the admin's own devices under the admin's ordinary authority.

Activation is an explicit decision. A client activates the component only when its user asks; this document does not
ask clients to activate it on their own.

## Removal

Once a group requires this component, it MUST keep requiring it for the rest of the group's lifetime. A Commit whose
candidate parent state requires `0x800d` and whose resulting state does not is invalid. No member, including an active
admin, is authorized to commit one. Such a group has no dictionary entry to remove, and an AppDataUpdate `remove`
targeting `0x800d` in it is invalid ("Data" above).

The candidate parent state decides whether same-account operations are authorized. The resulting state decides whether
the leaf limit applies and whether a joiner accepts a same-account Welcome. Because the requirement can never be
dropped, every client resolves branches that diverged across the activating Commit the same way.

## Security considerations

- Any device of an account can add a KeyPackage of that account to every group it is in, up to the leaf limit, and
  remove the account's other devices from those groups. A stolen device that is still a member can do the same. The
  sender rules cannot be enforced by other members.
- No device outranks another device of its account. If two devices of one account commit competing same-account Commits
  from the same parent, for example each removing the other, both are `ordinary` with the same `tip_committer`, so an
  otherwise tied race falls to `tip_digest`, which a committer can influence. An admin account gains nothing here
  either, because each of its devices is an admin.
- The component does not let a device act for another account. Adds and Removes of other accounts still need an active
  admin.
- Other members see every leaf of an account, so same-account Adds and Removes show them when an account's devices
  change.

## Migration

This is the first version. Groups that do not require it remain valid, and in them adding or removing a leaf of one's
own account follows the ordinary admin rules. A breaking change gets a new component id and document.
