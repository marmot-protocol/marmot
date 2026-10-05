# Accumulation relays

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

An accumulation relay is a specially configured Nostr relay that collects a broad feed of encrypted Marmot events and
buffers them for authorized clients. A user chooses a trusted shared relay or self-hosts one. When this mode is enabled,
the client uses that relay as its only Nostr relay connection and queries its current and retained group routing tags.

The goal is to reduce the exposure of individual group subscriptions to untrusted upstream relay operators, while
reducing mobile connection overhead and duplicate downloads. The additional collection bandwidth and storage move to
the accumulation relay. These benefits need measurement and depend on which sources the relay can collect.

## User flow

1. The user enters the accumulation relay URL and authorizes this device through private pairing or an invitation.
   Entering a URL alone does not grant access to a private relay.
2. The client checks the relay's capabilities, source coverage, retained history and collection status after
   authorization. An ordinary relay with authentication alone is insufficient.
3. The client submits normal Nostr group queries for every current and prior `h` address needed by its retained
   history. It receives the matching events and verifies them using the existing Nostr and MLS rules.
4. Inbox, discovery and publication traffic also pass through this connection. The accumulation relay contacts the
   appropriate upstream destinations; the client does not open additional Nostr relay connections for those operations.
5. Missing coverage, catch-up and outages remain visible. Returning to direct connections requires an explicit user
   choice because that can reveal subscriptions. The user can revoke a device or disconnect the accumulation relay.

Media downloads and connections to an external signer are separate from the one Nostr relay connection described here.

## Collection and history

The accumulation relay collects a broad group-event feed from its configured upstream sources continuously, including
while clients are offline. It does not forward clients' exact group filters upstream or fetch only the individual
event bodies selected by those filters. Group tags received from a client select its response from the local buffer.

