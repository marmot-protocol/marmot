# Shared message pinning v1

Status: draft. Optional; not required for baseline Marmot conformance.

Members can highlight multiple messages for everyone in a group. Pinning is shared group state; it does not change the
message body, create a saved copy, or change how long the message remains available. Applications can present a pin
bar, list, and jump action. Placement, icons, and visual ordering are client choices.

## Surfaces and capabilities

The [message-pins component](../app-components/message-pins-v1.md) owns the exact bytes, bounds, negotiation, update
rules, and mutation authorization. This feature owns the user-visible flow and reference resolution. It relies on
[application messages](../foundation/application-messages.md),
[admin policy](../app-components/admin-policy-v1.md),
[publish-before-apply](../protocol-core/publish-lifecycle.md),
[convergence](../protocol-core/convergence.md),
[durability](../protocol-core/durability.md), and
[retained history](../protocol-core/retained-history.md).

The feature adds no transport, exporter, application event kind, custom MLS proposal, AppEphemeral payload, or SafeAAD
contribution. Every mutation uses the existing AppDataUpdate and Commit flow. The component is required for groups
that opt in, even though pinning is optional for Marmot as a whole. An unsupported leaf cannot join an enabled group.

## Activation and permissions

An admin enables pinning after every member leaf supports the component. Existing groups enable it with an empty pin
set. Applications SHOULD explain when an unsupported member prevents activation and leave the conversation unchanged;
they MUST NOT silently remove that member or fall back to unauthenticated pin notices.

In the normal `members` mode, any current member can pin or unpin, including unpinning a message pinned by someone else.
An admin can choose `admins` mode to restrict both actions. Only admins change that permission or disable the feature.
Permission changes preserve existing references unless the authorized replacement also changes the pin list.
The component defines the exact candidate-parent authority checks; today's admin list does not authorize a delayed
Commit against another parent, and a resulting-state promotion cannot authorize its own operation.

## Pin and unpin flow

A producer MUST select a target that it has authenticated and accepted as an original kind-9 chat message or kind-1068
poll in this MLS group. Kind-9 media messages are eligible. Edits target their original message: the pin refers to the
original id, not a kind-1009 edit event. System rows, reactions, poll responses, and other unsupported kinds are not
eligible targets in v1. A producer MUST NOT initiate a new pin of a target it knows is deleted, expired, invalidated,
or unavailable. Unpinning an unavailable reference remains permitted.

The producer reads the selected component, adds or removes just the chosen reference, preserves unrelated references,
and prepares the canonical full replacement. At the limit, adding another reference fails locally without evicting an
existing pin or publishing an oversized state. Pinning an already present reference and unpinning an absent one are
locally satisfied no-ops. These checks do not replace component authorization.

Pending publication MAY have a separately identified UI indication. It MUST NOT be exposed as confirmed shared pin
state before the normal publication and canonical-application boundaries. A transport failure leaves the selected pin
set unchanged. An uncertain publish acknowledgement follows the existing exact-obligation recovery rule; it is not
permission to generate different Commit bytes.

## Concurrent actions, catch-up, and restart

Pins follow the selected MLS branch. This feature defines no timestamp ordering, relay-order winner, list merge, or
special priority for pin, unpin, or permission changes. After selection, two clients with the same authenticated
GroupContext have the same permission and canonical sorted reference list, even when their source-message history
differs. Duplicate Commit delivery cannot add another pin.

Competing Commits from the same parent can produce a losing pin action. Clients MUST withdraw pin state and derived
activity from a branch that convergence supersedes, and expose the selected component as one complete projection.
Pinning does not guarantee that every competing action survives. An unresolved local action MAY be retried under the
existing lifecycle and fair-scheduling rules, but MUST be reauthorized and prepared against selected state, applying
only its target operation and preserving intervening unrelated changes.

A local action becomes terminally completed when its effect first becomes canonical, or when it is accepted as an
already satisfied no-op against selected state. That completion MUST be recoverable with the corresponding state
transition and survive restart, later unpinning, and branch withdrawal. An application notification acknowledgement
is a separate observation boundary: a delayed or missing acknowledgement MUST NOT reopen the action. A completed
action MUST NOT be silently replayed; a further pin requires a new local action. A conclusively failed publication
whose action never completed remains eligible for a reauthorized retry. An uncertain acknowledgement retains the
original obligation until the publication contract resolves it.

Catch-up restores pins from authenticated group state, not from replaying chat notices. A Welcome includes the current
reference set but grants no historical-message access. Source-epoch decryption limits still apply. Restart preserves
or reconstructs confirmed and unresolved state at the observer boundaries defined by durability; it cannot promote a
pending state or show component bytes from one epoch with permissions from another.

## Resolving references and source lifecycle

For each reference, resolve only an authenticated, accepted eligible original app event in the same MLS group and
local account context. A matching id in another group, account's conversation, public relay result, transport object,
or local chat-ordering record MUST NOT satisfy the reference. The component never authorizes fetching arbitrary public
content or disclosing an id outside the group.

