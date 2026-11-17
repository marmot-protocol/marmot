# Per-message expiry

Status: draft.

A sender can shorten the lifetime of one text message or ordinary attachment without changing the conversation timer.
Expire-after-send uses an absolute cap. Burn-after-read adds an independent countdown on each receiving account-device,
with an absolute cap for content never opened. Both are cooperative deletion requests, not cryptographic revocation.

## Owning surfaces

- [Per-message expiry v1](../foundation/message-expiry-v1.md) owns tags, validation, and earliest-of-policy calculation.
- [Application payloads](../foundation/application-messages.md) owns event encoding, sender authentication, and edits.
- [Message retention](../app-components/message-retention-v1.md) owns the source-epoch group ceiling.
- [Nostr transport](../transports/nostr.md#message-expiration) owns the outer deletion hint.
- [Account synchronization](./account-sync.md#history-bundles) owns history and backup delivery.
- [Retained history](../protocol-core/retained-history.md) owns protocol evidence and cryptographic retention.

This feature introduces no group-state update, custom MLS proposal, or required component. An authenticated member may
select it for their own kind `9` message. A selected lifetime never extends or disables source-epoch group retention.

## Sending and activation

The sender selects expire-after-send duration, or both after-read duration and unopened duration. The producer validates
all durations and checked timestamp calculations before creating the app event. Retry and republication retain the
same authenticated policy bytes and absolute cap; they never restart expiry.

For burn-after-read, the sending device starts its local countdown at the first successful publication acknowledged
under the active transport binding. It MUST retain the deadline before reporting success or presenting sent content.
A failed send with no acknowledged publication starts no read countdown. Its absolute cap still applies.
After an interrupted publication, the client MUST reuse a retained deadline or reconstruct the original successful
publication time. If it knows publication succeeded but cannot establish that time, it expires its local content
rather than starting a fresh countdown. Other devices of the sending account follow the receiving-device rule.

## Explicit reveal

A receiving account-device starts its countdown only when the user explicitly reveals or marks that message read as
content presentation. A chat-level unread-cursor update, including one synchronized from another device, is not that
message's reveal. Neither background receipt, push, catch-up, notification indexing, nor search starts the countdown.

For an unopened burn-after-read message, every passive surface exposes only a placeholder and policy metadata. Before
returning text, preview text, or decrypted attachment bytes in response to an explicit reveal, the client MUST:

1. Recheck the pinned absolute cap and any existing local deadline against the device's current time.
2. If due, retain expired state and return no content.
3. Otherwise establish `local_read_expires_at` as the earlier of the absolute cap and checked first-reveal time plus
   `after_read_seconds`. An existing deadline can only stay the same or become earlier. An undefined sum is due.
4. Retain that decision durably before, or atomically with, releasing any content.

Failure to retain the decision releases no content. Concurrent reveals, retries, and a crash at this boundary MUST
NOT establish a later deadline. A restart between retention and presentation may consume time without displaying
content; it must not give the message a new lifetime. Each device has its own countdown, never beyond the same
absolute cap. Reading on one device does not start or reset another's countdown.

An explicit reveal gives access only while the effective deadline has not passed. Every later content access,
including a cached handle or attachment range read, checks that deadline. It is not a permanent disclosure grant.

## Time and expiry

A message is due when local time is equal to or greater than its effective expiry. An unopened absolute cap applies
even while the message is unread or the device was offline. Expiry MUST NOT wait for a read marker, network access,
or a group timer change. A delayed cleanup pass does not permit returning due plaintext.

Clients MUST retain sufficient local time observations to detect backward wall-clock movement across restart.
When such movement makes a held message's remaining lifetime ambiguous, the client treats that message as due and
retains the expired decision before any further presentation. It does not move its deadline later to compensate.
A monotonic clock SHOULD also bound countdowns within one running process. Time rollback cannot unexpire a message.
Undetectable clock manipulation and an OS restoring an older entire device state remain limitations; this feature
provides no trusted clock or rollback-resistant hardware.

Expiry removes the message's application plaintext and locally controlled derivatives: edit bodies, reply and chat
previews, search-index text, notification content, attachment plaintext and thumbnails, and decrypted media caches.
Cleanup MUST also revoke pending content projections and prevent a completing attachment fetch from repopulating an
expired cache. Media shared with an unexpired message is released only when that reference no longer needs it.
A client MUST NOT delete another message's attachment or unrelated epoch material to expire this message.

Local expired state survives replay, import, and branch re-selection. Keep enough non-content metadata to avoid
resurrection while retained protocol bytes could reproduce the message. The timeline may show an expired tombstone,
policy, and deadline, but no message body, attachment URL, filename, quoted body, or decrypted attachment handle.
Protocol bytes, pending publish obligations, and cryptographic material follow their own retention rules, not this
timer. Reprocessing those bytes does not authorize recreating expired application content.

Implementations SHOULD use deadline-ordered discovery and bounded cleanup batches, not a full history scan for each
message. Already-due arrivals produce no plaintext notification or repeating expiry task. Invalid policy allocates no
policy-specific timer. Cleanup failure keeps content inaccessible while cleanup is retried under bounded local work.

## Derived surfaces and updates

Burn-after-read notifications are generic by default and include no message text, attachment name, or thumbnail.
A host may explicitly opt into content notification previews only if the client durably consumes the message through
the same reveal boundary before constructing the preview. Delivery or notification-service receipt is never a reveal.
Notification removal is best effort once the OS owns a copy; clients do not claim erasure of OS history or captures.

Search, accessibility, reply previews, copy, share, forwarding, and transcript presentation use the same reveal and
expiry checks as the main timeline. Searching unopened content does not return body-derived snippets or matches.
A bookmark retains a reference, not a plaintext copy or an exemption from expiry. A reply carries a reference rather
than an automatically copied expiring body; any local quoted preview disappears when its source expires.

An edit inherits its target's pinned absolute cap, after-read policy, and existing device-local deadline. It does not
restart a countdown and cannot extend retention. Its own source-epoch group cap may shorten the inherited cap.
The edit carries no new per-message policy tags. Its content remains withheld until the target and its policy are
known; a client may discard an edit whose target remains unavailable under a bounded local holding policy.
An edit or reaction targeting expired content does not restore content or create a new visible chat message.

A client-generated forward is an explicit content access. It requires reveal before reading an unopened source and
uses a new message whose absolute cap is no later than the source's current effective deadline. It also preserves the
source's after-read duration when present. A client refuses a forward when those constraints cannot produce a valid,
unexpired policy. Manually copied text is outside this enforcement boundary and is covered by the capture warning.

Forwarding may expose the source's shortened deadline through the new message's absolute cap. It does not update
the original message's transport envelope or reset its countdown.

## History, backups, and compatibility

Automatic sibling history, backups, and transcript-file exports MUST exclude burn-after-read messages and the edit or
preview content derived from them, whether opened or unopened. These paths neither consume the message nor grant a
fresh countdown on restore. Clients MUST discard such events if an older or nonconforming client includes them in an
import. Referencing an omitted message does not itself authorize exporting a copied body.

Expire-after-send messages may travel in history or backups only with their original authenticated policy and pinned
group decision. Export and import both enforce their original absolute expiry, and archive availability metadata must
not advertise a lifetime beyond that deadline. A client that cannot preserve those facts omits the message instead.
An expired local tombstone wins over any imported copy. External exports or copies already made cannot be retracted.

A client supporting version `1` but unable to implement its reveal boundary MUST render burn-after-read content as
unsupported, not as ordinary chat. Unknown versions follow the wire profile's unsupported-policy rule without breaking
the group. A client supporting only absolute expiry may honor the valid absolute cap while withholding content it
cannot safely reveal. Clients predating this feature may ignore all these tags and retain or reveal the content.
There is no support negotiation in this version and no claim that every member implements the feature.

Before sending, clients MUST communicate this limitation in product copy. Suitable wording is:

> Recipients can copy or capture this message. Deletion depends on their clients and cannot erase saved copies.

## Conformance cases

Implementations need cases for an offline recipient receiving a past cap; different first reveals on two devices;
a crash before and after retaining a reveal; duplicate delivery and restart after reveal; clock rollback; zero,
overflowing, duplicated, unknown-version, and out-of-range policy fields; and every earliest-of-policy calculation.
Coverage also includes edit-before-target, reply and bookmark cleanup, refused expired forwards, notification and
search suppression before reveal, shared-media references, attachment completion racing expiry, history or backup
import attempting resurrection, and retention changes after acceptance. These are required behaviors to verify, not
a claim that this proposal has implementation or model-checking evidence.
