# Group invite links

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

This idea covers inviting someone into a group with a link: you share it, they see the group, they ask to join, and an
admin adds them with the Welcome flow Marmot already has. It describes the experience and the direction we want. The
protocol details come later, surface by surface.

The goal is for this to feel like sending someone a link to a chat. They should not have to handle keys or relays.
You should be able to hand them something short, and they should be able to wait if every admin is away.

## At a glance

- **You share a link, not a key.** The invitation itself is a long code. A short `wn.fo` link, or a QR code, is how that
  code gets onto their phone.
- **They see the group, then tap Join.** The name, the description, and the picture come first. Nothing is sent until
  they ask. The app says the preview is confirmed when an admin's invitation arrives.
- **Any admin can say yes.** Admins share a key for the request inbox, so whoever is around can read the request.
  Adding someone still follows [admin policy](../app-components/admin-policy-v1.md) and the normal Welcome.
- **Waiting is a normal outcome.** An admin who is offline does not drop the request. Expiry stops new people. It does
  not throw away a request an admin already has.
- **History starts at joining.** The invitation carries only what a Welcome already carries.
- **The picture is not the group.** The app shows who sent the Welcome. If the preview does not match that invitation,
  it says so before they accept.

## Words used here

| Term | Meaning |
| --- | --- |
| Long code | The Bech32m invitation. It locates an encrypted preview and carries the secrets that decrypt it. Text, or a QR code of the text. |
| Short link | About eight characters on `wn.fo`, for example `wn.fo/k3m9qx2a`. A lookup for one long code. |
| Inbox | A fresh random key that receives requests for one link. It is not an account, and it is not the group's delivery address. Active admins hold the private key. |
| Bearer | A secret in the long code. Holding it lets someone file a request. It does not put them in the group. |
| Preview | The name, description, and image the long code decrypts. |
| Preview commitment | A commitment to that preview in the group's authenticated state. Admins update it the same way they update other group policy. The inbox key cannot. |

The **requester** is the account asking to join from a particular device. **Active admin** has the meaning in admin
policy. **Approve** means attempt the authorized invitation, not that it has already succeeded. An accepted Add makes
the group-side result **Invited**; **Joined** waits for that requesting device's successful Welcome processing and
request association. No response is waiting, not rejection. These words also fit a future Requests screen containing
suggestions from existing members, but the two request sources are different.

An existing member suggesting another account can check that account's eligibility first and send only its public
key; the admin then discovers and validates a package independently. This link flow instead receives a request from
the joining device itself, with its offered package and private delivery context. It does not turn a member's
account-level suggestion into consent from an outsider or expose link request details to ordinary group members.

## What this does and does not protect

- **`wn.fo` can read the short links it hosts.** It stores the long code, so it can see the preview and file a request.
  Sharing the long code directly never sends it through that host.
- **The preview on the request screen is unconfirmed.** The inbox key publishes the encrypted preview, and anyone who
  kept that key can replace it. The commitment in group state is what gets checked when the Welcome arrives. If the
  two differ, the app says so before the person accepts.
