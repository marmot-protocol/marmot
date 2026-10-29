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
