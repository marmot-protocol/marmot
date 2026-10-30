# Group permissions

Status: non-normative proposal.

Admins could choose who can add members, change the disappearing-message timer, and edit the group's name, description,
or image. Each action category would have its own **Admins only** / **All members** selector. These choices would be
shared, authenticated group policy, so every client would enforce the same permissions.

This proposal explores that behavior. It does not change the adopted protocol or define interoperable wire formats.
The versioning and join-authentication questions below need to be settled before implementation.

## Three independent settings

| Setting | Actions covered | Choices |
| --- | --- | --- |
| Add members | Invite another account through an authorized MLS Add and Welcome | Admins only / All members |
| Disappearing messages | Set, change, or disable the timer for new messages | Admins only / All members |
| Group metadata | Change the name, description, or image | Admins only / All members |

The proposed initial value for each setting is **Admins only**, preserving existing authorization unless the creating
admin explicitly chooses otherwise. An admin could change each setting independently later. For example, a group could
allow everyone to change the timer and metadata while keeping invitations admin-only.

**All members** means current MLS-authenticated member accounts, including admins. It does not include removed accounts,
pending invitees, holders of invite links, or outside request senders. Admin status remains account-scoped across devices,
as described in [admin-policy-v1.md](../app-components/admin-policy-v1.md).

Admins would remain able to perform each of the three actions. Only admins would change these permission settings or
promote and demote admins. Permission to add a member would not include permission to promote that member.

The metadata selector covers the name and description from
[group-profile-v1.md](../app-components/group-profile-v1.md), and group image references currently described in
[group-avatar-url-v1.md](../app-components/group-avatar-url-v1.md) and
[group-blossom-image-v1.md](../app-components/group-blossom-image-v1.md). It does not grant control over media encryption
policy, relay routing, required capabilities, or arbitrary future components.

Removing another member, disbanding the group, changing security policy, and changing required components would remain
admin-only. Existing self-update and self-removal behavior would remain governed by their own protocol rules. No fourth
permission selector or custom roles are proposed here.

## User flows

An admin opens group permissions and sets **Disappearing messages: All members**. After that policy change takes effect,
a member can set or disable the timer directly, without an admin approving each change. The timer still follows the
source-epoch semantics in [message-retention-v1.md](../app-components/message-retention-v1.md): a new value affects new
messages, rather than retroactively expiring or extending existing messages.

An admin sets **Group metadata: All members**. A member can then change the group image without becoming an admin.
Changing the image is not an opportunity to overwrite the group's timer, permissions, or unrelated metadata.

An admin sets **Add members: All members**. A current member can invite another account using its valid KeyPackage.
Identity proofs, capability support, Welcome delivery, and publish-before-apply behavior still matter. Making an Add
available to members does not bypass those requirements or give an outsider a way to admit itself.

An admin later restores **Add members: Admins only**. A member's uncommitted invitation no longer has authority on a
branch whose parent state contains the restricted setting. Permission changes do not remove previously admitted members.

## Authorization concerns for the eventual specification

