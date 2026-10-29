# Marmot app components

Status: adopted.

Marmot app-owned MLS data is split into application components carried by the MLS `app_data_dictionary` extension. Each
component has a `ComponentID` and owns the opaque bytes stored under that id.

An `app_data_dictionary` can appear in a GroupContext, LeafNode, KeyPackage, or GroupInfo. The containing MLS object
determines the scope of its component entries:

- GroupContext entries are authenticated group state agreed for an epoch.
- LeafNode entries describe and advertise data associated with one member leaf.
- KeyPackage entries describe data associated with one KeyPackage, separate from entries in its embedded LeafNode.
- GroupInfo entries carry application data for a particular GroupInfo object.

The dictionary is the common carrier at all of those locations:

```text
uint16 ComponentID;

struct {
  ComponentID component_id;
  opaque data<V>;
} ComponentData;

struct {
  ComponentData component_data<V>;
} AppDataDictionary;
```

Dictionary entries are sorted by `component_id` and contain at most one entry for each component.

The `AppDataDictionary` and `ComponentData` structures are defined by the MLS extensions draft, not by Marmot. They are
reproduced here only for reference and use MLS/TLS encoding. Per
[../foundation/canonical-encoding.md](../foundation/canonical-encoding.md), Marmot treats these upstream structures as
opaque-from-MLS and owns only the bytes inside each `data` field for Marmot component ids, encoded with the Marmot
canonical encoding profile. Marmot does not wrap every entry in another generic component envelope.

## Upstream Basis

This spec follows:

