# Threat model and security considerations

Status: non-normative; draft for maintainer security review.

This document describes the security boundaries of the current Marmot specification: who can attack it, which assets
it aims to protect, what those protections depend on, and what remains exposed. The linked owning documents define
protocol requirements. This overview adds no wire format, authorization rule, deployment policy, or new guarantee.

The account identity, MLS group, delivery transport, application, and external services are separate trust domains.
Successful validation in one domain does not establish trust in another. In particular, authenticated group content
can be malicious, transport acceptance is not peer delivery, and a valid Welcome is not proof of the intended group's
continuity.

## Scope and evidence

The model covers the adopted foundation, protocol core, components, Nostr binding, and optional adopted features.
Experimental QUIC previews, draft moderation, superseded profiles, and ideas are identified separately in the
[coverage map](#surface-coverage). Supporting an optional feature brings its additional boundaries into scope.

The identifiers below are local reference points for later formalization, not additional protocol requirements.
Statements here summarize specification intent and assumptions. They are not a security audit, a formal proof, or
evidence that any particular implementation follows every rule. Model-checked properties, cryptographic arguments,
wire vectors, implementation tests, and deployment evidence answer different questions.

The original [threat model](https://github.com/marmot-protocol/marmot/blob/21a67b24ffbfe14fc52022769aff77495402d728/threat_model.md)
was introduced in [PR #12](https://github.com/marmot-protocol/marmot/pull/12) and removed by the surface reorganization in
[PR #71](https://github.com/marmot-protocol/marmot/pull/71). This document reconciles that history with current owners;
MIP-era throttles, encodings, and join assumptions are not restored by reference. Restoration is tracked in
[#14](https://github.com/marmot-protocol/marmot/issues/14); the broader assurance program is
[#457](https://github.com/marmot-protocol/marmot/issues/457).

Read the [overview assumptions](#assumptions) and [intended properties](#intended-properties-and-limits), then use the
[detailed scenario catalogue](#detailed-scenario-catalogue), [historical disposition index](#historical-scenario-disposition),
and [surface coverage](#surface-coverage) to follow individual risks and their owners.

## Assets

| Asset | Meaning |
| --- | --- |
| Content and keys | Application/media plaintext, MLS private state, exporter-derived secrets, account signing keys, device leaf keys, and unconsumed KeyPackage private material. |
| Identity and authority | Account-to-leaf binding, authenticated message authorship, membership, active-admin authority, and approved device enrollment. |
| Canonical state | The selected branch, epoch, components, capabilities, and lifecycle derived from authenticated input. |
| Recoverable work | Unresolved publication, retained dependencies, local action gates, dispositions, and effective application outputs across interruption. |
| Availability | Ability to acquire input, resolve retained work, deliver content, and recover under the protocol's stated conditions. |
| Metadata | Membership and device relationships, group routing, IP addresses, endpoint contacts, message timing/size, and external-service access patterns. |

## Actors and trust boundaries

| Actor or boundary | Capabilities and limits |
| --- | --- |
| Network observer or active attacker | Observes reachable traffic and may delay, partition, replay, inject, or suppress it. Scope includes colluding observation points; it does not assume one honest network path exists. |
| Relay or discovery provider | Can return stale, incomplete, reordered, duplicated, or hostile objects; acknowledge and later discard accepted bytes; censor users; and correlate connections. Authentication of an object is separate from completeness of discovery or retained history. |
| Outsider | Can discover public delivery coordinates, submit transport objects and invitations, and cause validation or decryption work. Knowing a routing address is not group membership. |
| Current member | Knows its available group secrets and plaintext, can disclose them, issue the operations permitted to its leaf/account, and withhold or compete with valid input. Member authentication does not make its content trustworthy. |
| Active administrator | Can exercise the authority granted by the candidate parent's policy, including harmful but authorized membership or policy changes. Admin status does not bypass resulting-state invariants or terminal lifecycle rules. |
| Former member | Retains any plaintext, old keys, files, or external credentials it copied. Removal changes protocol membership; it does not erase those copies or automatically revoke independent service capabilities. |
| Compromised device | Exposes the private state available on that device and its current protocol authority. Continued compromise is different from a past compromise followed by recovery and erasure. |
| Compromised account key | Can authorize new account-to-leaf proofs and published KeyPackages. This is not limited to the MLS state of one existing device, and an account signature alone cannot establish that a device was user-approved. |
| Blob, broker, notification, or endpoint service | Controls its own delivery/storage/dispatch behavior, sees service-specific metadata, and may attack clients that connect to it. An authenticated locator or credential is not evidence that contacting the service is safe. |
| Local host and application | Controls plaintext presentation, key custody, network policy, recovery and effective observation. The protocol does not isolate secrets from a compromised OS, a hostile local application, or the user exporting them. |

## Assumptions

| ID | Assumption and scope | Owner or analysis boundary |
| --- | --- | --- |
| A1 | The selected cryptographic primitives and MLS construction satisfy the security properties being relied on; implementations validate them correctly. This is an inherited cryptographic assumption, not a result established here. | [MLS profile](foundation/mls-protocol.md), [RFC 9420 security considerations](https://www.rfc-editor.org/rfc/rfc9420.html#section-16). |
| A2 | Randomness, private-key custody, nonce handling, and required key deletion work as specified. Copies in backups, compromised hosts, or hostile peers are outside a client's erasure control. | [KeyPackages](foundation/key-packages.md#selection-and-lifecycle), [encrypted media](features/encrypted-media.md#encryption); host/implementation boundary. |
| A3 | Account signatures establish account-key authorization; the user/client separately establishes whether that account, inviter, or device is the intended one. | [Identity](foundation/identity.md), [Welcome trust](protocol-core/joining.md#welcome-bootstrap-trust), [device sender rules](app-components/account-devices-v1.md#sender-rules). |
| A4 | Compared convergence executions have the same policy, retained anchor, authenticated frozen inputs and dependencies; progress additionally needs eventual relevant-input closure and acquisition within the applicable horizons. | [Convergence guarantees](protocol-core/convergence.md#guarantees-and-assumptions). |
| A5 | Clients continue executing, revisit required work, and have the resources and recovery material needed by the claimed progress property. Fairness is a premise to justify, not something that timers or a proof can supply. | [Convergence guarantees](protocol-core/convergence.md#guarantees-and-assumptions), [durability](protocol-core/durability.md). |
| A6 | The client can recover or reconstruct the protocol facts required at an observer boundary. Permanent corruption or loss of required facts is different from a normal process crash. | [Recoverable facts](protocol-core/durability.md#recoverable-protocol-facts), [missing material](protocol-core/durability.md#missing-or-corrupt-material). |
| A7 | A transport binding accurately exposes its specified acknowledgement to the client. That signal proves neither honest long-term retention nor recipient delivery, and cannot force a hostile service to retain bytes. | [Publish obligation](protocol-core/publish-lifecycle.md#publish-obligation), [Nostr acknowledgements](transports/nostr.md#publish-targets-and-acknowledgements). |
| A8 | Local connection policy and host protections are enforced at the point of network access. Component validity and a valid signature alone do not establish endpoint safety. | [Relay URL policy](transports/nostr.md#relay-url-profile), [media validation](features/encrypted-media.md#validation), [QUIC trust](transports/quic.md#connection-and-trust); shared policy work remains [#74](https://github.com/marmot-protocol/marmot/issues/74). |

The current required MLS suite and account proof are classical constructions. This model makes no end-to-end
post-quantum claim. Changing only an MLS suite would not, by itself, establish a new security argument for account
identity. The current constructions are owned by [MLS protocol](foundation/mls-protocol.md#required-ciphersuite) and
[account proof v2](app-components/account-identity-proof-v2.md); future choices remain
[#413](https://github.com/marmot-protocol/marmot/issues/413).

## Intended properties and limits

| ID | Intended boundary | Premises, limits, and normative owners |
| --- | --- | --- |
| G1 | Outsiders without the relevant secrets cannot read protected group or media content under the selected construction. | A1–A2. This excludes leakage by a member, retained decryption material, and endpoint compromise. [MLS profile](foundation/mls-protocol.md), [media](features/encrypted-media.md), [transport confidentiality](transports/README.md). |
| G2 | Accepted leaves bind an account to the exact MLS signature key, and delivered app authors match the authenticated MLS sender. | A1–A3. An identity proof is not human identity verification, user consent, benign content, or group continuity. [Identity](foundation/identity.md#account-identity-proof), [receiver authentication](foundation/application-messages.md#receiver-authentication). |
| G3 | Accepted state changes follow parent-relative authority and complete resulting-state validation. | A1–A3. Authorized administrators or same-account devices may still act maliciously within their powers. [Authorization evaluation](app-components/README.md#authorization-evaluation), [admin policy](app-components/admin-policy-v1.md), [account devices](app-components/account-devices-v1.md). |
| G4 | Equal admitted evidence under the stated convergence conditions yields equal canonical selection and dispositions. | A4. Local settlement is not global finality; different or incomplete evidence is not equivalent input. [Convergence](protocol-core/convergence.md#guarantees-and-assumptions), [conformance](foundation/conformance.md). |
| G5 | Interruption does not manufacture publication success, expose partial application, or duplicate an effective application output. | A6–A7. The contract is observer equivalence, not one physical callback or a prescribed storage transaction. [Publish lifecycle](protocol-core/publish-lifecycle.md), [durability](protocol-core/durability.md). |
| G6 | Continued execution under the stated closure, history, policy, and resource assumptions eventually reaches the specified equivalent canonical result. | A4–A6. Permanent suppression, endless relevant competition, or exhausted resources defeats these progress premises without relaxing safety. [Convergence guarantees](protocol-core/convergence.md#guarantees-and-assumptions). |
| G7 | Protocol surfaces minimize and constrain exposed metadata according to their owning rules. | A2, A8. This is not anonymity, traffic-analysis resistance, or unlinkability across colluding observers. [Identity/address separation](foundation/identity.md#delivery-addressing-is-separate), [Nostr exposure](transports/nostr.md#metadata-exposed-to-the-transport). |

Forward secrecy and post-compromise security are inherited MLS goals with conditions, not blanket claims about every
retained message or future epoch. Their application depends on which secrets were exposed, subsequent honest key
updates, attacker access, and erasure. Retaining past-epoch material for recovery deliberately extends exposure for
that retained material. See [retained history](protocol-core/retained-history.md),
[post-join behavior](protocol-core/joining.md#receiving-flow), and
[RFC 9420](https://www.rfc-editor.org/rfc/rfc9420.html#section-16). Automatic eviction and related lifecycle questions
remain tracked in [#411](https://github.com/marmot-protocol/marmot/issues/411).

## Threat and residual-risk map

### T1. Network observation, discovery, and traffic correlation

Observers and colluding relays target metadata even without defeating G1. TLS protects a connection under its trust
model, but the service sees its peer and its own application-level traffic. Random routing and fresh envelope keys do
not hide timing, message sizes, connection patterns, or all relationships between observations. Nostr also exposes
group routing handles, recipient inbox addressing, account-authored KeyPackages, publication-slot counts and optional
client metadata; retention hints reveal additional information. G7 does not promise anonymity.

Owners: [Nostr metadata](transports/nostr.md#metadata-exposed-to-the-transport),
[account addressing](foundation/identity.md#delivery-addressing-is-separate), and
[KeyPackage slots](foundation/key-packages.md#devices-and-publication-slots). Application network isolation and
privacy choices remain outside group-state validity. Discovery/session privacy proposals are
[#415](https://github.com/marmot-protocol/marmot/issues/415) and
[#414](https://github.com/marmot-protocol/marmot/issues/414).

### T2. Relay equivocation, replay, suppression, and false confidence in acknowledgements

A relay can supply different histories to different clients, replay envelopes, or acknowledge bytes and later discard
them. G2–G5 rely on inner authentication, stable protocol message identities and preserved obligations, not relay
honesty. Redundant delivery reduces dependence on one endpoint but does not establish that any honest or available
path exists. Equal epochs or a local `Settled` state do not prove complete history acquisition or exact state equality.

Owners: [Nostr replay](transports/nostr.md#duplicate-and-replay-handling),
[message identity](protocol-core/inbound-processing.md#message-identity),
[acknowledgements](protocol-core/publish-lifecycle.md#publish-obligation), and
[conformance equality](foundation/conformance.md#canonical-snapshot). Residual risk: A4–A7 can fail, leaving a client
blocked, unable to acquire missing evidence, or outside the progress guarantee.

Complete transport retention is not complete application history. A conforming client can lose the ability to decrypt
older app payloads after they leave its retained epoch window, even if a relay still holds their bytes. Applications
needing longer offline history need a separate mechanism; see
[app-payload retention](protocol-core/retained-history.md#app-payload-retention).

### T3. Invitation abuse, stale packages, and first-contact group substitution

Outsiders or hostile members can send invitations, serve obsolete packages, or construct an authentic branch that is
not the group continuation a joiner intended. Validation binds account and leaf under G2; it does not prove the
inviter's human identity or an external group-continuity anchor. The current Welcome author is the first-contact trust
root. Even another account speaking on the received branch is only an activity signal, not continuity proof.

Owners: [Welcome-bootstrap trust](protocol-core/joining.md#welcome-bootstrap-trust),
[Welcome failures](protocol-core/joining.md#failure-behavior), and
[KeyPackage selection](foundation/key-packages.md#selection-and-lifecycle). Under A3, inviter presentation and user
decisions matter; valid package publication does not prove user-approved device enrollment.

### T4. Device, account-key, and reusable KeyPackage compromise

Compromise exposes what the attacker obtains, with different consequences for an account key, one leaf's MLS state, or
one KeyPackage `init_key`. Reusable last-resort packages trade join availability for a wider exposure window: obtaining
their private `init_key` before deletion exposes recorded Welcomes encrypted to that package and the join secrets
inside them. The package's deletion bounds and replacement grace period limit this intended retention; a published
deletion does not revoke a copy held elsewhere. An `init_key` alone does not imply indefinite access after the other
leaf state changes or is erased.

Owners: [KeyPackage lifecycle](foundation/key-packages.md#selection-and-lifecycle),
[stopping publication](foundation/key-packages.md#stopping-publication),
[account identity](foundation/identity.md#account-identity-proof), and
[device sender rules](app-components/account-devices-v1.md#sender-rules). A1–A3 and later honest updates are essential;
this overview promises neither recovery during continued compromise nor recovery from account-key theft by a mere
MLS leaf update.

### T5. Malicious members, administrators, and same-account devices

Members can copy and disclose content, submit harmful authenticated app payloads, withhold traffic, and issue valid
competing Commits. Administrators can exercise harmful authorized powers. G3 checks authority, not good intent.
Account-wide admin rights apply to its device leaves. Where account-devices is required, a stolen current member
device can add or remove same-account leaves within that component's powers; other receivers cannot enforce the
sender's private device-approval decision. No device has superior account authority merely by being older or primary.

Owners: [active admins](app-components/admin-policy-v1.md#active-admins),
[account-device security](app-components/account-devices-v1.md#security-considerations),
[member departure](protocol-core/member-departure.md), and
[app authentication](foundation/application-messages.md#receiver-authentication). Removing a leaf or disbanding a
group does not erase plaintext or credentials it already copied. Sender authentication does not make embedded links,
instructions, displayed system notices or agent requests safe; display/provenance questions remain
[#75](https://github.com/marmot-protocol/marmot/issues/75) and
[#412](https://github.com/marmot-protocol/marmot/issues/412).

Deterministic branch ordering is not a fairness lottery or protection against every form of grinding: a committer can
influence the digest used for an otherwise tied branch. The
[account-device security considerations](app-components/account-devices-v1.md#security-considerations) explicitly
describe that case. Neither G3 nor G4 promises an administrative action will prevail during unbounded valid competition.

### T6. Input flooding and availability pressure

An outsider can learn the Nostr routing handle and send envelopes that reach validation and trial decryption.
Cryptographic rejection does not make that bandwidth/CPU work free or provide a member-authenticated admission filter.
An insider can also keep producing valid selection-relevant work. G4–G5 remain safety boundaries; G6 depends on A4–A5.

Owners: [Nostr group delivery](transports/nostr.md#group-message-delivery) and
[convergence guarantees](protocol-core/convergence.md#guarantees-and-assumptions). Operational admission, input and
resource budgets do not silently change authenticated validity or canonical branch scoring. The design question in
[#455](https://github.com/marmot-protocol/marmot/issues/455) is unresolved. The old threat model's self-update processing
throttle is not an adopted solution or a progress proof for this specification.

### T7. Crash, incomplete recovery, and rollback of externally visible work

A process crash can lose volatile progress after bytes or outputs became visible. Permanent loss/corruption may remove
facts that cannot be reconstructed. G5 requires recovery of uncertain obligations and complete observer projections,
not guessing success or selecting the only branch left on disk. Resuming an uncertain publication reuses its exact
bytes; reconstructing app effects preserves their stable effective identities. A6 does not assume arbitrary storage
corruption is harmless.

Owners: [publish interruption](protocol-core/durability.md#publish-interruption-boundaries),
[observer atomicity](protocol-core/durability.md#observer-atomic-transitions),
[missing material](protocol-core/durability.md#missing-or-corrupt-material), and
[application observation](protocol-core/durability.md#application-effects-after-restart). Temporary blocking and
permanent `Unrecoverable` are distinct safe outcomes, not equivalent claims of availability.

### T8. External media, shared credentials, and deletion limits

Blob services can suppress or replace bytes and correlate uploads/downloads. The owning media authentication/hash
rules protect accepted content under A1–A2, independently of the locator; they do not force a service to serve it.
Authenticated locators can still direct a client toward a tracking or unsafe endpoint (A8).

The group-image v1 upload credential is shared with members. A former member retaining it can continue using the
server's accepted write/delete authority; an admin gate on group-state updates cannot revoke that capability.
Replacement under a fresh credential can restore the reference's availability but cannot erase copied content.
Disappearing messages and moderation affect conforming applications, not hostile recipients, screenshots or backups.

Owners: [group-image capability](app-components/group-blossom-image-v1.md),
[media validation](features/encrypted-media.md#validation),
[media nonce rules](features/encrypted-media.md#encryption),
[retention](app-components/message-retention-v1.md#state), and
[draft moderation](features/content-moderation.md). Retroactive deletion proposals remain
[#418](https://github.com/marmot-protocol/marmot/issues/418).

Epoch advancement also does not automatically replace an existing group-image key or erase a recipient's saved media
key. The confidentiality of a stored object follows its own key's exposure and lifecycle, not merely the current MLS
epoch; see [image bytes](app-components/group-blossom-image-v1.md#image-bytes) and
[media key derivation](features/encrypted-media.md#key-derivation).

### T9. Preview brokers and group-shared stream keys

Experimental QUIC previews add an untrusted endpoint and broker boundary. TLS authenticates the hop according to its
configured trust; it does not establish MLS authorship. The group-shared preview key protects content from outsiders
and brokers without that key, but any current member can derive it and forge preview records. Sequence/transcript
checks do not make a preview sender-authenticated against another member. The final MLS message is authoritative.

Owners: [preview authenticity](features/agent-text-streams-quic.md#preview-authenticity),
[final message](features/agent-text-streams-quic.md#final-message), and
[QUIC trust](transports/quic.md#connection-and-trust). Room routing, injection and access-control questions remain
[#344](https://github.com/marmot-protocol/marmot/issues/344) and
[#78](https://github.com/marmot-protocol/marmot/issues/78). G1 here depends on the experimental construction and A1–A2;
it adds no stronger member-authentication or availability guarantee.

### T10. Notification service and platform trust

Push is optional and advisory. Token gossip adds group-visible metadata and encrypted server-specific token material;
the designated notification server decrypts the platform tokens it serves and participates in dispatch with the
platform provider. Encryption to that server does not hide those tokens from it or establish unlinkability of dispatch
and connection patterns. A malicious member or service can generate, suppress, replay or correlate hints subject to
the feature's validation rules. Push success or failure does not decide group state.

Owners: [notification behavior](features/push-notifications.md#behavior),
[token encryption](features/push-notifications.md#token-encryption),
[owner authentication](features/push-notifications.md#owner-authentication), and
[validation](features/push-notifications.md#validation). A1–A2 protect the specified token envelope, not the server,
platform or user's device against compromise; endpoint contacts remain subject to A8.

### T11. Local software, external signers, and incompatible profiles

A hostile client update, unsafe parser, side channel, or compromised local key store can violate A1–A2 without breaking
the abstract protocol. Reviewing a state-machine model does not establish memory safety, constant-time cryptography,
software-distribution integrity, or protection from malicious local software. Those require implementation and platform
evidence in addition to protocol analysis.

An external account signer is another boundary: a producer checks that the returned event exactly matches the request
and validates its id and signature before using the proof. A valid returned signature does not itself prove the user's
informed consent. Proofs bind their class and context, and different authority classes cannot be substituted simply
because their envelopes share an encoding; see [authorization proofs](foundation/authorization-proofs.md).

Incompatible or misunderstood required features fail through capability and resulting-state checks. Unknown optional
component bytes remain preserved, not reinterpreted as understood or silently rewritten. Superseded encodings and
experimental profiles do not acquire current-profile authority by appearing in this repository. Owners:
[negotiation](app-components/README.md#negotiation), [unknown data](app-components/README.md#unknown-data),
[proof versioning](foundation/authorization-proofs.md#versioning), and
[canonical encodings](foundation/canonical-encoding.md). Application resource limits remain separate from deterministic
protocol validity; rejecting a locally unsupported operation does not authorize rewriting the group's requirements.

## Detailed scenario catalogue

This catalogue complements the overview above. SC identifiers are stable references; titles and grouping may evolve,
but an identifier is not reused for a different threat. Each entry states an attack path and a concrete candidate
check. The historical index below accounts for every named scenario in the pre-reorganization document.

**Verification status:** `Unverified` means this PR links no scenario-specific model-check, proof, implementation-test,
or deployment result. Existing evidence may exist elsewhere; it has to be linked and scoped before upgrading that
status. `External assumption` identifies a primitive, platform, or software-trust premise that ordinary conformance
runs cannot establish. A proposed check is work to perform, not a result. The documentation CI checks structure and
links only. Mitigations summarize current owners or explicitly identify local implementation choices; this catalogue
adds no protocol requirement and contains no claim of an exhaustive universe of attacks.

| Scenarios | Subject |
| --- | --- |
| [SC-001](#sc-001)–[SC-010](#sc-010) | Admission, discovery, network observation, relay/member abuse and saved content. |
| [SC-011](#sc-011)–[SC-018](#sc-018) | Admin/device authority, policy changes, disband, competing branches and invalid state. |
| [SC-019](#sc-019)–[SC-030](#sc-030) | Device/account compromise, retained secrets, recovery and join lifecycle. |
| [SC-031](#sc-031)–[SC-045](#sc-045) | Event keys, replay, media and transport metadata. |
| [SC-046](#sc-046)–[SC-057](#sc-057) | Cryptographic assumptions, parser/version boundaries, updates and device privacy. |
| [SC-058](#sc-058)–[SC-068](#sc-068) | Current Welcome, endpoint, crash, capability, preview, push and signer boundaries. |

<a id="sc-001"></a>

### SC-001. Invalid KeyPackage discovery flood

- **Attacker and prerequisites:** An outsider publishes many malformed package objects to a discovery source;
  client bandwidth and validation CPU are the assets.
- **Attack sequence:** The client queries for candidates, downloads hostile objects, and spends work validating
  them before an invitation can proceed.
- **Affected property and assumptions:** G2 requires validation; G6 still depends on resource assumption A5.
- **Mitigations:** Reject invalid candidates before ranking or use. Caching and bounded discovery are
  operational defenses, not new package-validity rules.
- **Residual risk:** A valid signature or client-initiated lookup does not make hostile discovery free or
  guarantee a usable result.
- **Normative owners:** [KeyPackages](foundation/key-packages.md#failure-behavior), [Nostr
  transport](transports/nostr.md#keypackage-publication).
- **Verification status:** Unverified — candidate check: generate a mixed malformed/valid candidate corpus and
  measure work separately from acceptance; no availability result is established.

<a id="sc-002"></a>

### SC-002. Package author, credential, and leaf-key substitution

- **Attacker and prerequisites:** An outsider can publish or replace a candidate envelope and wants membership
  attributed to another account.
- **Attack sequence:** It pairs a package with the wrong outer author, credential identity, or account-to-leaf
  proof; the inviter is induced to select it.
- **Affected property and assumptions:** G2–G3 depend on A1–A3 and all binding checks, not just a valid outer
  signature.
- **Mitigations:** Validate the transport author against the credential and validate the account proof for the
  exact MLS leaf signature key before selection.
- **Residual risk:** Holding the real account signing key can produce valid proofs; binding does not establish
  human identity or approved-device consent.
- **Normative owners:** [KeyPackages](foundation/key-packages.md#failure-behavior),
  [Identity](foundation/identity.md#account-identity-proof), [Account proof
  v2](app-components/account-identity-proof-v2.md).
- **Verification status:** Unverified — candidate check: mutate each binding independently and require refusal
  without membership mutation.

<a id="sc-003"></a>

### SC-003. Inbox gift-wrap decryption flood

- **Attacker and prerequisites:** An outsider knows an account inbox and submits many encrypted gift wraps; the
  recipient has no trusted sender prefilter.
- **Attack sequence:** The client receives apparently addressed envelopes, unwraps them, and finds unusable or
  unwanted Welcome content.
- **Affected property and assumptions:** G2 rejects invalid joins; G6 is conditional on A5 and does not promise
  spam resistance.
- **Mitigations:** Apply the binding and Welcome validation rules. Relay admission and local resource budgets
  are operational choices with their own privacy costs.
- **Residual risk:** Wrapping hides useful admission information; proof-of-work or relay authentication is not a
  universally effective protocol guarantee.
- **Normative owners:** [Nostr transport](transports/nostr.md#welcome-delivery),
  [Joining](protocol-core/joining.md#receiving-flow).
- **Verification status:** Unverified — candidate check: exercise invalid, wrong-device, and valid Welcomes in
  the same inbox; verify safe refusal and that useful work remains distinguishable.

<a id="sc-004"></a>

### SC-004. Public group-route ciphertext flood

- **Attacker and prerequisites:** An outsider learns the current routing handle and can submit signed transport
  envelopes; bandwidth and trial-decryption CPU are exposed.
- **Attack sequence:** It sends valid-looking group-route objects with invalid inner ciphertext, forcing work
  before the recipient can reject them.
- **Affected property and assumptions:** G1–G3 protect content and acceptance under A1; G6 does not establish
  member-only admission or unlimited capacity.
- **Mitigations:** Validate outer shape and signatures before peeling and authenticate recovered content. Treat
  admission redesign as an open decision in #455.
- **Residual risk:** An ephemeral transport signature is not membership. The old multiple-current-route
  suggestion is not the v1 routing format.
- **Normative owners:** [Nostr transport](transports/nostr.md#group-message-delivery), [Nostr
  transport](transports/nostr.md#validation-before-peeling), [Nostr
  routing](app-components/nostr-routing-v1.md#routing-rotation).
- **Verification status:** Unverified — candidate check: separate malformed outer envelopes from valid outer
  envelopes with invalid ciphertext and account for work at both boundaries.

<a id="sc-005"></a>

### SC-005. IP-based membership inference

- **Attacker and prerequisites:** A relay or colluding observer sees network peers associated with subscriptions
  or publishes to a group route; metadata is the asset.
- **Attack sequence:** It correlates recurring IP addresses and routing handles, then joins observations across
  endpoints to infer participation.
- **Affected property and assumptions:** G7 constrains specified exposure under A8 but promises neither
  anonymity nor membership hiding against traffic analysis.
- **Mitigations:** Keep group routing independent of identity and use fresh event keys. Network isolation or
  anonymity services are local deployment choices.
- **Residual risk:** Shared IPs can create false associations; separate addresses or encrypted payloads do not
  eliminate correlation.
- **Normative owners:** [Identity](foundation/identity.md#delivery-addressing-is-separate), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: inventory observable fields and connection metadata; a
  future privacy experiment must state its observer and distinguish inference from proof.

<a id="sc-006"></a>

### SC-006. Publication timing and burst correlation

- **Attacker and prerequisites:** A passive observer or relay can collect timing at several points and compare
  it with known external events.
- **Attack sequence:** It aligns publication, subscription and burst patterns to infer likely senders,
  conversation activity, or coordinated behavior.
- **Affected property and assumptions:** G7 is metadata minimization, not timing anonymity; A8 includes the
  network-path boundary.
- **Mitigations:** The binding limits explicit identifiers. Delays or cover traffic would require a separately
  evaluated application/deployment design.
- **Residual risk:** Fresh keys do not hide timing. The historical suggested random-delay range and
  cover-traffic requirement are not adopted rules.
- **Normative owners:** [Nostr transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: document the timing observations available to each
  actor; do not label ordinary functional tests as a traffic-analysis proof.

<a id="sc-007"></a>

### SC-007. Censoring, flooded, or unavailable relays

- **Attacker and prerequisites:** An operator controls a relay or an attacker can exhaust selected relays;
  message acquisition and availability are at risk.
- **Attack sequence:** The attacker drops or selectively serves required objects, or makes endpoints unavailable
  while other clients observe a different history.
- **Affected property and assumptions:** G4 needs equal evidence (A4); G6 additionally needs delivery, continued
  execution and resources (A5).
- **Mitigations:** Required delivery bindings support redundancy and specify fanout. Inner validity and
  retained-history rules remain independent of endpoint behavior.
- **Residual risk:** Every selected path may fail or collude. Acknowledgement is not honest retention, and this
  model adds no automatic relay-removal policy.
- **Normative owners:** [Wire envelopes](foundation/wire-envelopes.md#redundant-delivery), [Nostr
  transport](transports/nostr.md#publish-targets-and-acknowledgements),
  [Convergence](protocol-core/convergence.md#guarantees-and-assumptions).
- **Verification status:** Unverified — candidate check: run selective suppression, endpoint loss and
  partial-history scenarios, requiring safe unresolved outcomes when progress premises fail.

<a id="sc-008"></a>

### SC-008. Authenticated member message and proposal spam

- **Attacker and prerequisites:** A current member has legitimate sending/proposal authority and group secrets;
  client resources and usable application output are exposed.
- **Attack sequence:** It sends many valid messages or permitted but unwanted proposals and forces peers to
  validate, retain, or display work.
- **Affected property and assumptions:** G2 authenticates the member, not benign behavior; G3 checks each
  proposal and committer separately; G6 needs A5.
- **Mitigations:** Enforce proposal and Commit authorization and resulting-state validity. Filtering and
  resource budgets do not invent alternate canonical rules.
- **Residual risk:** A member can use its legitimate powers maliciously. Removing it is itself an authorized,
  published transition, not instantaneous spam prevention.
- **Normative owners:** [Component framework](app-components/README.md#authorization-evaluation), [Member
  departure](protocol-core/member-departure.md#selfremove-commits), [Application
  payloads](foundation/application-messages.md#message-kinds).
- **Verification status:** Unverified — candidate check: mix valid unwanted proposals with unauthorized
  proposals and check that refusal, retained work, and application policy stay distinct.

<a id="sc-009"></a>

### SC-009. Insider disclosure of routing, membership, or tree state

- **Attacker and prerequisites:** A current or former member has copied group metadata, identities, routing
  information, or public ratchet-tree state.
- **Attack sequence:** It exports that material to an outsider, who correlates public account identities or
  targets previously hidden group activity.
- **Affected property and assumptions:** G1 does not protect information from an authorized recipient; G7 is not
  protection against insider disclosure.
- **Mitigations:** Transport encryption and identity-separated routing reduce unsolicited outsider exposure, but
  do not prevent an insider exporting decrypted state.
- **Residual risk:** Public account keys do not make the relationship between those accounts public or harmless;
  route rotation cannot undo a disclosed relationship.
- **Normative owners:** [Identity](foundation/identity.md), [MLS
  profile](foundation/mls-protocol.md#handshake-wire-format), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: audit which metadata each role learns and whether each
  additional external disclosure is required by the owning surface.

<a id="sc-010"></a>

### SC-010. Saved plaintext and noncompliant disappearing messages

- **Attacker and prerequisites:** A member or relay keeps received bytes, plaintext, screenshots, or exports;
  requested retention and historical privacy are the assets.
- **Attack sequence:** A recipient ignores expiry or copies content before deletion; a relay continues serving
  an expired object; later removal does not erase those copies.
- **Affected property and assumptions:** G1 excludes member disclosure. G3 authenticates the retention policy
  but cannot force hostile erasure; A2 excludes uncontrolled copies.
- **Mitigations:** Apply the source-epoch retention policy and preserve protocol evidence until its own release
  conditions. Draft moderation governs conforming display only.
- **Residual risk:** Sender-chosen timestamps can shift advisory expiry; local deletion does not erase backups
  or external blobs. No database setting is mandated here.
- **Normative owners:** [Message retention](app-components/message-retention-v1.md#state), [Message
  retention](app-components/message-retention-v1.md#validation), [Draft
  moderation](features/content-moderation.md#authorization-and-existing-protocol-rules), [Retained
  history](protocol-core/retained-history.md#retained-cryptographic-material).
- **Verification status:** Unverified — candidate check: check source-epoch expiry, sender timestamp boundaries
  and separation of app cleanup from retained protocol facts; hostile-recipient erasure is not testable as a
  guarantee.

<a id="sc-011"></a>

### SC-011. Socially engineered or maliciously authorized member addition

- **Attacker and prerequisites:** An active admin is malicious or is deceived about an account identity or
  invitation; group confidentiality and membership intent are at risk.
- **Attack sequence:** The admin signs a valid Add for the attacker, and conforming peers accept it because the
  account has the required authority.
- **Affected property and assumptions:** G3 establishes protocol authority under A3, not unanimous consent,
  identity vetting, or good intent.
- **Mitigations:** Validate identity/capabilities and the candidate-parent admin authority; applications can
  present identities and changes to support informed decisions.
- **Residual risk:** Multiple admins are not a quorum or veto mechanism. A cryptographically authorized addition
  can still violate the members' social expectations.
- **Normative owners:** [Admin policy](app-components/admin-policy-v1.md#admin-gated-actions),
  [Identity](foundation/identity.md#capability-negotiation), [Joining](protocol-core/joining.md).
- **Verification status:** Unverified — candidate check: distinguish unauthorized Add refusal from a valid but
  unwanted Add; verify identity presentation does not claim stronger approval than exists.

<a id="sc-012"></a>

### SC-012. Malicious administrator removes a legitimate account or device

- **Attacker and prerequisites:** An active admin can commit removals; a legitimate member's continued
  participation is the asset.
- **Attack sequence:** The admin removes the target leaf or account and publishes a valid Commit, excluding the
  target when the selected transition is applied.
- **Affected property and assumptions:** G3 enforces authority and resulting-state invariants; it does not
  promise fairness or permanent access to every member.
- **Mitigations:** Authenticate the parent-state admin and preserve admin/leaf coupling. Re-invitation requires
  a valid new join; removal has its own terminal local effects.
- **Residual risk:** Another admin cannot guarantee reversal or retention of authority during competing changes.
  Rejoin is not automatic restoration of old cryptographic state.
- **Normative owners:** [Admin policy](app-components/admin-policy-v1.md#active-admins), [Member
  departure](protocol-core/member-departure.md#realizing-removal),
  [Joining](protocol-core/joining.md#receiving-flow).
- **Verification status:** Unverified — candidate check: check valid removal, last-leaf admin coupling, local
  removal realization and explicit rejoin boundaries.

<a id="sc-013"></a>

### SC-013. Additional device leaves retain or expand account access

- **Attacker and prerequisites:** A malicious admin, compromised member device, or stolen account key can supply
  more account leaves; device consent and revocation are the assets.
- **Attack sequence:** It adds another leaf before the original device is removed, or a stolen member device
  uses enabled same-account authority to add/remove sibling leaves.
- **Affected property and assumptions:** G3 limits shape and account scope, but A3 is needed for sender-side
  approval; account authority is shared across its leaves.
- **Mitigations:** Apply account-devices activation, support, leaf-cap and sender rules. Existing-group
  same-account Adds require authenticated user-approved device material at the sender.
- **Residual risk:** Other receivers cannot verify private device approval; founding creation has its stated
  exception. Removing one leaf does not remove every leaf of the account.
- **Normative owners:** [Account devices](app-components/account-devices-v1.md#sender-rules), [Account
  devices](app-components/account-devices-v1.md#security-considerations), [Member
  departure](protocol-core/member-departure.md#accounts-with-several-devices).
- **Verification status:** Unverified — candidate check: exercise sibling persistence, same-account shape
  restrictions, cap boundaries, founding exceptions and loss of activation on another branch.

<a id="sc-014"></a>

### SC-014. Authorized policy manipulation and social engineering of admin grants

- **Attacker and prerequisites:** An admin is malicious or induced to grant authority or change routing/profile
  state; canonical policy, metadata and availability are exposed.
- **Attack sequence:** It proposes a harmful but valid admin/relay/profile/image change, or tries to grant
  itself authority inside the same Commit before other operations are checked.
- **Affected property and assumptions:** G3 uses candidate-parent authority and complete resulting-state
  validity; authorization is separate from user approval (A3).
- **Mitigations:** Check each component's authority and cross-component invariants against the correct states. A
  new admin list cannot authorize its own committer retroactively.
- **Residual risk:** Valid harmful changes still succeed. Signed relay or image state does not make endpoints
  safe (A8), and multiple admins cannot guarantee reversal.
- **Normative owners:** [Component framework](app-components/README.md#authorization-evaluation), [Admin
  policy](app-components/admin-policy-v1.md#authorization), [Nostr routing](app-components/nostr-routing-v1.md),
  [Group profile](app-components/group-profile-v1.md), [Group image](app-components/group-blossom-image-v1.md).
- **Verification status:** Unverified — candidate check: try self-authorizing updates, unauthorized mixed
  operations, and valid but harmful changes; compare refusal with authorized acceptance.

<a id="sc-015"></a>

### SC-015. Authorized terminal disband and invalid attempts to destroy state

- **Attacker and prerequisites:** An active admin wants to terminate the group or produce unusable state;
  continued group activity and retained history are exposed.
- **Attack sequence:** It prepares a disband request or a malformed mass-removal state; clients must distinguish
  valid terminalization from invalid state or ordinary competing branches.
- **Affected property and assumptions:** G3 rejects invalid resulting state; G4–G5 govern selection and one
  effective terminal projection, not protection from an authorized disband.
- **Mitigations:** Use the lifecycle component's mandatory convergence pass, terminal tombstone and outbound
  gate. The admin cannot bypass validation with arbitrary empty state.
- **Residual risk:** A selected disband is absorbing; another admin cannot revive the same group. A replacement
  conversation needs a new group.
- **Normative owners:** [Group lifecycle](app-components/group-lifecycle-v1.md), [Group
  state](protocol-core/group-state.md#legal-transitions),
  [Durability](protocol-core/durability.md#observer-atomic-transitions).
- **Verification status:** Unverified — candidate check: check competing disband/nonterminal branches, no
  premature terminalization, terminal restart and exactly one effective disband presentation.

<a id="sc-016"></a>

### SC-016. Competing Commits, fork selection, and digest grinding

- **Attacker and prerequisites:** Members with allowed Commit authority create competing valid branches and can
  influence Commit bytes; canonical agreement and fair access are exposed.
- **Attack sequence:** They deliver branches in different orders or vary a tied Commit's bytes to influence the
  final digest tie-breaker.
- **Affected property and assumptions:** G4 gives deterministic agreement under A4, not fair random selection;
  G6 has explicit closure/resource premises.
- **Mitigations:** Apply current eligibility, witness and comparison order to authenticated branch evidence.
  Outer timestamps and event ids never choose the winner.
- **Residual risk:** Digest grinding can favor a tied branch. The historical earliest-timestamp race rule is
  superseded, and deterministic selection does not guarantee admin success under endless competition.
- **Normative owners:** [Convergence](protocol-core/convergence.md#branch-selection),
  [Convergence](protocol-core/convergence.md#same-epoch-races), [Account
  devices](app-components/account-devices-v1.md#security-considerations).
- **Verification status:** Unverified — candidate check: permute branch delivery and candidate enumeration,
  include tied scores and influenced digests, and check the same admissible result.

<a id="sc-017"></a>

### SC-017. Rapid valid state changes prevent progress or exhaust clients

- **Attacker and prerequisites:** A member with ordinary self-update authority or an admin repeatedly issues
  valid changes; finite work and administrative progress are the assets.
- **Attack sequence:** It keeps selection-relevant input open or consumes client work budgets faster than peers
  can settle and prepare queued actions.
- **Affected property and assumptions:** G4–G5 remain safety boundaries. G6 needs A4–A5; bounded preparation
  opportunity is not guaranteed canonical admin progress.
- **Mitigations:** Use fixed collection deadlines, immutable resolution batches and the specified preparation
  opportunity. Local budgets must not change branch validity or scoring.
- **Residual risk:** No adopted 60-second per-sender Commit-processing throttle supplies a progress proof.
  Endless valid competition can violate the closure premise.
- **Normative owners:** [Convergence](protocol-core/convergence.md#convergence-policy),
  [Convergence](protocol-core/convergence.md#guarantees-and-assumptions).
- **Verification status:** Unverified — candidate check: exercise continuing self-updates, queued privileged
  work and resource pressure; require explicit non-progress rather than selection from incomplete evidence.

<a id="sc-018"></a>

### SC-018. Malformed proposals or invalid complete resulting state

- **Attacker and prerequisites:** A member or admin can submit a structurally malformed or semantically
  inconsistent operation; canonical integrity and parser safety are the assets.
- **Attack sequence:** It packages invalid component bytes or incompatible leaf/admin/capability changes in a
  Commit, relying on its authority to bypass validation.
- **Affected property and assumptions:** G3 requires both authorization and complete resulting-state validation
  under A1, even for an admin.
- **Mitigations:** Reject malformed bytes and any candidate edge whose resulting state fails
  component/cross-component invariants; a valid signature is insufficient.
- **Residual risk:** Validation itself still costs resources, and parser memory safety is an implementation
  obligation covered separately in SC-052.
- **Normative owners:** [Component framework](app-components/README.md#groupcontext-update-processing), [Admin
  policy](app-components/admin-policy-v1.md#validation),
  [Convergence](protocol-core/convergence.md#candidate-branches).
- **Verification status:** Unverified — candidate check: mutate encodings, admin/leaf coupling and required
  support independently; verify refusal leaves the prior observer projection intact.

<a id="sc-019"></a>

### SC-019. Full device compromise enables plaintext access and impersonation

- **Attacker and prerequisites:** An attacker controls a current device and reads the state available there;
  keys, stored plaintext and that leaf's sending authority are exposed.
- **Attack sequence:** It extracts secrets, decrypts accessible traffic and sends valid messages as the
  compromised leaf until its authority or secrets are changed.
- **Affected property and assumptions:** G1–G2 assume uncompromised relevant secrets (A1–A2); a valid sender may
  be attacker-controlled.
- **Mitigations:** Host key protection limits exposure; protocol removal, honest updates and erasure govern
  later recovery. Attribute current authority to actual authenticated leaves.
- **Residual risk:** Removal or epoch advancement does not erase already stolen plaintext, account keys, backups
  or independent capabilities; recovery during continued compromise is not promised.
- **Normative owners:** [Identity](foundation/identity.md), [Member
  departure](protocol-core/member-departure.md#realizing-removal), [Retained
  history](protocol-core/retained-history.md#retained-cryptographic-material).
- **Verification status:** Unverified — candidate check: classify which secrets are exposed in a compromise
  experiment and which subsequent updates isolate them; do not claim universal recovery from one epoch
  increment.

<a id="sc-020"></a>

### SC-020. Account signing-key theft crosses application and device boundaries

- **Attacker and prerequisites:** An attacker obtains the Nostr account signing key, even without one device's
  current MLS state; account authorization is the asset.
- **Attack sequence:** It signs new account-to-leaf proofs and package publications or impersonates the same
  account in other applications that trust that key.
- **Affected property and assumptions:** G2 binds possession of the account key under A1–A3, not exclusive
  ownership; an MLS self-update does not rotate the Nostr account identity.
- **Mitigations:** Protect and validate the account signer boundary and require approved-device authentication
  where specified. Existing-group admission remains subject to valid authority and component rules.
- **Residual risk:** Cross-application effects depend on each application's key use; this spec supplies no
  universal account-key revocation/rotation recovery flow.
- **Normative owners:** [Identity](foundation/identity.md#account-identity-proof), [Account proof
  v2](app-components/account-identity-proof-v2.md), [Account
  devices](app-components/account-devices-v1.md#sender-rules).
- **Verification status:** Unverified — candidate check: check that account-key possession alone is not
  described as approved-device proof, and document the distinct recovery authorities rather than assuming a leaf
  update repairs account theft.

<a id="sc-021"></a>

### SC-021. Saved history, backups, and restore reintroduce exposed secrets

- **Attacker and prerequisites:** An attacker accesses a device archive or backup containing old keys/plaintext,
  or a user restores such material after local deletion.
- **Attack sequence:** It reads preserved conversations or reloads secrets that the live process had pruned,
  extending the practical exposure window.
- **Affected property and assumptions:** G1 and forward-secrecy arguments depend on A2; protocol pruning does
  not certify physical erasure of uncontrolled copies.
- **Mitigations:** Follow protocol release conditions and use appropriate host/backup protection. Treat restore
  as a recovery boundary and retain uncertain publication facts consistently.
- **Residual risk:** No SQLite setting, file deletion, or removal event guarantees erasure from snapshots,
  storage hardware or hostile recipients.
- **Normative owners:** [Retained history](protocol-core/retained-history.md#retained-cryptographic-material),
  [Durability](protocol-core/durability.md#recoverable-protocol-facts), [Message
  retention](app-components/message-retention-v1.md#validation).
- **Verification status:** Unverified — candidate check: inventory backup contents and replay restored work
  against durability rules; physical erasure and backup confidentiality need platform evidence.

<a id="sc-022"></a>

### SC-022. Temporary memory-only key extraction

- **Attacker and prerequisites:** An attacker can inspect process memory or a transient memory image without
  controlling persistent storage; live secrets are exposed.
- **Attack sequence:** It captures active epoch, media, or signing material, then loses device access while
  retaining the extracted values.
- **Affected property and assumptions:** A2 must be qualified by which secrets were resident; temporary
  compromise is not equivalent to every key in the account being stolen.
- **Mitigations:** Host isolation, restricted key exposure and appropriate memory handling are implementation
  defenses. Later recovery follows the affected keys' actual lifecycle.
- **Residual risk:** Clearing current memory cannot erase the attacker's copy; a hardware signer does not
  protect every derived group secret in process memory.
- **Normative owners:** [Retained history](protocol-core/retained-history.md#retained-cryptographic-material),
  [Identity](foundation/identity.md).
- **Verification status:** Unverified — candidate check: use a secret-specific exposure inventory and recovery
  analysis; no memory-isolation result is established by this document.

<a id="sc-023"></a>

### SC-023. Retained epoch material extends the forward-secrecy window

- **Attacker and prerequisites:** An attacker later obtains retained candidate-parent or application secret-tree
  material; recorded in-window traffic is the asset.
- **Attack sequence:** It combines captured bytes with secrets deliberately retained for replay or delayed
  application decryption.
- **Affected property and assumptions:** G1 depends on A1–A2 and release conditions; forward secrecy is not
  defined merely by removal or by erasing a public group record.
- **Mitigations:** Retain only the material still required for the owning function, then release it under
  retained-history rules; distinguish protocol release from physical overwrite.
- **Residual risk:** Retained private path/membership material and saved plaintext have different exposures.
  Removing a member does not retrospectively make its saved content secret.
- **Normative owners:** [Retained history](protocol-core/retained-history.md#retained-cryptographic-material),
  [Retained history](protocol-core/retained-history.md#pruning).
- **Verification status:** Unverified — candidate check: exercise horizon boundaries and active-work exceptions;
  verify released material is unavailable to protocol processing, while treating physical erasure separately.

<a id="sc-024"></a>

### SC-024. Persistent group-image keys and image metadata correlation

- **Attacker and prerequisites:** A current/former member retains an image key or discloses its hash; a blob
  observer can correlate requests for the same object.
- **Attack sequence:** After membership or epoch changes, the former member decrypts the unchanged image using
  its saved key or correlates later fetches for that image.
- **Affected property and assumptions:** G1 excludes retained keys; G7 does not promise that repeated
  content-address requests are unlinkable.
- **Mitigations:** Image replacement supplies a new key/credential when the image is changed. Keep component
  values confidential in transit and evaluate external fetch privacy separately.
- **Residual risk:** Epoch changes alone do not replace the image key, and fresh encryption does not hide
  service-visible accesses to one unchanged blob.
- **Normative owners:** [Group image](app-components/group-blossom-image-v1.md#image-bytes), [Group
  image](app-components/group-blossom-image-v1.md#update), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: keep an image across epoch/removal transitions and
  confirm the model does not assert loss of access by someone retaining its old key.

<a id="sc-025"></a>

### SC-025. Delayed or ineffective post-compromise key updates

- **Attacker and prerequisites:** An attacker has some previously exposed MLS secrets; a peer remains offline,
  fails to update, or continues using attacker-known material.
- **Attack sequence:** Updates are delayed or an unrelated epoch increment is mistaken for recovery; clients
  resume sensitive sending without checking which compromise was excluded.
- **Affected property and assumptions:** A1–A2 condition post-compromise recovery; G6 cannot force an offline
  peer to process an honest recovery update.
- **Mitigations:** Use the actual MLS recovery/key-update argument and required catch-up. KeyPackage slot
  freshness and MLS leaf/epoch changes are distinct lifecycles.
- **Residual risk:** Not every Commit automatically heals every compromise. No universal weekly MLS signing-key
  schedule or quorum confirmation rule is introduced here.
- **Normative owners:** [MLS profile](foundation/mls-protocol.md),
  [Joining](protocol-core/joining.md#receiving-flow),
  [KeyPackages](foundation/key-packages.md#refreshing-a-slot),
  [Convergence](protocol-core/convergence.md#guarantees-and-assumptions).
- **Verification status:** Unverified — candidate check: model distinct exposed-key sets and offline peers;
  require a precise recovery premise before asserting later content secrecy.

<a id="sc-026"></a>

### SC-026. Reusable or consumed init_key material exposes recorded Welcomes

- **Attacker and prerequisites:** An attacker obtains a retained KeyPackage private init_key and the
  corresponding MLS Welcome bytes; join secrets are exposed.
- **Attack sequence:** It decrypts recorded Welcomes, potentially across several groups when the last-resort
  package was reused, before that private material was deleted.
- **Affected property and assumptions:** G1 depends on A1–A2 and the package's lifecycle; public KeyPackage
  bytes alone are not the private init_key.
- **Mitigations:** Delete consumed non-last-resort private material and enforce last-resort replacement/lifetime
  deletion bounds; failed Welcome processing preserves the prior package state.
- **Residual risk:** Obtaining MLS Welcome bytes through Nostr may require outer-unwrapping material, but that
  is not an extra universal secrecy premise for every transport or attacker.
- **Normative owners:** [KeyPackages](foundation/key-packages.md#selection-and-lifecycle),
  [KeyPackages](foundation/key-packages.md#failure-behavior),
  [Joining](protocol-core/joining.md#failure-behavior).
- **Verification status:** Unverified — candidate check: check consumed/nonconsumed/last-resort cases,
  replacement confirmation, expiry and failure rollback independently; link a cryptographic analysis before
  claiming recovery.

<a id="sc-027"></a>

### SC-027. Stale package replay despite slot replacement or deletion

- **Attacker and prerequisites:** A relay can withhold a newer slot publication or retain a deleted package;
  future invitations and join availability are exposed.
- **Attack sequence:** An inviter sees an old still-valid candidate, selects it, and sends a Welcome whose
  private material may already be unavailable to the intended device.
- **Affected property and assumptions:** G2 requires validity/capability checks, not globally freshest
  discovery; A4–A5 do not guarantee complete relay acquisition.
- **Mitigations:** Validate before ranking and apply the slot replacement, freshness, Lifetime and
  private-material grace rules. A deletion request is not cryptographic revocation.
- **Residual risk:** A missed replacement can produce an undecryptable invite. Existing joined groups are not
  automatically replaced by stale discovery.
- **Normative owners:** [KeyPackages](foundation/key-packages.md#stopping-publication),
  [KeyPackages](foundation/key-packages.md#selection-and-lifecycle), [Nostr
  transport](transports/nostr.md#keypackage-publication).
- **Verification status:** Unverified — candidate check: replay older publications and deletions across
  inconsistent relays; check candidate ranking and invite refusal without mutation of existing groups.

<a id="sc-028"></a>

### SC-028. Welcome publication races and rejected first joins

- **Attacker and prerequisites:** An inviter or crashing client can expose a Welcome before an existing-group
  Add obligation is satisfied, or a receiver may reject after tentative MLS processing.
- **Attack sequence:** The joiner obtains post-Add state while peers lack the Commit, or failed validation
  consumes its package/overwrites retained active state.
- **Affected property and assumptions:** G4–G5 need A4, A6–A7; acknowledging a Commit still does not prove every
  peer received it.
- **Mitigations:** Follow publish-before-apply and Welcome delivery ordering, including founding
  empty-obligation exceptions. Keep join validation tentative and preserve exact prior package/state on
  rejection.
- **Residual risk:** Asynchronous delivery and losing-branch joins still need convergence/rejoin handling;
  sender order alone does not prove intended group continuity.
- **Normative owners:** [Joining](protocol-core/joining.md#delivery),
  [Joining](protocol-core/joining.md#receiving-flow),
  [Publication](protocol-core/publish-lifecycle.md#publish-obligation).
- **Verification status:** Unverified — candidate check: exercise early Welcome, lost acknowledgement,
  wrong-device package, retained-group-id collision and failure after MLS processing; check full rollback.

<a id="sc-029"></a>

### SC-029. Large groups or Welcomes exceed transport and device capacity

- **Attacker and prerequisites:** A legitimate or malicious membership workload grows tree/state and Welcome
  size; join availability, memory and processing capacity are exposed.
- **Attack sequence:** A valid full-tree Welcome exceeds an endpoint's limit, or valid group traffic overwhelms
  a constrained client before it can finish required processing.
- **Affected property and assumptions:** G3 validates state but supplies no universal capacity guarantee; G6
  requires A5.
- **Mitigations:** Honor required tree/format rules and evaluate declared transport/device limits. Local budgets
  may fail or block explicitly rather than select from partial evidence.
- **Residual risk:** There is no normative 150-member threshold, universal relay size cap, or adopted
  lightweight-Welcome escape hatch in this model.
- **Normative owners:** [Joining](protocol-core/joining.md#behavior),
  [Convergence](protocol-core/convergence.md#guarantees-and-assumptions), [MLS
  profile](foundation/mls-protocol.md).
- **Verification status:** Unverified — candidate check: measure actual serialized Welcomes and memory/work at
  target capacities, including explicit refusal and retry behavior, without inventing group-validity limits.

<a id="sc-030"></a>

### SC-030. Post-join self-update is delayed or confused with public package exposure

- **Attacker and prerequisites:** A new leaf has not yet performed its recommended post-join update; an attacker
  may hold private join material.
- **Attack sequence:** The client starts sending with its joined state and delays the update, lengthening
  reliance on that material; an operator incorrectly treats public package publication alone as secret
  compromise.
- **Affected property and assumptions:** A1–A2 condition confidentiality; public KeyPackage distribution is
  intentional and does not itself disclose its private key.
- **Mitigations:** Follow the current prompt/as-practical self-update guidance, preferably before app sending
  when feasible, and the separate private init_key deletion rules.
- **Residual risk:** The historical mandatory 24-hour interoperability deadline is not the adopted
  receiving-flow rule, and one update does not repair a stolen account key.
- **Normative owners:** [Joining](protocol-core/joining.md#receiving-flow),
  [KeyPackages](foundation/key-packages.md#selection-and-lifecycle).
- **Verification status:** Unverified — candidate check: check that delayed updates are surfaced consistently
  with current guidance and do not create invented protocol-invalid joins.

<a id="sc-031"></a>

### SC-031. Ephemeral transport event key reuse

- **Attacker and prerequisites:** A buggy or restored sender reuses one event signing key across Nostr group
  envelopes; sender unlinkability at the explicit-field boundary is exposed.
- **Attack sequence:** Observers match the repeated outer public key across messages or groups even though the
  content remains encrypted.
- **Affected property and assumptions:** G7 depends on A2 and the fresh per-event-key rule; G1 does not imply
  metadata anonymity.
- **Mitigations:** Generate a fresh event key per newly created group envelope and never use the account
  identity for that key. Republishing the same signed event remains one existing transport object.
- **Residual risk:** Fresh keys do not remove timing, IP or size correlation; retrying the identical event is
  distinct from reusing its key for a different event.
- **Normative owners:** [Nostr transport](transports/nostr.md#group-message-delivery), [Nostr
  transport](transports/nostr.md#publish-targets-and-acknowledgements).
- **Verification status:** Unverified — candidate check: compare keys of separately constructed events and
  distinguish byte-identical retry/fanout from new-event construction.

<a id="sc-032"></a>

### SC-032. Signed inner payload leakage and forged inner authorship

- **Attacker and prerequisites:** A buggy sender signs the inner app event, or a member supplies another account
  in its inner pubkey; content and correct attribution are exposed.
- **Attack sequence:** A recipient leaks a signed inner object as a reusable relay event, or a receiver displays
  a claimed inner author without binding it to the MLS sender.
- **Affected property and assumptions:** G2 requires receiver binding under A1–A3; avoiding an inner relay
  signature reduces one leak format, not all insider disclosure.
- **Mitigations:** Inner payloads omit sig and receivers reject a mismatched author. Inner tags do not control
  outer routing, but this model adds no blanket ban on inner h tags.
- **Residual risk:** Unsigned plaintext can still be copied, re-signed or published in other forms; omission of
  sig is not leak prevention or benign-content assurance.
- **Normative owners:** [Application payloads](foundation/application-messages.md#encoding), [Application
  payloads](foundation/application-messages.md#receiver-authentication), [Application
  payloads](foundation/application-messages.md#message-kinds).
- **Verification status:** Unverified — candidate check: reject sig-bearing and author-mismatched app payloads
  without invalidating unrelated MLS state processing; preserve allowed inner-tag semantics.

<a id="sc-033"></a>

### SC-033. Compromise of an exporter-derived outer envelope key

- **Attacker and prerequisites:** An attacker obtains the current Nostr group-event key or retained exporter
  material and recorded envelopes.
- **Attack sequence:** It removes the outer encryption layer and inspects recovered MLS bytes, or uses any
  additional stolen MLS state to decrypt app content.
- **Affected property and assumptions:** G1 has layered assumptions A1–A2; a derived outer key and all MLS
  private state are not equivalent exposures.
- **Mitigations:** Use the specified exporter label/context, preserve confidential carriage for public
  handshakes, and release material when its owning use expires.
- **Residual risk:** Inner protection depends on MLS content type: PublicMessage handshake bytes exposed by
  outer-key compromise are not still encrypted like PrivateMessage app payloads.
- **Normative owners:** [Nostr transport](transports/nostr.md#group-message-delivery), [MLS
  profile](foundation/mls-protocol.md#handshake-wire-format), [Retained
  history](protocol-core/retained-history.md#retained-cryptographic-material).
- **Verification status:** Unverified — candidate check: document exposure separately for handshakes and
  application messages; do not treat two layers as independent keys or a uniform confidentiality theorem.

<a id="sc-034"></a>

### SC-034. Replay under new outer event identities

- **Attacker and prerequisites:** A relay or member redelivers the same authenticated MLS bytes in duplicate or
  different transport envelopes.
- **Attack sequence:** The receiver keys deduplication on outer event identity and applies the inner transition
  or effective output twice.
- **Affected property and assumptions:** G4–G5 need stable protocol identity and recovery facts (A4, A6), not
  uniqueness of transport ids.
- **Mitigations:** Deduplicate on the recovered MLS bytes' protocol message identity and preserve required
  effect/terminal-input facts across restart.
- **Residual risk:** Distinct valid app/MLS messages are not duplicates merely because the human-visible content
  matches; rewrapping must not invent a new effective input.
- **Normative owners:** [Wire envelopes](foundation/wire-envelopes.md#message-ids), [Inbound
  processing](protocol-core/inbound-processing.md#message-identity),
  [Durability](protocol-core/durability.md#application-effects-after-restart).
- **Verification status:** Unverified — candidate check: replay identical MLS bytes with multiple outer ids and
  across restart; assert one effective application while retaining distinct legitimate messages.

<a id="sc-035"></a>

### SC-035. Compromised blob service observes or suppresses stored media

- **Attacker and prerequisites:** A blob operator or observer sees ciphertext object identifiers,
  uploads/downloads and network peers; content availability and access privacy are exposed.
- **Attack sequence:** It correlates requests for the same encrypted object, substitutes responses, or withholds
  the blob.
- **Affected property and assumptions:** G1 needs A1–A2; G7 does not promise content-address unlinkability;
  service availability is separate from canonical state.
- **Mitigations:** Authenticate fetched content independently of its locator and keep content keys inside the
  specified protection. Treat fetch failure as attachment unavailability.
- **Residual risk:** Hashing ciphertext does not prevent repeated-object or IP/timing correlation; an insider or
  stolen media key can reveal plaintext.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#validation), [Group
  image](app-components/group-blossom-image-v1.md#image-bytes).
- **Verification status:** Unverified — candidate check: replace, suppress and correlate blob responses in a
  declared observer model; functional hash checks are not a privacy proof.

<a id="sc-036"></a>

### SC-036. Tampered blob bytes or authenticated attachment fields

- **Attacker and prerequisites:** A blob service alters ciphertext, or a malicious sender supplies inconsistent
  media fields; attachment integrity and caption availability are exposed.
- **Attack sequence:** The receiver fetches bytes with a wrong ciphertext hash, fails AEAD, observes a wrong
  plaintext hash, or resolves duplicate tag fields differently.
- **Affected property and assumptions:** G1–G3 depend on A1 and exact canonical metadata; an attachment failure
  is not a reason to undo valid group processing.
- **Mitigations:** Check the v2 ciphertext/plaintext hashes and AEAD with its specified metadata; reject
  malformed references and preserve valid captions/other attachments.
- **Residual risk:** A sender with authority can supply harmful but authentic content. Availability failure
  after reference validation remains attachment-local.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#validation), [Encrypted media
  v2](features/encrypted-media.md#encryption), [Encrypted media v2](features/encrypted-media.md#key-derivation).
- **Verification status:** Unverified — candidate check: mutate ciphertext, both hashes, AAD metadata and
  duplicate fields separately; require the correct reference-versus-fetch failure boundary.

<a id="sc-037"></a>

### SC-037. Unknown media version or unsupported locator causes wider rejection

- **Attacker and prerequisites:** A sender presents an unknown media version or a receiver lacks a locator kind;
  attachment handling and interoperability are exposed.
- **Attack sequence:** A decoder guesses an older schema or drops the entire valid chat because one attachment
  cannot be interpreted/fetched.
- **Affected property and assumptions:** G3 uses declared formats; G5 preserves unrelated effective output,
  without promising support for every optional attachment.
- **Mitigations:** Validate the declared media version, apply current locator rules and keep reference
  rejection/availability failures attachment-local. Unknown locator kinds are not automatically malformed.
- **Residual risk:** Unsupported attachments may remain unavailable. Deprecated v1 is not a permissive fallback
  for v2 bytes.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#current-version), [Encrypted media
  v2](features/encrypted-media.md#validation), [Media policy](app-components/group-encrypted-media-v2.md).
- **Verification status:** Unverified — candidate check: exercise unknown version, well-formed unknown locator
  and unsupported policy separately; assert surviving caption and valid sibling attachments.

<a id="sc-038"></a>

### SC-038. Authentic media type misleads a renderer

- **Attacker and prerequisites:** A malicious member supplies content with a canonical but misleading MIME label
  or filename; renderer safety is exposed.
- **Attack sequence:** The receiver authenticates the reference and decrypts the bytes, then trusts the declared
  type as proof that a parser is safe to invoke.
- **Affected property and assumptions:** G2 establishes authorship, not harmless content; A1–A2 do not establish
  renderer isolation or byte/type consistency.
- **Mitigations:** Enforce the canonical MIME/filename profiles and apply application media-type/size policy
  after decryption, without invalidating the carrying message.
- **Residual risk:** AEAD proves metadata was bound, not that a hostile sender described the file honestly or
  that a media decoder is memory-safe.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#media-type-canonicalization),
  [Encrypted media v2](features/encrypted-media.md#filename-profile), [Encrypted media
  v2](features/encrypted-media.md#validation).
- **Verification status:** Unverified — candidate check: use canonical deceptive labels, mismatched bytes and
  malformed labels; distinguish reference rejection, unavailable rendering and valid message delivery.

<a id="sc-039"></a>

### SC-039. Media key-context ambiguity or nonce reuse on retry

- **Attacker and prerequisites:** A buggy sender repeats encryption under one derived key or serializes distinct
  metadata ambiguously; file confidentiality/integrity are exposed.
- **Attack sequence:** A retry reuses a nonce, or two filename/type/hash contexts collide because a producer
  ignores the owning KDF/preimage rules.
- **Affected property and assumptions:** G1 depends on A1–A2 and unambiguous encoded inputs; changing a filename
  is not a general nonce-uniqueness guarantee.
- **Mitigations:** Use the exact v2 derivation/AAD construction and sample a fresh independent random nonce for
  every encryption, including resends of the same attachment.
- **Residual risk:** The same hash/type/filename in an epoch derives the same file key; domain separation does
  not excuse ambiguous variable-field boundaries or bad randomness.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#key-derivation), [Encrypted media
  v2](features/encrypted-media.md#encryption), [Canonical
  encoding](foundation/canonical-encoding.md#tuple-and-preimage-boundaries).
- **Verification status:** Unverified — candidate check: check fixed KDF/AAD vectors, distinct metadata cases
  and repeated-encryption nonce handling; statistical samples do not prove RNG security.

<a id="sc-040"></a>

### SC-040. Saved media keys outlive an epoch transition

- **Attacker and prerequisites:** A member or attacker retains a file key, derived exporter material, downloaded
  ciphertext or plaintext.
- **Attack sequence:** After the group advances epochs or removes that leaf, it decrypts the same object using
  the previously saved key.
- **Affected property and assumptions:** G1 excludes retained decryption material under A2; epoch advancement
  does not revoke already disclosed file keys.
- **Mitigations:** Follow the owning key derivation/release conditions and distinguish loss of an unused
  derivation path from erasure of a copied file key.
- **Residual risk:** The historical assertion that old media automatically becomes inaccessible on every epoch
  change is not a valid general guarantee.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#key-derivation), [Retained
  history](protocol-core/retained-history.md#retained-cryptographic-material).
- **Verification status:** Unverified — candidate check: retain a key across epoch/removal transitions and
  verify the security argument makes no claim that the saved key stops decrypting the old object.

<a id="sc-041"></a>

### SC-041. Public package metadata fingerprints accounts and devices

- **Attacker and prerequisites:** A discovery relay or observer sees account-authored package slots,
  capabilities, ciphersuites and permitted client metadata.
- **Attack sequence:** It counts slots and compares advertised support/client values over time to infer Marmot
  use, device count or software changes.
- **Affected property and assumptions:** G7 intentionally permits discovery metadata; neither A3 nor a fresh
  package hides its publishing account.
- **Mitigations:** Limit publication to the binding's permitted fields and keep slot ids independent of stable
  identity material as specified.
- **Residual risk:** Slot counts are an approximation, and public capability information remains
  fingerprintable. Alternative discovery/privacy designs are not adopted by this catalogue.
- **Normative owners:** [KeyPackages](foundation/key-packages.md#devices-and-publication-slots), [Nostr
  transport](transports/nostr.md#keypackage-publication), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: inventory published fields and compare slot refreshes
  for prohibited identifiers; record accepted leakage separately from format conformance.

<a id="sc-042"></a>

### SC-042. Ciphertext length reveals message shape

- **Attacker and prerequisites:** A relay or passive observer records group-envelope sizes; approximate content
  length and traffic classification are exposed.
- **Attack sequence:** It clusters ciphertext lengths and overhead to distinguish likely short text, media
  references or other activity patterns.
- **Affected property and assumptions:** G1 protects content under A1; G7 does not establish length hiding.
- **Mitigations:** Keep explicit metadata limited to the binding profile. Evaluate any additional padding
  separately rather than assuming encryption overhead obscures length.
- **Residual risk:** There is no fixed-size group-message envelope or general padding guarantee here; repeated
  lengths can still be correlated.
- **Normative owners:** [Nostr transport](transports/nostr.md#group-message-delivery), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport), [Application
  payloads](foundation/application-messages.md#shape).
- **Verification status:** Unverified — candidate check: measure wire lengths for representative message classes
  under declared observer capabilities; do not equate encrypted transport with size privacy.

<a id="sc-043"></a>

### SC-043. Longitudinal group-route activity tracking

- **Attacker and prerequisites:** An observer learns a Nostr routing id and queries its history; group activity
  and revocation of future routing knowledge are the assets.
- **Attack sequence:** It follows the same h tag over time, or a removed member decrypts a membership-removal
  Commit that also advertises the intended replacement route.
- **Affected property and assumptions:** G7 separates addressing from identity, not route secrecy from everyone
  who has learned it; A1–A2 protect later confidential updates.
- **Mitigations:** Use the owning retained-route and optional post-removal two-Commit rotation rules when that
  privacy property is desired.
- **Residual risk:** v1 has one current route, not multiple concurrent routes or mandatory monthly rotation; a
  later rotation does not hide old history or all timing correlations.
- **Normative owners:** [Nostr routing](app-components/nostr-routing-v1.md#routing-rotation), [Nostr
  transport](transports/nostr.md#metadata-exposed-to-the-transport).
- **Verification status:** Unverified — candidate check: compare same-Commit versus post-removal rotation and
  old-address catch-up; check which update the removed leaf can decrypt.

<a id="sc-044"></a>

### SC-044. Relay selection and activity link groups

- **Attacker and prerequisites:** Colluding relays or observers see overlapping endpoint contacts and timing
  across groups.
- **Attack sequence:** They combine similar relay lists, common peers and aligned activity to infer shared
  participants or relationships between conversations.
- **Affected property and assumptions:** G7 does not establish cross-group unlinkability; A8 is a
  connection-policy boundary, not a correlation defense.
- **Mitigations:** Keep account keys out of ordinary group envelopes and avoid unnecessary extra metadata.
  Endpoint isolation is a local privacy choice with availability tradeoffs.
- **Residual risk:** Different relay lists or devices are not guarantees against collusion or statistical
  linkage; signed group routing cannot be silently rewritten for privacy.
- **Normative owners:** [Nostr transport](transports/nostr.md#metadata-exposed-to-the-transport), [Nostr
  routing](app-components/nostr-routing-v1.md#state),
  [Identity](foundation/identity.md#delivery-addressing-is-separate).
- **Verification status:** Unverified — candidate check: document observables for one and several colluding
  endpoints, including the distinction between group-internal routing lists and service-visible contacts.

<a id="sc-045"></a>

### SC-045. Welcome size suggests group size

- **Attacker and prerequisites:** An observer sees incoming gift-wrap sizes and may infer which objects are
  invitations; join metadata is exposed.
- **Attack sequence:** It compares an observed envelope length with plausible full-tree Welcome sizes to
  estimate participant scale.
- **Affected property and assumptions:** G7 is not group-size hiding; A1 encryption does not eliminate
  size-dependent structure.
- **Mitigations:** Keep Welcome content confidential and use the required ratchet tree/transport formats;
  evaluate padding or a future profile separately.
- **Residual risk:** Estimates are uncertain and envelope type may be hidden, but there is no guaranteed size
  independence or adopted lightweight-Welcome mechanism.
- **Normative owners:** [Joining](protocol-core/joining.md#behavior), [Nostr
  transport](transports/nostr.md#welcome-delivery).
- **Verification status:** Unverified — candidate check: measure serialized Welcome/envelope lengths across
  controlled group sizes and clearly separate statistical inference from authenticated membership knowledge.

<a id="sc-046"></a>

### SC-046. Break or misuse of the selected MLS cryptography

- **Attacker and prerequisites:** An attacker can exploit a weakness in a selected primitive or its
  implementation; content, authentication and key evolution are exposed.
- **Attack sequence:** It uses the weakness to recover secrets or produce accepted ciphertext/signatures despite
  otherwise correct state-machine behavior.
- **Affected property and assumptions:** This challenges inherited A1, upon which G1–G3 rely; state-machine
  checking cannot prove cryptographic hardness.
- **Mitigations:** Use the required ciphersuite/profile and its validation; update the owning construction
  through an interoperable protocol process when needed.
- **Residual risk:** A tested implementation or negotiated suite is not proof that primitives remain secure;
  suite-specific and implementation assumptions must be distinguished.
- **Normative owners:** [MLS profile](foundation/mls-protocol.md#required-ciphersuite), [MLS
  profile](foundation/mls-protocol.md#what-marmot-uses-from-mls).
- **Verification status:** External assumption — require an appropriate cryptographic argument and
  implementation assurance, not a claim based on generated scenario tests.

<a id="sc-047"></a>

### SC-047. Account-signature break or future quantum adversary

- **Attacker and prerequisites:** An attacker can defeat the classical account signature assumption, including a
  future relevant quantum capability.
- **Attack sequence:** It forges account authorizations or derives signing authority even if an MLS-layer
  construction were independently upgraded.
- **Affected property and assumptions:** A1 and A3 underpin G2–G3; the current profile makes no end-to-end
  post-quantum guarantee.
- **Mitigations:** Keep the account identity construction explicit and evaluate migration of identity as well as
  group key agreement through the owning protocol surfaces.
- **Residual risk:** Changing only the MLS suite does not establish post-quantum account authentication, and
  this document adopts no provisional migration scheme.
- **Normative owners:** [Identity](foundation/identity.md), [Account proof
  v2](app-components/account-identity-proof-v2.md), [MLS
  profile](foundation/mls-protocol.md#required-ciphersuite).
- **Verification status:** External assumption — review the complete trust chain and #413 separately; no local
  test proves resistance to future cryptanalytic capability.

<a id="sc-048"></a>

### SC-048. Hash collision undermines names, commitments, or integrity

- **Attacker and prerequisites:** An attacker can find collisions or exploit an incorrect hash/preimage
  implementation; message identities and content commitments are exposed.
- **Attack sequence:** It makes distinct authenticated objects compare as one identity or makes altered content
  match a relied-on commitment.
- **Affected property and assumptions:** A1 underlies G2–G5; unambiguous encoding and the security of the hash
  are separate premises.
- **Mitigations:** Use the owning canonical preimages and hash definitions exactly. Any algorithm migration
  needs coordinated owning-format changes.
- **Residual risk:** Collision resistance is an external cryptographic assumption; replacing SHA-256 locally
  would break shared identity semantics.
- **Normative owners:** [Wire envelopes](foundation/wire-envelopes.md#message-ids), [Canonical
  encoding](foundation/canonical-encoding.md#tuple-and-preimage-boundaries), [Encrypted media
  v2](features/encrypted-media.md#validation), [Conformance
  projection](foundation/conformance.md#exporter-commitment).
- **Verification status:** External assumption — byte vectors can detect preimage/implementation mistakes but
  cannot establish collision resistance.

<a id="sc-049"></a>

### SC-049. Cryptographic migration splits compatibility or overstates protection

- **Attacker and prerequisites:** Implementers deploy mismatched suites, signature rules or derivation contexts
  while responding to an algorithm weakness.
- **Attack sequence:** One client advertises unsupported protection or changes bytes without an interoperable
  version boundary, causing rejection or inconsistent interpretation.
- **Affected property and assumptions:** G2–G4 depend on common profile/validation rules (A1, A4); cryptographic
  agility is not unilateral replacement.
- **Mitigations:** Honor ciphersuite compatibility and component/proof version rules, and require support from
  the relevant group leaves/packages.
- **Residual risk:** Availability can be lost when peers do not support a new profile; no claim is made that
  every historical group can upgrade without replacement.
- **Normative owners:** [MLS profile](foundation/mls-protocol.md#required-ciphersuite),
  [Identity](foundation/identity.md#capability-negotiation), [Component
  framework](app-components/README.md#component-ids), [Authorization
  proofs](foundation/authorization-proofs.md#versioning).
- **Verification status:** Unverified — candidate check: exercise mixed-capability/profile participants and
  verify refusal rather than silent reinterpretation or unsupported security claims.

<a id="sc-050"></a>

### SC-050. Timing, cache, power, or other local side-channel extraction

- **Attacker and prerequisites:** An attacker can observe execution, shared hardware state or physical signals
  near a cryptographic operation.
- **Attack sequence:** It correlates secret-dependent behavior with observations to infer key material without
  defeating the abstract primitive.
- **Affected property and assumptions:** A1–A2 need implementation/platform qualification; G1 is not established
  by a functional proof alone.
- **Mitigations:** Use appropriate implementation and platform side-channel defenses and review the
  operations/key custody in their actual deployment context.
- **Residual risk:** Calling a library or using hardware is not a universal side-channel-resistance proof;
  observable power and shared-cache threats differ.
- **Normative owners:** [MLS profile](foundation/mls-protocol.md), [Identity](foundation/identity.md).
- **Verification status:** External assumption — require threat-specific implementation/platform evaluation;
  state-machine or wire-vector checks alone are insufficient.

<a id="sc-051"></a>

### SC-051. Weak randomness or repeated nonces/keys

- **Attacker and prerequisites:** A buggy, cloned, resumed or compromised random source supplies predictable or
  repeated key/nonce material.
- **Attack sequence:** Two encryptions reuse a nonce under one key, or an attacker predicts generated secrets
  and defeats intended confidentiality.
- **Affected property and assumptions:** A2 is necessary for G1 and fresh-identifier privacy; functional format
  conformance alone is insufficient.
- **Mitigations:** Follow each construction's fresh randomness and key-context requirements, distinguishing
  immutable retransmission from a new encryption.
- **Residual risk:** A few observed unique samples do not prove entropy or crash/clone safety; compromise
  recovery still depends on which secrets were exposed.
- **Normative owners:** [Encrypted media v2](features/encrypted-media.md#encryption), [Nostr
  transport](transports/nostr.md#group-message-delivery), [Experimental
  previews](features/agent-text-streams-quic.md#key-derivation).
- **Verification status:** Unverified — candidate check: test forced repeat/failure behavior and lifecycle
  boundaries, and separately document the randomness source assurance.

<a id="sc-052"></a>

### SC-052. Parser or memory-safety failure exposes secrets

- **Attacker and prerequisites:** An outsider or member can deliver attacker-controlled bytes to a native
  parser, renderer or protocol implementation.
- **Attack sequence:** It triggers memory corruption, unsafe handling or a resource/panic path and obtains
  secrets or prevents safe processing.
- **Affected property and assumptions:** A1–A2 assume correct implementation; G3's abstract rejection rules do
  not establish executable memory safety.
- **Mitigations:** Validate exact bounds and encodings and use appropriate language, parser, fuzzing and runtime
  defenses; the protocol prescribes no one programming language.
- **Residual risk:** Memory-safe code can still mishandle authorization, resource use or unsafe dependencies; no
  implementation audit result is established here.
- **Normative owners:** [Canonical encoding](foundation/canonical-encoding.md#canonical-decoding),
  [KeyPackages](foundation/key-packages.md#failure-behavior), [Inbound
  processing](protocol-core/inbound-processing.md#classification).
- **Verification status:** Unverified — candidate check: exercise malformed/truncated/oversized input with
  implementation-appropriate tooling and verify no partial accepted projection.

<a id="sc-053"></a>

### SC-053. Ambiguous or wrong TLS/Marmot canonical encoding

- **Attacker and prerequisites:** A sender or buggy codec produces noncanonical lengths, trailing bytes,
  normalized text, ambiguous tuples, or the wrong encoding family.
- **Attack sequence:** Clients hash/sign different preimages or interpret the same bytes differently,
  potentially splitting state or bypassing validation.
- **Affected property and assumptions:** G2–G4 depend on canonical authenticated bytes (A1, A4), not
  human-readable equivalence.
- **Mitigations:** Keep MLS-owned TLS serialization separate from Marmot-owned binary encoding; enforce full
  consumption, shortest length prefixes and exact field boundaries.
- **Residual risk:** A domain separator does not fix adjacent ambiguous variable-length fields, and a decoder
  must not repair invalid bytes into canonical state.
- **Normative owners:** [Canonical encoding](foundation/canonical-encoding.md#upstream-tls-and-mls-bytes),
  [Canonical encoding](foundation/canonical-encoding.md#canonical-decoding), [Canonical
  encoding](foundation/canonical-encoding.md#tuple-and-preimage-boundaries).
- **Verification status:** Unverified — candidate check: use cross-language boundary vectors with overlong
  prefixes, truncation, trailing bytes, Unicode variation and ambiguous concatenation attempts.

<a id="sc-054"></a>

### SC-054. Required-feature downgrade or unknown component reinterpretation

- **Attacker and prerequisites:** An admin or incompatible client changes required capabilities or misreads
  unknown component data.
- **Attack sequence:** It uses a legacy schema as fallback, rewrites optional opaque bytes, or tries to drop a
  requirement whose component prohibits removal.
- **Affected property and assumptions:** G3 checks parent authority and resulting support; G4 needs the same
  policy/profile (A4).
- **Mitigations:** Use component ids as version boundaries, fail closed on unknown required features and
  preserve unknown optional bytes. Enforce component-specific non-removability.
- **Residual risk:** Not every authorized capability change is forbidden, and a version label alone cannot
  prevent downgrade. The old monolithic extension-version detection scheme is superseded.
- **Normative owners:** [Component framework](app-components/README.md#component-ids), [Component
  framework](app-components/README.md#unknown-data), [Identity](foundation/identity.md#capability-negotiation),
  [Account devices](app-components/account-devices-v1.md#removal), [Group
  lifecycle](app-components/group-lifecycle-v1.md#removal).
- **Verification status:** Unverified — candidate check: exercise unknown required/optional data, incompatible
  leaves and forbidden lifecycle/account-device requirement removal, preserving exact bytes.

<a id="sc-055"></a>

### SC-055. Malicious software update or distribution compromise

- **Attacker and prerequisites:** An attacker controls client source, a dependency, build/distribution path or
  installed update; the whole local trust boundary is exposed.
- **Attack sequence:** It installs code that exports keys/plaintext or bypasses protocol validation while
  presenting ordinary application behavior.
- **Affected property and assumptions:** A1–A2 and host trust are prerequisites for G1–G5; a valid abstract
  protocol cannot constrain a malicious local implementation.
- **Mitigations:** Use deployment-specific source/build/update verification and implementation review as
  separate evidence; no new update-distribution protocol is defined here.
- **Residual risk:** Code signing or reproducibility alone does not establish that the signed/reproduced code is
  benign, nor does a model proof verify a distributed binary.
- **Normative owners:** [MLS profile](foundation/mls-protocol.md), [Conformance
  projection](foundation/conformance.md).
- **Verification status:** External assumption — link release/build provenance and implementation review for a
  named artifact before making deployment claims.

<a id="sc-056"></a>

### SC-056. Device leaves and publication slots reveal common ownership

- **Attacker and prerequisites:** Group peers see account-bound leaves; discovery services see account-authored
  slots and their changes.
- **Attack sequence:** They associate multiple leaves with one account or correlate slot refreshes and
  additions/removals over time.
- **Affected property and assumptions:** G2 deliberately authenticates the account relation; G7 is not
  device-ownership unlinkability.
- **Mitigations:** Keep slot identifiers independent of device labels or identity-derived material and expose
  only fields the transport allows.
- **Residual risk:** A device being a separate leaf does not create a separate pseudonymous account; group
  members can see the authenticated relationship.
- **Normative owners:** [Identity](foundation/identity.md#devices),
  [KeyPackages](foundation/key-packages.md#devices-and-publication-slots), [Account
  devices](app-components/account-devices-v1.md#security-considerations).
- **Verification status:** Unverified — candidate check: inspect the exact peer and discovery projections for
  account/leaf links and verify no privacy claim treats them as hidden.

<a id="sc-057"></a>

### SC-057. Offline removed device sends from stale local state

- **Attacker and prerequisites:** A device has not learned that its leaf was removed, or restores an old local
  snapshot; current membership and safe UI state are exposed.
- **Attack sequence:** It attempts old-epoch operations; later it receives evidence of removal or merely sees
  undecryptable input and guesses its status.
- **Affected property and assumptions:** G2–G3 are source-state-relative; G5 preserves authenticated removal
  gates under A6, and decryption failure alone is not removal proof.
- **Mitigations:** Realize authenticated local-leaf removal as terminal for that copy. Treat unavailable
  authenticated history separately, and require explicit fresh rejoin to replace active state.
- **Residual risk:** Still-active receivers may deliver authorized pre-removal app payloads in-window; another
  leaf of the same account can remain active. The removed copy stays inactive. Offline knowledge cannot be
  updated instantly.
- **Normative owners:** [Member departure](protocol-core/member-departure.md#realizing-removal), [Retained
  history](protocol-core/retained-history.md#app-payload-retention),
  [Joining](protocol-core/joining.md#receiving-flow).
- **Verification status:** Unverified — candidate check: compare authenticated removal with an undecryptable
  unrelated input and restore a removed copy; require correct gates, no false eviction and no silent
  resurrection.

<a id="sc-058"></a>

### SC-058. Valid Welcome substitutes an unintended group branch

- **Attacker and prerequisites:** A malicious inviter or account-key holder can build a cryptographically valid
  group state and author a Welcome.
- **Attack sequence:** It supplies a branch whose own admin/component state makes the Welcome author acceptable,
  and the joiner mistakes that self-contained validation for intended-group continuity.
- **Affected property and assumptions:** G2–G3 under A3 establish the received state's author binding, not an
  external first-contact authenticity anchor.
- **Mitigations:** Authenticate and present the Welcome author under the current join rules. Treat another
  member speaking on the branch as an activity heuristic only.
- **Residual risk:** The current profile has no in-band first-contact continuity anchor. Valid genuine
  KeyPackages can also be added to an attacker-authored branch.
- **Normative owners:** [Joining](protocol-core/joining.md#welcome-bootstrap-trust), [Account
  devices](app-components/account-devices-v1.md#welcome-acceptance).
- **Verification status:** Unverified — candidate check: construct distinct valid branches/inviters and check
  that the interface does not label structural validity or later activity as continuity proof.

<a id="sc-059"></a>

### SC-059. Authenticated external locator reaches an unsafe or tracking endpoint

- **Attacker and prerequisites:** A member, compromised service or DNS responder influences a relay, media,
  avatar, broker or push endpoint that a client contacts.
- **Attack sequence:** The locator passes protocol-byte/authorship checks but directs the client to an unwanted
  host, changes address during resolution, or reveals its IP on contact.
- **Affected property and assumptions:** G3 authentication does not establish A8 endpoint safety or G7
  connection privacy.
- **Mitigations:** Apply local connection/trust policy at network access without changing otherwise-valid
  authenticated state. Shared endpoint policy remains #74, not a new rule defined here.
- **Residual risk:** Automatic fetching can disclose metadata even for a valid public host; rejecting a contact
  cannot silently rewrite group routing or invalidate the carrying message.
- **Normative owners:** [Nostr transport](transports/nostr.md#relay-url-profile), [Encrypted media
  v2](features/encrypted-media.md#validation), [Avatar locator](app-components/group-avatar-url-v1.md), [QUIC
  binding](transports/quic.md#connection-and-trust), [Push
  notifications](features/push-notifications.md#validation).
- **Verification status:** Unverified — candidate check: exercise allowed/refused endpoints and address changes
  in an implementation-specific harness, checking separation of contact policy from canonical validity.

<a id="sc-060"></a>

### SC-060. Crash after possible publication manufactures success or replacement bytes

- **Attacker and prerequisites:** A local crash loses acknowledgement knowledge after a transport may have
  accepted a prepared Commit; unresolved obligations are the asset.
- **Attack sequence:** Recovery assumes failure and generates Commit B, assumes success without evidence, or
  forgets the prior/pending state needed to resolve Commit A.
- **Affected property and assumptions:** G5 depends on A6–A7 and preserving uncertainty; one relay acceptance is
  not recipient delivery.
- **Mitigations:** Make the exact obligation recoverable before external exposure and retry byte-identically
  when acknowledgement is uncertain; irrecoverable required loss fails closed.
- **Residual risk:** A hostile relay can acknowledge and discard bytes. Application liveness cannot be inferred
  from publishing or from a queued send.
- **Normative owners:** [Publication](protocol-core/publish-lifecycle.md#publish-obligation),
  [Durability](protocol-core/durability.md#publish-interruption-boundaries).
- **Verification status:** Unverified — candidate check: interrupt before attempt, after possible acceptance,
  after confirmation and during apply; reject replacement bytes, guessed success and mixed state.

<a id="sc-061"></a>

### SC-061. Interrupted convergence selects from an accidental partial batch

- **Attacker and prerequisites:** A process crash or storage fault loses volatile progress or some admitted
  dependencies during frozen resolution.
- **Attack sequence:** Recovery admits later input into the old batch, drops inconvenient missing evidence, or
  selects the sole locally complete candidate.
- **Affected property and assumptions:** G4–G5 depend on A4 and A6; resource limits and interruption cannot
  change what the admitted evidence means.
- **Mitigations:** Resume the identical frozen batch or wholly recollect still-eligible input under the restart
  exception; distinguish temporary blocking from permanently missing required material.
- **Residual risk:** Equal epoch/member counts cannot establish equivalent history. Permanent loss may require
  Unrecoverable rather than an available-looking winner.
- **Normative owners:** [Durability](protocol-core/durability.md#convergence-interruption-boundaries),
  [Durability](protocol-core/durability.md#missing-or-corrupt-material),
  [Convergence](protocol-core/convergence.md#convergence-policy).
- **Verification status:** Unverified — candidate check: interrupt each resolution/apply boundary, delete one
  decisive dependency and vary later input; require complete prior/selected projection or explicit unresolved
  state.

<a id="sc-062"></a>

### SC-062. Former member retains blob write or delete authority

- **Attacker and prerequisites:** A member copied the group-image upload private key before removal; the
  external blob's availability is the asset.
- **Attack sequence:** After removal it signs a server-accepted write/delete request for the old image without
  modifying canonical group state.
- **Affected property and assumptions:** G3 protects component updates, not revocation of an already disclosed
  external credential; A8 is also relevant to the contacted service.
- **Mitigations:** Use a fresh upload credential for a replacement image and treat server operations and fetch
  failure separately from component validity.
- **Residual risk:** Membership removal cannot force an external server to revoke that key. A server's own
  narrower credential policy may help but is not guaranteed by v1.
- **Normative owners:** [Group image](app-components/group-blossom-image-v1.md#image-bytes), [Group
  image](app-components/group-blossom-image-v1.md#update).
- **Verification status:** Unverified — candidate check: retain the old credential, remove the leaf and attempt
  server actions; verify a failed fetch does not invalidate authenticated group state.

<a id="sc-063"></a>

### SC-063. Group member forges a provisional agent preview

- **Attacker and prerequisites:** A current member knows the group-shared preview key; broker or outsider
  injection without that key is a separate case.
- **Attack sequence:** It encrypts plausible records for another stream and a receiver mistakes provisional text
  for authenticated final authorship or an executable instruction.
- **Affected property and assumptions:** G1 can exclude an outsider under A1–A2; G2's authoritative sender
  binding comes from the final MLS payload, not group-shared preview AEAD.
- **Mitigations:** Keep preview presentation provisional and respect the explicit automation-input risk
  boundary; validate the final MLS message and its anchoring.
- **Residual risk:** TLS, transcript hashing and sequence numbers do not provide sender authentication against
  another current member. Broker room policy remains an additional transport boundary.
- **Normative owners:** [Experimental previews](features/agent-text-streams-quic.md#preview-authenticity),
  [Experimental previews](features/agent-text-streams-quic.md#final-message), [QUIC
  binding](transports/quic.md#connection-and-trust).
- **Verification status:** Unverified — candidate check: inject key-valid forged preview text and compare
  final-authenticated content; ensure preview status cannot silently authorize durable actions.

<a id="sc-064"></a>

### SC-064. Preview publisher reuses sequence-derived nonces after restart

- **Attacker and prerequisites:** An experimental preview publisher loses its next sequence value or two
  publishers use one start/key context.
- **Attack sequence:** It restarts seq at one and encrypts different content with the same
  context/sequence-derived nonce.
- **Affected property and assumptions:** A2 is necessary for G1; receiver duplicate rejection does not undo
  nonce reuse in already observed ciphertext.
- **Mitigations:** Retain the next unused sequence or stop that preview and rely on the final message; a new
  attempt uses a new start payload and stream identity.
- **Residual risk:** A broker cannot confer exclusive cryptographic publisher identity merely by routing a room,
  and another current member knows the shared key.
- **Normative owners:** [Experimental previews](features/agent-text-streams-quic.md#quic-records), [Experimental
  previews](features/agent-text-streams-quic.md#key-derivation), [QUIC
  binding](transports/quic.md#broker-relayed).
- **Verification status:** Unverified — candidate check: crash/reconnect at each publisher sequence boundary and
  check that uncertain state stops publication or starts a fresh context.

<a id="sc-065"></a>

### SC-065. Push token replay, unauthorized token ownership, or advisory failure

- **Attacker and prerequisites:** A member, notification server or observer replays token/trigger data or
  substitutes token ownership; wake privacy and dispatch correctness are exposed.
- **Attack sequence:** A client accepts an unbound owner record, or a server repeats/stops dispatch; push
  failure then incorrectly propagates into group-message validity.
- **Affected property and assumptions:** G2 for token ownership depends on the feature's proof rules; G4–G5 do
  not make advisory push part of canonical group state.
- **Mitigations:** Validate owner signatures and ordering per entry, apply trigger replay hygiene and keep
  malformed/advisory push handling separate from valid group messages.
- **Residual risk:** The designated server decrypts its platform tokens and can correlate dispatch. Replay
  prevention, removal and platform delivery are not universal availability or unlinkability guarantees.
- **Normative owners:** [Push notifications](features/push-notifications.md#owner-authentication), [Push
  notifications](features/push-notifications.md#replay-and-freshness), [Push
  notifications](features/push-notifications.md#validation), [Push
  notifications](features/push-notifications.md#server-retention).
- **Verification status:** Unverified — candidate check: mix valid, replayed and malformed entries/triggers and
  lost notifications; require entry-scoped effects and unchanged valid group processing.

<a id="sc-066"></a>

### SC-066. External signer substitutes context or a proof is reused for another authority

- **Attacker and prerequisites:** A buggy or hostile signer can return a signed event different from the
  request; an attacker may replay a valid proof in another carrier/class.
- **Attack sequence:** The producer extracts a signature without validating fields, or a verifier accepts a
  cryptographically valid envelope without its class-specific binding.
- **Affected property and assumptions:** G2–G3 need A1–A3 plus exact proof context; valid signature bytes alone
  do not establish the requested authorization or consent.
- **Mitigations:** Validate every returned event field, id and signature before extraction; verify the proof
  class, carrier, signer authority and exact bound values.
- **Residual risk:** A compromised legitimate account key can sign a matching request. Receiver wall-clock
  expiry cannot be invented for a proof class that defines none.
- **Normative owners:** [Authorization proofs](foundation/authorization-proofs.md#producing-a-proof),
  [Authorization proofs](foundation/authorization-proofs.md#validating-a-proof), [Account proof
  v2](app-components/account-identity-proof-v2.md).
- **Verification status:** Unverified — candidate check: mutate kind, ordered tags, timestamp, key binding,
  carrier and returned id independently; require refusal of substituted or cross-class proofs.

<a id="sc-067"></a>

### SC-067. Crash or branch replacement duplicates or leaves stale application effects

- **Attacker and prerequisites:** A crash interrupts canonical apply and app observation, or convergence later
  supersedes a branch with already visible effects.
- **Attack sequence:** Recovery forgets an unobserved delivery, repeats it under a new identity, or fails to
  withdraw an output tied only to the losing branch.
- **Affected property and assumptions:** G5 requires one effective projection under A6, not exactly one physical
  callback; G4 governs canonical branch evidence.
- **Mitigations:** Keep stable effect identities and observation/reconstruction evidence, and replay required
  inverse effects and gates consistently with the selected state.
- **Residual risk:** A callback invocation alone is not proven observation. Raw callback count is not the
  conformance oracle when equivalent reconstruction/deduplication is allowed.
- **Normative owners:** [Durability](protocol-core/durability.md#application-effects-after-restart),
  [Conformance projection](foundation/conformance.md#canonical-snapshot),
  [Convergence](protocol-core/convergence.md#applying-the-selected-branch).
- **Verification status:** Unverified — candidate check: interrupt before/after observation and supersede the
  branch; compare effective payloads, state notices, withdrawals and invalidations at declared observer
  boundaries.

<a id="sc-068"></a>

### SC-068. Missing candidate parent is mistaken for definitive authorization failure

- **Attacker and prerequisites:** A relay withholds a parent or a client evaluates retained input against the
  wrong source state.
- **Attack sequence:** A Commit fails authentication against an unrelated state, so the client labels it
  unauthorized or lets a new admin list retroactively authorize it.
- **Affected property and assumptions:** G2–G4 require authenticated parent-relative evaluation (A1, A4); absent
  evidence is not proof of unauthorized authorship.
- **Mitigations:** Derive the candidate parent through MLS authentication, then evaluate authority there and
  complete resulting-state validity. Defer absent-parent input within the specified horizon.
- **Residual risk:** Permanent loss of required retained state and a not-yet-arrived dependency have different
  safe outcomes; neither authorizes choosing arbitrary local state.
- **Normative owners:** [Convergence](protocol-core/convergence.md#candidate-branches), [Component
  framework](app-components/README.md#authorization-evaluation), [Inbound
  processing](protocol-core/inbound-processing.md#classification), [Retained
  history](protocol-core/retained-history.md#late-commits).
- **Verification status:** Unverified — candidate check: withhold then deliver the true parent, vary admin
  policy across epochs and test stale expiry; require the correct deferred, invalid or unrecoverable
  classification.

## Historical scenario disposition

Source: `threat_model.md` at pre-reorganization commit
[`21a67b24ffbfe14fc52022769aff77495402d728`](https://github.com/marmot-protocol/marmot/blob/21a67b24ffbfe14fc52022769aff77495402d728/threat_model.md).
The source contains **87** named T.x.y scenarios. The rows below preserve their identifiers and titles and account for
each exactly once. None is silently excluded.

- **Retained:** the attack remains a distinct current scenario, with current ownership and qualified limits.
- **Updated:** the attack remains, but the protocol, premises, mitigation or stated assurance changed.
- **Merged:** a shared current scenario explicitly retains this attack path with related historical paths; it is not
  merely a link to an overview category.
- **Superseded:** the historical formulation or mitigation is no longer valid; the linked scenario preserves the
  underlying risk and explains the current boundary.
- **Excluded:** no current scenario would be claimed; exclusion would need a rationale here and separate review.
  There are no excluded rows in this revision.

| Historical ID | Historical title | Disposition | Current scenario | Rationale |
| --- | --- | --- | --- | --- |
| T.1.1 | Invalid Key Package Publication | Merged | [SC-001](#sc-001) | Same discovery-validation workload as T.10.3; no universal spam-prevention claim. |
| T.1.2 | Key Package Credential Mismatch | Updated | [SC-002](#sc-002) | Retains author/credential mismatch and adds the required account-to-leaf proof; removes the unconditional no-residual-risk claim. |
| T.1.3 | Gift-Wrapped Event Spam (NIP-59) | Merged | [SC-003](#sc-003) | Duplicate inbox decryption-flood case T.10.1; operational defenses remain conditional. |
| T.1.4 | Application Message Spam | Merged | [SC-004](#sc-004) | Duplicate route flood T.10.2; no multiple-current-route mitigation is invented. |
| T.2.1 | Group Membership Inference | Merged | [SC-005](#sc-005) | Same IP/membership inference as T.11.8; fresh keys do not prevent traffic correlation. |
| T.2.2 | Timing Correlation | Merged | [SC-006](#sc-006) | Includes timing, bursts and publication/subscription correlation with T.11.2/T.11.9. |
| T.2.3 | Relay Censorship | Merged | [SC-007](#sc-007) | Combines selective censorship with relay flooding/outage; no automatic relay removal is required. |
| T.3.1 | Message Spam | Merged | [SC-008](#sc-008) | Combines valid member-message overload with permitted proposal overload, preserving both stimuli. |
| T.3.2 | Metadata Exposure | Merged | [SC-009](#sc-009) | Member disclosure of routing/admin metadata and tree/account relationships remain explicit, not harmless/public by assumption. |
| T.3.3 | Group State Disclosure | Merged | [SC-009](#sc-009) | Shares the insider-disclosure boundary with T.3.2; public keys do not make membership relationships public. |
| T.3.4 | Historical Message Retention | Merged | [SC-010](#sc-010) | Saved plaintext and cooperative expiry share the no-hostile-erasure boundary. |
| T.3.5 | Fake Proposals | Merged | [SC-008](#sc-008) | Proposal workload remains explicit; the old claim that every proposal needs admin commitment is not retained. |
| T.3.6 | Disappearing Message Non-Compliance | Updated | [SC-010](#sc-010) | Uses source-epoch retention and advisory expiry; does not prescribe SQLite secure_delete or promise relay/blob erasure. |
| T.4.1 | Unauthorized Member Addition | Updated | [SC-011](#sc-011) | A harmful admin-authorized Add is distinct from a cryptographically unauthorized Add; multiple admins are not a quorum. |
| T.4.2 | Legitimate Member Removal | Updated | [SC-012](#sc-012) | Retains abusive removal; fresh join and terminal local removal replace implied automatic undo. |
| T.4.3 | Device Addition for Persistence | Merged | [SC-013](#sc-013) | Combines additional-device persistence with current same-account authority and leaf-scoped revocation. |
| T.4.4 | Marmot Group Data Extension Manipulation | Updated | [SC-014](#sc-014) | Replaces the monolithic group-data extension with current component owners and parent-relative authorization. |
| T.4.5 | Group Destruction | Updated | [SC-015](#sc-015) | Adds the adopted terminal disband path and rejects the assumption that another admin can always reverse destruction. |
| T.4.6 | Commit Race Conditions | Superseded | [SC-016](#sc-016) | The threat remains; timestamp/outer-id priority is replaced by current authenticated branch selection and digest tie-breaking. |
| T.4.7 | Rapid State Changes | Merged | [SC-017](#sc-017) | Same rapid-valid-state workload as T.10.5; no processing throttle is promoted to canonical validity. |
| T.4.8 | Malformed Proposal Commits | Retained | [SC-018](#sc-018) | Malformed admin proposals/Commits still require rejection and full resulting-state validation. |
| T.5.1 | Key Material Exposure | Merged | [SC-019](#sc-019) | Full-device exposure, decryption and forgery share a compromise case with explicit secret scope. |
| T.5.2 | Message Decryption | Merged | [SC-019](#sc-019) | Decryption after device compromise is retained without claiming every epoch update heals it. |
| T.5.3 | Message Forgery | Merged | [SC-019](#sc-019) | Compromised-leaf impersonation remains explicit alongside content exposure. |
| T.5.4 | Identity Theft | Merged | [SC-020](#sc-020) | Account-key theft and its cross-application effects are one identity-root case. |
| T.5.5 | Device Addition | Merged | [SC-013](#sc-013) | Unauthorized device persistence is retained with current sender-approval and receiver-enforcement limits. |
| T.5.6 | Historical Message Access | Merged | [SC-021](#sc-021) | Stored plaintext/key exposure is combined with backup/restore; physical erasure is not assumed. |
| T.5.7 | Nostr Key Compromise Cross-Application Impact | Merged | [SC-020](#sc-020) | Preserves ecosystem-wide key-use scope without claiming specific financial access for every application. |
| T.5.8 | Partial Device Compromise (Memory-only) | Retained | [SC-022](#sc-022) | Temporary memory-only exposure remains distinct from full device/account compromise. |
| T.6.1 | Forward Secrecy Window | Superseded | [SC-023](#sc-023) | Retains exposure-window risk but replaces removal-only forward secrecy and automatic media-expiry claims with secret-specific retention. |
| T.6.2 | Group Image Forward Secrecy | Merged | [SC-024](#sc-024) | Persistent image keys and disclosed image identifiers share the stored-object boundary with T.11.5. |
| T.6.3 | PCS Recovery Window | Updated | [SC-025](#sc-025) | Offline recovery remains explicit; removes the claim that applying any relevant epoch increment automatically establishes PCS. |
| T.6.4 | Key Update Requirements | Merged | [SC-025](#sc-025) | Combines delayed updates/rotation; actual exposed secrets and honest updates determine recovery, not every Commit. |
| T.7.1 | Last Resort KeyPackage Reuse | Updated | [SC-026](#sc-026) | Replaces the old signing-key timetable with current last-resort init_key/lifetime/replacement bounds. |
| T.7.2 | Long-Lived Signing Keys | Merged | [SC-025](#sc-025) | Long-lived leaf material is covered in the key-specific recovery case; package refresh is not a universal weekly MLS-key rule. |
| T.7.3 | Stale KeyPackage Exposure | Updated | [SC-027](#sc-027) | Keeps stale-slot replay and current selection/lifetime rules; replacement/deletion does not revoke retained copies. |
| T.7.4 | Welcome Event Timing Race Conditions (State Fork Vulnerability) | Updated | [SC-028](#sc-028) | Keeps sender ordering and adds current tentative-join rollback and founding empty-obligation exceptions. |
| T.7.5 | Large Group Welcome Limitations | Merged | [SC-029](#sc-029) | Keeps Welcome-size and general group-resource failure; removes fixed participant estimates and unadopted light-Welcome mitigation. |
| T.7.6 | init_key Retention After Group Join | Updated | [SC-026](#sc-026) | Keeps private init_key exposure and rollback; transport access to Welcome bytes is an explicit prerequisite, not universally a stolen Nostr key. |
| T.7.7 | Delayed Self-Update After Join | Superseded | [SC-030](#sc-030) | Post-join update risk remains; current prompt SHOULD guidance replaces a mandatory 24-hour protocol deadline and public-key exposure is not secret leakage. |
| T.8.1 | Ephemeral Keypair Reuse | Retained | [SC-031](#sc-031) | Fresh per-new-event keys remain required; immutable retry is distinguished from new-event key reuse. |
| T.8.2 | Inner Event Signature Leakage | Updated | [SC-032](#sc-032) | Keeps unsigned payload and sender binding; removes leak-prevention overclaims and a blanket ban on inner h tags. |
| T.8.3 | Exporter Secret Compromise | Updated | [SC-033](#sc-033) | Separates recovered PublicMessage handshakes from still-protected application bytes instead of asserting uniform double-encryption protection. |
| T.8.4 | Message Replay Attacks | Superseded | [SC-034](#sc-034) | Replay remains; MLS-byte protocol identities replace outer Nostr event-id deduplication. |
| T.9.1 | Storage Provider Compromise | Updated | [SC-035](#sc-035) | Retains blob exposure/availability; content addressing does not prevent access correlation or revoke saved keys. |
| T.9.2 | File Integrity Attacks | Updated | [SC-036](#sc-036) | Uses v2 ciphertext/plaintext hashes, exact AAD and attachment-local failure boundaries. |
| T.9.3 | Version Compatibility Attacks | Updated | [SC-037](#sc-037) | Uses explicit media versions and distinguishes malformed references from well-formed unsupported locators. |
| T.9.4 | MIME Type Spoofing | Updated | [SC-038](#sc-038) | Retains deceptive MIME handling and distinguishes authenticated canonical metadata from safe renderer content. |
| T.9.5 | Key Derivation Attacks | Superseded | [SC-039](#sc-039) | Replaces filename-implies-nonce-uniqueness with exact current KDF/AAD and fresh random nonce requirements, including retries. |
| T.9.6 | Forward Secrecy for Media | Superseded | [SC-040](#sc-040) | The retained-media exposure remains; epoch change does not revoke a previously copied file key. |
| T.10.1 | Gift-Wrapped Event Spam | Merged | [SC-003](#sc-003) | Duplicate of the inbox gift-wrap flood in T.1.3. |
| T.10.2 | Application Message Spam | Merged | [SC-004](#sc-004) | Duplicate of group-route ciphertext flood T.1.4; monthly/multiple-route suggestions are not adopted defenses. |
| T.10.3 | Invalid Key Package Spam | Merged | [SC-001](#sc-001) | Duplicate invalid-discovery workload T.1.1. |
| T.10.4 | Large Group Resource Exhaustion | Merged | [SC-029](#sc-029) | General large-group pressure is retained alongside Welcome/device capacity, without inventing signed-state limits. |
| T.10.5 | Rapid State Changes | Merged | [SC-017](#sc-017) | Duplicate rapid state-change workload T.4.7. |
| T.10.6 | Relay Flooding | Merged | [SC-007](#sc-007) | Relay flooding is a distinct stimulus within censorship/outage; relay admission is operational policy. |
| T.10.7 | Targeted Relay Attacks | Merged | [SC-007](#sc-007) | Targeted relay outage remains an explicit stimulus; redundancy is not guaranteed availability. |
| T.11.1 | Key Package Metadata Leakage | Retained | [SC-041](#sc-041) | Public capability/account/device fingerprinting remains explicit under the current slot profile. |
| T.11.2 | Event Timing Patterns | Merged | [SC-006](#sc-006) | Publication-time inference joins T.2.2 and burst analysis T.11.9. |
| T.11.3 | Event Size Leakage | Merged | [SC-042](#sc-042) | Length leakage and content-shape fingerprinting retain one explicit wire-size scenario. |
| T.11.4 | Group ID Tracking | Superseded | [SC-043](#sc-043) | Tracking remains; current one-route and optional two-Commit removal rotation replace monthly/multiple-current-route claims. |
| T.11.5 | Group Image Metadata | Merged | [SC-024](#sc-024) | Disclosed image hashes/access correlation join retained image-key exposure. |
| T.11.6 | Relay List Correlation | Merged | [SC-044](#sc-044) | Shared relay contacts and cross-group temporal relationships are jointly analyzed, without guaranteed isolation. |
| T.11.7 | Group Activity Tracking | Merged | [SC-043](#sc-043) | Activity/count tracking remains in the route-history case; no automatic monthly rotation claim. |
| T.11.8 | IP Address Correlation | Merged | [SC-005](#sc-005) | Duplicate IP membership-inference case T.2.1. |
| T.11.9 | Message Burst Pattern Analysis | Merged | [SC-006](#sc-006) | Burst/external-event inference is explicit in the timing case; old delay/cover-traffic recommendations are not normative. |
| T.11.10 | Cross-Group Activity Correlation | Merged | [SC-044](#sc-044) | Cross-group temporal linkage remains explicit alongside shared relay observations. |
| T.11.11 | Message Size Fingerprinting | Merged | [SC-042](#sc-042) | Message-type size fingerprinting joins length leakage T.11.3; encryption overhead is not size hiding. |
| T.11.12 | Group Size Inference from Welcome Events | Retained | [SC-045](#sc-045) | Welcome-length inference remains separate from join capacity and claims no universal group-size estimate. |
| T.12.1 | MLS Ciphersuite Vulnerabilities | Updated | [SC-046](#sc-046) | Separates selected primitive security from implementation misuse and respects the current ciphersuite profile. |
| T.12.2 | secp256k1 Weaknesses | Updated | [SC-047](#sc-047) | Names the current classical account root and separates its migration from an MLS-only upgrade. |
| T.12.3 | Hash Collision Attacks | Updated | [SC-048](#sc-048) | Retains hash-security reliance without prescribing a unilateral substitute algorithm. |
| T.12.4 | Cryptographic Agility | Updated | [SC-049](#sc-049) | Migration follows profile/component/proof negotiation rather than assuming arbitrary in-place agility. |
| T.12.5 | Side-Channel Attacks | Retained | [SC-050](#sc-050) | Side-channel risks remain distinct and require implementation/platform evidence. |
| T.12.6 | Random Number Generation | Retained | [SC-051](#sc-051) | Weak entropy and nonce/key reuse remain explicit, including immutable-retry distinctions. |
| T.12.7 | Memory Safety | Retained | [SC-052](#sc-052) | Memory/parser safety remains an implementation boundary; no one language is mandated. |
| T.12.8 | TLS Serialization Errors | Updated | [SC-053](#sc-053) | Separates MLS TLS serialization from Marmot binary/canonical preimage rules. |
| T.12.9 | Version Detection Failures | Superseded | [SC-054](#sc-054) | Current component/proof ids and unknown-required handling replace monolithic extension version detection. |
| T.12.10 | Extension Version Downgrade | Superseded | [SC-054](#sc-054) | Current per-component authorization, resulting-state support and removal rules replace a generic older-extension downgrade policy. |
| T.13.1 | Key Backup Threats | Merged | [SC-021](#sc-021) | Backup/restore extends the stored-history exposure case and includes revived secrets/work. |
| T.13.2 | Key Rotation Failures | Merged | [SC-025](#sc-025) | Rotation failure is key-specific recovery; no generic calendar schedule establishes PCS. |
| T.13.3 | Malicious Client Updates | Retained | [SC-055](#sc-055) | Malicious distribution/update remains a separate external trust boundary. |
| T.13.4 | Unauthorized Member Addition | Merged | [SC-011](#sc-011) | Socially engineered admission joins the harmful admin-authorized Add case. |
| T.13.5 | Admin Privilege Granting | Merged | [SC-014](#sc-014) | Socially engineered admin granting is retained with parent-state policy manipulation. |
| T.13.6 | Device Synchronization Attacks | Merged | [SC-013](#sc-013) | Compromised-device/sibling persistence remains explicit under adopted account-devices authority. |
| T.13.7 | Cross-Device Correlation | Retained | [SC-056](#sc-056) | Account-linked leaf/slot privacy is distinct from cross-group IP correlation. |
| T.13.8 | Device Removal Race Conditions | Updated | [SC-057](#sc-057) | Separates authenticated terminal leaf removal from unknown decryption failure and preserves old source-epoch app semantics. |

Current cases SC-058–SC-068 add explicit adopted/experimental boundaries without inventing historical identifiers.
They supplement, rather than replace, the 87-row reconciliation.

## Surface coverage

The following map locates security ownership across the current surfaces. It does not certify conformance or proof
coverage. Optional, superseded, draft and experimental documents keep their own status. The surface READMEs remain
the document indexes; non-normative [ideas](ideas/README.md) are not adopted security mechanisms.

| Surface and documents | Boundaries covered here |
| --- | --- |
| [Identity](foundation/identity.md), [authorization proofs](foundation/authorization-proofs.md), [current account proof](app-components/account-identity-proof-v2.md), [legacy account proof](foundation/account-identity-proof-v1.md) | A1–A3, G2–G3, T3–T5, T11; legacy proof is superseded. |
| [KeyPackages](foundation/key-packages.md), [MLS profile](foundation/mls-protocol.md) | A1–A3, T3–T4; cryptographic inheritance and retained join exposure. |
| [Canonical encoding](foundation/canonical-encoding.md), [app payloads](foundation/application-messages.md), [wire envelopes](foundation/wire-envelopes.md), [registries](foundation/registries.md), [errors](foundation/errors.md), [conformance](foundation/conformance.md) | G2–G5, T2, T5, T7; exact identities, validation, dispositions and observable equivalence. |
| [Group setup](protocol-core/group-setup.md), [joining](protocol-core/joining.md), [group messaging](protocol-core/group-messaging.md), [member departure](protocol-core/member-departure.md), [group state](protocol-core/group-state.md) | G2–G6, T3–T5, T7; admission, policy, membership and lifecycle gates. |
| [Publish lifecycle](protocol-core/publish-lifecycle.md), [inbound processing](protocol-core/inbound-processing.md), [convergence](protocol-core/convergence.md), [retained history](protocol-core/retained-history.md), [durability](protocol-core/durability.md) | A4–A7, G4–G6, T2, T6–T7; scheduling versus safety, evidence retention and restart. |
| [Admin policy](app-components/admin-policy-v1.md), [account devices](app-components/account-devices-v1.md), [group lifecycle](app-components/group-lifecycle-v1.md) | G3, T3–T5, T7; parent-relative authority, device approval and terminal effects. |
| [Group profile](app-components/group-profile-v1.md), [avatar URL](app-components/group-avatar-url-v1.md), [group image](app-components/group-blossom-image-v1.md), [message retention](app-components/message-retention-v1.md) | A8, G3, T5, T8; authenticated data versus trusted endpoints, retained capabilities and deletion limits. |
| [Component framework](app-components/README.md), [media v2 component](app-components/group-encrypted-media-v2.md), [legacy media component](app-components/group-encrypted-media-v1.md), [media v2 feature](features/encrypted-media.md), [legacy media feature](features/encrypted-media-v1.md) | A1–A2, A8, G1, G3, T8, T11; capability negotiation, bytes and content/locator separation. Legacy v1 is deprecated. |
| [Nostr routing component](app-components/nostr-routing-v1.md), [Nostr transport](transports/nostr.md) | A7–A8, G7, T1–T2, T6; signed routing, outer metadata, replay and availability. |
| [Preview component](app-components/agent-text-stream-quic-v1.md), [preview feature](features/agent-text-streams-quic.md), [QUIC binding](transports/quic.md) | A1–A2, A8, T9; experimental, group-shared authenticity and authoritative final content. |
| [Push notifications](features/push-notifications.md) | A1–A2, A8, T10; optional service and platform boundary. |
| [Content moderation](features/content-moderation.md) | T5, T8; draft, source-state admin authority and conforming-client display effects. |

## Formalization and review boundary

A later claim register can link A/G/T identifiers to normative clauses, formal properties, checked bounds, concrete
vectors and implementation observations. A positive model result concerns that model and its premises. An abstract
authentication operation does not prove a signature implementation, and a finite model run does not establish a
general theorem over unbounded inputs or every process schedule. Required actions also need reachable witnesses and
negative controls so an impossible scenario cannot masquerade as a guarantee.

The present document establishes no such verification result. Before calling it reviewed, maintainers need to check
the scope and residual risks against every owning surface and resolve any disagreement there. Changes to assumptions,
attacker powers, metadata exposure, retained capabilities or claimed guarantees follow the
[security-model maintenance checklist](principles.md#security-model-maintenance).