Collection can use ordinary Nostr subscriptions and [NIP-77](https://github.com/nostr-protocol/nips/blob/master/77.md)
reconciliation where available. Reconciliation exposes its filter and identifies missing events; it does not transfer
their bodies or prove that an upstream supplied everything. Some upstreams may reject or limit broad collection.

The relay keeps a declared rolling history window applied independently of personal queries. Retaining only a user's
groups, extending their retention on demand, or requesting individual groups upstream would introduce interest-dependent
behavior. A broad buffer can include new or rotated addresses without learning their encrypted routing changes, but
only where its sources, collection interval and retention window cover the events.

The client compares reported coverage with the routing sources and history it needs. A source missing from the
collector is a coverage gap, not an empty conversation. Adding an upstream means collecting its broad feed; it is not
a request to follow only the requesting user's groups. Coverage for source changes discovered during catch-up is an
open recovery question. The collector has no MLS secrets with which to discover those changes itself.

Coverage reports distinguish live connectivity, historical reconciliation, retained ranges and known gaps. They are
self-reported operational evidence, not proofs of completeness. An end-of-stored-events response does not establish
upstream completeness. Retaining ciphertext also does not extend the client's MLS decryption or rollback windows; see
[retained history](../protocol-core/retained-history.md).

## Authentication and private access

The proposed endpoint uses [NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md) with an independently random
authentication key for each device, account and accumulation relay. This key is separate from the account signer and
is not derived from account or group keys. It is a revocable relay-specific pseudonym, rather than a new key on every
connection. NIP-42 makes the authentication event ephemeral; it does not require an ephemeral signing key.

Enrollment determines which keys have access. Possession of an arbitrary key does not authorize a client. Pairing,
key replacement and revocation need private, replay-resistant flows bound to the intended relay and an authenticated
encrypted connection. Revocation needs to end existing authorized sessions as well as prevent new ones. The client
does not silently substitute its main account key when authentication fails.

Queries, reconciliation, private capabilities, coverage, configuration and account-specific state are disclosed only
to authorized clients. A shared relay isolates clients' private query and administration state. Public information,
error responses and logs avoid publishing individual subscriptions, pairing credentials or account associations.

An upstream requiring unavailable identity-bound authentication is reported as unsupported. Client authentication
credentials are not forwarded upstream. Separate authentication does not hide account identities already present in
forwarded inbox filters or signed account metadata.

## Forwarding and publication

The one-connection mode needs a negotiated relay extension for upstream targets, request correlation and delivery
results. Ordinary Nostr message queries remain useful for buffered group events, but ordinary queries and event
publication do not name the upstream destinations of a proxy operation. Enrollment and these extension messages are
not defined by this idea.

The client's accumulation relay URL is local configuration. It does not replace the group's signed routing state or
publish a new account relay list merely to enable this mode. Inbox and discovery proxying follows the existing target
rules in the [Nostr transport](../transports/nostr.md), subject to supported authentication and source access.

For publication, the client retains the original signed event and its applicable upstream target set. The proposed
accumulation relay durably accepts a forwarding job and attempts the same event at every permitted target. Local
storage acceptance is reported separately from an upstream acceptance. The first upstream acceptance can satisfy the
existing publish lifecycle; outstanding fanout remains outstanding as described by the Nostr transport.

The intended relay continues accepted forwarding work while the phone is offline. The client retains enough information
to recover the job and target results after reconnecting. Relay restart, uncertain acknowledgements, exhausted capacity,
job retention and relay replacement need explicit recovery semantics before adoption. Retrying an uncertain publication
uses the retained signed event rather than generating another event. Transport delivery reports do not choose group state.

Forwarding is restricted to authorized, bounded upstream operations. It is not an open proxy: destination policy,
address validation across DNS resolution and redirects, credential isolation and per-client resource limits protect
against access to internal networks and abuse. Collection limits and refusals remain visible as availability limits.

## Privacy and availability limits

- **Upstream group subscriptions:** broad collection avoids exposing each client's exact group-query set. Collection
  schedules, source changes and a relay dedicated to one user can still offer clues about that user's activity.
- **Forwarded traffic:** publications retain their visible routing tags; inbox and discovery requests can reveal account
  identifiers upstream. Immediate forwarding also preserves timing correlations. This is not an app-wide anonymity claim.
- **Accumulation operator:** the operator sees requested groups, authentication pseudonyms, client network metadata and
  identities carried in forwarded requests. A separate authentication key does not make these observations unlinkable.
- **Outside observers:** private access prevents unauthorized enumeration, but the endpoint may remain identifiable as
  a Nostr relay. Encryption does not hide connection destinations, timing or volume. Global traffic analysis is outside
  this proposal's guarantee; padding, mixing and Tor integration need separate work.
- **Message security:** clients retain Nostr signature and MLS validation. The relay cannot substitute its reports for
  that validation, but it can withhold or delay events. It does not receive MLS secrets.
- **Availability:** upstream publication and group delivery retain their existing redundant targets. The selected
  accumulation relay adds a local dependency: that client's connection can fail even while the group continues elsewhere.
  Switching relays requires authorization, coverage checks and publication recovery; direct fallback is a user choice.

## Integration and path into the specification

This is an optional client transport mode, not new MLS group state. No component ids, event kinds or wire encodings are
assigned here. Existing groups and clients using direct relays remain interoperable.

Once settled, exact enrollment, capability, proxy, coverage and delivery-report behavior belongs in the Nostr transport
specification. A feature document can describe the user flow and reference those rules. Neither the private relay URL
nor its authentication credentials belongs in the group's app components.

In White Noise, shared client routing, authentication and recovery belong in MDK; Android presents configuration,
pairing and status. A separate optimized relay implementation can combine collection, buffering and authorized
forwarding. Its internal storage and scheduling choices stay outside normative protocol text.

## Open questions and validation

Before turning this into an interoperable profile, settle:

- The versioned enrollment, capability and forwarding exchange, including authorization scopes, replay protection,
  credential replacement, error results and recovery after an interrupted change.
- How source coverage, rotation catch-up and declared history are represented without claiming completeness, including
  sources discovered after an offline interval and upstreams that reject broad collection.
- Durable forwarding ownership, target results, job expiry and recovery after ambiguous acknowledgements, restart or
  replacement, preserving existing publication obligations.
- Safe destination policy and budgets for hostile input, large groups, many clients and broad feed flooding.
- Measured collection costs, mobile bandwidth and battery use, catch-up latency and the consequences of shared versus
  single-user deployment. One connection alone is not a bandwidth or battery benchmark.

Interop validation can cover unknown-key rejection, account isolation, authentication replay and wrong-relay attempts,
credential revocation, history gaps and offline rotation, original-event publication and target fanout, crash recovery,
destination and resource limits, and absence of unintended direct Nostr connections while the mode is enabled.
