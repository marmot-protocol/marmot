# marmot.group.message-pins.v1

Status: draft. Proposed component for the optional [message-pinning feature](../features/message-pinning.md).

## Registry and locations

- Component id: `0x800f` (proposed).
- Name: `marmot.group.message-pins.v1`.
- Location: GroupContext `app_data_dictionary` only.
- Default requirement: absent; required whenever present.

This component owns the group's pin permission and bounded set of message references. It defines no LeafNode,
KeyPackage, GroupInfo, AppEphemeral, or SafeAAD payload. It uses the
[Marmot binary profile](../foundation/canonical-encoding.md); its id carries its major version.

## State bytes

```text
enum {
  members(0),
  admins(1)
} MarmotPinPermissionV1;

struct {
  opaque app_event_id[32];
} MarmotPinnedMessageV1;

struct {
  MarmotPinPermissionV1 permission;
  MarmotPinnedMessageV1 pins<0..2048>;
} MarmotMessagePinsV1;
```

`permission` is exactly one byte: `0x00` or `0x01`. Every other value is invalid. `pins` has a shortest-form QUIC
variable-length byte-length prefix and contains zero through 64 references, each exactly 32 bytes. The list is sorted
lexicographically by raw reference bytes, with no duplicates. The largest state is 2051 bytes.

Each reference is the raw 32-byte value of an inner Marmot app event's `id`, as defined by
[application messages](../foundation/application-messages.md#shape). The surrounding MLS group scopes every reference.
It is neither an outer transport id nor an MLS message id. No message body, edited body, attachment, author claim,
timestamp, relay hint, or alternate-group identifier is stored here.

`members` permits any current member to change the pin set, including unpinning another member's pin. `admins` permits
only active admins to change it. Admin authority has the account-wide meaning defined in
[admin policy](./admin-policy-v1.md#active-admins).

## Negotiation and presence

Whenever the entry is present, the resulting GroupContext MUST require `0x800f` in `app_components`, and every
resulting nonblank member leaf MUST advertise support for it. Requiring the component without its entry is invalid.
These invariants apply to every Commit, including membership and required-component changes that carry no pin update.

A newly created group MAY enable this component with an empty pin set and either permission value. When an application
offers the normal member-enabled pinning mode, it creates the entry with `members`. The normal group-creation,
admin-policy, and capability checks still apply.

For an existing group, only a candidate-parent active admin MAY enable the component. Enablement MUST atomically add
an empty state and its required-component listing. Every resulting member must support the feature; activation cannot
silently exclude or remove an unsupported member. Removing a member, when explicitly requested, is a separately
authorized group operation. A nonempty initial pin set is invalid; pins are added by later updates.

## Update bytes and processing

The AppDataUpdate payload is the complete replacement state:

```text
MarmotMessagePinsV1 MarmotMessagePinsUpdateV1;
```

An add, replacement, or removal operation for this component MUST be inline in its Commit. Standalone proposals and
by-reference operations for this component are invalid. The proposal sender is therefore the authenticated committer.
This restriction prevents a retained full replacement from later overwriting intervening pin changes under another
member's attribution. The [shared component rules](./README.md#groupcontext-update-processing) still permit at most
one operation per component id in a Commit.

For replacement, decode the prior and replacement states exactly, check the authorization below, and replace the
component bytes. Partial updates and implicit list merges are not defined. An unchanged canonical state is a valid
no-op, subject to the same authorization checks, and produces no pin-change activity. A producer SHOULD avoid a Commit
for an already satisfied pin or unpin action.

Every operation in the Commit retains its own authorization. The member exception for this component grants no right
to change required components, invite or remove members, change admin policy, or mutate another admin-gated component.
Normal MLS validation, lifecycle gates, and [convergence](../protocol-core/convergence.md) remain in force.

## Validation

A component state is valid exactly when its bytes decode completely, its permission is defined, its vector body is a
multiple of 32 bytes and no larger than 2048 bytes, and its reference list is strictly increasing. Trailing bytes,
nonminimal lengths, duplicate references, unsorted references, and undefined permissions are invalid; receivers MUST
NOT repair them. The presence and capability invariants above are additional resulting-state checks.

Commit validity MUST NOT depend on whether any referenced application message is locally available, its kind or
content, a local deletion verdict, its expiration, a local clock, or transport delivery order. A member may have missed
the target or joined after it was sent. Rejecting a Commit for that reason would split authenticated group state.
Target resolution and producer-side target eligibility are owned by the [feature](../features/message-pinning.md).
Consequently, a structurally valid but unresolvable reference can occupy a pin slot without making the Commit invalid.

## Proposal and Commit authorization

There is no standalone proposal authority. For inline replacements, use the authenticated candidate-parent membership,
admin set, and prior permission, following [authorization evaluation](./README.md#authorization-evaluation):

- A permission change requires a candidate-parent active admin, even when the prior permission is `members`.
- With unchanged `members` permission, any candidate-parent member MAY replace the pin set.
- With unchanged `admins` permission, only a candidate-parent active admin MAY replace the pin set.
- An admin changing permission MAY also change pins in the same replacement.

The sender's payload claims never grant authority. Promoting the committer or changing permission in the same Commit
cannot authorize itself. Conversely, a valid action by a parent-state admin is not retroactively rejected merely
because another authorized operation demotes that account in the resulting state.

Authorization failure invalidates the Commit as `authorization_failed`. Invalid bytes, forbidden proposal form, or
violated presence/capability invariants invalidate it under the applicable
[shared rejection category](../foundation/errors.md). A received 65-reference state is invalid encoding, not a local
resource refusal. Clients MUST accept the full defined bound rather than impose a smaller wire-validity limit.

## Removal and reactivation

Only a candidate-parent active admin MAY remove this component, regardless of pin permission. The same Commit MUST
remove its required-component listing. Removal disables shared pinning and clears the selected pin set without deleting
source messages. Dropping the requirement while leaving the entry is invalid.

Reactivation follows enablement with an empty list; it MUST NOT restore old pins from a prior activation or from local
UI state. A losing removal or enablement Commit has only the effects allowed by ordinary branch selection. Removal
does not erase component bytes already present in retained authenticated group history.

## Migration

There is no adopted MIP-era shared message-pinning contract to migrate. Local chat ordering, private bookmarks, and
member-authored kind-1210 notices are not this component and MUST NOT be imported as authoritative shared pins.
Existing groups opt in through the capability-checked enablement flow. A breaking change requires a new component id
and document; this component has no reserved enum value or trailing extension field.

## Fixed encoding vectors

These are component value bytes, without an MLS dictionary or proposal envelope. Whitespace in displayed hex is only
for readability. Let `A` be 32 bytes of `0x11` and `B` be 32 bytes of `0x22`:

| Meaning | Canonical hex |
| --- | --- |
| Members; empty | `00 00` |
| Admins; empty | `01 00` |
| Members; A | `00 20 1111111111111111111111111111111111111111111111111111111111111111` |
| Admins; A then B | `01 4040 1111111111111111111111111111111111111111111111111111111111111111 2222222222222222222222222222222222222222222222222222222222222222` |

`00 4000` is invalid because the empty length uses a nonminimal two-byte prefix. `02 00` has an undefined permission.
`00 01 11` has a partial reference. `00 00 ff` has trailing bytes. The two-reference encoding with B before A or A
twice is invalid. A full 64-reference vector starts with `00 4800`; a 65-reference vector exceeds the defined bound.
