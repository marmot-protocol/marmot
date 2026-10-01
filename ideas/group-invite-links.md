# Group invite links

Status: proposal (non-normative). See [README.md](./README.md).

An admin shares a link; someone previews the group and requests an invitation. Admins receive the request privately
and add the person through the existing MLS Welcome flow. A shared inbox key lets any active admin receive requests.
Recipient-encrypted admin records travel inside the group's existing MLS channel.

This discussion draft proposes the experience and mechanisms for review. Identifiers, wire formats, capability
negotiation, and interoperable rules remain work for the owning surfaces before implementation.

## At a glance

- **Admin controls:** enable links and choose an admission mode with a validity period.
- **Explicit joining:** show the name, description, and image; submit a request only after the person chooses Join.
- **Private requests:** gift-wrap to a random link inbox; authenticate the real requesting account inside encryption.
- **Admin-only secrets:** encrypt a copy for each active admin, then carry those copies inside MLS group traffic.
- **Offline waiting:** show "Waiting for approval" or "Waiting for an invite" while every admin is offline.
- **Pending requests survive expiry:** any active admin can approve them later under current membership policy.
- **History starts at joining:** the invitation transfers only the state needed for the existing Welcome flow.

Active admins retain equal authority. The inbox key supplies decryption, while
[admin policy](../app-components/admin-policy-v1.md) supplies membership authority.

## Scope and privacy target

The target is outside readers of public events. Relay operators and network or timing correlation are excluded.
Link holders see the preview. Current members already see membership and admin policy; only admins receive the inbox
secret and decrypted request details.

The proposed baseline uses an admin-only key, one inbox per link, a separate secret bearer, and manual handling of
unverified requests discovered after expiry. Descriptor details and interoperable lifecycle rules remain open.

## Scene 1: Create and share a link

An admin enables links and sets the mode and expiration, then shares a link or QR code. Clients encode a fresh random
inbox public key, relay hints, preview material, and an unguessable bearer token. Admins retain the inbox private key.
A fresh inbox address is independent of account identities and existing group identifiers, including the MLS group id
and normal group delivery address.

The token distinguishes someone holding the link from someone who only saw the inbox address in a public request.
It permits requesting admission; membership still depends on current group policy and a valid Welcome.

The preview can be inline or an encrypted fetched descriptor. Images use encrypted assets whose decryption material
travels with the link. The client shows the full preview; web unfurls stay generic. Secret-bearing web links use
fragments, with analytics and secret-bearing unfurl requests excluded. The opening website or application can still
read the fragment. Distinctive relay hints can identify a group.

Anyone holding or forwarding the link can disclose its preview. Publishing the link deliberately discloses the preview
and inbox. Trust starts with whoever supplied the link: endpoint key possession alone proves neither admin status
nor authenticity of a previously known group.

## Scene 2: Request an invitation

