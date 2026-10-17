# Changes

Status: adopted.

This log lists changes to the specification that implementers need to know about, newest first. Each entry says what
changed, which documents it touches, what an implementation has to do differently, and which pull request made the
change. Idea documents, editorial fixes, and repository housekeeping are not listed.

The specification has no version number, and this log does not version the protocol. An interop-visible breaking change
still needs an explicit versioning hook, as [layout.md](./layout.md#features) requires.

The log starts at the 2026-07-05 baseline, the oldest commit on `master`. Earlier MIP-era changes are mapped in
[mip-coverage.md](./mip-coverage.md).

## 2026-10-16: Replaced KeyPackage init keys outlive replacement by 24 hours

[#440](https://github.com/marmot-protocol/marmot/pull/440) changes
[foundation/key-packages.md](./foundation/key-packages.md). After a successful Welcome, a last-resort KeyPackage's
`init_key` must now be deleted 24 hours after confirmed publication of its replacement, or at `Lifetime.not_after` if
that is earlier. Before, it had to be deleted at confirmed replacement. Clients SHOULD keep the key for the whole grace
period, so that a Welcome built from the old publication before the replacement reached the inviter can still be
processed.

## 2026-10-15: Existing groups can adopt new app components

[#439](https://github.com/marmot-protocol/marmot/pull/439) changes [app-components/README.md](./app-components/README.md),
[foundation/key-packages.md](./foundation/key-packages.md), and
[app-components/group-lifecycle-v1.md](./app-components/group-lifecycle-v1.md). A client SHOULD replace its published
KeyPackages when the set of component ids it supports changes, and keep advertising every id it still supports. It
refreshes a stale own leaf after a randomized delay. Once every leaf advertises an id, an authorized member can activate
the component in one Commit. Activation is always an explicit decision. Lifecycle-v1 enablement follows this process.

## 2026-10-05: Nostr KeyPackage discovery without kind 10051

[#422](https://github.com/marmot-protocol/marmot/pull/422) adds a migration subsection to
[transports/nostr.md](./transports/nostr.md). It changes no requirement. It spells out that the kind `10002`
write-capable relay set is where kind `30443` KeyPackages are published and fetched, with no kind `10051` step, and that
kind `10050` stays the source of Welcome inbox relays. Relays where metadata was found are lookup locations, not
advertised destinations.

## 2026-09-20: Encrypted NIP-88 polls

[#425](https://github.com/marmot-protocol/marmot/pull/425) changes
[foundation/application-messages.md](./foundation/application-messages.md) and
[foundation/registries.md](./foundation/registries.md). NIP-88 poll kinds `1068` and `1018` are ordinary Marmot app
events inside MLS. Inner `relay` tags do not select relays; authenticated group routing does. Supporting polls is
optional, and polls are neither anonymous nor fit for elections.

## 2026-09-16: Group reports, dismissal labels, and admin deletion

[#423](https://github.com/marmot-protocol/marmot/pull/423) adds
[features/content-moderation.md](./features/content-moderation.md) and registers three app-event kinds: `1984` for
NIP-56 reports of messages in the same group, `1985` for NIP-32 `marmot.report-review.v1` / `dismissed` labels on
reports, and `4891` for an admin's deletion of any member's chat message with its edits and attachments. Admin
authority is checked against the event's authenticated source-epoch state, and a dismissal does not override a deletion.

## 2026-08-13: Durability and restart contract

[#416](https://github.com/marmot-protocol/marmot/pull/416) adds [protocol-core/durability.md](./protocol-core/durability.md)
and cross-links it from the convergence, publish-lifecycle, group-state, and retained-history documents. A restart must
not change canonical branch selection, input dispositions, unresolved outbound gates, or the application-visible
projection. Possible external acceptance without a recoverable acknowledgement remains `PendingPublish`. There are no
wire, component, or registry changes.

## 2026-07-30: Convergence assurance and deferred input

[#410](https://github.com/marmot-protocol/marmot/pull/410) changes
[protocol-core/convergence.md](./protocol-core/convergence.md),
[protocol-core/inbound-processing.md](./protocol-core/inbound-processing.md),
[foundation/errors.md](./foundation/errors.md), and [transports/nostr.md](./transports/nostr.md), and adds
[foundation/conformance.md](./foundation/conformance.md). Transport-deferred and resource-refused input is now distinct
from stale, invalid, or deduplicated input. It must stay refetch-eligible instead of being discarded when a local retry
or storage limit is reached, and the affected range must not be reported as synchronized. A change to state-selecting
convergence policy needs an explicit capability or component. The conformance projection is test-only.

## 2026-07-28: Group disbanding

[#409](https://github.com/marmot-protocol/marmot/pull/409) registers required app component `0x800c`,
`marmot.group.lifecycle.v1` ([app-components/group-lifecycle-v1.md](./app-components/group-lifecycle-v1.md)), with an
irreversible `Active` to `Disbanded` transition made by an authenticated admin Commit. `Disbanded` becomes the sixth
canonical group lifecycle state. New groups require the component and start `Active`. An existing group can disband only
after an admin enables the component in one Commit and every current leaf advertises support.

## 2026-07-23: Push owner proofs signed as unpublished Nostr events

Commit [`dedeaf4`](https://github.com/marmot-protocol/marmot/commit/dedeaf4) changes
[features/push-notifications.md](./features/push-notifications.md) and
[foundation/registries.md](./foundation/registries.md). A push token or removal entry's `owner_sig` is now a BIP-340
signature over the id of an exact, unpublished kind `451` Nostr event. `SHA-256(SignedRecord)` remains only the ordering
tie-breaker, and the legacy signature preimage is not reinterpreted.

## 2026-07-23: Specification issue sweep

[#408](https://github.com/marmot-protocol/marmot/pull/408) resolves 200 specification issues, one commit each. The
changes implementers most often need:

- Membership and admin authority is checked against candidate parent state. A group has a non-empty admin policy from
  creation, and losing every admin freezes governance.
- Convergence is bounded and deterministic, with defined retained-history behavior and canonical-state-derived
  self-removal.
- Welcome, KeyPackage, publish-before-apply, rollback, Nostr routing, fetch, and acknowledgement rules are aligned. This
  set the KeyPackage `init_key` deletion bound that #440 later relaxed.
- Push v1 is stateless and best-effort. Service revocation, storage, and rate policy are outside the wire protocol.
- Encrypted-media, group-image, retention, component, registry, identity-proof, and inner sender-binding rules are
  repaired.
- Endpoint reachability, DNS and SSRF policy, remote-fetch consent, storage, and application-event ordering are not
  part of protocol validity.
- The QUIC preview documents are corrected and are not required for Marmot operation.

## 2026-07-05: Adopted baseline

The oldest commit on `master` contains the adopted specification as it stood after
[#236](https://github.com/marmot-protocol/marmot/pull/236) tightened its wire-boundary validation rules. That
specification was imported in [#71](https://github.com/marmot-protocol/marmot/pull/71), marked adopted in
[#170](https://github.com/marmot-protocol/marmot/pull/170), and had its admin-policy, membership, and role-change rules
aligned in [#171](https://github.com/marmot-protocol/marmot/pull/171). Later entries are relative to this baseline.
