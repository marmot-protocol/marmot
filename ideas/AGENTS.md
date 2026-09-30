# AGENTS.md - ideas

Agent operating rules for the ideas surface. Read [`README.md`](README.md) for what an idea is; the cross-surface map is
in [`../AGENTS.md`](../AGENTS.md).

## Scope

Idea documents are non-normative explorations of future protocol work, written for early feedback: user-visible flows,
trade-offs, and open questions. They are not spec text.

## Rules

- Do not use `MUST`, `SHOULD`, or `MAY` as requirement keywords in an idea document. Describe the intended behavior in
  plain language.
- Do not assign or reserve ids of any kind (component, extension, proposal, event kind, exporter label), and do not add
  idea material to [`../foundation/registries.md`](../foundation/registries.md).
- Do not define wire bytes, structs, or validation rules. Name the surface that will own them instead.
- Normative spec documents may link to an idea only as non-normative context, never to delegate a rule to it.
- Keep open questions explicit. When a question is settled and the rule moves into an owning surface, remove it from
  the idea document in the same change.
- Figures live in a directory named after the idea document (for example `multi-device/`). Use SVG with light and dark
  styles and no external fonts or scripts.

## Verification

- When adding, renaming, or removing an idea document, update [`../layout.md`](../layout.md) and
  [`README.md`](README.md) in the same change.
- Grep idea documents for uppercase `MUST`, `SHOULD`, and `MAY`, and for hexadecimal ids; neither belongs here.
- Confirm every link and image path resolves.

## Pointers

- Up to the cross-surface map: [`../AGENTS.md`](../AGENTS.md).
- Where settled rules go: [`../layout.md`](../layout.md).
