# Accumulation relays

Status: idea (non-normative). Nothing here is part of the Marmot protocol yet. See [README.md](./README.md).

An accumulation relay is a specially configured Nostr relay that collects a broad feed of encrypted Marmot events and
buffers them for authorized clients. A user can authorize one or more trusted accumulation relays, including
self-hosted ones. The client can use multiple authorized relays in parallel while keeping direct upstream connections off.

Independently operated accumulation relays with overlapping coverage provide alternate paths if one fails. Relays
with disjoint coverage can extend reach, but each unique source still has a single path. Group routing and upstream
fanout stay intact. A single usable accumulation path remains a client-side exception to Marmot's
[redundant-delivery invariant](../principles.md#write-the-stable-marmot-invariants-once), which needs an explicit
protocol-level decision before adoption.

The goal is to reduce exposure of individual group subscriptions upstream. The mode may also reduce mobile connection
overhead compared with connecting to every upstream, depending on how many accumulators the client uses. Parallel
subscriptions can increase duplicate downloads. The accumulators bear the collection bandwidth and storage costs.

## User flow

1. The user adds relay URLs and authorizes the device separately at each relay through private pairing or an invitation.
2. The client checks each relay's capabilities, source coverage, retained history and collection status.
3. The client queries authorized relays for the current and prior `h` addresses it needs. It validates events under
   the existing Nostr and MLS rules and processes duplicate deliveries through the existing deduplication rules.
4. Inbox, discovery and publication go through authorized accumulation relays that support the requested operation.
   Another authorized relay can take over when it covers the needed targets.
5. The client shows missing coverage and loss of redundancy. The user can disconnect or revoke access per relay.
   Direct upstream connections require an explicit user choice because they can reveal subscriptions.

Media downloads and connections to an external signer are separate from accumulation relay connections.

## Collection and history

The accumulation relay collects a broad group-event feed from its configured upstream sources continuously, including
while clients are offline. Here, broad means collecting the group-event kind across its configured sources without
upstream filters or event-body fetches selected by clients’ group tags, including aggregate tags from multiple clients.
Client group tags select responses from the local buffer only.

Collection can use ordinary Nostr subscriptions and [NIP-77](https://github.com/nostr-protocol/nips/blob/master/77.md)
reconciliation where available. Reconciliation exposes its filter and identifies missing events; it does not transfer
their bodies or prove that an upstream supplied everything. If an upstream rejects or limits the broad feed, the relay
reports the resulting gap and keeps interest-dependent collection off. A client unable to establish the relay’s
declared collection mode shows degraded or unavailable coverage and does not silently fall back. Any separate
interest-dependent mode would reveal group interests upstream and would require explicit user opt-in.

The relay keeps a declared rolling history window applied independently of personal queries. It honors the existing
[Nostr event-expiration policy](../transports/nostr.md#message-expiration) when retaining and serving buffered
events. The rolling window limits how long it can keep events that remain eligible to serve. Retaining only a user's
groups, extending their retention on demand, or requesting individual groups upstream would introduce interest-dependent
behavior. A broad buffer can include new or rotated addresses without learning their encrypted routing changes, but
only where its sources, collection interval and retention window cover the events.

The client compares each relay's reported coverage with the routing sources and history it needs. Reports can describe
complementary coverage, but an unavailable relay leaves a gap wherever no remaining relay covers the needed source
and time range. A source missing from the
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

This mode needs a negotiated relay extension for upstream targets, request correlation and delivery
results. Ordinary Nostr message queries remain useful for buffered group events, but ordinary queries and event
publication do not name the upstream destinations of a proxy operation. Enrollment and these extension messages are
not defined by this idea.

The client's accumulation relay URLs are local configuration. Enabling this mode leaves the group's signed routing
state and account relay lists intact. Inbox and discovery proxying follows the existing target
rules in the [Nostr transport](../transports/nostr.md), subject to supported authentication and source access.

For publication, the client retains the original signed event and its applicable upstream target set. The proposed
accumulation relay durably accepts a forwarding job and attempts the same event at every permitted target. Local
storage acceptance is reported separately from an upstream acceptance. The first upstream acceptance can satisfy the
existing publish lifecycle; outstanding fanout remains outstanding as described by the Nostr transport.

The intended relay continues accepted forwarding work while the phone is offline. The client retains enough information
to recover the job and target results after reconnecting. Relay restart, uncertain acknowledgements, exhausted capacity,
job retention and relay replacement need explicit recovery semantics before adoption. Retrying an uncertain publication
uses the retained signed event, including when another authorized relay takes over. The client tracks confirmations
by upstream target across relays. Duplicate reports for the same target do not count as additional upstream
acceptances. Outstanding targets remain owed. Transport delivery reports do not choose group state.

Forwarding is limited to authorized, bounded upstream operations.

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
- **Availability:** overlapping coverage through independently operated relays can keep a client connected during an
  outage. Common infrastructure or shared upstream outages can still affect multiple paths. The client reports the
  resulting loss of coverage or redundancy without silently switching to direct connections.
- **Parallel exposure:** each queried operator can see the queries it handles. Operators may correlate shared group
  tags, client network metadata or timing even when each relay sees a different authentication key.

## Integration and path into the specification

This is an optional client transport mode, not new MLS group state. No component ids, event kinds or wire encodings are
assigned here. Existing groups and clients using direct relays remain interoperable.

Once settled, exact enrollment, capability, proxy, coverage and delivery-report behavior belongs in the Nostr transport
specification. A feature document can describe the user flow and reference those rules. Relay URLs
and authentication credentials stay in local configuration.

## Open questions and validation

Before turning this into an interoperable profile, settle:

- Whether an opt-in single relay path is an acceptable exception to redundant delivery at the client.
- The versioned enrollment, capability and forwarding exchange, including authorization scopes, replay protection,
  credential replacement, error results and recovery after an interrupted change.
- How source coverage, rotation catch-up and declared history are represented without claiming completeness, including
  sources discovered after an offline interval and upstreams that reject broad collection. Define the broad filters and
  how clients can distinguish a declared operating mode from verified collection behavior.
- Durable forwarding ownership, target results, job expiry and recovery after ambiguous acknowledgements, restart or
  replacement, preserving existing publication obligations.
- Safe destination policy and budgets for hostile input, large groups, many clients and broad feed flooding.
- Measured collection costs, mobile bandwidth and battery use, catch-up latency and the consequences of shared versus
  single-user deployment. Compare single and parallel paths under overlapping and complementary coverage.

Interop validation can cover unknown-key rejection, account isolation, authentication replay and wrong-relay attempts,
credential revocation, history gaps and offline rotation, original-event publication and target fanout, crash recovery,
destination and resource limits. Also test loss of one parallel path with overlapping or disjoint coverage, duplicate
event and target-report handling, and failover without unintended direct Nostr connections.
