# marmot.group.view-once.v1

Status: adopted.

## Registry

- Component id: `0x8010`
- Name: `marmot.group.view-once.v1`
- Location: none. The component carries no data at any location.
- Default requirement: optional, activated only by an explicit user decision
- Owning feature: [view-once-v1.md](../features/view-once-v1.md)

## Data

Support is advertised by listing `0x8010` in the KeyPackage and LeafNode `app_components` support lists. A group
activates the feature by listing `0x8010` in its GroupContext `app_components` required list. An empty component entry
is not a support or activation marker.

This component defines no GroupContext, LeafNode, KeyPackage, or GroupInfo entry bytes, no AppDataUpdate payload, and
no AppEphemeral or SafeAAD bytes. A producer MUST NOT emit any of them under `0x8010`, even with empty data, except
for the pre-activation GroupContext removal operation specified below.

When the resulting group requires `0x8010`, no entry under that id is permitted in:

- its resulting GroupContext;
- any resulting member LeafNode, including the Welcome ratchet tree;
- the KeyPackage-level dictionary of any KeyPackage added by a Commit or the joiner's own KeyPackage consumed by a Welcome;
- a GroupInfo being accepted with a Welcome.

Every admission path MUST enforce the applicable checks: group creation, Commit validation, and Welcome acceptance.
A joiner checks both its resulting GroupContext and its consumed KeyPackage, not only GroupInfo and tree leaves.
Receivers also enforce these transition rules:

- A Commit whose candidate parent requires `0x8010` is invalid if it contains an AppDataUpdate targeting `0x8010`.
- A Commit whose candidate parent or resulting state requires `0x8010` is invalid if it contains AppEphemeral data
  under that id. The same parent-or-resulting predicate applies to a SafeAAD contribution under that id.

When neither the candidate parent nor the resulting state requires `0x8010`, receivers MUST treat its entries,
AppDataUpdate operations, AppEphemeral data, and SafeAAD contributions exactly as for an unknown non-required
component, irrespective of local support. This includes opaque adds, updates, and removes, subject to the same generic
proposal-shape and authorization rules. No feature-specific payload decoder or no-data rejection applies on that path.
The [unknown-data preservation rule](README.md#unknown-data) still applies to unrelated opaque bytes.

For an MLS application message, receivers check SafeAAD against that message's source epoch. A contribution under
`0x8010` is invalid if that epoch requires this component. Otherwise, receivers apply the unknown non-required
component rules irrespective of local support.

An activation Commit has a non-requiring parent and a requiring result. It MUST reject AppEphemeral and SafeAAD
contributions under `0x8010`. Its only permitted AppDataUpdate under that id is `remove` of an entry present in the
candidate parent's GroupContext; it MUST perform that removal if the entry exists. Every other operation under this
id is invalid in that Commit. The resulting GroupContext and leaves MUST contain no entry under the id.

An owner replacing a leaf before activation MAY omit a pre-existing `0x8010` entry, and receivers MUST accept that
omission. This component-specific cleanup is an exception to opaque-byte preservation, not a component payload.
Leaves still carrying an entry must be replaced before activation.

## Activation and authorization

The [shared activation process](README.md#enabling-a-component-in-an-existing-group) applies to existing groups. New
groups MAY require the component at creation only when their creator explicitly requests view-once support. Clients
MUST NOT activate it automatically merely because all members advertise support.

Only an active admin in the candidate parent state MAY commit activation in an existing group. Activation changes the
required list, not a component entry, and grants no standalone AppDataUpdate proposal authority under `0x8010`.
The normal authorization rules for changing required capabilities still apply.

Every leaf in a resulting state requiring `0x8010` MUST advertise support for it. That state MUST also require
`marmot.group.encrypted-media.v2` and carry valid [v2 media policy](group-encrypted-media-v2.md). These invariants apply
to the activation Commit and every later Commit, including Adds and self-updates. A Commit breaking either invariant
is invalid. Welcome acceptance checks the same resulting-state invariants.

Whether an app event may use view-once is decided by the authenticated GroupContext of its MLS source epoch, not by
whether the receiver's current epoch requires the component. Activation does not reinterpret earlier messages.

## Lifecycle and removal

Once a candidate parent requires `0x8010`, every resulting state MUST keep it required. No member, including an active
admin, may commit its removal from the required list. The component has no state bytes to update, replace, or remove.
The required v2 media policy may still be updated under its own rules but cannot be removed while view-once is required.

Activation and branch selection use the normal [convergence rules](../protocol-core/convergence.md). A losing activation
is not permission to activate again automatically. Replaying or selecting another branch does not reset a device's
terminal consumption decisions for an authenticated app event, as defined by the owning feature.

## Migration

This is the first negotiated view-once profile. Existing groups remain ordinary media groups until explicit activation.
Neither `marmot.group.encrypted-media.v2` support alone nor an application preference implies view-once support.
A breaking view-once version requires a new component id and feature version. Historical references retain their
original format and consumption identity.