The permission decision would come from the authenticated candidate parent state, following the existing separation in
[app-components/README.md](../app-components/README.md#authorization-evaluation). A change to the settings cannot grant
its own sender authority for other actions in that same transition. A non-admin setting its own invitation permission
and adding someone in one Commit would not be an intended valid flow.

The eventual specification needs to cover both proposal senders and committers. A permissive setting would allow an
eligible member to act directly, rather than merely send a standalone proposal that still requires an admin committer.
Changes carried together would each need the appropriate authority; permission for one category would not authorize a
bundled role, removal, routing, or security change.

Pending proposals and stale edits need explicit treatment when policies or membership change. The owning documents would
retain proposal-source-epoch checks, current candidate-parent commit authorization, and atomic rejection of a transition
containing an unauthorized action. Full replacement of a component also needs to preserve unrelated values when a user
intends to edit a single field; concurrent edits remain subject to the existing
[convergence rules](../protocol-core/convergence.md), rather than local UI or arrival order.

## Relationship to invitations and change requests

The [private group invite proposal](https://github.com/marmot-protocol/marmot/pull/429) covers link records, requests,
approval modes, and delivery of Welcomes. This proposal answers a separate question: which current members may perform
the underlying membership Add?

A member with **Add members: All members** could make a direct invitation. That permission would not automatically give
it access to admin-only link secrets or inboxes, or authority to create, rotate, revoke, or administer links. Under the
invite proposal's current design, automatic link admission still needs an authorized admin client. A link recipient is
not already a member and gains no Add authority merely by possessing the link.

Member-operated admission from links would therefore need a separate, explicit amendment to the invite proposal's
secret distribution and processing roles. The permission selector alone does not enable it. Restricting future Adds
also does not, by itself, revoke an existing link generation; link lifecycle stays with its owning feature.

The [member change-request proposal](https://github.com/marmot-protocol/marmot/pull/432) remains useful when an action is
admin-only. A member can request an invitation, timer change, or metadata change and an admin can decide. With an
all-members setting, direct action would be available instead. Requests and receipts would not themselves grant authority
or change group state. This proposal does not alter either pending pull request.

## Compatibility and owning surfaces

Current [admin-policy-v1.md](../app-components/admin-policy-v1.md) and the affected component documents require admins
for these actions. [group-messaging.md](../protocol-core/group-messaging.md) also restricts non-admin commits, and
[joining.md](../protocol-core/joining.md) requires a Welcome's GroupInfo signer to be an admin. A local setting cannot
safely loosen those rules while claiming current-profile compatibility.

The proposed policy would live in authenticated GroupContext component state. Because authorization is changing, its
normative form needs new component identities and explicit required-capability negotiation, following the breaking-change
rules in [app-components/README.md](../app-components/README.md#component-ids). An optional component silently overriding
v1 authorization would let older clients disagree about valid commits. Clients without the required new capabilities
would be unable to join groups using the new model.

Before adoption, the owning surfaces would need to define:

- **App components:** the policy bytes, selectors, admin list relationship, exact scope of each operation, proposal and
  commit authorization, and versioned successors for affected authorization surfaces.
- **Protocol core:** member-authored commits, Add and Welcome authorization, policy transitions, and migration from
  existing groups without reinterpreting v1 bytes.
- **Foundation:** capability negotiation, registered identifiers, and conformance cases for the agreed versions.
- **Features:** the permission controls and their interaction with invite links and change requests, referencing the
  owning rules rather than redefining them.

Existing groups would retain their existing authorization until an authorized, capability-compatible migration.
Removing policy state would not be a way to turn restricted permissions into all-members access. The migration needs
one unambiguous active authority model, including when legacy and successor components are encountered together.

## MDK and client responsibilities

Clients would expose the three settings, present the current permissions, and choose explicit initial settings when
creating a group. Shared protocol handling, storage, authorization, and validation would belong in MDK so that a hidden
UI control cannot be bypassed by another client. This PR proposes behavior; it adds no MDK or client implementation.

How a client chooses its founding admin accounts is a separate product decision. This proposal defines no special
admin defaults for DMs and no rule that converts a DM into a separate group when someone is added.

## Questions before normative adoption

- Which new component versions carry the permissions and each affected authorization surface, and how does an existing
  group migrate while keeping all current members capability-compatible?
- How does a joiner recognize an authorized non-admin Welcome signer under the new model? The current
  [Welcome-bootstrap trust limits](../protocol-core/joining.md#welcome-bootstrap-trust) still apply: state in a Welcome
  does not independently prove that the joiner received the intended group's branch.
- Does adding another device to an existing account use the same Add selector, or stay with a separately negotiated
  multi-device authorization flow? The selector's initial scope here is inviting another account.

## Review scenarios for the eventual specification

Useful acceptance cases include an ordinary member changing each category independently when enabled; an admin changing
any of them; and a member being unable to change the selectors or admin list. Review also needs to cover disabling a
timer, image removal, unrelated-field preservation, mixed authorized and unauthorized changes, pending actions after a
restriction or removal, and unsupported clients refusing the new profile.

Invitation cases include an authorized non-admin Add and Welcome, an outsider trying to self-admit, and member Add
permission without invite-link administration authority. Compatibility cases include unchanged legacy groups, migration
with an unsupported member, conflicting authority components, and policy removal. These are review targets, not completed
implementation or interoperability tests.