A client MUST apply accepted source edits when rendering a pin and preserve the source's current deletion,
moderation, expiry, and branch-invalidation rules in every pin view and jump action. See
[message edits](../foundation/application-messages.md#message-edits-kind-1009),
[content moderation](./content-moderation.md), and
[message retention](../app-components/message-retention-v1.md).
Pin metadata MUST NOT retain a second message body or decrypted attachment. It MUST NOT extend source retention,
restore purged content, or keep source-epoch decryption material beyond its existing release condition.

An unavailable source is an unresolved or unavailable pin, not proof that the authenticated reference is invalid.
Clients MUST NOT render guessed content. They SHOULD distinguish deleted or expired content from history that has not
arrived when they have authenticated evidence for that distinction. They MAY show a placeholder or hide the
unavailable item from the visible pin bar, but MUST preserve the selected reference set for subsequent mutations.
An unsupported or ineligible target kind likewise has no renderable pin content and does not invalidate group state.

Source arrival or local expiry changes resolution only. It MUST NOT automatically add or remove component entries.
Authenticated references can therefore occupy slots after their bodies disappear; an authorized unpin clears the
slot. This separation prevents local clocks or differing history from choosing group state. Pin ids remain visible to
group members in retained state, even after a source body expires; pinning does not promise erasure of those ids.

## Activity and failure behavior

Clients MAY derive pin/unpin activity by comparing a selected Commit's candidate-parent pin state with its resulting
state. Actor attribution comes from that Commit's authenticated member, never from a received free-text notice.
No change means no pin activity. Joining with an existing pin list does not attribute old pins to the inviter or
synthesize a new pin action. This version defines no new kind-1210 system type or historical per-pin author field.

An arbitrary kind-1210 event claiming that a message was pinned, unpinned, or that permission changed MUST NOT mutate
the component. Its author assertion remains subject to
[group system event provenance](../foundation/application-messages.md#group-system-events-kind-1210).

Applications SHOULD distinguish unsupported feature, permission failure, pin limit, unavailable target, pending
publication, publication failure, and convergence withdrawal. These are local action/source outcomes; the owning
component and [shared errors](../foundation/errors.md) define inbound rejection categories. A failed action does not
remove a successful pin made by another member.

Group departure and account deletion release local pin projections under their existing lifecycle. Disbanding follows
[group lifecycle](../app-components/group-lifecycle-v1.md); pins never authorize further work in a terminal group.

## Design tradeoffs and migration

Keeping a small reference set in GroupContext gives new members and offline clients the selected pins without needing
an unbounded pin-event log. It also makes permission changes and pins subject to the same authenticated parent state.
The cost is an MLS Commit and epoch advance for each effective mutation. Applications SHOULD avoid duplicate no-op
Commits and MUST honor the existing publication and convergence gates; frequent pinning still consumes protocol and
retained-history resources. This version favors bounded shared state over a separate application-event conflict model.

Legacy clients remain usable in groups that have not enabled the feature. Enabled groups require supporting leaves;
unknown optional-data preservation alone is insufficient to validate the member-authorized pin updates. Local chat
pinning and private bookmarks are separate behavior. Existing member-authored pin notices are not an automatic
migration source. A future interoperable event-based design needs its own explicit version and migration contract.

## Conformance scenarios

Conformance uses the [canonical snapshot](../foundation/conformance.md), including exact component bytes. At minimum,
independent implementations cover:

1. Activation with empty pins, both modes, unsupported-leaf refusal, and nonempty activation refusal.
2. Canonical vectors and malformed permissions, lengths, ordering, duplicates, trailing bytes, and the full bound.
3. Member pin/unpin in `members`, including another member's pin; member rejection in `admins`.
4. Admin-only permission changes, enablement/removal, same-Commit self-promotion rejection, and unrelated-operation
   rejection under the member exception.
5. Delayed candidates authorized against their authenticated parent, demotion/removal, standalone/by-reference
   rejection, and membership changes that would violate required support.
6. Concurrent pin/unpin and policy changes, selected-branch withdrawal, duplicate/reordered delivery, preserving
   unrelated pins on a retry, and no replay of an already completed action.
7. Publish failure and each applicable crash/restart boundary, especially uncertain acknowledgement and partial
   canonical application.
8. A Welcome or offline client without target history, then source arrival, edits, deletion-before-source, expiry,
   unsupported kinds, invalidated sources, and same-id objects in another group or account.
9. Full pin capacity including unavailable references; unpin without source history; disable/reactivate with empty
   pins; and retention of only reference bytes, never a content copy or an expiry exception.

The bounded reference fixtures under `tests/` exercise encoding and transition rules. They do not implement MLS or
prove cryptographic authorization, relay behavior, full convergence, or runtime durability; those remain required
independent-implementation scenarios above.
