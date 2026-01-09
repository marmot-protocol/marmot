# Marmot Protocol Data Flow and Architecture

This document provides comprehensive data flow diagrams and architectural overviews for the Marmot Protocol, illustrating how data moves between clients, groups, relays, and storage systems, with detailed cryptographic protections applied at each layer.

## Table of Contents

1. [Actor Definitions](#actor-definitions)
2. [Key Package Distribution Flow](#key-package-distribution-flow)
3. [Group Creation Flow](#group-creation-flow)
4. [Member Invitation Flow](#member-invitation-flow)
5. [Group Messaging Flow](#group-messaging-flow)
6. [Group Administration Flow](#group-administration-flow)
7. [Cryptographic Protection Layers](#cryptographic-protection-layers)

---

## Actor Definitions

### Clients
- **Identity**: Nostr keypair (secp256k1)
- **MLS Identity**: Credential containing Nostr pubkey
- **Capabilities**: Create groups, send/receive messages, send/receive files, publish KeyPackages, Welcomes, and other events
- **Local State**: MLS group state, message history, KeyPackages, local media storage

### Relays
- **Role**: Store and distribute Nostr events
- **Trust Model**: Untrusted for confidentiality, relied upon for availability
- **Capabilities**: Accept, store, query, and distribute events
- **Observable Data**: Event metadata (kind, timestamps, tags), encrypted content

### Blossom Servers
- **Role**: Content-addressed storage for encrypted media
- **Trust Model**: Untrusted - cannot decrypt stored content, relied upon for availability
- **Capabilities**: Store and retrieve blobs by SHA256 hash
- **Observable Data**: Encrypted blob hashes, access patterns

---

## Key Package Distribution Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R1 as Relay 1
    participant R2 as Relay 2
    participant R3 as Relay 3

    Note over C: Generate MLS Signing Key<br/>Create Credential<br/>Build KeyPackage

    C->>C: Create kind: 443 event<br/>Sign with Nostr key

    C->>R1: Publish KeyPackage (443)
    C->>R2: Publish KeyPackage (443)
    C->>R3: Publish KeyPackage (443)


    C->>C: Create kind: 10051 event<br/>List relay URLs

    C->>R1: Publish Relay List (10051)
    C->>R2: Publish Relay List (10051)
    C->>R3: Publish Relay List (10051)

    Note over C,R3: KeyPackages now discoverable<br/>on user's advertised relays

    rect rgb(100, 100, 100)
        Note over C: Later: KeyPackage consumed<br/>for group join
        C->>R1: DELETE KeyPackage (kind: 5)
        C->>R2: DELETE KeyPackage (kind: 5)
        C->>R3: DELETE KeyPackage (kind: 5)
    end
```

**Data Flow:**
1. Client generates MLS KeyPackage locally
2. KeyPackage published to multiple relays (redundancy)
3. Relay list published (helps others find KeyPackages)
4. After use, KeyPackage deleted (unless last_resort)

**Security Notes:**
- KeyPackage content is public (needed for invitations)
- Nostr signature prevents impersonation
- Credential links Nostr identity to MLS signing key
- Last resort KeyPackages can be reused (with quick rotation)

---

## Group Creation Flow

```mermaid
sequenceDiagram
    participant A as Admin Client
    participant MLS as MLS Library
    participant GS as Local Group State

    Note over A: User initiates<br/>group creation

    A->>MLS: Create new group<br/>with random 32-byte ID

    MLS->>MLS: Generate initial<br/>cryptographic state

    MLS->>MLS: Create ratchet tree<br/>with admin as founder

    A->>A: Build Marmot Group<br/>Data Extension

    Note over A: Extension fields:<br/>- version: 1<br/>- nostr_group_id (random 32 bytes)<br/>- name, description<br/>- admin_pubkeys (TLS array)<br/>- relays (TLS array)<br/>- image fields (optional)

    A->>MLS: Add extension to<br/>GroupContext

    MLS->>GS: Initialize epoch 0<br/>group state

    GS-->>A: Group ready<br/>for invitations

    Note over A,GS: Group created locally<br/>Not yet published anywhere
```

**Data Flow:**
1. Admin generates random MLS group ID (private, never published)
2. Generates random `nostr_group_id` for relay routing
3. Creates Marmot Group Data Extension with metadata
4. MLS library initializes group state (epoch 0)
5. Group state stored locally only

**Security Notes:**
- MLS group ID is private (cryptographic boundary)
- `nostr_group_id` is public-ish (observable by relays)
- Extension is cryptographically authenticated
- No data leaves client during creation
- Initial creation Commit is applied locally only (never sent to relays)
- This intentionally departs from MLS spec to preserve privacy—no coordination needed when creator is the only member

---

## Member Invitation Flow

```mermaid
sequenceDiagram
    participant A as Admin Client
    participant R as Relays
    participant M as Member Client
    participant MLS as MLS Library

    Note over M: Published KeyPackage<br/>available on relays

    A->>R: Query KeyPackages<br/>for target member
    R-->>A: KeyPackage event (443)

    A->>A: Verify credential matches<br/>Nostr pubkey in event

    A->>MLS: Create Add Proposal<br/>with KeyPackage

    A->>MLS: Create Commit<br/>(includes Add proposal)

    MLS->>MLS: Advance to epoch N+1<br/>Update ratchet tree

    A->>MLS: Create Welcome object<br/>for new member

    Note over A: Commit references<br/>group state at epoch N+1

    A->>R: Publish Commit (kind: 445)
    R-->>A: OK confirmation

    Note over A: WAIT for relay<br/>confirmation before<br/>sending Welcome

    A->>A: Gift-wrap Welcome<br/>using NIP-59

    A->>R: Send Welcome (kind: 1059)

    R->>M: Deliver Welcome<br/>(subscribed to p tag)

    M->>M: Unwrap NIP-59<br/>Decrypt to kind: 444

    M->>MLS: Process Welcome<br/>Join group

    MLS->>M: Group state at epoch N+1<br/>Ratchet tree, secrets

    M->>R: DELETE consumed<br/>KeyPackage

    R->>M: Subscribe to Group Events<br/>h tag = nostr_group_id

    Note over A,M: Member now in group<br/>at same epoch
```

**Data Flow:**
1. Admin fetches member's KeyPackage from relays
2. Admin creates MLS Add Proposal and Commit
3. **Critical**: Commit published and confirmed BEFORE Welcome sent
4. Welcome gift-wrapped and sent privately (NIP-59)
5. Member decrypts Welcome and joins group
6. Member deletes consumed KeyPackage

**Security Notes:**
- ✅ Credential validation prevents impersonation
- ✅ Commit/Welcome ordering prevents race conditions
- ✅ Gift-wrapping hides invitation from observers
- ✅ Welcome unsigned (cannot be republished)
- ⚠️ Relay can observe timing correlation

---

## Group Messaging Flow

### Application Message (Chat)

```mermaid
sequenceDiagram
    participant S as Sender Client
    participant MLS as MLS Library
    participant R as Relays
    participant Rec as Recipient Client

    Note over S: User types message

    S->>S: Create inner event<br/>kind: 9 (text)<br/>pubkey: sender's Nostr key<br/>NO SIGNATURE

    S->>MLS: Create ApplicationMessage<br/>with inner event

    MLS->>MLS: Encrypt with group<br/>symmetric keys

    S->>S: Extract exporter_secret<br/>for current epoch

    S->>S: Derive NIP-44 keys<br/>from exporter_secret

    S->>S: Encrypt MLSMessage<br/>with NIP-44

    S->>S: Generate fresh<br/>ephemeral keypair

    S->>S: Create kind: 445 event<br/>ephemeral pubkey<br/>encrypted content<br/>h tag: nostr_group_id

    S->>R: Publish Group Event (445)

    R->>Rec: Deliver to subscribers<br/>(subscribed to h tag)

    Rec->>Rec: Derive NIP-44 keys<br/>from own exporter_secret

    Rec->>Rec: Decrypt to MLSMessage

    Rec->>MLS: Process MLSMessage

    MLS->>MLS: Verify sender in group<br/>Decrypt with group keys

    MLS->>Rec: Inner Nostr event

    Rec->>Rec: Verify inner pubkey<br/>matches MLS sender

    Rec->>Rec: Display message

    Note over S,Rec: Message encrypted twice:<br/>MLS + NIP-44
```

**Data Flow:**
1. Sender creates unsigned inner event
2. MLS encrypts with group keys
3. NIP-44 encrypts MLS message (exporter_secret)
4. Published with ephemeral keypair
5. Recipients decrypt NIP-44 layer
6. MLS decrypts and authenticates inner content

**Security Notes:**
- ✅ Double encryption (MLS + NIP-44)
- ✅ Ephemeral key per message (sender privacy)
- ✅ MLS authentication (sender identity)
- ✅ Inner event unsigned (leak protection)
- ⚠️ Relay sees timing and size patterns

### Proposal Message

```mermaid
sequenceDiagram
    participant M as Member Client
    participant MLS as MLS Library
    participant R as Relays
    participant A as Admin Client

    Note over M: Member wants to<br/>propose a change

    M->>MLS: Create Proposal<br/>(Add/Remove/Update)

    MLS->>MLS: Sign with MLS<br/>signing key

    M->>M: Wrap in MLSMessage<br/>Encrypt (MLS + NIP-44)

    M->>M: Create kind: 445 event<br/>with ephemeral key

    M->>R: Publish Proposal (445)

    R->>A: Deliver to admin<br/>(subscribed to h tag)

    A->>A: Decrypt and process<br/>Proposal

    A->>MLS: Validate Proposal<br/>Check member signature

    Note over A: Admin decides whether<br/>to commit this proposal

    Note over A: See Commit flow<br/>for next steps
```

**Data Flow:**
1. Member creates MLS Proposal
2. Wrapped in encrypted Group Event
3. Published to relays
4. Admins receive and review
5. Admin may include in future Commit

**Security Notes:**
- ✅ MLS signature authenticates proposer
- ✅ Encrypted like application messages
- ⚠️ Any member can create proposals
- ✅ Only admins can commit proposals

### Commit Message

```mermaid
sequenceDiagram
    participant A as Admin Client
    participant MLS as MLS Library
    participant R as Relays
    participant M1 as Member 1
    participant M2 as Member 2

    Note over A: Admin decides to<br/>commit proposals

    A->>MLS: Create Commit<br/>(includes proposals)

    MLS->>MLS: Advance epoch N → N+1<br/>Update ratchet tree<br/>Generate new secrets

    Note over A: DO NOT apply locally yet

    A->>A: Wrap Commit in<br/>MLSMessage + NIP-44

    A->>A: Create kind: 445 event<br/>ephemeral key

    A->>R: Publish Commit (445)

    R-->>A: OK confirmation

    Note over A: NOW apply locally

    A->>MLS: Apply own Commit<br/>Update to epoch N+1

    R->>M1: Deliver Commit
    R->>M2: Deliver Commit

    M1->>M1: Verify sender in<br/>admin_pubkeys array

    M1->>MLS: Process Commit

    MLS->>MLS: Advance to epoch N+1<br/>Update state

    M2->>M2: Verify admin status
    M2->>MLS: Process Commit

    Note over A,M2: All members now<br/>at epoch N+1
```

**Data Flow:**
1. Admin creates MLS Commit
2. **Critical**: Published to relays BEFORE applying locally
3. Wait for relay confirmation
4. Then apply locally
5. Members verify admin status
6. Members process and advance epoch
7. Race conditions handled by timestamp/ID priority

**Exception - Initial Group Creation**: The very first Commit that creates a group MUST NOT be sent to relays. This initial Commit is applied locally only, establishing epoch 0. It exists purely on the creating admin's device until the first member invitation. This preserves privacy by not exposing group creation metadata to relays. The first Commit published to relays is the one adding the first member. This intentionally departs from MLS spec recommendations—since no other members exist yet, there's no risk of state divergence, and privacy benefits outweigh coordination guarantees.

**Security Notes:**
- ✅ Admin verification REQUIRED
- ✅ Epoch advancement provides PCS
- ✅ Timestamp ordering prevents forks
- ⚠️ Multiple admins need coordination
- ✅ Only authenticated admins can commit

---

## Group Administration Flow

### Update Group Metadata

```mermaid
sequenceDiagram
    participant A as Admin Client
    participant MLS as MLS Library
    participant R as Relays
    participant M as Members

    Note over A: Admin wants to update<br/>group name/relays/etc.

    A->>A: Create updated<br/>Marmot Group Data Extension

    Note over A: Updated fields:<br/>- name or description<br/>- relays list<br/>- nostr_group_id<br/>- admin_pubkeys

    A->>MLS: Create GroupContextExtensions<br/>Proposal

    A->>MLS: Create Commit<br/>(includes extension update)

    MLS->>MLS: Advance epoch<br/>New extension active

    A->>R: Publish Commit (445)

    A->>MLS: Apply locally

    R->>M: Deliver Commit

    M->>M: Verify admin status<br/>of sender

    M->>MLS: Process Commit

    MLS->>M: Updated extension<br/>in GroupContext

    Note over M: Update relay subscriptions<br/>if relays changed

    M->>R: Subscribe to new relays<br/>(if relay list updated)

    Note over A,M: All members now have<br/>updated metadata
```

**Data Flow:**
1. Admin creates updated extension
2. Wraps in Proposal and Commit
3. Publishes and waits for confirmation
4. Members verify admin and apply
5. Update relay subscriptions if needed

**Security Notes:**
- ✅ Extension changes cryptographically authenticated
- ✅ Admin verification REQUIRED
- ✅ TLS serialization ensures consistency
- ✅ Version field enables future upgrades
- ⚠️ Old `nostr_group_id` may leak correlation

### Add/Remove Members

```mermaid
sequenceDiagram
    participant A as Admin Client
    participant MLS as MLS Library
    participant R as Relays
    participant M as Existing Members
    participant N as New/Removed Member

    alt Add Member
        Note over A: See Member Invitation Flow<br/>for complete add sequence
        A->>MLS: Add Proposal + Commit
        A->>R: Publish Commit
        A->>N: Send Welcome (NIP-59)
    else Remove Member
        A->>MLS: Remove Proposal<br/>for target member
        A->>MLS: Create Commit
        MLS->>MLS: Advance epoch<br/>Removed member cannot<br/>decrypt new messages
        A->>R: Publish Commit (445)
        R->>M: Deliver to remaining members
        R->>N: Deliver to removed member
        N->>N: Process Commit<br/>Realize removed<br/>Delete group state
        M->>M: Process Commit<br/>Update member list
    end

    Note over A,N: Forward secrecy:<br/>Removed member cannot<br/>read future messages
```

**Data Flow:**
- **Add**: Proposal → Commit → Welcome (see detailed flow above)
- **Remove**: Proposal → Commit → Epoch advance → Keys invalidated

**Security Notes:**
- ✅ Epoch change invalidates removed member's keys
- ✅ Forward secrecy for future messages
- ⚠️ Removed member retains historical messages
- ⚠️ Removed member knows group metadata

### Signing Key Rotation

```mermaid
sequenceDiagram
    participant M as Member Client
    participant MLS as MLS Library
    participant R as Relays
    participant Others as Other Members

    Note over M: Weekly rotation<br/>or after compromise

    M->>MLS: Create Update Proposal<br/>with new signing key

    Note over M: Any member can<br/>propose own key update

    M->>R: Publish Proposal (445)

    R->>Others: Deliver Proposal<br/>to admins

    Note over Others: Admin includes in<br/>next Commit

    Others->>MLS: Create Commit<br/>(includes Update)

    MLS->>MLS: Advance epoch<br/>Member's new key active

    Others->>R: Publish Commit (445)

    R->>M: Deliver Commit

    M->>MLS: Process Commit

    Note over M,Others: Member now using<br/>new signing key<br/>Old key invalidated
```

**Data Flow:**
1. Member creates Update Proposal
2. Admin includes in Commit
3. Epoch advances
4. New signing key active

**Security Notes:**
- ✅ Regular rotation limits compromise impact
- ✅ RECOMMENDED: Weekly rotation
- ✅ CRITICAL: Rotate after last_resort KeyPackage use
- ✅ PCS achieved after epoch advance

---

## Cryptographic Protection Layers

### Protection Matrix by Event Kind

| Event Kind | TLS | Nostr Sig | Ephemeral Key | NIP-44 | MLS Encrypt | MLS Auth | Inner Unsigned |
|------------|-----|-----------|---------------|--------|-------------|----------|----------------|
| **443** (KeyPackage) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ Credential | N/A |
| **10051** (Relay List) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | N/A |
| **444** (Welcome) via NIP-59 | ✅ | ✅ Ephemeral | ✅ | ✅ | ❌ Content is MLS | ❌ | ✅ |
| **445** (Group Event) | ✅ | ✅ Ephemeral | ✅ | ✅ | ✅ | ✅ | ✅ |


