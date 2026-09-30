# Spec validation reference tests

Run `python3 -m unittest discover -s tests -v` from the repository root.

The history-purge model exercises admin-mediated opening, local admission/cooldown and closure obligations, the
request-fixed purge boundary, the accepted Commit's rollback horizon,
terminal actors and proposal sets, selected-branch races, restart state, and receipt aggregation. Its inputs assume
authenticated identities, valid proofs, and an already selected MLS branch. It does not implement MLS, signature
verification, branch convergence, or actual persistent-store deletion. Restart tests copy model state; integration
implementations must separately demonstrate durable storage and crash recovery.

The [V1 fixture](vectors/history-purge-v1.json) pins exact canonical bytes and domain-separated SHA-256 identities.
Its byte preimages were also cross-checked with independent fixed-width packing. The all-zero signatures are
synthetic encoding placeholders and are invalid authorization proofs. The encoding tests cover shortest QUIC
prefixes, request/open-state/finalization framing, maximum vector bounds, malformed framing, timestamp bounds,
ordering, and unknown enums. They do not
establish signature validity, curve-point validity, or complete protocol conformance.

The layout regression rejects a feature listed under `ideas/` when its actual file is under `features/`.
The validator's separate phrase checks provide structural documentation coverage only.
