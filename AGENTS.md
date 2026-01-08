# AGENTS.md (aka CLAUDE.md)

A guide for AI coding agents working on the Marmot Protocol specification. This will work for most major AI harnesses. The `CLAUDE.md` file in this repo is a symlink to this doc.

## Project Overview

Marmot is a secure, decentralized group messaging protocol that combines the [MLS Protocol](https://www.rfc-editor.org/rfc/rfc9420.html) with [Nostr's](https://github.com/nostr-protocol/nostr) decentralized network. The protocol enables end-to-end encrypted group messaging without relying on centralized servers.

**Key Characteristics:**
- Protocol specification repository (not an implementation)
- Markdown-based documentation (MIPs - Marmot Implementation Proposals)
- References MLS RFCs and Nostr NIPs
- Focus on security, interoperability, and clarity

## Project Structure

```plaintext
marmot/
├── README.md              # Main project overview
├── AGENTS.md             # This file
├── 00.md - 04.md         # Marmot Implementation Proposals (MIPs)
├── threat_model.md       # Security threat analysis
├── data_flows.md         # Protocol flow diagrams
├── dependency_reqs.md    # Implementation dependencies
├── docs/mls/             # Local copies of MLS RFCs
│   ├── rfc9420.txt       # MLS Protocol spec
│   ├── rfc9750.txt       # MLS Architecture
│   └── draft-ietf-mls-extensions-08.txt
└── assets/               # Images and diagrams
```

## Key Documents

### Marmot Implementation Proposals (MIPs)

- **[MIP-00](00.md)**: Credentials & Key Packages (REQUIRED)
- **[MIP-01](01.md)**: Group Construction & Marmot Group Data Extension (REQUIRED)
- **[MIP-02](02.md)**: Welcome Events (REQUIRED)
- **[MIP-03](03.md)**: Group Messages (REQUIRED)
- **[MIP-04](04.md)**: Encrypted Media (OPTIONAL)

### Supporting Documentation

- **[threat_model.md](threat_model.md)**: Comprehensive security analysis
- **[data_flows.md](data_flows.md)**: Protocol flow diagrams and architecture
- **[dependency_reqs.md](dependency_reqs.md)**: Implementation dependencies

## Protocol Fundamentals

### Core Concepts

1. **MLS (Messaging Layer Security)**: Provides group encryption, forward secrecy, and post-compromise security
2. **Nostr**: Provides decentralized relay network and identity system
3. **Marmot Group Data Extension**: Custom MLS extension containing group metadata
4. **KeyPackages**: Public invitation cards for asynchronous group joins
5. **Double Encryption**: MLS symmetric encryption + NIP-44 encryption for application messages

### Event Kinds

- `kind: 443`: KeyPackage events (public invitations)
- `kind: 444`: Welcome events (gift-wrapped via NIP-59)
- `kind: 445`: Group events (messages, proposals, commits)
- `kind: 10051`: KeyPackage relay list events

### Critical Security Requirements

When working on protocol specifications, ensure these are always addressed:

1. **Credential Validation**: MLS credential identity MUST match Nostr pubkey in KeyPackage events
2. **Commit/Welcome Ordering**: Commits MUST be confirmed before sending Welcome events
3. **Ephemeral Keypair Uniqueness**: Fresh keypair for EVERY kind: 445 event
4. **Unsigned Inner Events**: Inner events MUST NOT be signed (prevents leak publication)
5. **Admin Authorization**: Commits MUST verify sender is in admin_pubkeys array
6. **TLS Serialization**: Exact TLS presentation language format required

## Code Style & Conventions

### Markdown Formatting

- Use clear headings with descriptive names
- Include code examples in JSON format for Nostr events
- Reference other MIPs using `[MIP-XX](XX.md)` format
- Use tables for structured data (event fields, security properties, etc.)
- Include security notes with ✅ (protections) and ⚠️ (limitations)

### Specification Writing

- **MUST/SHOULD/MAY**: Use RFC 2119 terminology for requirements
- **CRITICAL**: Mark security-critical requirements explicitly
- **Examples**: Include complete, valid examples
- **Edge Cases**: Document race conditions, error handling, and failure modes
- **Interoperability**: Consider cross-implementation compatibility

### Security Considerations

- Always reference threat_model.md for security context
- Document observable metadata and privacy limitations
- Include countermeasures for identified threats
- Mark security-critical sections with **CRITICAL** labels

## Common Tasks

### Adding a New MIP

1. Create `XX.md` file (next sequential number)
2. Follow structure of existing MIPs:
   - Title and status (review/draft)
   - Required/optional flag
   - Overview and motivation
   - Detailed specification
   - Examples
   - Security considerations
   - References to other MIPs
3. Update README.md MIP table
4. Update threat_model.md if security implications exist

### Updating Protocol Specifications

1. Read relevant MIPs and MLS RFCs
2. Check threat_model.md for security implications
3. Update data_flows.md if protocol flows change
4. Ensure examples remain valid
5. Update cross-references between MIPs

### Security Analysis

1. Review threat_model.md for relevant threats
2. Consider new attack vectors
3. Document countermeasures
4. Update security requirements section
5. Reference specific threat IDs (e.g., T.1.2)

## Reference Materials

### MLS Documentation

- **RFC 9420**: [docs/mls/rfc9420.txt](docs/mls/rfc9420.txt) - MLS Protocol specification
- **RFC 9750**: [docs/mls/rfc9750.txt](docs/mls/rfc9750.txt) - MLS Architecture overview
- **MLS Extensions**: [docs/mls/draft-ietf-mls-extensions-08.txt](docs/mls/draft-ietf-mls-extensions-08.txt)

### Nostr Documentation

- Use Nostrbook MCP server to query NIPs (if available)
- Key NIPs referenced:
  - NIP-01: Basic protocol flow
  - NIP-44: Encrypted Direct Message (key derivation)
  - NIP-59: Gift Wrap (Welcome event encryption)
  - NIP-70: Replaceable Events (KeyPackage deletion)

### Implementation References

- [MDK](https://github.com/parres-hq/mdk): Reference Rust implementation
- [marmot-ts](https://github.com/parres-hq/marmot-ts): TypeScript implementation

## Testing & Validation

### Specification Validation

- Verify all JSON examples are valid
- Check that event kinds match Nostr standards
- Ensure TLS serialization examples are correct
- Validate cross-references between documents

### Interoperability Considerations

- Consider how different implementations might interpret specs
- Document ambiguous areas clearly
- Provide test vectors where helpful
- Reference implementation behavior when relevant

## Important Notes for Agents

1. **This is a specification repo**: Focus on protocol design, not implementation code
2. **Security-first**: Always consider security implications of changes
3. **Backward compatibility**: Changes should maintain interoperability
4. **Cross-references**: Update related documents when making changes
5. **Examples**: Keep examples complete and valid
6. **Terminology**: Use precise MLS and Nostr terminology
7. **Status tracking**: Update MIP status (draft → review → stable)

## Common Pitfalls to Avoid

1. **Missing security considerations**: Always document security implications
2. **Incomplete examples**: JSON examples must be complete and valid
3. **Broken references**: Check that all `[MIP-XX](XX.md)` links work
4. **Ambiguous requirements**: Use MUST/SHOULD/MAY consistently
5. **Ignoring edge cases**: Document race conditions and error handling
6. **TLS serialization errors**: Verify exact byte-level format matches spec

## Questions to Consider

When making changes, ask:

- Does this maintain backward compatibility?
- What are the security implications?
- Are there race conditions or edge cases?
- Do examples need updating?
- Should threat_model.md be updated?
- Are cross-references still valid?
- Does this affect interoperability?

## Getting Help

- Review existing MIPs for patterns and style
- Check threat_model.md for security context
- Reference MLS RFCs for cryptographic details
- Consult Nostr NIPs for event format requirements
- Look at implementation repos for clarification

---

**Remember**: This is a protocol specification. Clarity, precision, and security are paramount. When in doubt, err on the side of explicitness and security.