After explicit consent, the client sends a persistent [NIP-59 gift wrap](https://github.com/nostr-protocol/nips/blob/master/59.md)
to the random inbox. The outer signer is a one-time random key. The authenticated requester account stays inside the
encryption, together with the request details.

Conceptually, the request identifies its link and a stable request, proves bearer possession, supplies a compatible
KeyPackage publication reference and validation material, and supplies Welcome routing. A private status-return
address is an option. These conceptual inputs need encodings in their future owning documents.

The identity chain ties the authenticated seal author to the requesting account, KeyPackage credential and account
proof, publication provenance, selected package reference, and eventual Welcome recipient. Delivery hints supply
routing only. [KeyPackage validation and lifecycle](../foundation/key-packages.md) continue to apply, including
single-use packages and supported last-resort reuse.

Persistent delivery supports offline retrieval. Redundant relays and retries improve availability, while relay
retention remains best effort. Retrying the same intent keeps its stable request identity. Long offline periods or
loss of every stored copy can require resubmission.

## Scene 3: Admins process the request

Each active admin can receive the inbox key and listen for requests. The Requests screen shows the requesting profile,
source link, status, and any package or timing problem. Local notifications can use a generic lock-screen label.

Approval mode offers Approve and Reject. Automatic mode performs the same membership checks in the background.
Request decisions identify the acting admin privately and use the admin channel below. Clients consult current group
policy before acting. Receipt of a control message supplies evidence, not a policy change.

Concurrent approvals, rejection races, retries, and legitimate multi-device requests need defined outcomes coupled
to existing MLS convergence. Arrival order and relay timestamps cannot choose group policy. A rejection leaves already
established membership unchanged.

## Scene 4: Receive the Welcome

The admin follows the existing [join flow](../protocol-core/joining.md), including successful Commit publication before
Welcome delivery for an existing group. [Nostr Welcome delivery](../transports/nostr.md#welcome-delivery) stays addressed
to the requester's actual account and references the selected KeyPackage publication.

The client marks the link request Joined only after successful Welcome validation and association with that request.
An unrelated valid Welcome remains an ordinary invitation. A proposed private correlation response binds the request
to its Welcome and a matching link record in the joined group state; names and package references alone are insufficient.

Request-to-Welcome association remains an adoption question. A forged group can copy public link records; shared inbox
signatures prove key possession only. The [Welcome-bootstrap trust](../protocol-core/joining.md#welcome-bootstrap-trust)
limits still apply. The requester ultimately trusts the authenticated inviter, with that identity presented at join.

Status replies are advisory until their authority is established. An admin-account signature reveals that admin to
the requester; an inbox-key signature can be forged by any inbox custodian. Encryption hides either reply from public
readers. Missing replies mean waiting, and a claimed rejection requires authentication.

## Encrypted admin records inside MLS

### Distribution

The proposed admin channel reuses group delivery with a second encryption layer:

1. An active admin creates the link inbox secret and the associated secret link material.
2. The client makes an authenticated recipient-encrypted copy for every active admin account. NIP-59 envelopes are
   the proposed Nostr-key baseline, retaining their signed seals.
3. The copies are carried inside the content of a Marmot app event, then inside an MLS application message.
4. Each recipient unwraps its copy, associates it with the intended group, and checks the link's secret generation.

Recipient envelopes stay inside MLS; publishing them separately would expose their recipient npubs. The surrounding
[Marmot app event](../foundation/application-messages.md) keeps its existing unsigned shape. The signatures belong to
the nested envelopes, not the surrounding app event.

```text
Existing group transport
  MLS application message: authenticated member sender
    Unsigned Marmot app event: proposed control-record content
      Recipient-encrypted envelope for admin A
      Recipient-encrypted envelope for admin B
```

Public readers see existing encrypted group traffic. Group members see recipient addresses and encrypted copies.
Only the intended admin accounts can decrypt their copies, assuming uncompromised keys. Clients process the payload
as a control record, separately from visible chat.

The same channel carries identifying admission decisions and request records. Sending a plaintext request record
inside ordinary all-member MLS traffic would disclose it to every member.

### Authority and replay

Nested envelope authors agree with the MLS-authenticated sender account. That sender's admin authority comes from
the authenticated source group state. Recipients also check intended group, link, generation, and recipient association.
These bindings prevent a valid envelope being transplanted from another group or operation.

Current authenticated group state supplies enablement, mode, validity, and generation. Application delivery alone
cannot establish those settings. Historical control records can support pending-request evidence; present actions
still require current active-admin authority and current policy.

A current custodian authors fresh redistribution. Forwarding an old envelope preserves its old authority and context.
Duplicates and delayed records leave already applied decisions unchanged. Concurrent generations and conflicting
decisions need explicit convergence rules before adoption. First arrival remains delivery evidence only.

### Catch-up and key loss

- **Offline admin:** retrieve retained MLS traffic when possible. Erased epoch keys or missing relay copies can prevent
  decryption; an existing custodian can send fresh current-state material.
- **New admin:** after authenticated promotion, an existing active admin sends a fresh encrypted copy.
- **New device:** a device currently in the group under an active admin account receives fresh material as needed.
  Account-key decryption through external signers and device recovery require an explicit integration design.
- **Missing custodian:** wait until an admin with a retained copy comes online and sends fresh material.
- **Every copy lost:** issue a replacement inbox and link. Retained request metadata cannot reconstruct an unknown key
  or decrypt requests that remain unread.

Fresh delivery includes only the material needed for current links and unresolved requests. It gives the new admin
or device neither old chat history nor blanket access to retired inboxes. Supporting pending requests across promotion
can require deliberately sharing selected retired key material.
Sharing a retired key also exposes any retained request ciphertext encrypted to it. Forwarding selected decrypted
pending records through the admin channel limits disclosure when access to the whole retired inbox is unnecessary.

### Admin removal and key rotation

Demoting or removing an admin leaves previously learned secrets with that person. Future request confidentiality
requires a fresh inbox key distributed to the remaining admins and replacement links. Authenticated policy retires
the old endpoint for automatic admission.

Copied old links still encrypt to the old key. Retiring an endpoint stops its admission authority; it cannot stop
former custodians decrypting requests sent there. Existing admins retain or recover the old material needed to handle
pending requests. Expiry alone keeps pending requests approvable. Security-driven retirement needs a separate,
explicit rule for pending requests.

### Alternative: every member holds the key

An all-member distribution would be simpler but would reveal requester identities and bearer material to every
member, including former members who retained a copy. Members could forge inbox-only status replies. The proposal
uses admin-only custody; all-member custody is a separate privacy choice. Possessing either shared key grants only
inbox capabilities, while membership changes remain admin-gated.

## Expiry and pending requests

Expiration closes the link to new submissions and preserves pending requests. Later approval uses current admin
authority and revalidates account binding, package lifetime, capabilities, provenance, and existing reuse rules.
Package refresh remains tied to the original authenticated requester and intent.

A requester timestamp can be backdated. NIP-59 outer timestamps are deliberately fuzzed. Ordinary offline relay
delivery provides insufficient evidence of submission before expiry.

The proposed fallback preserves first-discovered late requests for explicit approval as "timing unverified".
Automatic admission after expiry needs trustworthy pre-expiry acceptance evidence, whose format and cross-admin
availability are still open. Until that exists, requests first discovered after all admins were offline across expiry
normally require manual review. An authenticated status update explains the transition to Waiting for approval.

Link revocation, requester withdrawal, rejection, security-driven retirement, and group disbanding need distinct
semantics. Whether explicit revocation also cancels old pending requests remains open. None removes existing members
as a side effect.

## Security and availability limits

- Public request envelopes expose a random inbox address. They also show event sizes and activity. Requests to one
  inbox are linkable.
  Someone holding the link can associate that address with its preview.
- Existing Welcome envelopes expose the recipient npub publicly. Sender identity and group contents remain wrapped.
  This proposal protects request contents and associations; full admission-path anonymity would need different
  Welcome transport work.
- [NIP-44 limitations](https://github.com/nostr-protocol/nips/blob/master/44.md#limitations) include lack of forward
  secrecy. Inbox-key compromise exposes retained request ciphertext; rotation protects fresh endpoints.
  Nesting distribution inside MLS does not retract secrets copied by a recipient.
- Admins can disclose decrypted requests or signed seals. Encryption cannot guarantee deletion or deniability against
  a custodian. Nested account-signed admin seals can become transferable evidence when disclosed, even though the
  surrounding Marmot app event is unsigned.
- Processing needs bounds on recipient counts, envelope sizes, pending requests, retries, and preview rendering.
  A leaked bearer permits admission attempts under the link's policy, and automatic mode increases that exposure.
- Unsupported clients need defined capability and presentation behavior. Account-signer support needs validation,
  together with partial distribution and fresh catch-up.

## Work before adoption

The idea allocates no component ids, event kinds, exporter labels, or wire bytes. Adoption needs work in these surfaces:

- **Foundation:** control-record representation, requester/package binding, capabilities, and bounded encodings.
- **App components:** authenticated link policy and generation, plus admin-authorized lifecycle state.
- **Protocol core:** request-to-Add behavior and Welcome association, including duplicate and concurrent decisions.
- **Transport:** descriptor addressing, nested recipient envelopes, persistent request/status delivery, and relay hints.
- **Feature:** preview and admin controls, notifications, pending requests, privacy disclosure, and error presentation.

Open questions:

1. Inline or fetched preview; descriptor authentication and relay-hint disclosure.
2. Exact nested-envelope bindings and the disclosure cost of transferable signatures; signer support, bounded
   distribution, generation convergence, and catch-up.
3. Request-to-Welcome correlation and requester-visible status authority under first-contact trust.
4. Concurrent decisions and reproducible pre-expiry evidence, including confirmation of the manual late-request fallback.
5. Revocation, withdrawal, security-driven retirement, and retired-key retention for pending requests.

Review scenarios cover normal joining; offline admins across expiry; late or backdated requests; duplicate and
conflicting decisions; reusable and single-use packages; unrelated Welcomes; forged group records; mismatched nested
authors or groups; replay after demotion; promotion and device catch-up; partial distribution and total key loss;
copied retired links; public metadata inspection; and unsupported clients.
