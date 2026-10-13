# marmot.group.convergence-policy.v2

Status: adopted.

## Registry

- Component id: `0x8010`
- Name: `marmot.group.convergence-policy.v2`
- Location: GroupContext `app_data_dictionary`
- Default requirement: optional; activated automatically once every member supports it

## Purpose

This component selects convergence policy v2 for a group. Policy v2 changes how app-payload witnesses are counted and
the order in which candidate branches are compared. [../protocol-core/convergence.md](../protocol-core/convergence.md)
defines both policies and which one a convergence pass uses ("Active policy"). This document defines only the component
bytes, how a group starts requiring the component, and what a client MUST NOT do with it afterwards.

Convergence policy v1 has no component. A group that does not require this component uses v1. The name carries `v2`
because it names the policy version it selects.

## State

The state bytes are empty. A GroupContext entry for `0x8010` whose `data` is not zero bytes long is invalid.

The component carries no parameters. Convergence parameters are protocol constants, not group settings (see
[../protocol-core/convergence.md](../protocol-core/convergence.md), "Convergence policy").

The entry has meaning only while `0x8010` is listed in the GroupContext required `app_components` list. A resulting
state that contains the entry without requiring `0x8010`, or that requires `0x8010` without the entry, is invalid.

## Leaf advertisement

A client that implements convergence policy v2 advertises `0x8010` in the `app_components` support list of its
KeyPackages and of every replacement LeafNode it creates for its own leaf, as described in
[README.md](./README.md) ("Enabling a Component in an Existing Group"). This component defines no LeafNode entry.

## Activation

This component uses the automatic activation mode in [README.md](./README.md) ("Enabling a Component in an Existing
Group").

An activation Commit:

- adds the `0x8010` entry with empty state bytes; and
- adds `0x8010` to the required `app_components` list.

The Commit is valid only when:

- the authenticated committer is an active admin in the candidate parent;
- `0x8010` is not already required in the candidate parent;
- every leaf in the resulting state advertises `0x8010` in its `app_components` support list; and
- the resulting state satisfies normal MLS and Marmot validation.

The activation MAY share a Commit with other valid proposals.

Once every leaf in the current canonical state advertises `0x8010`, an active admin's client SHOULD commit the
activation without user action. It SHOULD wait for a delay chosen uniformly at random before doing so, and SHOULD commit
only while the group's lifecycle is `Stable`. Activations by different admins for the same epoch are an ordinary
same-epoch race: whichever branch is selected, the group ends up requiring `0x8010`, so a client whose activation lost
does not retry it once the selected state already requires the component.

A client creating a new group SHOULD require `0x8010` at creation when its own leaf and every initial member's
KeyPackage advertise `0x8010`. Otherwise the group starts under policy v1 and later activates as above.

## Proposal and Commit authorization

Only an active admin MAY propose or commit the activation. No other AppDataUpdate operation on `0x8010` is defined: an
`update` operation targeting `0x8010` is invalid, and so is an `add` operation when `0x8010` is already present.

## Effect on convergence

The component affects a convergence pass only through the active-policy rule in
[../protocol-core/convergence.md](../protocol-core/convergence.md) ("Active policy"). That rule reads the GroupContext
of the pass's policy epoch, not the GroupContext of any candidate branch. An activation Commit therefore does not change
the policy used to choose between branches that diverged before it, even when one of those branches contains it.

## Removal

This component cannot be removed while present, and `0x8010` cannot be removed from the required `app_components` list.
An AppDataUpdate `remove` operation targeting `0x8010`, or a Commit whose resulting required list drops `0x8010` while
the candidate parent required it, is invalid.

Returning a group to policy v1 would let a later pass rewind history that policy v2 had protected, so there is no
downgrade path. The only exception is the activation Commit of a later convergence-policy component whose own document
defines replacing `0x8010`.

## Migration

This is the first convergence-policy component. A later convergence policy receives a new component id and document.
That document defines how a group moves from policy v2 to it; a client MUST NOT infer the active policy from software
version.
