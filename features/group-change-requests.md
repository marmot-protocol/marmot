# Group change requests v1

Status: draft. Optional; not required for baseline Marmot conformance.

A current member can request that an admin invite an account or change the group's name, description, image, or
disappearing-message timer. Any active admin can Approve or Reject. A request grants no admin powers and changes no
group state by itself. Requests and decisions are visible to group members, not private submissions to admins.

## Surfaces and terminology

This feature owns kind `458` inner app events and their request/decision semantics. It uses the existing
[application payload contract](../foundation/application-messages.md), [admin policy](../app-components/admin-policy-v1.md),
[component updates](../app-components/README.md#groupcontext-update-processing), [KeyPackages](../foundation/key-packages.md),
[Welcome flow](../protocol-core/joining.md), [convergence](../protocol-core/convergence.md),
[durability](../protocol-core/durability.md), and [retention](../app-components/message-retention-v1.md).
It adds no MLS proposal type, persistent component, transport, or change to existing authorization.

- **Requester:** the current member suggesting the change; the MLS-authenticated app-event author.
- **Requested account:** the person to invite, distinct from the requester.
- **Request:** one immutable suggestion, identified by its inner app-event id within this MLS group.
- **Active admin:** exactly the role defined by admin policy, not possession of an inbox key.
- **Approve:** attempt the existing authorized operation; not proof that it succeeded.
- **Applied:** an authenticated decision correlated with an accepted matching Commit.
- **Invited versus Joined:** an accepted Add establishes the invitation's group-state effect. It does not prove that
  the requested account received, accepted, or successfully processed its Welcome.

The [group invite-links proposal](https://github.com/marmot-protocol/marmot/pull/429) is non-normative context, not a
dependency. Both experiences use Requests, Approve/Reject, active admins, waiting, and the existing Welcome flow.
An invite-link join request comes from outside the group and targets a particular joining device; this feature's
member request suggests an account and deliberately carries no package or device reference. Its group-visible
privacy, account-level subject, and retention rules do not specify the invite-link admin-private flow.

## Eligibility before requesting an invitation

Before sending `invite_account`, a requester client MUST verify that the account is not already a member and discover
at least one valid KeyPackage compatible with the group's current requirements, following
[KeyPackage validation and selection](../foundation/key-packages.md#selection-and-lifecycle) and the active transport
binding. The check does not consume or reserve the package.

No valid candidate found and discovery unavailable are distinct local outcomes. Neither permits normal submission;
the client explains the problem and offers retry. Failure to find a candidate is not proof that none exists anywhere.
No other invitee data is sent: `data` contains only the requested account's public key. KeyPackage bytes, references,
publication references, device identifiers, and discovery hints are not part of the request.

Clients SHOULD explain that group members can see the requested account and that preflight discovery can expose
interest in that account to the queried transport services. Encryption of the request does not hide those lookups.

This preflight is not verifiable from a public-key-only request. Receivers MUST NOT treat it as a security proof.
When approving, the admin client MUST independently discover and validate a currently usable package for the exact
requested account, including lifetime, identity proof, compatibility, publication provenance, and reuse/replacement
rules. Selection follows the existing rules, not merely the newest timestamp or the requester's cached choice.
Package rotation between the two checks needs no new request if the account identity remains the same.

If no usable package can be established, the client MUST NOT create an Add or report Applied. It offers retry without
turning that operational failure into Rejected. Discovery cannot guarantee that a recipient still retains a package's
private material when a delayed Welcome arrives. The existing Commit-before-Welcome and receiver validation remain
unchanged; no new Joined receipt or first-contact authenticity guarantee is defined here.

## Message format

All actions use kind `458`, the ordinary six-field unsigned app-event envelope, and `tags: []`. `content` is UTF-8 JSON
with the exact members below; unknown members, duplicate keys, unsupported actions/operations/versions, wrong types,
noncanonical encodings, and content longer than 32,768 UTF-8 bytes have no request/decision effect. This does not reject
otherwise-valid MLS processing or create a group-state authorization check.

Content objects, including nested objects, use lexicographically sorted ASCII member names, no whitespace between
tokens, and the string escaping in [canonical encoding](../foundation/canonical-encoding.md#nostr-shaped-values).
Strings contain Unicode scalar values; control characters below U+0020 are excluded except backspace, form feed,
newline, carriage return, and tab, whose named JSON escapes are used. Receivers MUST require byte equality with that
canonical serialization. JSON object ordering therefore has one encoding; strings are never normalized or trimmed.
The complete app-event id is calculated by the existing foundation rule over the exact content string.

### Request

Exact members: `v` (integer `1`), `action` (`"request"`), `nonce`, `operation`, and `data`.
`nonce` is 32 cryptographically random bytes represented by 64 lowercase hex characters. A fresh intent gets a fresh
nonce, including an otherwise-identical submission in the same second. Retrying republishes the same complete app
event; editing a request creates a new request and withdraws the old one when possible.

| Operation | Exact `data` members | Values and existing owner |
| --- | --- | --- |
| `invite_account` | `pubkey` | 64 lowercase hex characters encoding a valid x-only account key; [identity](../foundation/identity.md). |
| `set_name` | `expected`, `value` | UTF-8 strings satisfying the name bounds in [profile](../app-components/group-profile-v1.md). |
| `set_description` | `expected`, `value` | UTF-8 strings satisfying the description bounds in [profile](../app-components/group-profile-v1.md). |
| `set_retention` | `expected`, `value` | Unsigned decimal strings representing the duration range in [retention](../app-components/message-retention-v1.md). |
| `set_avatar_url` | `expected`, `value` | Encoded complete component state; [URL avatar](../app-components/group-avatar-url-v1.md). |
| `set_blossom_image` | `expected`, `value` | Encoded complete component state; [Blossom image](../app-components/group-blossom-image-v1.md). |

For settings, `expected` may instead be JSON `null`, meaning the owning component is absent. It is distinct from a
present empty string, explicit zero timer, or encoded empty image state. `value` MUST NOT be null. Decimal strings
are `"0"` or start with `1..9` followed by decimal digits; leading zeros, signs, whitespace, and numeric JSON values
are invalid. Zero disables disappearing messages through a present retention component.

Image strings use RFC 4648 standard padded base64 with no whitespace or alternative alphabet. Decoded bytes are at
most 4096 bytes and MUST decode exactly as a canonical valid state of the named component. Empty images use that
component's encoded empty state, not an empty base64 string. Its opaque render hints retain their owning validation.
Only those two image components are allowed; this is not an arbitrary component update interface. URL/Blossom
coexistence and display precedence remain unchanged. Clients SHOULD explain when a proposed Blossom image would be
hidden by an existing URL avatar. Rendering or fetching a suggested image is local policy, not an acceptance check.

The requester MUST obtain `expected` from the current authenticated group state. At approval, the relevant candidate
parent value MUST equal it. Otherwise the request is locally Stale and MUST NOT be executed through this request.
A new request or an independent admin action can supersede it. Unrelated epoch changes do not stale the request.
For profile fields, the admin changes only the requested field and preserves the other current field in the full
replacement component. When creating an absent profile, its other field is the empty string. Image requests replace
only the named component; they do not clear a coexisting image component. Component removal is not defined here.

### Rejection and withdrawal

Rejection has exactly `v: 1`, `action: "rejected"`, `request` (the 64-character lowercase hex request app-event id),
and `reason` (a UTF-8 string of at most 1024 bytes; empty is allowed).
Withdrawal has exactly `v: 1`, `action: "withdrawn"`, and `request`.

Receivers MUST verify that a rejecting sender was an active admin in the event's authenticated source-epoch branch.
A withdrawal MUST be authored by the same account as the request, including another valid leaf of that account.
Today's admin list and author-provided timestamps MUST NOT replace these checks. A rejection dismisses a suggestion;
it does not veto an admin's independent action or remove an already-added account.

### Applied receipt

Exact members: `v: 1`, `action: "applied"`, `request`, and `commit`.
`request` has the same encoding as above. `commit` is the 64-character lowercase hex SHA-256 digest of the complete
serialized Commit MLSMessage bytes, as used by [convergence](../protocol-core/convergence.md#same-epoch-races), not an
outer transport event id. The receipt sender's MLS-authenticated account MUST equal the committer's account; another
valid leaf of that account is allowed. The sender MUST be an active admin in the receipt's source-epoch branch.
A receipt never applies or authorizes its referenced Commit.

All references are resolved within the same MLS group. Receivers MUST establish the retained request, receipt
authorization, and an accepted matching Commit before showing Applied. Missing evidence remains Unresolved, not
success. Commit validity MUST NOT depend on possession of a request or receipt.

A matching Commit MUST have been authorized under existing rules and have the requester as a current member in its
candidate parent. That parent MUST be the request's authenticated source-epoch state or a descendant on the selected
branch, not an older epoch or unrelated branch. The receipt's authenticated source epoch MUST be the matching
Commit's resulting state or a descendant on that branch. For `invite_account`, the requested account is absent in that parent and exactly one added leaf
belongs to it; no other leaves are added or removed. For settings, the parent satisfies `expected`, the resulting
requested value equals `value`, and any unaffected field in the owning component is preserved as specified above.
For either operation, other component values, required capabilities, and existing membership MUST be unchanged;
ordinary MLS epoch advancement and the committer's routine leaf/key update are allowed. Resulting-state component
validation still applies. An unrelated or broader admin change is not fulfillment of this exact request.

The admin emits a receipt only after successful Commit publication and local canonical application under the existing
publish lifecycle. Publication failure leaves the request unapplied. An Add receipt means Invited, never Joined;
Welcome delivery failure MUST remain separately visible, not be hidden behind the Applied request status.

Before publishing a request-driven Commit, the admin MUST retain or be able to reconstruct its request correlation
under [durability](../protocol-core/durability.md#recoverable-protocol-facts). After restart it SHOULD publish a missing
receipt for an accepted matching Commit when the request is still retained/unexpired and its current leaf can author
an authorized receipt. A prepared receipt retains its exact app-event identity across retries. The admin MUST NOT
repeat an Add or settings mutation solely because its receipt is missing. Without retained correlation or current
receipt authority, the client reports the group change separately and leaves request fulfillment Unresolved rather
than fabricating success; old authenticated receipts retain their source-epoch authorization after demotion.

## Projection, concurrency, and recovery

For retained requests, supported clients MUST derive the same status from the same authenticated evidence set:

1. Applied if at least one valid receipt references an accepted matching Commit.
2. Otherwise Withdrawn if at least one valid requester withdrawal exists.
3. Otherwise Rejected if at least one authorized rejection exists.
4. Otherwise Pending; an unresolved receipt is separately indicated and never interpreted as Applied.

Local Stale, Already a member, Unable to check eligibility, and Waiting for an admin explain why an otherwise Pending
request is not currently actionable. They do not synthesize decisions. A rejected or withdrawn request MUST NOT be
offered for approval. Before staging a Commit, the admin rechecks the request status, current authority, requester
membership, expected values, and invitation eligibility. Admins may act independently outside a request.

Simultaneous admin actions follow existing convergence. Neither receipt timestamps nor first arrival choose group
state. An in-flight authorized Commit can race rejection or withdrawal; a verified Applied result wins over either,
because they cannot undo the Commit. Multiple matching receipts do not apply the operation again. Reasons remain
attributed to their admins; the protocol does not select a winning explanation.

When convergence withdraws a request, receipt, rejection, withdrawal, or its matching Commit, clients MUST recompute
the projection and withdraw effects supported only by that input. Applied is not irreversible global finality.
Receipt authorization and matching evidence MUST remain reproducible, or be recorded as a verdict bound to the
request, receipt, Commit digest, and authenticated branch, for as long as their effects are retained. Pruning a parent
state MUST NOT revoke an established verdict; later branch withdrawal still invalidates its effect. Restart uses the
same evidence and MUST NOT invent Applied or reopen a retained decision merely because a process restarted.

Requests and decisions follow existing app-message expiry and retained-history limits, with no silent exemption.
Expired request content MUST NOT be revived for approval; the member can make a new request. Pruning evidence is an
availability limit, not evidence of rejection or that a completed group change was undone. A timer change preserves
every older message's pinned expiry and never performs a retroactive history purge.

Clients SHOULD bound active request lists, unresolved-reference buffering, retries, and notifications. Resource limits
are local admission/presentation policy; they MUST NOT make otherwise-valid MLS input invalid. Unsupported clients
use ordinary unknown-app-event handling and are not assumed to offer a Requests screen. No response means waiting,
not rejection. A request is not an invitation or consent from the requested account.

## Examples

These are canonical `content` strings inside kind `458` events; the ordinary envelope still applies.

```json
{"action":"request","data":{"pubkey":"79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"},"nonce":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","operation":"invite_account","v":1}
```

The nonce above is a fixture only; real clients generate it randomly.

With envelope author `79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798`, `created_at: 1700000000`,
kind `458`, empty tags, and the exact invitation content above, the canonical NIP-01 app-event id is
`e5ab295cece5e1a951e8d0c591f42f4a0666c26f9f7f7d34d9e09fe21ab36d31`.
This example author/subject equality demonstrates encoding only; an already-member subject fails invitation preflight.

A proposed timer change:

```json
{"action":"request","data":{"expected":"86400","value":"604800"},"nonce":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","operation":"set_retention","v":1}
```

An applied receipt for a fixture request and Commit:

```json
{"action":"applied","commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","request":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","v":1}
```

The example references are placeholders, not evidence that a Commit exists. Rejection uses the same `request` reference:

```json
{"action":"rejected","reason":"Please check with the person first.","request":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","v":1}
```

## Conformance and migration

Implementations of this feature need conformance cases for canonical content and app-event ids, no package fields in invitation requests, proposer preflight
and independent approval discovery, expired/rotated/incompatible packages, stale field checks, preservation of other
profile fields, exact image bytes and precedence, absent versus empty state, response-before-request delivery,
non-admin decisions, cross-group references, two-admin races, losing Commit invalidation, restart, expiry, missing
evidence, and unsupported clients. Successful invitation and successful Welcome processing are tested separately.

This is a new optional application feature, not a migration of MIP-era MLS proposal queues. The new kind and `v: 1`
identify its wire semantics. Unsupported future versions have no v1 effect. No adoption of a separate idea, including
invite links or multi-device enrollment, changes this operation set or authorizes new state transitions implicitly.
