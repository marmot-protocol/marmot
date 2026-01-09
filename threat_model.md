# Marmot Threat Model and Security Considerations

## Abstract

This document provides a comprehensive threat model and security considerations for the Marmot protocol, which implements the Messaging Layer Security (MLS) protocol on top of the Nostr decentralized relay and identity network. This document identifies potential threats, attack vectors, and security considerations based on the Marmot Implementation Proposals (MIPs) and MLS protocol specifications. The goal is to communicate security assurances and limitations to help users understand what protections Marmot provides and what risks remain.

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [Scope](#11-scope)
   - 1.2 [Threat Model Assumptions](#12-threat-model-assumptions)
   - 1.3 [Security Properties](#13-security-properties)
   - 1.4 [Trust Model](#14-trust-model)
2. [Threat Model](#2-threat-model)
   - 2.1 [Network Observers](#21-network-observers)
   - 2.2 [Relay Operators](#22-relay-operators)
   - 2.3 [Group Members](#23-group-members)
   - 2.4 [Group Administrators](#24-group-administrators)
   - 2.5 [Compromised Clients](#25-compromised-clients)
   - 2.6 [Forward Secrecy and Post-Compromise Security](#26-forward-secrecy-and-post-compromise-security)
   - 2.7 [Key Package Security (MIP-00)](#27-key-package-security-mip-00)
   - 2.8 [Group Message Security (MIP-03)](#28-group-message-security-mip-03)
   - 2.9 [Encrypted Media Security (MIP-04)](#29-encrypted-media-security-mip-04)
   - 2.10 [Denial of Service Attacks](#210-denial-of-service-attacks)
   - 2.11 [Metadata Leakage](#211-metadata-leakage)
   - 2.12 [Cryptographic Attacks](#212-cryptographic-attacks)
   - 2.13 [Operational Security](#213-operational-security)
3. [Security Considerations](#3-security-considerations)
   - 3.0 [Critical Security Requirements](#30-critical-security-requirements)
   - 3.1 [Implementation Pitfalls](#31-implementation-pitfalls)
   - 3.2 [Implementation Requirements](#32-implementation-requirements)
   - 3.3 [Best Practices](#33-best-practices)
   - 3.4 [User Recommendations](#34-user-recommendations)
   - 3.5 [Testing Requirements](#35-testing-requirements)
   - 3.6 [Security Properties Summary](#36-security-properties-summary)
4. [References](#4-references)
5. [Acknowledgments](#5-acknowledgments)

## 1. Introduction

The Marmot protocol enables secure group messaging by combining MLS end-to-end encryption with Nostr's decentralized infrastructure. This document models threats from various perspectives including network observers, relay operators, group members, administrators, and compromised clients.

### 1.1 Scope

This threat model covers:
- Key package management and credential validation
- Group construction and state management
- Welcome event handling and group invitations
- Group message encryption and delivery
- Encrypted media sharing (MIP-04)
- Metadata leakage and correlation attacks
- Denial of service vectors
- Cryptographic implementation vulnerabilities

### 1.2 Threat Model Assumptions

This document assumes attackers may have:
- **Passive network observation**: Ability to monitor network traffic and relay communications
- **Active network manipulation**: Ability to inject, modify, or drop messages
- **Relay operator access**: Control over one or more Nostr relays
- **Group membership**: Access to group secrets and state as a member or admin
- **Client compromise**: Access to device storage, keys, and application state
- **Infrastructure compromise**: Control over storage providers or other infrastructure

### 1.3 Security Properties

#### What Marmot Provides

Marmot aims to provide:
- **Message confidentiality**: Protection against unauthorized reading of messages through MLS symmetric encryption
- **Message integrity**: Protection against unauthorized modification via cryptographic signatures
- **Authentication**: Verification of message origin and group membership through MLS credentials and Nostr identities
- **Forward secrecy**: Past messages remain secure after member removal and key deletion (See [MIP-00](00.md) Signing Key Rotation)
- **Post-compromise security**: Recovery from compromise through key updates and epoch transitions
- **Metadata privacy**: Minimization of observable information through ephemeral keypairs and double encryption (See [MIP-03](03.md))

#### What Marmot Does NOT Provide

Users should be aware of the following limitations:

- **Group existence hiding**: The `nostr_group_id` for a group is observable by relay operators and network observers
- **Traffic analysis protection**: Message timing, frequency, and size patterns can be correlated by relay operators
- **Malicious insider protection**: Group members and administrators can leak information, spam messages, or abuse privileges
- **Guaranteed message delivery**: Relays may censor, drop, or delay messages; no delivery guarantees exist
- **Perfect metadata privacy**: IP addresses, connection timing, and relay usage patterns may reveal information about users if clients don't take extra precautions to protect this data.
- **Protection against state-level adversaries**: Sophisticated attacks (traffic analysis, timing attacks, correlation attacks) may succeed
- **Defense against compromised clients**: Full device compromise exposes all keys and messages accessible to that device
- **Spam prevention**: Gift-wrapped events and application messages can be spammed, forcing decryption attempts

### 1.4 Trust Model

Understanding what entities users must trust is critical for evaluating Marmot's security guarantees.

#### Entities Users MUST Trust

1. **Their own devices**:
   - Device security is fundamental - compromised devices expose all keys and messages
   - Users must trust their device OS, hardware, and security features

2. **Group administrators**:
   - Admins control group membership, configuration, and can modify the Marmot Group Data Extension (See [MIP-01](01.md))
   - Malicious admins can add unauthorized members, remove legitimate members, or disrupt groups
   - Use multiple admins for checks and balances

3. **Group members**:
   - Members have access to all messages and can retain/leak historical content
   - Removed members keep all messages received while in the group
   - Members can disclose group metadata (`nostr_group_id`, relay lists, member lists)

4. **MLS implementation**:
   - Cryptographic correctness depends on the MLS library (e.g., OpenMLS)
   - Implementation bugs can compromise security

5. **Nostr identity security**:
   - Users must secure their Nostr private keys
   - Compromised Nostr keys enable identity theft across all Nostr applications

#### Entities Users Do NOT Need to Trust

1. **Nostr relay operators**:
   - Relays cannot decrypt message content (double encryption prevents this)
   - Relays cannot forge messages (cryptographic signatures prevent this)
   - Relays CAN observe metadata, IP addresses, and timing patterns

2. **Network observers**:
   - Passive observers cannot decrypt traffic (TLS + MLS + [NIP-44](https://github.com/nostr-protocol/nips/blob/master/44.md) encryption)
   - Active attackers cannot forge or modify messages without detection

3. **Storage providers** (for encrypted media, See [MIP-04](04.md)):
   - Content-addressed storage providers cannot decrypt media files
   - Storage addresses are hashes of encrypted content (effectively random)
   - Providers CAN observe access patterns and metadata

4. **Other Marmot users** (outside the group):
   - Non-members cannot decrypt group messages or join groups without invitation
   - Non-members cannot impersonate group members

#### Trust Boundaries

The primary trust boundaries in Marmot are:

1. **Group membership boundary**: The MLS group is the fundamental security perimeter. All members have access to group content.

2. **Device boundary**: Each device has its own keys and must be explicitly added to groups. Device compromise affects only that device.

3. **Admin privilege boundary**: Only users listed in the `admin_pubkeys` array can commit structural group state changes (membership, settings, extension updates). Non-admin members may only create self-update Commits to rotate their own key material (See [MIP-01](01.md) and [MIP-03](03.md)).

4. **Epoch boundary**: MLS epochs provide forward secrecy and post-compromise security boundaries. Key material rotates with epoch transitions.

5. **Relay trust boundary**: Relays are untrusted for confidentiality but relied upon for message delivery (with redundancy via multiple relays).

## 2. Threat Model

### 2.1 Network Observers

Network observers include entities that can capture packets between clients and relays, as well as observers that can query Marmot-specific event kinds from relays.

#### 2.1.1 Passive Network Observation

**Threat**: Attackers monitoring network traffic can observe TLS-encrypted packets and Nostr event metadata.

**Attack Scenarios**:
- Observing event kinds (443, 444, 445, 10051) published to relays
- Monitoring event sizes and timing patterns
- Tracking `nostr_group_id` values in kind: 445 event `h` tags
- Correlating activity patterns across multiple relays

**Observable Information**:
- **Key Package events (kind: 443)**: Public signing keys, MLS credentials containing Nostr public keys, supported ciphersuites, and capabilities. This data is intentionally public and unencrypted.
- **Key Package list events (kind: 10051)**: Relay URLs where users publish KeyPackages. This data is intentionally public.
- **Welcome events (kind: 444)**: Gift-wrapped using [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md), appearing as kind: 1059 events. Observers cannot determine the payload is a Welcome message without the recipient's Nostr private key.
- **Application Message events (kind: 445)**: Double-encrypted content (MLS symmetric encryption + [NIP-44](https://github.com/nostr-protocol/nips/blob/master/44.md)-derived encryption). Observers see encrypted content and ephemeral public keys but cannot decrypt without group secrets.

**Countermeasures**:
- Use TLS for all WebSocket connections to relays
- Gift-wrapping Welcome events ([NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md)) prevents identification of Welcome messages
- Ephemeral keypairs for kind: 445 events prevent sender correlation
- Double encryption provides defense in depth

#### 2.1.2 Malicious Nostr Users

**Threat**: Malicious users actively disrupt the system by publishing invalid or malicious events.

**Attack Scenarios**:

#### T.1.1 - Invalid Key Package Publication

- **Description**: Attackers publish many invalid KeyPackage events that clients must download and validate.
- **Impact**: Resource exhaustion on clients attempting to process invalid KeyPackages.
- **Countermeasures**:
  - Client-side validation and caching
  - Relay filtering based on reputation
  - In practice, KeyPackage use is client-initiated, limiting exposure

#### T.1.2 - Key Package Credential Mismatch

- **Description**: Attackers attempt to publish KeyPackages with mismatched credentials (Nostr pubkey in MLS credential doesn't match kind: 443 event pubkey).
- **Prerequisites**: Attacker can publish events to relays.
- **Impact**: Critical authentication bypass if clients don't validate credential matching. Attacker could impersonate other users in groups.
- **Affected Components**: [MIP-00](00.md) (KeyPackage Events), MLS Credentials
- **Countermeasures**:
  - **CRITICAL**: Clients MUST validate that the Nostr public key in the MLS BasicCredential identity field matches the kind: 443 event's pubkey field (See [MIP-00](00.md) Identity Requirements)
  - Cryptographic signatures prevent forgery on behalf of other users
  - Event ID tamper-proofing ([NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md)) prevents content modification after publishing
- **Residual Risk**: None if validation is properly implemented. This is a preventable vulnerability.

#### T.1.3 - Gift-Wrapped Event Spam (NIP-59)

- **Description**: Attackers publish large numbers of encrypted [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) kind: 1059 events addressed to users, forcing decryption attempts.
- **Impact**: Resource exhaustion as users decrypt many events only to find invalid payloads. Affects Welcome messages (kind: 444).
- **Countermeasures**:
  - Relay-level spam protection ([NIP-13](https://github.com/nostr-protocol/nips/blob/master/13.md) proof-of-work, [NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md) authentication)
  - Client-side rate limiting
  - Note: Proof-of-work is asymmetric (mobile clients vs. server attackers) and not highly effective
  - This is a fundamental limitation of [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) beyond Marmot's scope

#### T.1.4 - Application Message Spam

- **Description**: Attackers publish kind: 445 events with valid-looking `h` tags for known groups but invalid ciphertexts.
- **Impact**: Clients must download and attempt decryption before detecting invalidity, wasting resources.
- **Countermeasures**:
  - Client-side filtering based on event signatures
  - Use multiple `nostr_group_id` values per group to distribute attack surface
  - Rotate group IDs periodically to limit exposure

### 2.2 Relay Operators

Relay operators have similar capabilities to network observers but with additional access to client IP addresses and connection metadata.

#### 2.2.1 IP Address Correlation

**Threat**: Relay operators can observe client IP addresses and correlate them with group activity.

**Attack Scenarios**:

#### T.2.1 - Group Membership Inference

- **Description**: Relay operators correlate IP addresses that publish/subscribe to the same `nostr_group_id` values.
- **Impact**: Potential inference of group membership based on IP address overlap.
- **Countermeasures**:
  - Use Tor, i2p, or VPNs to hide IP addresses
  - Use multiple relays per group and distribute events across relays
  - Rotate `nostr_group_id` values periodically
  - Use different relays for different groups

#### T.2.2 - Timing Correlation

- **Description**: Relay operators correlate event publication timing with subscription patterns.
- **Impact**: Potential inference of message authorship or group activity patterns.
- **Countermeasures**:
  - Add random delays before publishing events
  - Use cover traffic to obscure activity patterns
  - Distribute events across multiple relays with varying timing

#### T.2.3 - Relay Censorship

- **Description**: Malicious relay operators drop or censor Marmot events, either broadly or selectively targeting specific users or groups.
- **Impact**: Message delivery failures, group state desynchronization. Selective censorship is particularly dangerous as it may appear as intermittent network issues.
- **Countermeasures**:
  - Use multiple relays per group (redundancy)
  - Implement relay failover in clients
  - Monitor relay reliability and switch when necessary
  - Clients SHOULD monitor message delivery rates per relay and automatically remove consistently failing relays
  - Compare delivery success across relays to detect selective censorship

### 2.3 Group Members

Group members have access to all group state, including cryptographic secrets and metadata.

#### 2.3.1 Malicious Group Members

**Threat**: Malicious members can disrupt groups, leak metadata, or abuse group resources.

**Attack Scenarios**:

#### T.3.1 - Message Spam

- **Description**: Malicious members send large volumes of valid encrypted messages.
- **Impact**: Resource exhaustion, degraded user experience.
- **Countermeasures**:
  - Admins can remove malicious members via MLS Remove operations
  - Client-side rate limiting and message filtering
  - No cryptographic prevention without member removal

#### T.3.2 - Metadata Exposure

- **Description**: Members share group metadata (`nostr_group_id`, relay list, admin list) with non-members.
- **Impact**: Information leakage about group structure and configuration.
- **Countermeasures**:
  - Group metadata is designed to be non-sensitive (public identifiers)
  - Trust model assumes members won't leak metadata
  - Rotate `nostr_group_id` if compromise suspected

#### T.3.3 - Group State Disclosure

- **Description**: Members share ratchet tree structure and public keys with non-members.
- **Impact**: Correlation of group membership with public Nostr identities.
- **Countermeasures**:
  - Ratchet tree structure is group-internal but not highly sensitive
  - Public keys are already public on Nostr network
  - Ephemeral keypairs for messages prevent sender correlation

#### T.3.4 - Historical Message Retention

- **Description**: Removed members retain copies of all messages received while in the group.
- **Impact**: Forward secrecy does not apply to historical messages for removed members.
- **Countermeasures**:
  - MLS forward secrecy ensures removed members cannot read future messages
  - For sensitive conversations, rotate group membership periodically
  - Remove members who no longer need access promptly

#### T.3.5 - Fake Proposals

- **Description**: Members create proposals that waste bandwidth and processing time.
- **Impact**: Resource exhaustion, though proposals require admin commitment to take effect.
- **Countermeasures**:
  - Admins can ignore or reject malicious proposals
  - Client-side proposal validation and filtering
  - Remove members who abuse proposal system

### 2.4 Group Administrators

Group admins have all member capabilities plus additional privileges to modify group state.

#### 2.4.1 Admin Privilege Abuse

**Threat**: Malicious admins can manipulate groups, members, and metadata.

**Attack Scenarios**:

#### T.4.1 - Unauthorized Member Addition

- **Description**: Admins add unauthorized users to private groups.
- **Impact**: Privacy breach, potential information leakage.
- **Countermeasures**:
  - Use multiple admins for checks and balances
  - Client-side admin action logging and notifications
  - Users should carefully vet admin privileges
  - Members can leave and create new groups without malicious admin

#### T.4.2 - Legitimate Member Removal

- **Description**: Admins remove legitimate members from groups.
- **Impact**: Denial of service, group disruption.
- **Countermeasures**:
  - Multiple admins can restore removed members
  - Admin action logging provides audit trail
  - Removed members can be re-invited by other admins

#### T.4.3 - Device Addition for Persistence

- **Description**: Admins add their own additional devices to maintain access even if primary device is removed.
- **Impact**: Persistent access despite device removal attempts.
- **Countermeasures**:
  - Other admins can remove additional devices
  - Monitor admin device additions
  - Rotate admin privileges if compromise suspected

#### T.4.4 - Marmot Group Data Extension Manipulation

- **Description**: Admins modify extension fields to disrupt group operations.
  - Change `nostr_group_id` to cause message routing issues
  - Modify relay list to exclude relays or add malicious relays
  - Change admin list to remove other admins or add unauthorized admins
  - Update group name/description to misleading content
  - Update group image to inappropriate content
- **Impact**: Group disruption, message delivery failures, privilege escalation.
- **Countermeasures**:
  - Client-side validation of extension changes
  - Admin action notifications to all members
  - Multiple admins can reverse malicious changes
  - Version detection prevents unknown format attacks

#### T.4.5 - Group Destruction

- **Description**: Admins remove all members or modify group state to be unusable.
- **Impact**: Complete group destruction, data loss.
- **Countermeasures**:
  - Multiple admins prevent single point of failure
  - Members can leave and create new groups
  - Client-side state validation prevents processing invalid states

#### T.4.6 - Commit Race Conditions

- **Description**: Multiple admins send competing Commits simultaneously, causing group state forks.
- **Impact**: Group state desynchronization, message delivery failures.
- **Countermeasures**:
  - Clients MUST apply Commits using timestamp priority (earliest first)
  - ID tiebreaker for identical timestamps (lexicographically smallest)
  - Clients SHOULD retain previous group states temporarily for recovery
  - Admin coordination reduces race conditions

#### T.4.7 - Rapid State Changes

- **Description**: Admins commit updates at high frequency to overwhelm clients.
- **Impact**: Resource exhaustion, client crashes.
- **Countermeasures**:
  - Client-side rate limiting
  - Admin removal if behavior detected
  - Client warnings for rapid admin actions

#### T.4.8 - Malformed Proposal Commits

- **Description**: Admins commit malformed proposals causing client errors.
- **Impact**: Client crashes, group state corruption.
- **Countermeasures**:
  - Client-side proposal validation before processing
  - Error handling and recovery mechanisms
  - Admin removal for repeated violations

**Important Note**: Admins are an application-layer concept enforced by the Marmot Group Data Extension and client validation. Unlike MLS protocol-level roles, admin privileges are defined in authenticated group state and MUST be verified by all clients before processing admin actions.

### 2.5 Compromised Clients

A compromised client device represents a severe threat with access to all stored secrets.

#### 2.5.1 Device Compromise

**Threat**: Attackers gain access to device storage, keys, and application state through malware, physical access, or other means.

**Attack Scenarios**:

#### T.5.1 - Key Material Exposure

- **Description**: Attackers access all MLS private keys, Nostr private keys, and derived secrets stored on device.
- **Impact**: Complete compromise of user's cryptographic identity and group access.
- **Countermeasures**:
  - Strong device encryption (FileVault, BitLocker)
  - Device PIN/biometric authentication
  - Secure enclaves or hardware security modules (HSM)
  - Key rotation and re-authentication mechanisms

#### T.5.2 - Message Decryption

- **Description**: Attackers decrypt all messages sent to groups the compromised device is a member of.
- **Impact**: Complete loss of message confidentiality for affected groups.
- **Countermeasures**:
  - Remove compromised devices from all groups immediately
  - MLS post-compromise security: after removal and key updates, attacker cannot decrypt new messages
  - Forward secrecy: past messages remain secure if device was removed previously

#### T.5.3 - Message Forgery

- **Description**: Attackers send messages as the compromised user to any groups they're a member of.
- **Impact**: Impersonation, false information dissemination.
- **Countermeasures**:
  - Remove compromised device immediately upon detection
  - MLS authentication prevents forgery after device removal
  - Group members can detect anomalous behavior

#### T.5.4 - Identity Theft

- **Description**: Attackers use the user's Nostr private key to impersonate them across the Nostr network.
- **Impact**: Complete identity compromise beyond Marmot groups.
- **Countermeasures**:
  - Use separate Nostr keys for different purposes if possible
  - Rotate Nostr keys if compromise suspected (affects all Nostr usage)
  - Device security prevents initial compromise

#### T.5.5 - Device Addition

- **Description**: Attackers add additional devices to groups on behalf of the user.
- **Impact**: Persistent access even if primary device is removed.
- **Countermeasures**:
  - Monitor device additions in groups
  - Remove unauthorized devices immediately
  - Use device management features to track authorized devices

#### T.5.6 - Historical Message Access

- **Description**: Attackers access historical messages stored on device (depending on retention policy).
- **Impact**: Exposure of past conversations.
- **Countermeasures**:
  - Limit message retention on devices
  - Encrypt message storage
  - Delete messages when no longer needed
  - Forward secrecy limits exposure if device was removed previously

#### T.5.7 - Nostr Key Compromise Cross-Application Impact

- **Description**: Unlike device-specific MLS keys, Nostr private keys control identity across ALL Nostr applications (social media, payments, lightning addresses, etc.), not just Marmot groups.
- **Impact**: Compromise extends far beyond Marmot - attacker can impersonate user across entire Nostr ecosystem, post on behalf of user, access DMs, potentially access funds, and more. Key rotation on Nostr is more complex than MLS key rotation and affects all applications.
- **Countermeasures**:
  - Consider using dedicated Nostr identities specifically for Marmot if high security is required
  - Use separate keys for financial vs. social applications when possible
  - Document this risk clearly in user-facing materials
  - Understand that Nostr key compromise has ecosystem-wide implications
  - Hardware security modules (HSM) or secure enclaves strongly recommended for Nostr keys

#### T.5.8 - Partial Device Compromise (Memory-only)

- **Description**: Attacker gains temporary access to device memory (cold boot attack, memory dump, process inspection) without persistent access to storage.
- **Impact**: Can extract keys currently in memory but not persistent storage. Shorter exposure window than full device compromise.
- **Countermeasures**:
  - Use memory protection features (iOS Data Protection, Android KeyStore, secure enclaves)
  - Clear sensitive data from memory when not in use
  - Use secure enclaves when available to minimize key exposure in application memory
  - Short-lived key caching reduces exposure window
  - Lock devices when not in use to prevent physical memory access

### 2.6 Forward Secrecy and Post-Compromise Security

MLS provides specific security guarantees related to key compromise, but with important limitations.

#### 2.6.1 Forward Secrecy Limitations

**Threat**: Compromise of current keys might expose past messages.

**Attack Scenarios**:

#### T.6.1 - Forward Secrecy Window

- **Description**: Forward secrecy only applies after a member is removed from the group and their local state is deleted. A compromised member can retain all messages they received while in the group.
- **Impact**: Historical messages remain accessible to compromised members.
- **Countermeasures**:
  - Members who leave groups voluntarily should delete local group state
  - For sensitive conversations, rotate group membership periodically
  - Remove members who no longer need access promptly
  - Note: Forward secrecy for encrypted media ([MIP-04](04.md)) follows MLS epoch changes, meaning historical media becomes inaccessible after epoch transitions

#### T.6.2 - Group Image Forward Secrecy

- **Description**: Group images ([MIP-01](01.md)) persist across MLS epochs, unlike chat media which rotates with epochs. This is by design to ensure consistency across epochs.
- **Impact**: Historical group images remain accessible to removed members who had access when images were set.
- **Countermeasures**:
  - Group images are encrypted but keys persist in extension for consistency
  - Update group images when members are removed if needed
  - Understand that group images have different forward secrecy properties than messages
  - This trade-off enables reliable group image display without re-fetching

#### 2.6.2 Post-Compromise Security

**Threat**: After compromise, future messages might remain vulnerable.

**Attack Scenarios**:

#### T.6.3 - PCS Recovery Window

- **Description**: Post-Compromise Security (PCS) requires not just removing the compromised member, but also that remaining members process the Commit and update to the new epoch. Each member achieves PCS independently as soon as they apply the Commit. Offline members create a recovery window where they remain vulnerable.
- **Prerequisites**: Compromised member has been removed via admin Commit, but some members haven't processed it yet.
- **Impact**: Compromised keys remain useful for attacking members who haven't processed the Commit yet. Attacker can decrypt messages sent by offline members during the window.
- **Affected Components**: MLS epoch transitions, [MIP-03](03.md) (Commit Messages)
- **Countermeasures**:
  - Remove compromised members immediately upon detection through admin Commit (See [MIP-03](03.md) Commit Messages)
  - **Recovery timing**: Each member achieves PCS as soon as they apply the Commit that advances the epoch - this happens immediately upon processing, not at a future time
  - **Note**: PCS is achieved per-member, not per-group. Member Alice achieves PCS immediately upon processing the Commit, even if Member Bob is still offline. However, messages from Bob during his offline period remain vulnerable since Bob is still using compromised epoch secrets.
  - Offline members catch up when they reconnect and process pending Commits
  - Client implementations SHOULD prioritize processing Commits upon reconnection
  - For critical situations, wait for majority of members to confirm epoch update before resuming sensitive communications
- **Residual Risk**: Offline members remain vulnerable until they process the Commit. No way to force immediate synchronization in asynchronous system.

#### T.6.4 - Key Update Requirements

- **Description**: PCS requires key material updates through MLS Commits that advance the epoch. Each Commit that modifies group membership or updates keys generates fresh cryptographic secrets. Groups without regular updates have delayed PCS recovery because they remain in the same epoch longer.
- **Prerequisites**: Group rarely updates keys or modifies membership.
- **Impact**: Longer epochs mean extended windows between PCS opportunities. Compromised keys remain useful for longer periods.
- **Affected Components**: [MIP-00](00.md) (Signing Key Rotation), MLS epoch management
- **Countermeasures**:
  - **RECOMMENDED**: Rotate signing keys weekly in all active groups (See [MIP-00](00.md) Signing Key Rotation)
  - Any admin Commit advances the epoch, providing PCS - member additions, removals, or updates all trigger epoch transitions
  - Prompt processing of Commits that remove compromised members takes priority
  - Client UI SHOULD make key rotation easy and visible to encourage regular updates
  - Consider implementing automatic periodic key rotation for high-security groups
- **Residual Risk**: PCS window depends on update frequency. Weekly rotation provides reasonable balance between security and usability.

#### 2.6.3 Key Rotation Comparison

Different types of keys in Marmot have different rotation characteristics:

| Key Type | Rotation Mechanism | Rotation Frequency | Impact Scope |
|----------|-------------------|-------------------|--------------|
| **MLS Signing Keys** | Update proposals ([MIP-00](00.md)) | Recommended: Weekly | Single group |
| **MLS Encryption Keys** | Automatic with epoch transitions | Every Commit | Single group |
| **Nostr Private Keys** | Manual key migration | Rare/Never | All Nostr applications |
| **Ephemeral Keypairs** | Fresh generation per message | Every message | Single message |

**Important Notes**:
- **MLS Signing Keys**: Rotated via Update proposals within each group independently. Weekly rotation recommended for security.
- **MLS Encryption Keys**: Automatically rotated with every epoch transition (any Commit that modifies membership or updates keys).
- **Nostr Keys**: Identity keys that control user identity across ALL Nostr applications. Rotation affects entire Nostr ecosystem and should be done carefully.
- **Ephemeral Keypairs**: Used for kind: 445 event encryption. Must be unique per message to maintain privacy guarantees.

### 2.7 Key Package Security ([MIP-00](00.md))

Key packages enable asynchronous group invitations and have specific security considerations.

#### 2.7.1 Key Package Threats

**Attack Scenarios**:

#### T.7.1 - Last Resort KeyPackage Reuse

- **Description**: Last resort KeyPackages can be reused, creating a window where a compromised KeyPackage could be used multiple times for group invitations.
- **Prerequisites**: KeyPackage marked with last_resort extension is used multiple times.
- **Impact**: Persistent attack vector if KeyPackage is compromised. Multiple groups could be affected by single key compromise.
- **Affected Components**: [MIP-00](00.md) (KeyPackage Consumption and Reuse)
- **Countermeasures**:
  - **CRITICAL**: Clients MUST rotate signing keys within one week after using last resort KeyPackages (See [MIP-00](00.md) Signing Key Rotation)
  - Best practice: Rotate signing keys within 24-48 hours of last resort KeyPackage use
  - Last resort packages SHOULD NOT be deleted immediately (they're meant to be reused), but SHOULD be deleted after fresh packages are published
  - Retain private keys for all groups to enable rotation
  - Monitor for unexpected or excessive KeyPackage usage
  - Publish fresh KeyPackages regularly to avoid last resort usage
- **Residual Risk**: Window of vulnerability exists between KeyPackage use and key rotation. Minimize by rotating quickly.

#### T.7.2 - Long-Lived Signing Keys

- **Description**: Signing keys that aren't rotated regularly increase compromise impact and extend the window for post-compromise attacks.
- **Prerequisites**: User doesn't rotate signing keys for extended periods.
- **Impact**: Extended exposure window if keys are compromised. Compromised keys remain useful for longer periods.
- **Affected Components**: [MIP-00](00.md) (Signing Key Rotation), MLS Update Proposals
- **Countermeasures**:
  - **RECOMMENDED**: Rotate signing keys weekly in all active groups (See [MIP-00](00.md) Signing Key Rotation)
  - Client implementations SHOULD prompt for rotation and make it user-friendly
  - Rotate keys immediately after suspected compromise
  - Consider automatic rotation for high-security use cases
- **Residual Risk**: Some exposure window exists even with regular rotation. Weekly rotation balances security and usability.

#### T.7.3 - KeyPackage Deletion Failures

- **Description**: KeyPackages might not be properly deleted from relays, leaving stale invitation vectors. Deletion timing differs for last resort vs. non-last-resort packages.
- **Impact**: Old KeyPackages could be used if not properly deleted.
- **Countermeasures**:
  - Clients SHOULD delete non-last-resort KeyPackages after successful group join
  - Last resort KeyPackages SHOULD be deleted after fresh packages are published, not immediately after use
  - Do NOT delete if Welcome processing fails (to allow retry)
  - Monitor relay deletion confirmations

#### T.7.4 - Welcome Event Timing Race Conditions

- **Description**: Welcome events sent before Commits are confirmed could reference stale group state.
- **Impact**: New members might join with incorrect group state.
- **Countermeasures**:
  - **CRITICAL**: Clients MUST wait for relay confirmation of Commit before sending Welcome ([MIP-02](02.md))
  - Ensure group state change is committed before inviting
  - Validate Welcome against current group state

#### T.7.5 - Large Group Welcome Limitations

- **Description**: Welcome events for large groups may exceed Nostr relay message size limits (commonly 64KB-128KB). The actual threshold depends on ratchet tree structure, ciphersuite overhead, and extension data. ~150 participants is a conservative estimate.
- **Prerequisites**: Group size grows beyond relay message size limits.
- **Impact**: Denial of service for large groups, inability to add new members through standard Welcome mechanism.
- **Affected Components**: [MIP-02](02.md) (Welcome Events), MLS Welcome objects
- **Countermeasures**:
  - Clients SHOULD actively monitor Welcome message sizes during testing and development
  - Clients MAY implement warning thresholds (e.g., warn admins when group reaches 100 members)
  - ~150 participants is a conservative threshold - actual limits vary by relay and group configuration
  - MLS protocol work underway on "light" client Welcome objects that don't require full ratchet tree (See [MIP-02](02.md) Large Groups)
  - Consider implementing group size limits or splitting large groups until light Welcome support is available
  - Test with target relays to determine actual size limits
- **Residual Risk**: Large groups fundamentally limited until light Welcome objects are standardized and implemented.

### 2.8 Group Message Security ([MIP-03](03.md))

Group messages use double encryption and ephemeral keypairs for privacy.

#### 2.8.1 Message Encryption Threats

**Attack Scenarios**:

#### T.8.1 - Ephemeral Keypair Reuse

- **Description**: Clients might accidentally reuse ephemeral keypairs for kind: 445 events.
- **Impact**: Breaks privacy guarantees, enables sender correlation.
- **Countermeasures**:
  - **CRITICAL**: Never reuse ephemeral keypairs ([MIP-03](03.md) requirement)
  - Generate fresh keypair for each Group Event
  - Client implementations must enforce this

#### T.8.2 - Inner Event Signature Leakage

- **Description**: Inner events (Nostr events inside MLS ApplicationMessages) that are signed with user's Nostr key could be published to public relays if leaked from compromised clients or through implementation bugs.
- **Prerequisites**: Inner events contain valid signatures and could be extracted from encrypted envelopes.
- **Impact**: Leaked events could be published to public relays, exposing group content to anyone. Most relays accept any validly-signed event, making published leaks irreversible.
- **Affected Components**: [MIP-03](03.md) (Application Messages, Security Requirements)
- **Countermeasures**:
  - **CRITICAL**: Inner events MUST remain unsigned - omit the `sig` field entirely (See [MIP-03](03.md) Security Requirements)
  - Do NOT include `h` tags or other group identifiers in inner events
  - Without signatures, relays will reject leaked events as invalid, preventing publication
  - Clients MUST verify inner event pubkey matches MLS sender identity for authentication
- **Residual Risk**: Minimal if properly implemented. Unsigned events cannot be published to standard Nostr relays.

#### T.8.3 - Exporter Secret Compromise

- **Description**: Compromise of `exporter_secret` for current epoch allows decryption of kind: 445 content field.
- **Impact**: Partial decryption (still requires MLS symmetric keys for full decryption).
- **Countermeasures**:
  - Double encryption provides defense in depth
  - Epoch rotation limits exposure window
  - Remove compromised members immediately

#### T.8.4 - Message Replay Attacks

- **Description**: Malicious relay or network attacker replays old kind: 445 messages.
- **Impact**: Clients might process messages multiple times, causing UI confusion or logic errors.
- **Countermeasures**:
  - Clients SHOULD track processed message IDs (Nostr event IDs are unique)
  - MLS provides epoch-based replay protection
  - Client-side deduplication prevents duplicate processing
  - Event ID uniqueness ensures same message cannot be replayed with same ID

### 2.9 Encrypted Media Security ([MIP-04](04.md))

Encrypted media sharing has specific security considerations beyond message encryption.

#### 2.9.1 Media Storage Threats

**Attack Scenarios**:

#### T.9.1 - Storage Provider Compromise

- **Description**: Encrypted media blobs stored on Blossom or other content-addressed storage could be accessed if provider is compromised.
- **Impact**: While content remains encrypted, access patterns and metadata could be observed.
- **Countermeasures**:
  - Content-addressed storage (hash-based) prevents correlation - addresses are hashes of encrypted content (essentially random)
  - Encryption keys derived from MLS exporter secrets
  - Only current group members can decrypt
  - Storage providers cannot determine content without decryption keys

#### T.9.2 - File Integrity Attacks

- **Description**: Attackers modify encrypted blobs or `imeta` tags to cause decryption failures or serve malicious content.
- **Impact**: Denial of service, potential malicious content if decryption succeeds with wrong keys.
- **Countermeasures**:
  - **CRITICAL**: Clients MUST verify SHA256 hash matches `x` field after decryption
  - AEAD associated data binding prevents metadata tampering
  - MIME type validation prevents content-type spoofing

#### T.9.3 - Version Compatibility Attacks

- **Description**: Clients encounter unknown encryption versions, potentially causing denial of service.
- **Impact**: Inability to decrypt media, client crashes.
- **Countermeasures**:
  - Version detection before decryption attempts
  - Graceful handling of unknown versions with clear error messages
  - Version negotiation during group creation

#### T.9.4 - MIME Type Spoofing

- **Description**: Attackers modify MIME types in `imeta` tags to cause clients to mishandle files.
- **Impact**: Security vulnerabilities if clients trust MIME types without validation.
- **Countermeasures**:
  - Validate MIME type consistency between `imeta` and actual content
  - MIME type canonicalization prevents format variations
  - Content-type validation after decryption

#### T.9.5 - Key Derivation Attacks

- **Description**: Same file encrypted with different filenames must produce unique keys/nonces.
- **Impact**: Nonce reuse could compromise ChaCha20-Poly1305 security.
- **Countermeasures**:
  - Filename inclusion in key/nonce derivation ensures uniqueness ([MIP-04](04.md))
  - This is a security property, not a vulnerability
  - Prevents dangerous nonce reuse scenarios

#### T.9.6 - Forward Secrecy for Media

- **Description**: Historical media becomes inaccessible after MLS epoch changes, not just member removal.
- **Impact**: Media forward secrecy differs from message forward secrecy.
- **Countermeasures**:
  - Understand that media forward secrecy follows epoch transitions
  - Download and store media locally if long-term access needed
  - Epoch changes invalidate media decryption keys

### 2.10 Denial of Service Attacks

Various DoS vectors exist that can degrade service quality or exhaust resources.

#### 2.10.1 Spam Attacks

**Attack Scenarios**:

#### T.10.1 - Gift-Wrapped Event Spam

- **Description**: Large volumes of encrypted [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) events force decryption attempts.
- **Impact**: Resource exhaustion, degraded performance.
- **Countermeasures**:
  - Relay-level spam protection ([NIP-13](https://github.com/nostr-protocol/nips/blob/master/13.md) proof-of-work, [NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md) authentication)
  - Client-side rate limiting
  - Note: This is a fundamental limitation of [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) beyond Marmot's scope (See also T.1.3)

#### T.10.2 - Application Message Spam

- **Description**: Invalid kind: 445 events with valid-looking `h` tags for known groups but invalid ciphertexts.
- **Impact**: Decryption attempts waste resources.
- **Countermeasures**:
  - Client-side filtering based on event signatures
  - Use multiple `nostr_group_id` values per group to distribute attack surface
  - Rotate group IDs monthly to limit targeting (See also T.1.4)

#### T.10.3 - Invalid Key Package Spam

- **Description**: Many invalid KeyPackage events published to relays that clients must download and validate.
- **Impact**: Client validation overhead, resource exhaustion on clients attempting to process invalid KeyPackages.
- **Countermeasures**:
  - Client-side validation and caching to avoid reprocessing
  - Relay filtering based on reputation
  - In practice, KeyPackage use is client-initiated, limiting exposure (See also T.1.1)

#### 2.10.2 Resource Exhaustion

**Attack Scenarios**:

#### T.10.4 - Large Group Resource Exhaustion

- **Description**: Extremely large groups exhaust client resources.
- **Impact**:
  - Large ratchet tree sizes (memory and computation)
  - High message volume
- **Countermeasures**:
  - Implement client-side group size limits
  - Optimize ratchet tree operations
  - Use efficient data structures
  - Monitor resource usage

#### T.10.5 - Rapid State Changes

- **Description**: Malicious admins commit updates at high frequency to overwhelm clients.
- **Impact**: Client overwhelm, resource exhaustion, potential crashes.
- **Countermeasures**:
  - Client-side rate limiting for Commit processing
  - Remove malicious admin if behavior detected
  - Client warnings for rapid admin actions (See also T.4.7)

#### 2.10.3 Network-Level DoS

**Attack Scenarios**:

#### T.10.6 - Relay Flooding

- **Description**: Attackers flood relays with Marmot events.
- **Impact**: Degraded service quality, relay unavailability.
- **Countermeasures**:
  - Relay-level rate limiting
  - Authentication requirements ([NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md))
  - Proof-of-work ([NIP-13](https://github.com/nostr-protocol/nips/blob/master/13.md))
  - Use multiple relays for redundancy

#### T.10.7 - Targeted Relay Attacks

- **Description**: DDoS specific relays that groups depend on.
- **Impact**: Message delivery failures for affected groups.
- **Countermeasures**:
  - Use multiple relays per group
  - Implement relay failover in clients
  - Monitor relay availability
  - Distribute events across relays

### 2.11 Metadata Leakage

Despite strong encryption, metadata can leak information about users and groups.

#### 2.11.1 Publicly Observable Metadata

**Attack Scenarios**:

#### T.11.1 - Key Package Metadata Leakage

- **Description**: Key Package events reveal Marmot usage, public keys, ciphersuites, capabilities.
- **Impact**: Identification of Marmot users, capability fingerprinting.
- **Countermeasures**:
  - This data is intentionally public (needed for group invitations)
  - Consider privacy implications when publishing KeyPackages
  - Use direct device-to-device sharing for sensitive cases

#### T.11.2 - Event Timing Patterns

- **Description**: Timing of event publications reveals activity patterns.
- **Impact**: Inference of user activity, group communication patterns.
- **Countermeasures**:
  - Add random delays before publishing
  - Use cover traffic to obscure patterns
  - Distribute events across time

#### T.11.3 - Event Size Leakage

- **Description**: Size of kind: 445 events leaks information about message length.
- **Impact**: Inference of message content length.
- **Countermeasures**:
  - MLS padding obscures exact lengths
  - Multiple encryption layers add overhead
  - Consider additional padding for sensitive messages

#### T.11.4 - Group ID Tracking

- **Description**: The `h` tag on kind: 445 events contains the `nostr_group_id` value from the Marmot Group Data Extension, allowing observers to track message volume and timing patterns for specific groups.
- **Prerequisites**: Observer can query relays for kind: 445 events.
- **Impact**: Tracking of message counts per group, activity levels, and communication patterns. Cannot determine group membership or content.
- **Affected Components**: [MIP-01](01.md) (Marmot Group Data Extension), [MIP-03](03.md) (Group Events)
- **Countermeasures**:
  - **RECOMMENDED**: Rotate `nostr_group_id` values monthly through admin Commit updating the Marmot Group Data Extension (See [MIP-01](01.md))
  - Use multiple `nostr_group_id` values per logical group by having different members subscribe to different IDs
  - Ephemeral keypairs on kind: 445 events prevent sender identification
  - Distribute messages across multiple relays to fragment visibility
- **Residual Risk**: Some activity tracking remains possible. Monthly rotation limits long-term tracking.

#### T.11.5 - Group Image Metadata

- **Description**: Group image hashes in extension could be used for correlation.
- **Impact**: Potential group identification across different contexts.
- **Countermeasures**:
  - Image hashes are group-internal (encrypted in extension)
  - Rotate group images if correlation is concern
  - Understand that image hashes persist across epochs

#### T.11.6 - Relay List Correlation

- **Description**: Consistent relay lists across groups enable correlation.
- **Impact**: Inference of group relationships or user overlap.
- **Countermeasures**:
  - Use different relays for different groups when possible
  - Rotate relay lists periodically
  - This affects all Nostr users, not just Marmot

#### 2.11.2 Correlation Attacks

**Attack Scenarios**:

#### T.11.7 - Group Activity Tracking

- **Description**: Observers track activity levels for specific groups via `nostr_group_id` monitoring.
- **Impact**: Inference of group importance, activity patterns.
- **Countermeasures**:
  - Rotate group IDs regularly
  - Ephemeral keys prevent sender identification
  - Multiple group IDs obscure tracking

#### T.11.8 - IP Address Correlation

- **Description**: Relay operators correlate IP addresses that publish/subscribe to the same `nostr_group_id` values.
- **Impact**: Potential inference of group membership based on IP address overlap.
- **Countermeasures**:
  - Use Tor, i2p, or VPNs to hide IP addresses
  - Use multiple relays per group and distribute events across relays
  - Rotate `nostr_group_id` values monthly
  - Use different relays for different groups (See also T.2.1)

#### T.11.9 - Message Burst Pattern Analysis

- **Description**: Attackers analyze patterns of message bursts to infer conversation dynamics, identify active discussions, or correlate group activity with external events.
- **Prerequisites**: Observer can monitor event timing across relays.
- **Impact**: Inference of conversation topics based on timing, identification of coordinated group activity, potential correlation with real-world events.
- **Affected Components**: [MIP-03](03.md) (Group Events)
- **Countermeasures**:
  - Add random delays (0-30 seconds) before publishing events to obscure exact timing
  - Use cover traffic by periodically sending dummy encrypted messages
  - Distribute events across multiple relays with varying timing
  - Client implementations SHOULD implement timing obfuscation
- **Residual Risk**: Sophisticated traffic analysis may still detect patterns. Complete protection requires constant cover traffic.

#### T.11.10 - Cross-Group Activity Correlation

- **Description**: Observers correlate activity patterns across multiple groups to identify users who participate in multiple groups based on timing similarities.
- **Prerequisites**: Observer monitors multiple groups and can perform statistical correlation.
- **Impact**: Potential identification of users active in multiple groups, even with ephemeral keys.
- **Affected Components**: [MIP-03](03.md) (Group Events), cross-group user behavior
- **Countermeasures**:
  - Use different devices or identities for different groups when privacy is critical
  - Vary timing patterns across different groups
  - Use Tor or VPNs to prevent IP-based correlation
  - Consider using different relays for different groups
- **Residual Risk**: Sophisticated correlation attacks may succeed against users active in many groups.

#### T.11.11 - Message Size Fingerprinting

- **Description**: While MLS provides some padding, encrypted message sizes still leak information about plaintext length, potentially allowing inference of message type (short text vs. media sharing).
- **Prerequisites**: Observer can monitor message sizes.
- **Impact**: Inference of message content type (text, links, media references), potential identification of specific message patterns.
- **Affected Components**: [MIP-03](03.md) (Group Events), [MIP-04](04.md) (Encrypted Media)
- **Countermeasures**:
  - MLS padding obscures exact message lengths
  - Double encryption adds overhead
  - Consider application-level padding for sensitive messages
  - Use consistent message sizes where possible
- **Residual Risk**: Some information leakage remains. Perfect size hiding requires significant bandwidth overhead.

#### T.11.12 - Group Size Inference from Welcome Events

- **Description**: Gift-wrapped Welcome events sent to new members have sizes correlated with group size (ratchet tree scales with member count).
- **Prerequisites**: Observer monitoring a user's incoming kind: 1059 events.
- **Impact**: Observers monitoring a user's incoming gift-wrapped events might infer approximate size of groups they're being added to based on message sizes.
- **Affected Components**: [MIP-02](02.md) (Welcome Events), MLS Welcome objects
- **Countermeasures**:
  - This is inherent to MLS architecture and Welcome message structure
  - Light Welcome objects (future MLS feature) would partially mitigate by reducing Welcome size
  - Padding could obscure exact sizes but at significant bandwidth cost
  - Gift-wrapping still prevents identification of Welcome vs. other message types
- **Residual Risk**: Some group size inference possible for sophisticated observers. Mitigation limited until light Welcome objects available.

### 2.12 Cryptographic Attacks

The protocol relies on cryptographic primitives that could be targets for attack.

#### 2.12.1 Algorithm Weaknesses

**Attack Scenarios**:

#### T.12.1 - MLS Ciphersuite Vulnerabilities

- **Description**: Vulnerabilities discovered in MLS ciphersuites (AES-GCM, ChaCha20-Poly1305, HKDF).
- **Impact**: Compromise of group message confidentiality.
- **Countermeasures**:
  - MLS supports multiple ciphersuites for negotiation
  - Follow cryptographic best practices
  - Update to patched versions when vulnerabilities discovered
  - Implement cryptographic agility for algorithm upgrades

#### T.12.2 - secp256k1 Weaknesses

- **Description**: Breakthrough in elliptic curve cryptography compromises secp256k1.
- **Impact**: Compromise of Nostr identities and signatures.
- **Countermeasures**:
  - Affects all of Nostr, not just Marmot
  - Migration to post-quantum cryptography may be necessary
  - Monitor cryptographic research and advisories

#### T.12.3 - Hash Collision Attacks

- **Description**: SHA-256 collisions become practical.
- **Impact**: Event ID spoofing, integrity check bypass.
- **Countermeasures**:
  - Transition to SHA-3 or other hash functions if needed
  - Monitor hash function security research
  - Implement hash function agility

#### T.12.4 - Cryptographic Agility

- **Description**: Deprecated or broken algorithms require protocol updates.
- **Impact**: Inability to upgrade without breaking compatibility.
- **Countermeasures**:
  - MLS ciphersuite negotiation enables algorithm selection
  - Extension versioning enables format evolution
  - Design for cryptographic agility from the start

#### 2.12.2 Implementation Vulnerabilities

**Attack Scenarios**:

#### T.12.5 - Side-Channel Attacks

- **Description**: Timing attacks, cache attacks, or power analysis leak key material.
- **Impact**: Key exposure despite encryption.
- **Countermeasures**:
  - Use constant-time cryptographic implementations
  - Rely on well-audited libraries (e.g., OpenMLS)
  - Use secure hardware when available
  - Implement side-channel resistant algorithms

#### T.12.6 - Random Number Generation

- **Description**: Poor randomness in key generation or nonce generation.
- **Impact**: Predictable keys compromise encryption.
- **Countermeasures**:
  - Use cryptographically secure random number generators
  - Rely on OS-provided or well-audited library RNGs
  - Validate randomness quality
  - Never reuse nonces

#### T.12.7 - Memory Safety

- **Description**: Memory corruption bugs in native implementations leak keys.
- **Impact**: Key material exposure.
- **Countermeasures**:
  - Use memory-safe languages (Rust)
  - Use sanitizers (AddressSanitizer, etc.)
  - Implement fuzzing for security testing
  - Secure memory handling practices

#### T.12.8 - TLS Serialization Errors

- **Description**: Incorrect TLS serialization of Marmot Group Data Extension causes interoperability or security issues.
- **Impact**: Group state corruption, security bypasses.
- **Countermeasures**:
  - **CRITICAL**: Use exact TLS presentation language serialization ([MIP-01](01.md))
  - Proper length prefixes and byte alignment
  - Comprehensive serialization testing
  - Version detection prevents format mismatches

#### T.12.9 - Version Detection Failures

- **Description**: Clients fail to properly detect or handle extension versions.
- **Impact**: Security bypasses, client crashes.
- **Countermeasures**:
  - Implement version detection algorithm ([MIP-01](01.md))
  - Forward compatibility for unknown versions
  - Graceful error handling with clear messages
  - Version validation before processing

#### T.12.10 - Extension Version Downgrade

- **Description**: Malicious admin could commit an older version of Marmot Group Data Extension to remove security features or bypass protections introduced in newer versions.
- **Impact**: Potential security regression, removal of security features added in later versions.
- **Affected Components**: [MIP-01](01.md) (Marmot Group Data Extension), version management
- **Countermeasures**:
  - Clients SHOULD warn users when extension version decreases
  - Consider requiring unanimous member consent for version downgrades
  - Document minimum supported versions clearly in client implementations
  - Log version changes prominently for audit purposes
- **Residual Risk**: Some downgrades may be legitimate (compatibility with older clients). Balance security with interoperability.

### 2.13 Operational Security

Operational security considerations beyond protocol-level protections.

#### 2.13.1 Key Management

**Attack Scenarios**:

#### T.13.1 - Key Backup Threats

- **Description**: Key backup or restore mechanisms could be compromised.
- **Impact**: Exposure of backed-up keys.
- **Countermeasures**:
  - Encrypt backups with strong passwords
  - Use secure backup storage
  - Limit backup access
  - Consider whether backups are necessary

#### T.13.2 - Key Rotation Failures

- **Description**: Keys not rotated regularly increase compromise impact.
- **Impact**: Extended exposure windows.
- **Countermeasures**:
  - Regular signing key rotation ([MIP-00](00.md))
  - Client UI for easy key rotation
  - Automatic rotation prompts
  - Immediate rotation after compromise

#### 2.13.2 Client Updates

**Attack Scenarios**:

#### T.13.3 - Malicious Client Updates

- **Description**: Malicious client updates introduce vulnerabilities or backdoors.
- **Impact**: Complete compromise of client security.
- **Countermeasures**:
  - Code signing for client updates
  - Integrity checks for updates
  - Reproducible builds enable verification
  - Update from trusted sources only
  - Review update changelogs

#### 2.13.3 Social Engineering

**Attack Scenarios**:

#### T.13.4 - Unauthorized Member Addition

- **Description**: Attackers trick users into adding malicious members to groups.
- **Impact**: Privacy breach, information leakage.
- **Countermeasures**:
  - User education about group security
  - Verify member identities before adding
  - Use multiple admins for verification
  - Monitor group membership changes

#### T.13.5 - Admin Privilege Granting

- **Description**: Attackers trick users into granting admin privileges.
- **Impact**: Complete group control by attacker.
- **Countermeasures**:
  - Careful vetting of admin candidates
  - Use multiple admins for checks and balances
  - Admin action logging and notifications
  - Revoke admin privileges if compromise suspected

#### 2.13.4 Multi-Device Security

**Attack Scenarios**:

#### T.13.6 - Device Synchronization Attacks

- **Description**: One device compromised while others remain secure creates synchronization issues.
- **Impact**: Partial compromise, state desynchronization.
- **Countermeasures**:
  - Remove compromised devices immediately
  - Monitor device additions
  - Use device management features
  - Regular device audits

#### T.13.7 - Cross-Device Correlation

- **Description**: Multiple devices in groups affect privacy properties.
- **Impact**: Potential correlation of device ownership.
- **Countermeasures**:
  - Understand that multiple devices increase attack surface
  - Use different devices for different groups when possible
  - Monitor device activity patterns

#### T.13.8 - Device Removal Race Conditions

- **Description**: Device removed while offline creates synchronization issues.
- **Impact**: Device might attempt to use stale group state.
- **Countermeasures**:
  - MLS handles out-of-order messages gracefully
  - Clients should validate group state on reconnect
  - Error handling for stale state scenarios

## 3. Security Considerations

### 3.0 Critical Security Requirements

These requirements are CRITICAL for security and MUST be implemented correctly. Failure to implement any of these creates serious vulnerabilities.

**Severity Levels**:
- **CRITICAL (Security Bypass)**: Requirements that prevent authentication bypass or information leakage. Failure enables impersonation or content exposure.
- **CRITICAL (Correctness)**: Requirements that ensure protocol correctness and state consistency. Failure causes synchronization issues or data corruption.
- **HIGH (Security Reduction)**: Requirements that significantly reduce security properties. Failure weakens but doesn't eliminate protections.

#### 3.0.1 Credential Validation (MIP-00) - CRITICAL (Security Bypass)

**Requirement**: Clients MUST validate that the Nostr public key in the MLS BasicCredential identity field exactly matches the kind: 443 KeyPackage event's pubkey field.

- **Why Critical**: Prevents impersonation attacks where attackers publish KeyPackages with credentials belonging to other users
- **Related Threat**: T.1.2 - Key Package Credential Mismatch
- **Specification**: See [MIP-00](00.md) (Identity Requirements)

#### 3.0.2 Commit/Welcome Ordering ([MIP-02](02.md)) - CRITICAL (Correctness)

**Requirement**: Clients MUST wait for relay confirmation of Commit publication before sending corresponding Welcome events.

- **Why Critical**: Prevents race conditions where new members receive Welcome for group state that hasn't been finalized
- **Related Threat**: T.7.4 - Welcome Event Timing Race Conditions
- **Specification**: See [MIP-02](02.md) (Timing Requirements)

#### 3.0.3 Ephemeral Keypair Uniqueness ([MIP-03](03.md)) - HIGH (Security Reduction)

**Requirement**: Clients MUST generate fresh ephemeral keypairs for EVERY kind: 445 Group Event. Never reuse keypairs.

- **Why Critical**: Reuse breaks privacy guarantees and enables sender correlation across messages
- **Related Threat**: T.8.1 - Ephemeral Keypair Reuse
- **Specification**: See [MIP-03](03.md) (Privacy Protection)

#### 3.0.4 Unsigned Inner Events ([MIP-03](03.md)) - CRITICAL (Security Bypass)

**Requirement**: Inner events (Nostr events inside MLS ApplicationMessages) MUST remain unsigned - omit the `sig` field entirely.

- **Why Critical**: Signed events could be published to public relays if leaked, exposing group content irreversibly
- **Related Threat**: T.8.2 - Inner Event Signature Leakage
- **Specification**: See [MIP-03](03.md) (Security Requirements)

#### 3.0.5 Signing Key Rotation After Last Resort Use ([MIP-00](00.md)) - HIGH (Security Reduction)

**Requirement**: Clients MUST rotate signing keys within one week after using last resort KeyPackages. Best practice: rotate within 24-48 hours.

- **Why Critical**: Last resort KeyPackages can be reused, creating extended vulnerability window
- **Related Threat**: T.7.1 - Last Resort KeyPackage Reuse
- **Specification**: See [MIP-00](00.md) (Signing Key Rotation)

#### 3.0.6 Admin Authorization Verification ([MIP-01](01.md), [MIP-03](03.md)) - CRITICAL (Security Bypass)

**Requirement**: Clients MUST verify that Commit senders are listed in the current `admin_pubkeys` array before processing any Commit, EXCEPT for self-update Commits. Self-update Commits (containing only an Update proposal for the sender's own LeafNode) MAY be processed from any member without admin verification.

- **Why Critical**: Prevents unauthorized structural group state changes by non-admin members while allowing all members to maintain key hygiene
- **Related Threat**: T.4.x - Admin Privilege Abuse scenarios
- **Specification**: See [MIP-01](01.md) (Marmot Group Data Extension), [MIP-03](03.md) (Commit Messages)

#### 3.0.7 Commit Race Condition Handling ([MIP-03](03.md)) - CRITICAL (Correctness)

**Requirement**: When receiving competing Commits for the same epoch, clients MUST apply exactly one using timestamp priority (earliest first), with ID as tiebreaker (lexicographically smallest).

- **Why Critical**: Prevents group state forks and ensures all members converge on same state
- **Related Threat**: T.4.6 - Commit Race Conditions
- **Specification**: See [MIP-03](03.md) (Commit Message Race Conditions)

#### 3.0.8 TLS Serialization Accuracy ([MIP-01](01.md)) - CRITICAL (Correctness)

**Requirement**: Implementations MUST use exact TLS presentation language serialization for Marmot Group Data Extension with proper length prefixes and byte alignment.

- **Why Critical**: Incorrect serialization causes interoperability failures and potential security bypasses
- **Related Threat**: T.12.8 - TLS Serialization Errors
- **Specification**: See [MIP-01](01.md) (TLS Serialization Requirements)

#### 3.0.9 Media Integrity Verification ([MIP-04](04.md)) - CRITICAL (Correctness)

**Requirement**: Clients MUST verify SHA256(decrypted_content) matches the `x` field in `imeta` tags after decrypting media.

- **Why Critical**: Detects file corruption, tampering, or decryption failures
- **Related Threat**: T.9.2 - File Integrity Attacks
- **Specification**: See [MIP-04](04.md) (Integrity Verification)

### 3.1 Implementation Pitfalls

Common mistakes that developers should avoid when implementing Marmot:

#### 3.1.1 Ephemeral Key Management

**Pitfall**: Accidentally reusing ephemeral keypairs across multiple kind: 445 events, often due to caching or optimization attempts.

**Consequences**: Sender correlation, privacy loss, breaks unlinkability guarantees.

**Solution**: Generate fresh keypair for EVERY event. Never cache or reuse. Add assertions in development to detect reuse.

#### 3.1.2 Credential Field Validation

**Pitfall**: Only checking Nostr signatures without validating that the credential identity matches the event pubkey.

**Consequences**: Authentication bypass, impersonation attacks.

**Solution**: Implement explicit validation: `credential.identity == event.pubkey`. Add test cases for mismatched credentials.

#### 3.1.3 Commit/Welcome Race Conditions

**Pitfall**: Sending Welcome immediately after publishing Commit, without waiting for relay confirmation.

**Consequences**: New members join with stale state, group desynchronization.

**Solution**: Implement proper async flow: publish Commit → wait for confirmation → then send Welcome. Use relay OK responses.

#### 3.1.4 Inner Event Signatures

**Pitfall**: Signing inner events "just in case" or for consistency with other Nostr events.

**Consequences**: Signed events can be published if leaked, irreversible content exposure.

**Solution**: Never populate `sig` field for inner events. Add validation to reject signed inner events.

#### 3.1.5 Admin Verification Timing

**Pitfall**: Checking admin status after processing Commit, or using stale admin list.

**Consequences**: Unauthorized state changes, privilege escalation.

**Solution**: For non-self-update Commits, verify admin status BEFORE processing, using current epoch's admin list from extension. For self-update Commits, verify the Commit contains ONLY an Update proposal for the sender's own LeafNode before processing.

#### 3.1.6 TLS Serialization Edge Cases

**Pitfall**: Incorrect handling of variable-length fields, missing length prefixes, or wrong byte order.

**Consequences**: Interoperability failures, inability to join groups from other implementations.

**Solution**: Use well-tested TLS serialization libraries. Test with reference implementations. Validate against specification byte layouts.

#### 3.1.7 Exporter Secret Context

**Pitfall**: Using wrong context strings for key derivation, or inconsistent formatting (e.g., using UTF-8 vs raw bytes).

**Consequences**: Decryption failures, inability to decrypt messages from other implementations.

**Solution**: Use exact context strings from specification. For [MIP-04](04.md): `"mip04-v1" || 0x00 || file_hash || 0x00 || mime_type || 0x00 || filename || 0x00 || "key"`. Test cross-implementation compatibility.

#### 3.1.8 Extension Version Handling

**Pitfall**: Failing to detect or validate extension version before processing, causing crashes on future versions.

**Consequences**: Client crashes, inability to handle protocol evolution.

**Solution**: Implement version detection (See [MIP-01](01.md)). Handle unknown versions gracefully with clear error messages.

#### 3.1.9 Commit Priority Logic Errors

**Pitfall**: Using incorrect timestamp comparison or missing ID tiebreaker, causing different clients to apply different Commits.

**Consequences**: Group state forks, message delivery failures.

**Solution**: Use timestamp priority first, then lexicographic ID comparison for ties. Test with simultaneous Commits.

#### 3.1.10 Key Rotation Negligence

**Pitfall**: Not implementing or prompting for regular signing key rotation.

**Consequences**: Extended compromise windows, reduced PCS effectiveness.

**Solution**: Implement weekly rotation prompts. Make UI prominent and easy. Consider automatic rotation for high-security contexts.

### 3.2 Implementation Requirements

Implementations MUST:
- Validate credential matching for KeyPackage events (Nostr pubkey in credential matches event pubkey)
- Wait for Commit confirmation before sending Welcome events
- Never reuse ephemeral keypairs for Group Events
- Keep inner events unsigned to prevent accidental public publishing
- Rotate signing keys regularly, especially after using last resort KeyPackages
- Verify admin status before processing Commits (except self-update Commits from any member)
- Handle Commit race conditions using timestamp/ID priority
- Use exact TLS serialization for Marmot Group Data Extension
- Verify file integrity after media decryption

### 3.3 Best Practices

Implementations SHOULD:
- Use multiple admins for groups to provide checks and balances
- Implement client-side rate limiting and message filtering
- Rotate `nostr_group_id` values periodically
- Use multiple relays per group
- Add random delays to obscure timing patterns
- Monitor for suspicious admin actions
- Provide clear UI for key rotation and device management
- Implement forward compatibility for unknown extension versions
- Use Tor or VPNs when privacy is critical
- Limit message retention on devices
- Implement comprehensive error handling

### 3.4 User Recommendations

#### 3.4.1 For Individual Users

Individual group members SHOULD:

- **Device Security**:
  - Enable full disk encryption (FileVault on macOS, BitLocker on Windows, LUKS on Linux)
  - Use strong device authentication (PIN/password + biometrics)
  - Keep operating systems and applications updated
  - Use reputable anti-malware software
  - Never share devices with untrusted individuals

- **Key Management**:
  - Rotate signing keys weekly in all active groups (See [MIP-00](00.md))
  - Secure Nostr private keys carefully - they control your identity across all Nostr applications
  - Consider using hardware security modules (HSM) or secure enclaves for key storage
  - Back up keys securely if needed, but understand backup security trade-offs

- **Privacy Practices**:
  - Use Tor, i2p, or reputable VPNs when privacy is critical
  - Understand that metadata (timing, IP addresses, relay usage) can leak despite encryption
  - Use different devices or identities for different contexts when high privacy is required
  - Be aware that relay operators can observe your IP address and connection patterns

- **Group Participation**:
  - Understand that all messages you receive while in a group remain accessible to you after leaving
  - Be thoughtful about what you share - members can retain and leak content
  - Verify the identity of group admins before trusting them with sensitive information
  - Leave groups promptly when you no longer need access

#### 3.4.2 For Group Administrators

Group admins SHOULD:

- **Access Control**:
  - Carefully vet who receives admin privileges - admins have significant power
  - Use multiple admins (3-5) for important groups to provide checks and balances
  - Monitor admin actions for anomalous behavior
  - Remove admin privileges immediately if compromise is suspected

- **Member Management**:
  - Verify member identities before adding to sensitive groups
  - Remove members promptly when they no longer need access
  - Remove compromised devices immediately upon detection
  - Monitor group membership changes and investigate unexpected additions

- **Group Configuration**:
  - Use multiple relays (3-5) per group for redundancy (See [MIP-01](01.md) Marmot Group Data Extension)
  - Rotate `nostr_group_id` values monthly to limit tracking (See [MIP-01](01.md))
  - Update group configuration (relays, metadata) as needed through Commits
  - Monitor relay reliability and switch when necessary

- **Security Maintenance**:
  - Prompt all members to rotate signing keys weekly
  - Lead by example - rotate your own keys regularly
  - Coordinate key rotation after using last resort KeyPackages
  - Consider implementing automatic rotation reminders

#### 3.4.3 For Client Developers

Client implementers SHOULD:

- **Security-First Development**:
  - Implement all Critical Security Requirements (Section 3.0) without exception
  - Avoid all Implementation Pitfalls (Section 3.1)
  - Use well-audited cryptographic libraries (e.g., OpenMLS, libsecp256k1)
  - Implement comprehensive error handling with clear user-facing messages

- **Testing and Validation**:
  - Test interoperability with other Marmot implementations
  - Implement fuzzing for security-critical code paths
  - Validate against all MIP specifications (00-04)
  - Test edge cases: large groups, race conditions, network failures

- **User Experience**:
  - Make key rotation easy and prominent - weekly rotation should be simple
  - Provide clear warnings for security-relevant actions (granting admin, adding members)
  - Display admin actions and membership changes prominently
  - Implement device management features for multi-device users

- **Privacy Features**:
  - Implement timing obfuscation (random delays 0-30 seconds)
  - Support Tor and VPN usage
  - Provide options for message retention limits
  - Make privacy settings discoverable and understandable

#### 3.4.4 For Relay Operators

Relay operators SHOULD:

- **Abuse Prevention**:
  - Implement rate limiting to prevent spam attacks
  - Consider requiring authentication ([NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md)) for posting Marmot events
  - Consider proof-of-work requirements ([NIP-13](https://github.com/nostr-protocol/nips/blob/master/13.md)) for expensive operations
  - Monitor for abuse patterns and respond appropriately

- **Reliability**:
  - Provide reliable service with good uptime
  - Communicate planned downtime to users
  - Monitor relay performance and capacity
  - Scale infrastructure to handle Marmot event traffic

- **Privacy Considerations**:
  - Understand that you can observe metadata (IP addresses, timing, event patterns)
  - Implement privacy-preserving practices where possible
  - Be transparent about logging and data retention policies
  - Consider supporting privacy-enhancing technologies (e.g., accepting Tor connections)

### 3.5 Testing Requirements

Comprehensive testing is essential to ensure security requirements are properly implemented. This section provides concrete testing recommendations for implementers.

#### 3.5.1 Security Testing

**Critical Security Requirements Testing**:
- **Credential mismatch detection**: Test that clients reject KeyPackages where MLS credential identity doesn't match event pubkey
- **Ephemeral keypair uniqueness**: Validate that each kind: 445 event uses a unique keypair (add assertions in development)
- **Inner event signature validation**: Verify clients reject or warn about signed inner events
- **Admin authorization bypass**: Attempt non-self-update Commits from non-admin members and verify rejection; verify self-update Commits from non-admins are accepted
- **Race condition handling**: Send simultaneous Commits and verify consistent state across clients

**Attack Scenario Testing**:
- **Gift-wrapped event spam**: Test client behavior under high volume of invalid [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) events
- **Welcome timing races**: Test new member join when Commit hasn't propagated
- **Large group limits**: Test Welcome message sizes approaching relay limits
- **Replay attacks**: Verify clients deduplicate replayed kind: 445 events

#### 3.5.2 Interoperability Testing

**Cross-Implementation Compatibility**:
- Message exchange between different Marmot client implementations
- TLS serialization compatibility for Marmot Group Data Extension
- Extension version handling across different client versions
- Media encryption/decryption across implementations

**Protocol Compliance**:
- MLS message format validation against OpenMLS
- Nostr event format validation against NIPs
- [NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md) gift-wrapping format compliance
- [NIP-44](https://github.com/nostr-protocol/nips/blob/master/44.md) encryption compatibility

#### 3.5.3 Fuzzing Targets

**High-Priority Fuzzing**:
- Extension deserialization (TLS format parsing)
- MLS message processing (Commits, Proposals, Welcome objects)
- Nostr event parsing (kind: 443, 444, 445, 10051)
- Media decryption ([MIP-04](04.md) format handling)
- Key derivation (exporter secret contexts)

**Fuzzing Goals**:
- Detect crashes from malformed input
- Identify memory safety issues
- Find edge cases in parsing logic
- Validate error handling paths

#### 3.5.4 Performance Testing

**Resource Exhaustion Scenarios**:
- Large group scalability (100-150 members)
- High message volume handling
- Rapid Commit frequency response
- Multiple concurrent group membership

**Limits Testing**:
- Welcome message size limits
- Relay message size constraints
- Event processing throughput
- Memory usage under load

### 3.6 Security Properties Summary

**Strong Protections**:
- Message confidentiality via MLS symmetric encryption
- Forward secrecy (after member removal and state deletion)
- Post-compromise security (after key updates)
- Authentication via MLS and Nostr signatures
- Double encryption for application messages

**Remaining Vulnerabilities**:
- Malicious insiders (members and admins)
- Metadata leakage (timing, group activity, IP correlation)
- Spam and DoS attacks (gift-wrapped events, invalid messages)
- Compromised clients (complete key exposure)
- Relay operator surveillance (IP addresses, timing)
- Social engineering (unauthorized member addition, admin granting)

## 4. References

### 4.1 Normative References

- **[RFC 9420](https://www.rfc-editor.org/rfc/rfc9420.html)**: The Messaging Layer Security (MLS) Protocol
- **[RFC 9750](https://www.rfc-editor.org/rfc/rfc9750.html)**: MLS Architecture
- **[MIP-00](00.md)**: Credentials & Key Packages
- **[MIP-01](01.md)**: Group Construction & Marmot Group Data Extension
- **[MIP-02](02.md)**: Welcome Events
- **[MIP-03](03.md)**: Group Messages
- **[MIP-04](04.md)**: Encrypted Media (optional)

### 4.2 Informative References

- **[NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md)**: Basic protocol flow description
- **[NIP-13](https://github.com/nostr-protocol/nips/blob/master/13.md)**: Proof of Work
- **[NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md)**: Authentication of clients to relays
- **[NIP-44](https://github.com/nostr-protocol/nips/blob/master/44.md)**: Encrypted Direct Message
- **[NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md)**: Gift Wrap
- **[NIP-70](https://github.com/nostr-protocol/nips/blob/master/70.md)**: Replaceable Events
- **[NIP-92](https://github.com/nostr-protocol/nips/blob/master/92.md)**: File Metadata
- **RFC 6819**: OAuth 2.0 Threat Model and Security Considerations (format reference)

## 5. Acknowledgments

This threat model is based on the Marmot protocol specifications, MLS protocol documentation, and security analysis of the Nostr protocol. It incorporates considerations from all Marmot Implementation Proposals (MIPs) and aims to provide comprehensive coverage of potential threats and mitigations.

---

**Note**: This is a living document and should be updated as new threats are identified or protocol specifications evolve.