- **A matching preview does not name the group they joined.** Whoever authors the Welcome authors the group state
  inside it, commitment included. The first-contact limit in
  [Welcome-bootstrap trust](../protocol-core/joining.md#welcome-bootstrap-trust) still applies. They are trusting the
  inviter the app shows them.
- **The bearer stops strangers, not a leaked link.** A public request reveals the inbox address. The bearer is how the
  app tells a link holder from someone who only saw that address. In automatic mode, holding the link is enough for an
  online admin's app to add them without a person looking.
- **Removing an admin does not take the inbox key back.** Requests already sent to that inbox stay readable by anyone
  who learned the key. Later requests need a new link. A removed admin still cannot change the preview commitment.
- **Joining is not anonymous.** The request's contents are encrypted to the inbox. The Welcome is still addressed to
  the joiner's npub, as in [Nostr Welcome delivery](../transports/nostr.md#welcome-delivery), and the timing of the two
  public events can connect them.
- **An admin seal can be shown outside the group.** The [Marmot app event](../foundation/application-messages.md)
  around it stays unsigned. A signed seal nested inside can be forwarded to someone who never received the group
  message.

## Scene 1: Alice shares a link

![Alice turns invite links on for Book club, chooses approval and a 7 day expiry, then shares a short wn.fo link, a QR
code, or the long code.](group-invite-links/scene-1-share.svg)

**What Alice sees:** in the group, she turns invite links on. She picks what happens when someone asks, and how long
the link works.

- **Approve requests.** Bob shows up on the Requests screen. An admin taps Approve or Reject.
- **Add automatically.** The same checks run in the background. Bob sees "Waiting for an invite" until an admin's app
  is online to send it.

The share sheet then offers three ways to hand over one invitation:

- **Short link.** `https://wn.fo/k3m9qx2a`. This is the one she pastes into a chat.
- **QR code.** Of the short link, for a poster, or of the long code, for when `wn.fo` should not be involved.
- **Long code.** The Bech32m string, for pasting or for that second QR.

**The long code:** a custom [Bech32m](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki) value. A prefix
such as `wn` or `marmot` is the candidate; this idea does not reserve one. The shape follows
[NIP-19 `naddr`](https://github.com/nostr-protocol/nips/blob/master/19.md): an author, a kind, an identifier, and
optional relay hints. It then carries secrets an `naddr` has no place for, and ordinary `naddr` is Bech32, so this is
its own encoding rather than an `naddr` with the prefix swapped.

The inbox public key is the descriptor's author, so the public address is not Alice's account, not the MLS group id,
and not the group's delivery address. Admins keep the inbox private key. The bearer and the preview key travel in the
long code. The image is fetched with the descriptor. The code carries the key for that image, not the image itself.
Alice's app also writes the preview commitment into group state. That commitment is what makes the preview the
group's. The inbox key is only what outsiders encrypt a request to.

**The short link:** about eight characters after `wn.fo/`. `wn.fo` stores the long code under that id. There is no
public list of ids.

- **The app is installed.** The phone treats the link as Marmot's. It opens the app and passes the Bech32m in. Bob
  lands on the preview in Scene 2.
- **The app is not installed.** `wn.fo` shows how to download it, and nothing about the group. After he installs, the
  same link opens the app with the Bech32m.

**Trade-offs:**

- `wn.fo` holds the long code, so it can read the preview and the bearer. The long code, shared as text or as its own
  QR, never goes through that host. A QR of the short link still needs `wn.fo` to be up when it is scanned.
- Chat apps that unfurl links see a generic page. They do not get the group name or the picture. The site that serves
  the page can still read the id, because it is in the path.
- Deleting the short link only breaks that URL. Anyone who already opened it, and anyone holding the long code, still
  has the invitation. Turning the invitation off is Scene 6.
- Eight characters is short enough to read over a shoulder. Guessing one at random is not practical if the host does
  not offer a directory and does not answer bulk lookups.

**Decision:** the invitation is the long code. The short link and the QR codes are ways to get that code into the app.
`wn.fo` does not admit anyone.

## Scene 2: Bob asks to join

![Bob opens wn.fo/k3m9qx2a. With no app he gets a download page. With the app he sees the Book club preview, marked
unconfirmed, and a Join button.](group-invite-links/scene-2-open.svg)

**What Bob sees:**

1. He taps the short link, scans a QR, or pastes the long code.
2. **No app.** The page says someone sent him a Marmot invite, tells him how to install the app, and tells him to open
   the same link again afterward. It does not show Book club.
3. **App installed.** Marmot shows the name, the description, and the picture, with a line that this preview is
   confirmed when an admin invites him.
4. He taps **Join**. Nothing was sent before that.
5. He then sees **Waiting for approval**, or **Waiting for an invite** if Alice chose automatic.

**Underneath:** the app sends a [NIP-59 gift wrap](https://github.com/nostr-protocol/nips/blob/master/59.md) to the
inbox. The outer signer is a one-time key. Inside, Bob's account is authenticated, the request names this link and a
stable request id, shows the bearer, points at a KeyPackage, and says where to deliver the Welcome. A private address
for status replies is optional. Those fields get their encodings in the documents that will own them.

The chain ties that account to the KeyPackage credential, the account proof, the publication, and the Welcome
recipient. Hints are for routing only. [KeyPackage validation](../foundation/key-packages.md) still applies, including
single-use packages and supported last-resort reuse. Retrying keeps the same request id. If every relay copy
disappears, Bob submits again.

**Trade-offs:**

- Publishing a fresh KeyPackage in the same minute as the gift wrap gives observers a timing hint. A package that is
  already public avoids that pairing.
- In automatic mode, anyone who has the link will be added as soon as an admin's app is online. That is what Alice
  chose. Approval mode is the one where a person looks at Bob first.

**Decision:** the bearer lets Bob file a request. It does not add him. The Welcome adds the device that sent the
request. His other devices catch up the way [multi-device](./multi-device.md) already describes.

## Scene 3: An admin handles it

![Alice and Carol both see Bob waiting on the Book club Requests screen, with Approve and Reject.](group-invite-links/scene-3-requests.svg)

**What Alice sees** on the Requests screen:

| Shows | What she can do |
| --- | --- |
| Who asked, and which link they used | Approve, Reject |
| A problem with the KeyPackage, or with timing | The row says why it cannot be added as-is |
| Automatic-mode requests | No prompt when eligible. The app runs the same checks and sends the Welcome; timing-unverified requests after expiry wait for manual approval as in Scene 6. |

A lock-screen alert can say that a request is waiting, without Bob's name.

**Underneath:** every active admin who holds the inbox key can fetch the gift wrap. Carol sees the same row even
though Alice created the link. The decision is recorded on the admin channel in Scene 5, and it names which admin
acted. The app reads current group policy before it acts. A delivered control message shows that an admin sent it. It
does not change policy by itself.

Two admins can approve or reject at the same time, and Bob can ask from two devices. Arrival order and relay
timestamps do not choose membership. The Commit does. A rejection leaves someone who is already a member in the group.

**Decision:** every active admin has the same say. The inbox key lets them read the request. Admin policy lets them
add or refuse.

## Scene 4: Bob gets the Welcome

![If the preview matches the invitation, Bob sees Book club and Alice as the inviter. If it does not, the app says the
link showed a different group and still names Alice.](group-invite-links/scene-4-welcome.svg)

**What Bob sees:** the request becomes Joined only after the Welcome checks out and belongs to this request. Some
other Welcome is an ordinary invitation and does not close the request.

On that screen the inviter's account is the identity he is accepting, next to the preview.

- **The preview matches** the commitment in the group he is joining. The app says the invitation matches the preview
  he saw, and shows who invited him. That match does not independently authenticate the intended group.
- **It does not match.** The app says the link showed a different group than this invitation. It still shows the
  inviter. He can join that person's group, or not.

The comparison keeps the preview Bob actually saw when he tapped Join. The app can fetch the descriptor again to
diagnose a slow update, but a changed preview is shown as **updated since you saw it**, not silently substituted as
a match. Bob can review that updated preview and make a fresh choice; an inbox-key holder cannot rewrite what his
earlier confirmation meant.

**Underneath:** the approving admin follows the existing [join flow](../protocol-core/joining.md). For a group that
already exists, the Commit is published successfully before the Welcome is sent. The Welcome is addressed to Bob and
names the KeyPackage he offered.

A forged group can copy the public link records. Holding the inbox key proves custody of that key. It does not prove
this is the Book club Bob meant.

**Decision:** the preview check is the commitment inside the Welcome's group state. Bob is deciding about the inviter.
How a status reply binds this request to this Welcome is still open. The preview's name is not that binding. A missing
reply means keep waiting. A claimed rejection has to be authenticated before the app treats it as final. An
admin-account signature on a reply tells Bob which admin answered. An inbox-key signature can be made by anyone who
holds that key.

## Scene 5: Carol can read the request too

![Alice puts a copy of the inbox key for herself and for Carol inside a normal group message. Members see the
envelopes. Only Alice and Carol open them.](group-invite-links/scene-5-admins.svg)

**What Carol sees:** Bob on her Requests screen, including when she was offline and opens the app later. If the relay
copy is gone and no admin forwarded the request, she waits until one who still has it sends it again.

**Underneath:** group messages go to every member, so a secret that ordinary members are not meant to read is encrypted a
second time.

1. Alice creates the inbox key and the rest of the secret link material.
2. Her app encrypts a copy for every active admin, Alice included. On Nostr keys the proposed shape is a NIP-59
   envelope with its signed seal.
3. Those copies ride inside an unsigned Marmot app event, inside a normal group message.
4. Each admin opens their own copy and checks that it is for this group and this generation of the link.

The inbox public key, the bearer, and the preview key stay inside those copies. The surrounding event's tags do not
carry them, or every member would learn the inbox. Members can see the admin addresses on the envelopes. They already
know the admin list from group policy. Relays see ordinary group traffic, because the envelopes were not published by
themselves.

The same channel carries the approve or reject, and a copy of the request for admins who missed the gift wrap.
Putting the request in a normal group message, in the clear, would show Bob to every member.

A current admin authors a fresh copy when someone new needs it. Forwarding an old envelope keeps that envelope's old
context. A duplicate does not reopen a decision already applied. First arrival is only evidence that a message showed
up.

**When someone is missing the key:**

- **Carol was offline.** She reads retained group traffic if it is still there. If the epoch keys are gone, she waits
  for an admin who still has the material to send a fresh copy.
- **A new admin.** After the promotion is in group state, a current admin sends a fresh copy.
- **A new device of an admin.** A device that is already in the group receives a fresh copy. A device that cannot sign
  with the account key needs a signer design before it can author these records.
- **Nobody still has it.** Alice issues a new link. Unread requests cannot be reconstructed.

Fresh copies cover current links and requests still open. They do not include old chat, and they do not include every
retired inbox. Sending a retired inbox key also exposes whatever requests are still encrypted to it. Forwarding the
specific pending requests, already decrypted, is the smaller disclosure.

**Trade-offs:**

- Giving the inbox key to every member would be simpler, and every member would see who asked, including someone who
  left and kept a copy. They could also forge a status reply that is signed only by the inbox key.
- Removing Carol as admin leaves her with any key she already learned. New requests need a new link. She cannot change
  the preview commitment, and automatic admission stops using the old inbox.
- The signed seals are the disclosable records in the section above. MLS already says which member sent the group
  message.

**Decision:** only admins hold the inbox key. Group state, not this message, says whether the link is on and which
generation is current.

## Scene 6: The link expires

![After expiry a new visitor is told the link is closed. Alice's queue still has Bob, and a request found only after
expiry is marked timing unverified.](group-invite-links/scene-6-expiry.svg)

**What a new person sees:** the link no longer takes requests. If they had already asked, they still see waiting.

**What Alice sees:** Bob's request stays on the list after the expiry time, and she can still approve it. A request
that turns up only after expiry is marked **timing unverified**. She approves that one by hand. If a Welcome already
went out, the row follows the Commit. The late label does not undo it.

**Underneath:** Bob can put any time he wants on the request, and NIP-59 fuzzes the outer timestamp on purpose. The
app does not treat either one as proof he asked before expiry. Automatic admission after expiry would need evidence
this idea does not have. Until it does, a request first found after every admin was offline across the expiry goes to
the manual queue.

Approving later still checks the account binding, the package lifetime, capabilities, provenance, and the usual reuse
rules. A refreshed package comes from the authenticated requester and stays tied to the same account, request, and
intended joining device. An admin does not substitute an arbitrary package just because it names the same account:
that could invite a different device than the one that asked. How a refresh proves continuity when the device's leaf
signing key also changes remains an explicit wire-format question. Rotation after validation can still make a delayed
Welcome unusable, so Invited never promises Joined.

Revoking the link, Bob withdrawing, and rejecting him do not remove members. Whether revocation also drops requests
already in the queue is open. Disbanding the group follows the adopted
[group lifecycle](../app-components/group-lifecycle-v1.md), which does remove members. A security-driven retirement of
an inbox, where Alice suspects the key leaked, needs its own rule for the queue. That rule is open. Expiry by itself
is not that retirement.

**Decision:** expiry means stop taking new people. It does not decide a request an admin has already seen, and it does
not outrank a Commit that already added someone.

## Numbers

| | |
| --- | --- |
| Short link | about 8 characters, hosted at `wn.fo` |
| Example | `https://wn.fo/k3m9qx2a` |
| What the short link resolves to | the long Bech32m code |
| Long-code prefix | not chosen (`wn` and `marmot` are the candidates) |
| QR of the short link | needs `wn.fo` when scanned |
| QR of the long code | opens in the app with no `wn.fo` lookup; preview assets can still need network fetches |

## Open questions

These are the pieces we know are unsettled.

1. **Long-code layout.** The prefix, the Bech32m payload, the total length, and how many relay hints are worth the
   fingerprint and the QR size.
2. **Short-link details.** The exact alphabet, how `wn.fo` rate-limits lookups, and how long it keeps a code after the
   invitation expires. The group's expiry is what stops new requests. The host's retention only affects the short URL.
3. **Two admins at once.** What should happen when Alice and Carol both act, and what evidence would ever be enough to
   add someone automatically after expiry.
4. **Revocation and the queue.** Whether turning a link off, withdrawing, or retiring an inbox after a suspected leak
   cancels requests already waiting, and how long a retired key is kept for that queue.
5. **Status replies.** Who Bob is entitled to believe, and how a reply points at one Welcome. The preview name is not
   the binding.
6. **Signers.** A device that is in the group but does not hold the account key cannot author the sealed admin copies
   until there is an explicit signer design.
7. **Package refresh.** The authenticated refresh message, package selection/reference, and proof of continuity to
   the intended requesting device, including a changed leaf signing key. An account match alone is not that proof.

## Path into the spec

Nothing here assigns component ids, event kinds, exporter labels, or wire bytes. `wn.fo` is a way to deliver the long
code. It is not a protocol role.

1. **App components.** Link policy, generation, and the preview commitment in group state.
2. **Transport.** The long-code encoding, where the descriptor lives, the admin envelopes, and how requests and status
   replies stay available for an offline admin.
3. **Foundation.** How a request binds a person to a KeyPackage, and the bounds on envelope size, pending requests,
   retries, and preview rendering.
4. **Protocol core.** How a request becomes an Add, how it lines up with one Welcome, and how two decisions meet
   existing convergence.
5. **Feature.** The share sheet, the download page, the unconfirmed preview, the inviter shown at join, and the
   Requests screen.

Before those rules are adopted, the owning documents spell out versioned bounded request and decision formats,
canonical encodings and references, account/device/group/link/generation bindings, package refresh and Welcome
correlation, sender authorization at source epoch and action time, duplicate/replay handling, competing decisions,
restart and retention behavior, unknown-version handling, and fixed examples with negative conformance cases. This
checklist does not assign wire identifiers or settle those open questions inside an idea document. Expiring a link
and losing a retained request copy remain separate events; neither is evidence of rejection or a completed join.
