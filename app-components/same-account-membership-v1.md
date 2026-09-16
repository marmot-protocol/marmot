# marmot.same-account-membership.v1

Status: experimental.

This data-less component enables bounded same-account leaf admission and removal.

## Assignment

- Component id: `0x800d`
- Name: `marmot.same-account-membership.v1`
- GroupContext component data: none
- LeafNode component data: none
- KeyPackage component data: none
- GroupInfo component data: none
- AppEphemeral data: none
- SafeAAD data: none

Support and group enablement use the upstream `app_components` component. A supporting leaf lists `0x800d` in its
LeafNode `app_components` support list. An enabled group lists `0x800d` in its GroupContext `app_components` required
list. Component `0x800d` is a negotiated behavior marker and has no `AppDataDictionary` entry at any location. Any
`0x800d` component-data entry is invalid.

## Enablement

An active admin MAY enable `0x800d` only when every current leaf advertises support for it. Unsupported members MUST
NOT be removed automatically. Enablement follows the ordinary administrator-authorized GroupContext capability update
flow.

While enabled, every Commit MUST leave at most five current leaves for any one Marmot account identity. This is a
resulting-state invariant, including for administrator-authored Commits and Commits unrelated to membership.

An active admin MAY disable `0x800d` only when no account has more than one current leaf in the resulting state.
Disabling removes `0x800d` from the required `app_components` list. There is no component-data entry to remove.

## Commit authorization

When `0x800d` is required in the candidate parent, a current leaf MAY author either of these narrow Commit shapes
without being an active admin:

- **Same-account Add:** exactly one inline Add, no referenced proposal, no other proposal, and a normal UpdatePath. The
  added KeyPackage has a valid `marmot.member.account-identity-proof.v2`; its account identity equals the committer's;
  its KeyPackage and leaf signature key are distinct from every current leaf; and the resulting-state limit passes.
- **Same-account Remove:** one to four inline Remove proposals, no referenced proposal, no other proposal, and a normal
  UpdatePath. Every target is a current leaf of the committer's account, no target is the committer, and targets are
  distinct. Self-removal continues to use SelfRemove.

The same shapes are valid for an active admin, but an admin gains no broader same-account shape. Standalone Add and
Remove proposals are not authorized by this component. Both Commit shapes have ordinary convergence priority.

Existing members validate the Commit against its candidate parent. The joining member uses the locally approved
pairing intent and sponsor leaf binding defined in [multi-device.md](../features/multi-device.md); no `0x800d` data is
added to GroupInfo or another MLS object.

If the five-leaf limit is reached, a sponsor first removes stale sibling leaves and waits for that Remove Commit to
become canonical, then starts a separate Add with a fresh KeyPackage. The two operations MUST NOT be combined.

An active admin MAY use the ordinary admin removal path to remove orphaned leaves only when that account controls no
current leaf in the group. If an account has no surviving group leaf and the group has no active admin, v1 defines no
in-band recovery path.

## Trust model

The pairing sponsor is the joining device's trust root for the branch delivered by the Welcome. Existing members, not
the joiner, validate the Add-only Commit against its candidate parent. The sponsor-signed GroupInfo authenticates the
resulting branch but does not establish global finality or agreement by another account. Ordinary convergence decides
which branch survives.

## Migration

`0x800d` is the first version. A breaking change requires a new component id and document. Implementations of the
withdrawn External-Commit multi-device draft MUST NOT map its released identifiers or payloads to this component.