- [draft-ietf-mls-extensions-10](https://datatracker.ietf.org/doc/html/draft-ietf-mls-extensions-10)
- [OpenMLS AppData handling](https://book.openmls.tech/user_manual/app_data_updates.html)

OpenMLS exposes this support behind its `extensions-draft-08` feature. Marmot targets the draft-10 code points and
semantics; the pinned ids in [../foundation/registries.md](../foundation/registries.md) match
draft-ietf-mls-extensions-10. Where OpenMLS's draft-08 implementation emits a different code point or wire layout than
draft-10, that gap MUST be reconciled before interop rather than papered over locally.

For the profile Marmot currently implements, the pinned upstream component, extension, and proposal ids are listed in
[../foundation/registries.md](../foundation/registries.md). Changing them is a wire-compatibility change, not a local
implementation detail.

## Component IDs

Marmot uses private MLS component ids in the `0x8000..0xffff` range.

Marmot does not plan to request public component ids for these components.

Each file defines one component id. Component names include `v1` for human readability. The versioning rule for breaking
changes is:

- a breaking v2 gets a new component id;
- a breaking v2 gets a new component file;
- component state and update payloads do not add a generic major-version field. A component-specific format constant
  retained as part of an inherited byte schema is not version negotiation and MUST NOT replace the component-id rule.

Compatible changes are valid only when the active component document explicitly reserves the needed field, value, or
behavior.

This is a Marmot policy choice, not a rule imposed by the MLS extensions draft. The MLS `app_components` mechanism
negotiates component ids, not `(component_id, version)` pairs.

Assigned component ids are registered in [../foundation/registries.md](../foundation/registries.md).

## Placement

Application data SHOULD use a component at the MLS location whose existing lifecycle matches the data. Leaf-scoped data
does not become a custom extension merely because it is security-critical or must be validated before accepting a
member. A custom MLS extension is appropriate only when the feature needs MLS protocol machinery or extension semantics
that `app_data_dictionary` and the safe application interface cannot express.

Persistent Marmot group state uses GroupContext components. Per-member application metadata or an application-owned
proof about a leaf normally uses a LeafNode component. A component document MUST state every valid location and define
the bytes and validation rules for each location.

A component MAY have no valid location. It then carries no data: it exists only as an id in `app_components` support
and required lists, and its document defines what requiring it changes and how an unexpected entry under its id is
handled. [account-devices-v1.md](./account-devices-v1.md) is such a component.

Location also determines how the bytes change:

- GroupContext component entries change through `AppDataUpdate`.
- LeafNode component entries change only when a new or replacement LeafNode is created.
- KeyPackage and GroupInfo component entries are set when their containing object is created.
- Commit-scoped component data is carried by `AppEphemeral` and does not become persistent component state.
- A component that contributes MLS additional authenticated data uses `SafeAAD` when the group has negotiated it.

An `AppDataUpdate` targets only the GroupContext dictionary. It MUST NOT be used or reinterpreted as an update mechanism
for a LeafNode, KeyPackage, or GroupInfo component.

`AppEphemeral` and SafeAAD are not interchangeable. A value whose lifetime is exactly one Commit SHOULD use
`AppEphemeral`. SafeAAD is for component-separated contributions to the MLS `authenticated_data` field and changes the
framing of that entire field when enabled in the GroupContext.

## Negotiation

Every implementation that advertises support for `app_data_dictionary` MUST understand and advertise the registered
upstream `app_components` component, and MUST understand the registered upstream `safe_aad` component. A LeafNode
advertises supported component ids in its `app_components` entry. A GroupContext lists the component ids required by
the group in its `app_components` entry.

The LeafNode support list does not replace a required component's data. If a Marmot component requires an entry in each
member LeafNode, the owning component document MUST require and validate that entry separately.

A member that does not support every required component id MUST NOT join the group.

Every current-profile Marmot KeyPackage MUST advertise the registered `app_data_update` proposal (`0x0008`), and every
new Marmot group MUST list it among the group's required proposal capabilities. Every current-profile group carries
mutable GroupContext component state, including the required admin-policy component, so this requirement is not
conditional on enabling a particular optional component.

New groups also require `marmot.group.lifecycle.v1` (`0x800c`) with `active`
state. Existing groups that predate that component remain valid without it and
use the explicit enablement flow in
[group-lifecycle-v1.md](./group-lifecycle-v1.md).

## Enabling a Component in an Existing Group

A group that predates a component can start requiring it once every member supports it. Members learn about support from
authenticated group state, so the process has three steps: members advertise support, the group becomes eligible, and
one Commit activates the component.

### Advertising support

A client advertises the component ids it supports in its KeyPackages
([../foundation/key-packages.md](../foundation/key-packages.md), "Capability advertising") and in its own leaf in each
group. A LeafNode's `app_components` support list changes only when the member creates a replacement LeafNode, through
an Update proposal or the UpdatePath of its own Commit.

When a client creates a replacement LeafNode for its own leaf, it SHOULD advertise every component id it currently
supports. The replacement MUST still advertise every component id the group requires.

A client MUST NOT advertise a component id it does not support. A client that drops support for a component id stops
advertising it in new KeyPackages, and SHOULD stop advertising it in its next replacement LeafNode in each group that
does not require it. A client MUST NOT drop support for a component id that a group it belongs to requires: it keeps
supporting that component while it remains a member, or leaves the group first
([../protocol-core/member-departure.md](../protocol-core/member-departure.md)). There is no way for a member to
withdraw support for a required component and stay in the group.

A client whose own leaf in a group advertises fewer component ids than it supports SHOULD replace that leaf, for example
with a self-update Commit. It SHOULD first wait for a delay chosen uniformly at random from a window that starts when
the client notices the stale leaf, so that installing a new release does not make every member of a group commit at
once. The window's length is implementation-defined and SHOULD be at least several hours. When the delay ends, the
client replaces the leaf only if it still advertises fewer component ids than the client supports. Any replacement
LeafNode the client created for that group in the meantime, for example in an UpdatePath, already makes the delayed
replacement unnecessary. The delayed replacement is an ordinary Commit and follows the normal publication rules.

### Eligibility

A group is eligible to require a component when every leaf in the current canonical state advertises that component id.
Eligibility is read from authenticated leaves, so every member computes the same answer.

### Activation

An activation Commit adds the component's initial GroupContext state, if the component has any, and adds its id to the
required `app_components` list in the same Commit. It is valid only when every leaf in the resulting state advertises
the id. Its authorization is the component's commit authorization: an active admin unless the component document says
otherwise.

Activation is an explicit decision by an authorized member. A client MUST NOT activate a component unless its user, or
the component's own document, asks it to. Before committing, the client checks again that the component is not already
required and that every leaf still advertises it, so it does not repeat an activation another admin already committed.
If the activation Commit loses branch selection ([../protocol-core/convergence.md](../protocol-core/convergence.md)), or
those checks fail when a queued activation is regenerated after convergence settles
([../protocol-core/group-state.md](../protocol-core/group-state.md), "Local actions during convergence"), the client
does not commit it on its own. It activates only if its user asks again.

After activation, a member whose KeyPackage does not advertise the id cannot be added ("Negotiation" above). A client
SHOULD tell an inviter when an invitee's KeyPackages are refused for this reason, so the invitee can update.

A component that supports activation in an existing group MUST say so in its own document and define the initial state
its activation Commit installs. A component whose required status changes how clients validate or select group state
MUST forbid removing it, and MUST say which state's GroupContext decides its effect, so that branches that diverged
across the activating Commit are resolved the same way by every client. [group-lifecycle-v1.md](./group-lifecycle-v1.md)
and [account-devices-v1.md](./account-devices-v1.md) follow this process.

## Common Rules

All state and update payloads use the Marmot binary profile unless a component says otherwise.

Each component document MUST define:

- component id
- component name
- every valid component entry location
- bytes and validation at each location
- negotiation and presence requirements
- the location-appropriate creation or update lifecycle
- any `AppEphemeral` or SafeAAD bytes and processing rules owned by the component
- authorization rules for every mutation the component permits
- removal or replacement rules
- migration rule

GroupContext component documents additionally MUST define state bytes, update bytes, proposal authorization, commit
authorization, and removal rules. LeafNode, KeyPackage, and GroupInfo component documents MUST NOT invent
`AppDataUpdate` bytes; they instead define validation and the rules for creating or replacing the containing MLS
object.

For v1 GroupContext component documents, these defaults apply unless the component says otherwise:

- If the update payload is a full replacement state, partial field updates are not defined. A caller that wants to
  change one field reads the current state, changes that field, and sends a full replacement.
- An inline AppDataUpdate requires the sender to satisfy the component's commit authorization because the proposal
  sender and committer are the same member. For admin-gated components, the sender MUST be an active admin (defined
  in [admin-policy-v1.md](./admin-policy-v1.md)).
- A component MUST NOT be removed while it is listed as required in the GroupContext `app_components` component.

Component state and update decoders follow the canonical decoding rule in
[../foundation/canonical-encoding.md](../foundation/canonical-encoding.md): bytes that are not canonical are invalid,
and a decoder MUST NOT trim, case-fold, normalize, deduplicate, or reorder values while decoding. Fields an owning
component document marks as opaque hints are validated only against their stated bounds.

## GroupContext Update Processing

Each Marmot GroupContext component document defines two byte formats:

- state bytes stored in `AppDataDictionary.component_data.data`;
- update bytes carried in `AppDataUpdate.update`.

For each Commit, a Marmot client groups AppDataUpdate operations by component id. A Commit MUST contain at most one
operation for a given component id, whether that operation adds, updates, or removes the component. More than one
operation for the same component id makes the Commit invalid.

The update rule returns new state bytes or rejects the Commit. A component's update rule decides how update bytes relate
to prior state. In v1 every GroupContext component document defines its update payload as a full replacement state,
except [device-roster-v1.md](./device-roster-v1.md), whose update is a diff. The
client validates the operation's proposal sender, committer, component-local encoding, value rules, and removal policy.
Any invalid operation makes the whole Commit invalid. Resulting-epoch and cross-component invariants are then checked
against the complete final state. Last-wins processing is not defined, and partial field updates are not defined
outside a diff-style update rule (see "Common Rules" above).

A component MAY define a diff-style update rule, but it MUST say so explicitly in its own document, define how the
update applies to the candidate parent's state, and make the result independent of the order of its operations.
[device-roster-v1.md](./device-roster-v1.md) is the only component that does.

Update rules MUST be deterministic. They MUST NOT read local wall-clock time, transport state, random numbers, local UI
state, or local storage order.

AppDataUpdate proposals MAY appear inline in a Commit or as standalone MLS proposals later referenced by a Commit.
Inline updates are the default when the committer is authorized. A standalone MLS proposal is not the default request
mechanism for an admin-gated component change: the component's proposal authorization defines who may create it, and v1
group-level components default to the same active-admin role that may commit it. A non-admin request for an admin-gated
component change, if a feature defines one, is carried as a Marmot app payload or feature-owned request flow rather than
as an MLS AppDataUpdate proposal.

For a Commit, a Marmot client evaluates the single AppDataUpdate operation, if any, for each component. The component
validates the proposal sender, the committer, the prior state, and the operation. It returns the new state bytes, removes
the component, or returns an invalid result. If any component operation is invalid, the Commit is invalid.

## Authorization Evaluation

Standalone proposal authorization is evaluated against the authenticated candidate state for the proposal's MLS
source epoch. It checks the proposal sender independently from the later Commit's committer; a resulting-state update
does not retroactively grant or revoke the proposal sender's authority.

Commit authorization for every component operation, including update and removal, is evaluated against the candidate
parent state: the active-admin set and other authorization inputs from the epoch before the Commit. Updates carried in
the Commit cannot grant their own committer authority or revoke authority before the other operations in that Commit
are authorized. After authorization, every component and cross-component invariant is evaluated against the complete
resulting epoch state.

## GroupContext Removal

The MLS AppDataUpdate `remove` operation removes a component entry from the GroupContext dictionary. Each Marmot
component states whether removal is allowed.

Removal is a component change and inherits that component's commit authorization unless its owning document explicitly
defines a different removal actor. Each component's Removal section restates the authorized actor so the rule does not
depend on treating the word "update" as implicit coverage of `remove`.

Required components MUST NOT be present in the resulting epoch's required-component list after they are removed. One
authorized Commit MAY atomically update `app_components` to stop requiring a component and remove that component from
the dictionary unless the owning component freezes stricter legacy sequencing. Authorization is evaluated against the
candidate parent and the required-component invariant against the complete resulting state, as defined above.

## Unknown Data

Unknown required components fail closed through negotiation.

Unknown non-required component entries MUST be preserved byte-for-byte when a client rewrites `app_data_dictionary`. The
client MUST NOT parse, normalize, sort inside, partially copy, or re-encode unknown component bytes.

## Default GroupContext Authorization

The component validates authorization. OpenMLS validates the MLS message shape; Marmot validates whether the sender MAY
make the requested semantic change.

Each component document defines who MAY propose an update and who MAY commit an update. These MAY be different roles
only when the component explicitly defines a separate proposal role.

Group-level component proposals and commits are admin-gated by default.

A component MAY define a looser rule, but it MUST do so explicitly. In v1, the admin set is defined by
`marmot.group.admin-policy.v1`.

## Current Marmot Components

Assigned component ids are registered in [../foundation/registries.md](../foundation/registries.md).

The currently adopted persistent GroupContext components are:

- [marmot.group.profile.v1](./group-profile-v1.md)
- [marmot.group.blossom.image.v1](./group-blossom-image-v1.md)
- [marmot.group.admin-policy.v1](./admin-policy-v1.md)
- [marmot.transport.nostr.routing.v1](./nostr-routing-v1.md)
- [marmot.group.message-retention.v1](./message-retention-v1.md)
- [marmot.group.avatar-url.v1](./group-avatar-url-v1.md)
- [marmot.group.encrypted-media.v2](./group-encrypted-media-v2.md)
- [marmot.group.lifecycle.v1](./group-lifecycle-v1.md)

The following adopted component carries no data. A group lists it among its required components to let members add and
remove leaves of their own account:

- [marmot.group.account-devices.v1](./account-devices-v1.md)

The following persistent GroupContext component is experimental and is not required for baseline Marmot conformance:

- [marmot.group.agent-text-stream.quic.v1](./agent-text-stream-quic-v1.md)

The following persistent GroupContext component is a draft. A group that requires it is an account's device group
([../features/device-group.md](../features/device-group.md)):

- [marmot.account.device-roster.v1](./device-roster-v1.md)

The following LeafNode component is a draft. An account's linked devices carry it in their leaves so that they can tell
which of the account's leaves belongs to which device:

- [marmot.member.device-tag.v1](./device-tag-v1.md)

The frozen [marmot.group.encrypted-media.v1](./group-encrypted-media-v1.md) component remains documented for legacy
bytes but is not part of the current profile.

Every Marmot leaf uses the adopted
[marmot.member.account-identity-proof.v2](./account-identity-proof-v2.md) LeafNode component.

## Resolved Direction

- Marmot component ids stay in the private-use range for the foreseeable future.
- Marmot component major versions are represented by component ids.
- `marmot.group.admin-policy.v1` and the LeafNode component `marmot.member.account-identity-proof.v2` are required for
  every Marmot group. Other Marmot core components are optional unless a group profile, transport, or feature requires
  them.
- `marmot.group.blossom.image.v1` is Blossom-specific. Other image-reference models SHOULD use separate components.
- `marmot.transport.nostr.routing.v1` is required for Nostr-routed Marmot groups.
- Nostr relays in `marmot.transport.nostr.routing.v1` are canonical signed group state, not local hints.
- Experimental application profiles MAY require `marmot.group.agent-text-stream.quic.v1` for agent-stream-ready
  groups. Its `receive` role is final-message fallback compatibility, not a requirement to implement the raw QUIC
  live-preview data plane.
- AppDataUpdate proposals MAY be inline or standalone. Inline is the default path when the committer is authorized;
  standalone MLS proposals are not the default non-admin request path for admin-gated component changes.
- `marmot.group.encrypted-media.v2` owns the current group media policy. Individual media attachments remain message
  metadata and are described in [encrypted-media.md](../features/encrypted-media.md).
