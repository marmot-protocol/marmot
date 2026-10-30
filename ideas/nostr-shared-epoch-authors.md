# Shared epoch authors for Nostr delivery

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

This idea explores using one shared Nostr signing key per MLS epoch for group delivery. It addresses the outsider
flood described in [issue #455](https://github.com/marmot-protocol/marmot/issues/455), where anyone who learns a group's
public routing tag can make members download and attempt to decrypt arbitrary events. The shared author replaces that
routing tag as the group's address on a relay.

It depends on the separately proposed [NIP-D9: Deletion Request Protection](https://github.com/nostr-protocol/nips/pull/2531).
That proposal is still under discussion. Neither its acceptance nor deployed relay support is assumed here.

## At a glance

- **The group shares an outer author.** Alice and Bob publish group events using the same transport signing key for
  the current epoch. They still authenticate as different senders inside MLS.
- **The author is the address.** Members subscribe to the expected author instead of a group routing tag, and group
  events carry no routing tag. An outsider can copy the public author field but cannot produce its signature.
- **The key follows MLS state.** Members derive it from the epoch's secrets. Each epoch gets a new author, including
  epochs created by membership changes and key updates. A removed member can neither publish under nor subscribe to
  the next author.
- **Catch-up walks forward one epoch at a time.** A returning member fetches the epoch it knows, processes the
  transition, derives the next author, and repeats.
- **Sharing an author needs deletion protection.** Otherwise, any holder could request deletion of everybody's outer
  events under that author, including commits needed for catch-up.
- **Old-key flooding remains a problem.** A removed member cannot sign for the new epoch, but can still attack traffic
  admitted under an old key. Recovery across that boundary needs more work.

## What is shared

The shared key is a dedicated transport signing key. It is separate from every member's Nostr account key, individual
MLS signing keys, and the key already used to encrypt group events. Everyone in the epoch holds its private half and
can publish independently, even when the other members are asleep. There is no co-signing round or signing service.

The intended source is a dedicated MLS exporter use. Members in the same candidate group state derive the same key;
different branches can have different authors even when their numeric epoch is equal. The exact derivation and its
exporter registration belong in a later spec change, not in this idea.

The replacement private key is not a field sent in a GroupContext update. A member being removed can read the removal
commit under the old epoch's outer encryption. Deriving the next author from the resulting MLS secrets avoids handing
that member the replacement signing secret in the commit it can read.

The epoch author replaces the independently random group routing ID as the delivery address. The group's signed relay
list stays where it is, owned by [nostr-routing-v1.md](../app-components/nostr-routing-v1.md); only the routing ID
stops being used for groups that switch.

## Scene 1: Alice sends a message

Alice, Bob, and Carol are in a group. Today, each kind 445 event uses a fresh outer author, and their subscriptions
select the public group routing tag. A stranger can publish events with that tag using unrelated keys. The events
reach the members before they discover that the ciphertext does not authenticate. See the
[current Nostr binding](../transports/nostr.md#group-message-delivery).

With a shared epoch author, their subscriptions select the group's expected public signing key instead. There is no
tag left for a stranger to copy. The relay checks ordinary Nostr signatures and matches the subscription before
delivering events. A stranger's valid event under an unrelated key does not match; an event falsely claiming the group
author fails signature verification at a validating relay. Merely learning the public key does not give the stranger
permission to publish under it.

Alice still encrypts the MLS bytes with the confidential outer envelope. Bob and Carol recover the MLS message and
authenticate Alice there. The outer signature says that its maker holds the epoch's transport capability, not which
member made it or whether the inner operation is authorized.

For members, the intended benefit is fewer unsolicited downloads, decryptions, and retries during an outsider flood.
The relay needs neither the shared private key nor a list of the members' account identities for this filter.

## Scene 2: The group changes epoch

Alice is an admin and removes Carol:

1. Alice prepares the removal using the group's existing MLS and authorization rules.
2. The removal commit travels under the old epoch's author, encryption key, and relay list. That is what members who
   have not processed it can find and read.
3. Publication and application follow the existing [publish lifecycle](../protocol-core/publish-lifecycle.md).
4. After processing the commit, Alice and Bob derive the new epoch author. Carol cannot derive it from her old state.
   Subsequent traffic uses the new author.

Because the author is now the group's only address on a relay, Carol also loses the ability to follow the group. She
cannot derive the new author, so she cannot subscribe to it. Today a removed member keeps the stable routing tag and
can keep watching new ciphertext arrive, unless the group rotates the tag in a second commit (see
[routing rotation](../app-components/nostr-routing-v1.md#routing-rotation)). Here the epoch change does that on its
own. What Carol can still do is watch relays she knows for new authors that start publishing right after the removal
commit. Timing can narrow her guess, especially on a relay that serves few groups, unless the group also changes its
relay list.

A new member added to the group learns the resulting MLS state through its Welcome and derives the current author
from that state. The account and Welcome authentication mechanisms do not change.

The same author rotation happens on other epoch transitions, not only adds and removals. Rotating only on membership
changes would keep a transport capability alive across ordinary key updates and introduce a separate key lifecycle.
Rotation at every epoch keeps it tied to MLS state. It still does not impose a time limit: a quiet group can stay in
one epoch until somebody performs an update. The appropriate refresh cadence remains open.

## Scene 3: Bob comes back after being offline

Suppose Bob was offline before the removal and missed several transitions. He knows an older author, not today's one.
He fetches the transition from the state he knows, processes it, derives the next author, and continues through the
available history. This depends on retained state and available commits; it does not extend the recovery guarantees in
[retained-history.md](../protocol-core/retained-history.md).

Each step returns only one epoch's events, and Bob can decrypt every real event in it when it arrives. Today a
returning member receives events from later epochs before the commits that unlock them, and has to hold and retry them.
The total amount of real traffic Bob downloads is the same; it arrives in the order he can process it. That ordering
also helps with history: Bob decrypts each epoch's application messages while that epoch is still inside the
[retained application window](../protocol-core/retained-history.md#app-payload-retention), instead of fetching
everything first and losing what falls outside it.

The cost is time. The walk takes one relay round trip per epoch, and the steps cannot run in parallel, because each
author comes from the previous epoch's commit. A quiet group may have a handful of epochs to walk; a large group with
frequent updates may have hundreds.

Catch-up and forks mean a receiver cannot simply subscribe to today's author and forget all earlier ones. The intended
subscriptions follow the same retained candidate states and any relevant staged state already used for
[outer decryption](../transports/nostr.md#outer-decryption-and-epoch-selection). That includes states reached by
replaying a competing branch, and commits replayed but not yet applied: convergence compares branch depth and
application witnesses on each branch, so a member that followed only its own branch could see less than another member
and choose differently. Where authors and relay lists change, the receiver keeps track of which ones belong together.

A matching author could help locate a known decryption candidate instead of trying unrelated retained keys. It is not
evidence that a branch is canonical. Competing commits from the same parent share the parent author, while their
resulting states can have different authors. [Convergence](../protocol-core/convergence.md) still decides group state;
transport authors and arrival order do not.

## Scene 4: Carol attacks the old author

After removal, Carol can make unlimited correctly signed envelopes under her old key. Bob's catch-up fetch needs that
same author to find the real removal commit. The relay cannot distinguish his required transition from Carol's junk
by the outer signature alone. Nothing else on the outside can either: Bob and Carol hold exactly the same secrets for
that epoch.

Alice may also need old-author input for late messages and convergence. A fresh current author creates a useful
separation, but keeping current delivery responsive while historical traffic is flooded still needs a concrete design.
The transition needed to escape the old key is itself delivered under that key.

Sharing an author does give relays one lever they lack today. Once the transition is out, honest traffic under the old
author falls to occasional late messages, so a per-author publish limit or storage quota caps how much junk Carol can
add. A flood under fresh authors cannot be limited per author at all. This is relay policy, not a fix: Carol can still
add junk up to the limit, and the same limit applies to honest late messages under that author.

Deletion protection makes that transition harder to erase by protocol request. It also protects signature-valid junk
carrying the marker: relays cannot inspect the MLS payload to know which protected events are useful. Independent
admission, retention, and abuse policy remains necessary. Neither the new signature nor the marker is a complete
historical-admission or safe-escape solution.

## Why deletion protection is part of the idea

Under ordinary Nostr author deletion, everyone holding a shared private key can request deletion of every outer event
under that key. Carol could retain an old key and later request removal of the commit that removed her, or other
members' commits from that epoch. Rotating the author cannot take back that power over old events.

The proposed NIP-D9 marker would waive deletion through that signing key for the marked event. Its exact tag and relay
behavior are owned by the NIP. The group would use that protection for its outer events and use relays that advertise
support. Acceptance by a relay that ignores the marker would not provide the intended protection.

The two halves could be deployed separately, but not safely. Author filtering alone works on any relay that verifies
signatures. Without deletion protection, though, it adds an attack that does not exist today: with fresh authors,
nobody else holds the key for an event, so nobody else can delete it. Filtering alone trades the outsider flood for
deletion by any current or former key holder.

Protection is per relay. A needed commit survives deletion requests as long as at least one relay that honors the
marker keeps it, and catch-up reaches that relay. The group needs supporting relays in its list, and receivers need to
know which ones they are.

**The protection does not expire.** An application's signed expiration still has its normal relay-facing effect, but
it never restores deletion rights through the shared signing key. An expired copy that a relay retains stays marked.
Neither expiration nor the marker guarantees physical erasure or permanent storage.

Commits and proposals would keep the existing no-expiration treatment, so application retention does not remove the
history needed for group-state catch-up. Application events would keep the existing retention-derived expiration
behavior. See [message expiration](../transports/nostr.md#message-expiration) and
[message-retention-v1.md](../app-components/message-retention-v1.md).

This does not change user-visible message deletion or moderation inside MLS. Those remain separately authorized
operations under [content-moderation.md](../features/content-moderation.md). NIP-D9 also preserves independently
defined recipient and delegator deletion authority. The intended group-event profile would not introduce those
authorities into kind 445 delivery; Welcome gift wraps are outside this change.

## What the relay can and cannot stop

| Input or attacker | Expected effect and limit |
| --- | --- |
| Outsider publishing new events aimed at the group | There is no routing tag to copy. A valid unrelated author does not match members' author filters. Claiming the group author without its key fails signature verification. |
| Outsider replaying an existing event | Existing duplicate and replay handling is still needed. The signature does not prevent redelivery. |
| Current member, or someone given the shared transport key | Can publish matching, signature-valid junk. The capability is copyable; it is not proof that its holder is an authorized individual sender. |
| Removed member holding an old epoch key | Cannot sign for or subscribe to the new state, but can flood historical subscriptions or fetches still using the old author. Per-author relay limits can cap the volume (Scene 4). |
| Malicious or overloaded relay | Can withhold events, send unwanted data, or lose storage. Signature filtering does not guarantee relay availability. |

The relay can still be flooded with events it has to reject or with events under unrelated keys. The proposal reduces
delivery to group subscribers; it does not eliminate relay CPU, bandwidth, or storage attacks.

## Against the properties in issue #455

Issue #455 lists five properties a group routing scheme needs. This idea meets all five against outsiders. Against a
removed member, admission holds only for epochs that member never held, and revocation has a timing caveat:

| Property | Result |
| --- | --- |
| Admission: only a current member can address the group | Yes for outsiders. A removed member can still publish under authors of epochs it held (Scene 4). |
| Sender anonymity: the relay cannot tell which member sent a message | Yes. Every member publishes under the same author. |
| Membership privacy: the relay cannot learn the member set or link members across groups | Yes. The relay needs no member list. Connection metadata is unchanged (see below). |
| Convergence: members derive the same routing state, and a member who missed messages can recover it | Yes, if subscriptions follow every candidate state (Scene 3). |
| Revocation: a removed member can neither address nor follow future state | Yes. A removed member cannot derive the next author. Timing on relays it knows can still hint at the new one (Scene 2). |

## Privacy and key lifetime

- **Event-level sender anonymity is preserved.** The outer author identifies the shared capability, not a member's
  account. It does not improve on the individual identity hiding already provided by fresh authors today.
- **Removed members lose the address.** With no stable routing tag, a removed member cannot subscribe to the group's
  new traffic. The two-commit routing rotation that hides a replacement routing ID today is no longer needed for that
  purpose.
- **Relays can still link epochs.** A member's subscription swaps one author for the next, often on the same
  connection, and the transition commit is the last event under the old author. A relay that watches its own
  subscriptions can link consecutive epochs much as the stable tag lets it today. Dropping the tag removes a
  published, permanent link, not the relay's view of its own connections.
- **Epoch changes become more visible.** Author changes expose transport-state changes and can help observers infer
  churn or forks. Expiration tags already identify application-message carriage in conforming traffic; their absence,
  combined with author changes and timing, can make transition commits easier to infer without proving an event's type.
- **Connections still reveal metadata.** IP addresses, timing, sizes, subscriptions, and any relay-required account
  authentication can link participants and groups. A shared event author does not hide those observations.
- **Relay reputation becomes shared.** Per-author limits or bans affect the whole group epoch. One holder can exhaust
  the allowance; rotating also changes the author on which a relay might base payment or reputation policy. The same
  property is what lets per-author limits cap old-key flooding (Scene 4).

A separately derived transport signing key is intended to limit what disclosure of that key alone exposes. It permits
outer forgery for that state without also handing over the outer encryption key or another member's individual MLS
signing key. Compromise of complete member state is a larger event; recovery still depends on MLS refreshes and release
of old secrets, not merely a new public author appearing.

Keeping a public author for verification or historical fetching does not itself require keeping its private key.
However, retained MLS state or exporter material may allow that private key to be derived again. Deleting a cached
signing key alone does not erase the capability. Any eventual retention changes need to fit the existing
[cryptographic-material lifecycle](../protocol-core/retained-history.md#retained-cryptographic-material).

## Compatibility and alternatives

This is incompatible with today's fresh-author, routing-tag, and permitted-tag rules. It needs an explicit negotiated
transport version or capability before adoption. Letting arbitrary-author legacy events through for current traffic
would preserve the original attack path. Historical legacy recovery needs a bounded migration path rather than a silent
fallback when protected delivery fails. One shape: a group switches at a single epoch boundary. The commit that
switches is published the old way, and later epochs use only authors, so catch-up across the switch uses the routing
tag before it and authors after it.

Groups would need redundant delivery through independently operated relays supporting NIP-D9, and NIP-40 where
expiration is used. An unsupported relay's acknowledgement is not evidence of protected delivery. How support changes
interact with publish success and changes to the signed relay list still needs to be settled.

Alternatives considered:

- **Keep the routing tag beside the author.** Members would subscribe to both. This keeps a stable handle for relay
  operators and a simpler migration, but a removed member could keep following the group through the tag, and the tag
  stays a permanent public link across epochs.
- **Separate authors for commits and application messages in each epoch.** Catch-up would fetch only the small commit
  stream, and application history could follow in parallel while it is still inside the retained window. The cost is
  that relays learn which events are commits, and members subscribe to twice as many authors.
- **Sender-owned pools of preauthorized public keys, or fresh event authors carrying separate group admission
  proofs.** Pools need advance key distribution and replenishment; admission proofs need additional relay validation.

Shared epoch authors choose ordinary author filtering plus the smaller deletion-protection extension. Anonymous
per-member quotas would be a further requirement, not a property of this shared-key design.

## From idea to spec

| Owning surface | Work needed before adoption |
| --- | --- |
| [Nostr transport](../transports/nostr.md) and [transport versioning](../transports/README.md#versioning) | Event authorship, removal of the routing tag, deletion protection, subscriptions, relay support, publication outcomes, and the compatibility hook. |
| [MLS protocol](../foundation/mls-protocol.md) and [registries](../foundation/registries.md) | A reviewed, domain-separated exporter use and deterministic conversion to a Nostr signing key, with agreed examples. |
| [KeyPackages](../foundation/key-packages.md) and the owning capability rules | Negotiating support before a group switches to the new transport behavior. |
| [Nostr routing component](../app-components/nostr-routing-v1.md) | A component version without the routing ID and its rotation rules, keeping the signed relay list; any changes needed to manage supporting relays as authenticated group state. |
| [Retained history](../protocol-core/retained-history.md), [convergence](../protocol-core/convergence.md), and [publish lifecycle](../protocol-core/publish-lifecycle.md) | Review recovery and secret-lifetime implications; move any settled changes into their owning documents rather than deriving group state from transport metadata. |

This idea assigns no identifiers or exporter labels and defines no interoperable bytes. The current Nostr binding and
protocol-core rules remain the adopted behavior.

## Open questions

1. How does Bob reliably find the required transition while an old-key holder floods its author, and how is current
   traffic kept responsive without declaring refused history synchronized?
2. How are subscriptions and historical fetches updated across staging, forks, relay-list changes, and pruning without
   losing the eligible alternatives or exceeding practical relay filter limits?
3. How is relay support established and refreshed, and which acknowledgements count when some relays lose support or
   every supporting relay is unavailable? How does a group migrate its signed relay list safely?
4. Which compatibility mechanism keeps unsupported members out of a switch they cannot follow, while allowing recovery
   of required legacy history without reopening current delivery to arbitrary authors?
5. What reviewed exporter construction and key-lifetime policy fit MLS recovery, and how often should quiet groups
   refresh their secrets when no other operation advances the epoch?
6. Is the remaining linkage acceptable? Relays can still link consecutive epochs through subscription swaps, timing,
   and connections. Are mitigations such as swapping authors on a fresh connection worth their cost?
