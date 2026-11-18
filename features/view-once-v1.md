# View-once media v1

Status: adopted.

View-once media allows one bounded opening of an image or video on each receiving account-device. It is a rule for
conforming clients, not cryptographic revocation against a recipient that retains keys or copies plaintext.

## Surfaces and activation

- [group-view-once-v1.md](../app-components/group-view-once-v1.md) owns capability negotiation, explicit activation,
  the support invariant, and the prohibition on removal.
- [encrypted-media.md](encrypted-media.md) owns the reusable source-epoch media exporter, attachment fields, locators,
  MIME type, filename, and ordinary media construction.
- [application-messages.md](../foundation/application-messages.md) owns inner-event authentication and identity.
- [message-retention-v1.md](../app-components/message-retention-v1.md) owns composition with message expiry.
- [nostr.md](../transports/nostr.md#message-expiration) owns relay-facing expiration metadata.
- [account-sync.md](account-sync.md#history-bundles) owns portable history bundles and backups.
- [retained-history.md](../protocol-core/retained-history.md) owns protocol evidence and secret-release conditions.

A sender MUST use this profile only in a source epoch requiring `marmot.group.view-once.v1` and
`marmot.group.encrypted-media.v2`. Ordinary v2 remains a separate reusable attachment profile. Supporting ordinary v2
alone does not authorize sending view-once, and a client MUST NOT silently downgrade a requested view-once send to v2.

## Authenticated message format

The message is an unsigned inner kind `9` app event with empty `content`, exactly one `imeta` tag, and exactly one
message-wide marker tag. No other message tags are allowed. The marker is:

```json
["view-once", "view-once-v1", "<absolute Unix seconds>"]
```

The marker has exactly three strings. Its name and version are exact, case-sensitive ASCII bytes. Its deadline is a
canonical unsigned decimal integer in `0..18446744073709551615`: digits only, no sign, whitespace, or leading zero
unless the entire value is `0`. The event's `created_at` MUST be an exact non-negative decimal JSON integer in the same
range, with no sign, fraction, exponent, or leading zeros.

Let `deadline` be the marker timestamp and `created_at` the inner timestamp. Validity requires:

```text
0 < deadline - created_at <= 3888000
```

The subtraction is checked unsigned-64-bit arithmetic. The upper bound is 45 days of 86,400 seconds each. A receiver
MUST NOT wrap, round, or saturate either timestamp. The deadline is absolute and does not start at delivery or opening.

A sender MUST set `created_at` to its current Unix time. For the first authenticated application admission, a receiver
samples its local wall clock and MUST durably cap the effective deadline at no later than that sample plus 3,888,000 seconds, using checked
arithmetic. An older high-water value MUST NOT replace this sample as the cap's base. The high-water still governs
expiry decisions, so a corrected clock can make a newly received message immediately expired. A future-dated sender
timestamp cannot extend this local cap. Replay, reimport, and republication MUST NOT refresh it. This is an additional
maximum, not a replacement for an earlier authenticated deadline.
The cap is relative to the receiver's admission-time wall-clock reading, not independently verified UTC. An inaccurate
clock and later correction can lengthen or shorten the lifetime in true elapsed time; the high-water does not correct
that initial reading. This profile does not provide a trusted-time maximum across such clock errors.

The device MUST commit first application admission and its sample or resulting cap in one durable admission record,
including for an unopened message, before any application-visible projection. That commit is the first application
admission even if the projection has not committed. A crash or re-emission MUST NOT replace that record's sample or cap.
Admission records share the durability
and cleanup boundary of retained source-epoch secret access; ordinary history deletion or projection rebuild MUST NOT
remove them while that access remains. Protocol persistence alone is not application admission: a delivery without a
first admission record may be re-emitted and sampled for that first admission. A message already
admitted never gets another sample or cap. A previously admitted message missing its admission record or stored cap while
source-epoch secrets remain MUST fail closed rather than initialize another cap. These guarantees assume intact durable
device state, not arbitrary erasure or corruption of admission evidence while retaining the keys.

The single attachment uses `v encrypted-media-view-once-v1`. It inherits the
[encrypted-media v2 message shape](encrypted-media.md#message-shape), reference-level
[validation and locator-kind fetchability rules](encrypted-media.md#validation), with `encrypted-media-view-once-v1`
replacing `encrypted-media-v2` in the version check. These additional restrictions apply:

- The canonical MIME type has type `image` or `video`. Before display, the decoded content MUST agree with that type
  and satisfy bounded decoder, size, and dimension policies. The authenticated MIME type alone is not content validation.
- A sender MUST NOT encrypt more than 64 MiB of plaintext. Ciphertext is at most 64 MiB plus its 16-byte AEAD tag.
  Image or video dimensions MUST NOT exceed 8,192 pixels per edge or 16,777,216 pixels per frame. Both sender and
  receiver enforce these bounds; local decoder policy MAY refuse additional formats or impose stricter bounds.
- `dim`, `thumbhash`, `blurhash`, thumbnails, preview URLs, and alternate attachments are forbidden.
- Empty attachment fields, duplicate fields other than `locator`, and fields named `thumb`, `image`, `fallback`, `alt`,
  or `summary` are forbidden.
- The message MUST NOT contain a caption, reply thumbnail, quoted media content, reaction payload, or edit form.
  Receivers MUST NOT honor edits that target this message or use it as a source of media previews.

A receiver MUST refuse media access if the event violates any rule in this section, including kind, content, tag set,
deadline range, marker or attachment grammar, or version agreement. This includes a view-once attachment
without its marker and an ordinary media attachment with a view-once marker. A source epoch not requiring the feature
also makes the media unusable. A receiver MUST NOT repair such inputs, ignore the marker to render ordinary media, or
try another media profile after decryption fails. These are feature-level failures, not a reason to roll back otherwise
valid MLS state. They expose at most a content-free unavailable placeholder.

View-once grammar, deadline, and attachment failures by themselves affect only media access and presentation. They
MUST NOT alter app-payload validity for delivery, receiver authentication, or app-payload witness counting.

## Cryptographic domain

The construction uses the existing media exporter of the authenticated application message's source epoch:

```text
media_secret = MLS-Exporter("marmot", "encrypted-media", 32) at source_epoch
file_key     = HKDF-Expand(media_secret,
                           "encrypted-media-view-once-v1" || 0x00 || plaintext_sha256_bytes ||
                           0x00 || media_type || 0x00 || filename ||
                           0x00 || "key",
                           32)
nonce        = random(12)
aad          = "encrypted-media-view-once-v1" || 0x00 || plaintext_sha256_bytes ||
               0x00 || media_type || 0x00 || filename
ciphertext   = ChaCha20-Poly1305.encrypt(file_key, nonce, plaintext, aad)
```

The key derivation and byte encoding are identical to [v2 key derivation](encrypted-media.md#key-derivation),
except for the view-once domain label shown above.
The [v2 nonce rules](encrypted-media.md#encryption) apply to every encryption, including resend and retry.
Ciphertext and plaintext hashes MUST both be verified before display.

The epoch and branch used for the file exporter MUST be the epoch and branch used to encrypt the MLS application
message. A queued send MUST retain that epoch identity rather than silently moving the payload to a later epoch.
If convergence or a concurrent Commit changes it, the sender MUST visibly refuse the send or rebuild the attachment
with the new exporter, a fresh nonce, and a new event. Sending MUST fail if the resulting source epoch does not require
the two components above. This check occurs at MLS encryption, not only before upload.

After a sent view-once message is invalidated or loses branch selection, the sender MUST NOT automatically resend it.
Resending requires an explicit user action and creates a new message with a new opening on each receiving device.

Both the KDF and AAD use the view-once domain. Removing the marker or changing `v` to `encrypted-media-v2` therefore
cannot make the ciphertext decrypt under the ordinary media construction. A receiver MUST NOT return view-once
plaintext through ordinary attachment acquisition, download, cache, or export paths, even if the caller supplies a
complete reference or the same blob is already present locally.

This profile does not carry a random independent per-file key and does not erase source-epoch media secrets on opening.
Ordinary media can share that exporter. Deleting it to consume one attachment would break other attachments and is
neither required nor permitted as a substitute for the consumption rules below. A recipient retaining the exporter and
reference can derive the file key again outside a conforming client.

## Per-device consumption

The consumption identity is the receiving account-device, MLS group identity, authenticated inner app event id, and
attachment index `0`. It is not the transport wrapper, ciphertext hash, filename, or a disposable history projection.
Different receiving devices, including siblings of one account, have independent openings. Concurrent callers on one
device compete for the same opening. The sender's account MUST NOT consume its own message, including on a sibling
device. The sender may inspect its original input before sending but MUST release its draft and upload ownership after
sending instead of retaining the sent view-once file as an ordinary attachment.

An opening requires that device to authenticate the original MLS application message. Portable history does not
deliver it to a sibling; an offline member may still obtain the original envelope from a relay before expiry.

A conforming client maintains these local outcomes:

- `unopened`: authenticated, visible, within its expiry, and not yet claimed;
- `consumed`: its opening was durably claimed, whether or not decryption or display succeeded;
- `expired`: its effective unopened deadline was reached;
- `unavailable`: source authentication, visibility, membership, format, required material, or a local safety check
  does not allow access.

The receiver MUST commit a claim only against one coherent eligibility decision covering every ciphertext-independent
rule in [authenticated message format](#authenticated-message-format), the configured MIME allowlist, current locator-kind
fetchability and endpoint-contact policy, expiry, source visibility, and exclusive admission to the account's single viewer. If any check fails,
the receiver MUST refuse without committing consumption. This includes a malformed event or reference, unsupported MIME,
no locator or fallback endpoint that the client's current policy will contact, or a busy viewer. Contact-policy checks
include permitted schemes, blocked endpoints, and locally unsafe destinations. A local refusal does not invalidate the
authenticated message or its media reference; it leaves the opening unclaimed.

A separate metadata preflight MUST either keep the checked metadata and policy stable through the claim or recheck
them before committing; a stale preflight result cannot authorize a claim. Serialization can establish that coherence;
the rules do not require one physical database transaction for every check. Checking viewer availability and obtaining
exclusive admission MUST be atomic against competing opening attempts. A claim MUST NOT commit without that admission,
which stays exclusive through the claim and resulting viewer. When the claim fails or the opening attempt ends,
that exclusive admission ends without resetting a terminal consumption decision.
The [implementation model](../implementation-model.md#view-once-viewer-admission) describes viewer-slot mechanics.

Before fetching or reading attachment ciphertext, decrypting any attachment bytes, or exposing plaintext, the receiver MUST atomically and durably claim the
opening. At most one concurrent claimant may succeed. A crash before a durable claim exposes no plaintext and may
leave the message unopened. After a claim, cancellation, transport failure, decryption failure, invalid content, viewer
failure, and a crash all leave it consumed. Restart MUST NOT resume the viewer or grant another opening.

Consumed takes precedence over unavailable once a claim commits: material or safety failures discovered afterward
do not reset it. Ciphertext prefetching or validation before claiming is not permitted for this profile.
A network or blob-server failure can spend the opening without displaying anything; clients MUST
communicate that opening is an attempt, not a guarantee of successful display. A refusal before a claim exposes no
plaintext and does not consume an unopened message.

Terminal consumed and expired decisions MUST survive ordinary history deletion, replay, transport republication,
projection rebuild, branch changes, rejoin, and imported history on that device. If consumption state is unavailable or
cannot be committed, access fails closed. Only an explicit full account-device wipe ends that local identity. Portable
history, backups, and sibling messages MUST NOT carry consumption state or create a new opening on an existing device.
Whole-device restoration to a snapshot predating the decision is outside the rollback guarantee below.

A full wipe MUST remove the account-device's MLS state and source-epoch secrets as well as its consumption state.
Clearing app projections or consumption records while retaining those secrets is not a new identity and MUST fail
closed rather than grant another opening.

Opening, closing, consuming, and expiry MUST NOT send receipts, reactions, deletion requests, consumption broadcasts,
or account-device synchronization messages. Another recipient's ability to open the file is unaffected.

This does not hide the ciphertext fetch. The blob server can observe an opening attempt's request time, network
address, and any authentication metadata; it does not prove successful display. Local endpoint-contact policy still
applies; see [SC-059](../security-considerations.md#sc-059-authenticated-external-locator-reaches-an-unsafe-or-tracking-endpoint).

## Expiry and bounded viewing

The effective unopened deadline is the earliest finite bound from the marker, the durable first-receipt cap,
and the absolute source-epoch `expiry_timestamp` calculated by
[message retention](../app-components/message-retention-v1.md#state). A disabled duration or undefined calculation
supplies no finite group bound. An arbitrary inner `expiration` tag has no independent authority and is not permitted
by this profile's message grammar. Later policy changes or republication MUST NOT extend that deadline. An offline
receiver checks expiry before claiming, not only when it first receives the event.

A device MUST retain a wall-clock high-water value for expiry decisions and use at least that value after a local clock
rollback. Once expired, an attachment stays expired. This prevents reopening after a clock adjustment while the durable
state remains intact. It does not defend against replacing the entire state with an older backup or a hostile host
changing the clock and consumption records together.
A forward clock error can deny openings on this receiving account-device even after correction: new messages expire
immediately while their effective deadlines are no later than the stored high-water. Correcting the clock does not
lower that floor or restore expired messages. New messages become usable only when their deadlines exceed the floor.

A successful claim permits one foreground viewer for at most 60 seconds of monotonic elapsed time, and never beyond
the effective deadline. The budget starts no later than the durable claim and includes fetching, decryption, and
validation; it does not restart when plaintext becomes available or the first frame is displayed. A sender MUST
communicate this opening-attempt budget, including that a slow transfer can spend it without display and a long video
may not play in full. This profile bounds the opening session, not media duration or a guaranteed complete playback;
it does not require a particular playback interface. A device MUST permit at most one live view-once viewer per account.
The viewer MUST hold plaintext only in bounded memory, with at most 64 MiB plus the 16-byte AEAD tag of ciphertext
input and 64 MiB of plaintext. A stricter local bound is permitted. Plaintext files, retained media assets, system gallery insertion, automatic
prefetch decryption, and background preview generation are forbidden.

Before each plaintext read or continued display, the client MUST recheck expiry and source visibility. Deletion,
withdrawal from the selected branch, account closure or removal, group departure or disband, explicit close, and the
viewing timeout revoke the viewer. Revocation MUST prevent further reads and display and trigger best-effort cleanup
of buffers and decoder state. It MUST NOT reset the terminal claim or remove other owners of an ordinary shared file.

Clients SHOULD use available screenshot and recording suppression and exclude view-once content from notifications,
app-switcher snapshots, and crash diagnostics. Cleanup SHOULD clear owned plaintext, keys, and rendered buffers as soon
as possible. Host copies, graphics buffers, swap, crash dumps, cameras, and adversarial recipients prevent a guarantee
of screenshot prevention or physical erasure. Clients MUST NOT claim those guarantees.

Consumption and expiry MUST NOT delete the shared remote blob. Sender cleanup releases only the sender's local
ownership. Other recipients, devices, and unrelated attachments must remain usable under their own policies.

## Media references and content-free history

A usable reference includes any locator, ciphertext or plaintext hash, nonce, MIME type, filename, key, or combination
of attachment metadata that allows locating, deriving, decrypting, or reacquiring the file. Removing just its URL or
`imeta` version is not content-free. Source-epoch exporter secrets are not presentation data either.

Ordinary message projections, transcript listings, search, gallery, notification, quote, and attachment-descriptor
surfaces MUST expose only a content-free placeholder for view-once messages, including malformed combinations above.
They MAY expose the view-once flag, local outcome, deadline, and ordinary envelope metadata such as sender, position,
and inner event id. They MUST NOT expose the original `imeta`, usable references, filenames, media hashes, previews,
plaintext, or a path or handle usable by an ordinary downloader. Only the bounded opening path may privately resolve
the authenticated reference after admission. Merely listing history never claims or opens a message.

Portable transcript exports, backups, and sibling history transfers MUST omit view-once content, original events,
references, and derived file keys, regardless of whether the message is unopened or consumed. A format with a separate
presentation-record type MAY carry a content-free placeholder but MUST NOT label it as the original authenticated app
event: redacting an event changes its canonical id. The current [history bundle](account-sync.md#history-bundles) schema
has no such record type and omits the whole event. Import MUST NOT install a usable reference or restore an opening
from an event carrying a view-once marker or this media format, even if malformed or accompanied by a per-file key.

These application-history restrictions do not remove the protocol evidence that
[retained history](../protocol-core/retained-history.md) requires for convergence and crash recovery. Reprocessing such
evidence MUST still consult the durable consumption identity. It MUST NOT recreate ordinary media ownership or turn a
terminal message into unopened media. View-once does not change MLS branch selection or provide cryptographic erasure
of an epoch, retained MLS bytes, external blobs, or copied references.

## Migration and failure limits

Existing ordinary media references retain their original behavior. A historical event cannot become view-once by an
edit, nor can view-once become reusable through an edit or reference reclassification. Unsupported required capability
fails closed at negotiation. Unknown marker versions and media formats never fall back to ordinary v2.

The feature's guarantee assumes a conforming application and intact durable device state. A malicious member can save
plaintext or exporter material, take photographs, use a modified viewer, or forward copies. A whole-state rollback can
restore an earlier consumption decision. This profile neither prevents those actions nor makes shared source-epoch
key deletion a remedy for them.
