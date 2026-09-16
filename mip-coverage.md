# MIP coverage

Status: adopted.

This file maps the deprecated Marmot MIPs to this spec. It is a review aid, not a normative surface.

The merged canonical MIP set currently lives on the old Marmot repo's `origin/master`. MIP-06 remains branch-draft
work and is tracked here because it affects this spec's design.

## Deprecated MIPs

- MIP-00, Credentials & Key Packages: Review and required.
  - Foundation: [foundation/identity.md](./foundation/identity.md) and
    [foundation/key-packages.md](./foundation/key-packages.md);
    [app-components/account-identity-proof-v2.md](./app-components/account-identity-proof-v2.md) is new in this spec and
    breaking; [foundation/account-identity-proof-v1.md](./foundation/account-identity-proof-v1.md) records its
    superseded predecessor
  - Transport binding: [transports/nostr.md](./transports/nostr.md)
  - Protocol flow: [protocol-core/joining.md](./protocol-core/joining.md)
- MIP-01, Group Construction & Marmot Group Data Extension: Review and required.
  - Protocol flow: [protocol-core/group-setup.md](./protocol-core/group-setup.md)
  - App components: [app-components/](./app-components/)
  - Encoding: [foundation/canonical-encoding.md](./foundation/canonical-encoding.md)
- MIP-02, Welcome Events: Review and required.
  - Protocol flow: [protocol-core/joining.md](./protocol-core/joining.md)
  - Transport binding: [transports/nostr.md](./transports/nostr.md)
- MIP-03, Group Messages: Review and required.
  - Protocol flow: [protocol-core/group-messaging.md](./protocol-core/group-messaging.md)
  - Member departure: [protocol-core/member-departure.md](./protocol-core/member-departure.md)
  - Transport binding: [transports/nostr.md](./transports/nostr.md)
  - App payloads: [foundation/application-messages.md](./foundation/application-messages.md)
- MIP-04, Encrypted Media: Review and required for new app groups.
  - Feature flow: [features/encrypted-media.md](./features/encrypted-media.md)
  - Current app component: [app-components/group-encrypted-media-v2.md](./app-components/group-encrypted-media-v2.md)
  - Frozen v1 behavior: [features/encrypted-media-v1.md](./features/encrypted-media-v1.md) and
    [app-components/group-encrypted-media-v1.md](./app-components/group-encrypted-media-v1.md)
- MIP-05, Push Notifications: Draft and optional.
  - Feature flow: [features/push-notifications.md](./features/push-notifications.md)
- MIP-06, Multi-Device Support: Branch-draft and optional. The MIP-era External-Commit design and its join
  authorization component were withdrawn from this spec; the current experimental direction is the same-account
  enrollment baseline.
  - Feature flow: [features/multi-device.md](./features/multi-device.md)
  - App component: [app-components/same-account-membership-v1.md](./app-components/same-account-membership-v1.md)
  - Content synchronization exploration: [features/account-sync.md](./features/account-sync.md)
  - Commit authorization boundary: [protocol-core/group-messaging.md](./protocol-core/group-messaging.md)
  - Foundation: [foundation/identity.md](./foundation/identity.md)
  - Convergence: [protocol-core/convergence.md](./protocol-core/convergence.md)

## MIP-01 field split

MIP-01 used one monolithic MLS extension, `marmot_group_data`. This spec keeps the same semantics but splits that
state into smaller app components.

| MIP-era field               | Owner in this spec                  |
| --------------------------- | ----------------------------------- |
| `name`                      | `marmot.group.profile.v1`           |
| `description`               | `marmot.group.profile.v1`           |
| `admin_pubkeys`             | `marmot.group.admin-policy.v1`      |
| `nostr_group_id`            | `marmot.transport.nostr.routing.v1` |
| `relays`                    | `marmot.transport.nostr.routing.v1` |
| `image_hash`                | `marmot.group.blossom.image.v1`     |
| `image_key`                 | `marmot.group.blossom.image.v1`     |
| `image_nonce`               | `marmot.group.blossom.image.v1`     |
| `image_upload_key`          | `marmot.group.blossom.image.v1`     |
| `disappearing_message_secs` | `marmot.group.message-retention.v1` |

The component docs own the exact bytes. This table only records where the old fields went.

## Transport-specific MIP details

Nostr-specific MIP details stay in [transports/nostr.md](./transports/nostr.md). Examples include:

- kind `30443` KeyPackage publication to the account's kind `10002` NIP-65 relays;
- NIP-59 Welcome delivery with kind `444` rumors;
- kind `445` group message envelopes;
- the `h` tag and Nostr group routing id;
- NIP-40 `expiration` tags for message retention.

Protocol-core docs MAY refer to the active transport binding, but they SHOULD NOT duplicate these Nostr event shapes.
