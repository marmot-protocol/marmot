# Agents in chats v1

Status: draft. It describes what [MDK](https://github.com/marmot-protocol/mdk) (at `bea7b400b`) and the
[marmot-agents](https://github.com/marmot-protocol/marmot-agents) core send and read today, and moves the agent
carrier from [the idea document](../ideas/agents-in-chats.md) into the specification. Passages marked
**[Inferred]** were concluded rather than read in either implementation, and need checking before adoption.

An agent is a program that takes requests in a chat and acts on them. It joins a group as an ordinary member, with
an account of its own. This feature defines how its work reaches the chat and how people answer and steer it:

- **The agent's words** are ordinary chat messages, kind `9`, with a tag naming their turn.
- **Everything else the agent does** is an *agent item*, kind `1201`: a turn, a tool call, a request for permission,
  a question, a plan, a background task, a notice, an error, its reasoning, or its session. An item changes by
  being sent again, whole, as a kind `1009` edit of its first event with a higher version.
- **What a person sends back** is a *request*, kind `1202`: an answer to an approval or a question, or a control
  such as "interrupt". The agent's own reply settles each request exactly once.

Every item carries a plain rendering in its `content`, so a client that knows nothing of agents can still show it,
and the agent program's own message beside it, unchanged, for a client that wants more.

## Contents

- [Terms](#terms)
- [Surfaces and requirements](#surfaces-and-requirements)
- [Common rules](#common-rules)
- [Kind 1201: an agent item](#kind-1201-an-agent-item)
- [Item types and their fields](#item-types-and-their-fields)
- [The session item](#the-session-item)
- [Versions of an item (kind 1009)](#versions-of-an-item-kind-1009)
- [Where an item sits](#where-an-item-sits)
- [The agent's words](#the-agents-words)
- [Kind 1202: answers and controls](#kind-1202-answers-and-controls)
- [Settling a request](#settling-a-request)
- [Attention](#attention)
- [The size limit](#the-size-limit)
- [Unknown, unreadable and retired shapes](#unknown-unreadable-and-retired-shapes)
- [Extension: items in subagent threads](#extension-items-in-subagent-threads)
- [Retention, deletion and convergence](#retention-deletion-and-convergence)
- [Security and privacy considerations](#security-and-privacy-considerations)
- [Migration](#migration)
- [Examples](#examples)

## Terms

| Term | Meaning |
| --- | --- |
| Agent | A group member whose account is run by an agent program. |
| Harness | The agent program, such as Codex or Claude Code, with its own way of reporting its work. |
| Owner | The person who runs the agent and decides who may use it. |
| Item | One thing the agent did or asked, shown as one row. |
| First event | The kind `1201` event that began an item. Its event id identifies the item. |
| Version | One state of an item: its first event, or an accepted edit of it. |
| Request | A kind `1202` event: an answer or a control. |
| Settle | The agent's reply that says what became of a request. |
| Turn | One piece of the agent's work, from what started it until the agent stops. |
| Session | The harness's memory of one conversation. A chat has one current session with an agent. |

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are as in RFC 2119.

## Surfaces and requirements

| Surface | What this feature adds |
| --- | --- |
| [foundation/application-messages.md](../foundation/application-messages.md) | An exception to kind `1009` edits for a kind `1201` target; two tags on kind `9` (`turn`, `phase`) and one shared with items (`settles`) |
| [foundation/registries.md](../foundation/registries.md) | Kinds `1201` and `1202` move from "reserved" into the main table, owned by this document |
| This document | The shapes of kinds `1201` and `1202`, the item types, versions, requests and their settling |

No app component, proposal, capability, transport change or group-size limit is needed. Agent events are ordinary
Marmot app events: the [application payload rules](../foundation/application-messages.md) own their encoding and the
authentication of their author, and every rule here applies after them. Nothing here changes how a group delivers,
orders or retains app events.

The feature is optional. A client that does not support it still delivers these events to its application layer, as
for any kind ([Message kinds](../foundation/application-messages.md#message-kinds)); what it shows is in
[Unknown, unreadable and retired shapes](#unknown-unreadable-and-retired-shapes).

## Common rules

These apply to every tag this document defines on kinds `1201`, `1202`, `1009` (of an item) and `9`.

- **A tag's value** is its second element. A tag with a name and no second element has the empty string as its
  value, and still counts as present. Elements after the second are ignored, except where this document (`native`,
  `left_out`, `cut`) or NIP-22 ([Extension](#extension-items-in-subagent-threads)) gives them a meaning.
- **A single tag** is one this document says appears at most once. A repeated single tag never reads as one of its
  values. On kinds `1201`, `1202` and an item's `1009`, a repeated single tag that decides readability
  ([items](#when-an-item-is-readable), [requests](#tags-1)) makes the event unreadable; a repeated optional one
  (`native`, `left_out`, `subagent`) is ignored, both copies. On kind `9`, a repeated `turn` or `phase` is ignored and
  the message is still an ordinary chat message.
- **An event id** in a tag value is exactly 64 lowercase hexadecimal characters: a Marmot app event id in the same
  group. Uppercase is not an event id.
- **An account key** in a tag value or a field is exactly 64 lowercase hexadecimal characters: an x-only public key,
  as the app event's `pubkey` is.
- **A counter** (`v`, `seq`) is a positive integer from `1` to `9223372036854775807`, written in plain decimal: no
  sign, no leading zero, no spaces. Any other spelling is invalid, so one number has one spelling.
- **JSON in a tag** (`fields`, `details`, `native`) is one UTF-8 JSON value encoded as the tag's string. A JSON
  object in it MUST NOT repeat a member name; a reader that finds one MAY treat the value as invalid **[Inferred:
  MDK's reader does not check this for `fields`; the core's reader of requests refuses a repeated member]**. Member
  order and whitespace carry no meaning, except inside `native`.
- **Text** is UTF-8 and is compared byte for byte. No normalisation applies.
- **Unknown tags** are kept. A client stores and passes on every tag of an event it accepts, including those it does
  not read, and a later version replaces them only as [Versions](#versions-of-an-item-kind-1009) says.

## Kind 1201: an agent item

The first version of an item is a kind `1201` event. Its `content` is the item's plain rendering: one or more lines a
person can read on their own, possibly empty. Everything else is in tags.

### Tags

| Tag | Value | Cardinality | Read by |
| --- | --- | --- | --- |
| `["v", <counter>]` | The item's version, from `1` | Exactly one | Every client |
| `["state", <state>]` | `running`, `waiting`, `done`, `failed`, `declined` or `cancelled` | Exactly one | Every client |
| `["title", <text>]` | A few words: "Running a command", "Allow this command?". May be empty | Exactly one | Every client |
| `["harness", <text>]` | The harness's name, such as `codex`. Not empty | Exactly one | Every client |
| `["item_id", <text>]` | The harness's own id for the item. Not empty | Exactly one | Every client |
| `["seq", <counter>]` | The event's place among its session's events, from `1` | Exactly one | Every client |
| `["fields", <JSON>]` | The item type and its own fields: `{"type": <type>, "body": {...}}` | Exactly one | Every client |
| `["session", <text>]` | The harness's session | At most one | Every client |
| `["turn", <text>]` | The turn the item belongs to | At most one | Every client |
| `["started_by", <event id>]` | On a `turn`: the chat message that started it. On a `refused` notice: the chat message not acted on | At most one | Every client |
| `["settles", <event id>]` | A request whose effect this version shows. One tag per request | Any number | Every client |
| `["native", <kind>, <JSON>]` | The harness's own message: its name for the message, then the message as the exact text it arrived as | At most one | Optional |
| `["left_out", "native", <bytes>]` | The sender left `native` out to fit the [size limit](#the-size-limit), and how large it was | At most one | Optional |
| `["cut", <field kind>, <number>]` | The sender cut text of this kind to fit, with the full length of what was cut, or a count. One tag per kind | Any number | Optional |
| `["subagent", <text>]` | For a subagent's work: the `item_id` of the subagent's `task` item. **Provisional** | At most one | Optional |
| `E`, `K`, `P`, `e`, `k`, `p` | NIP-22's thread tags, only on an item in a subagent's thread | See [Extension](#extension-items-in-subagent-threads) | Optional |

"Read by every client" means a client that supports this feature reads the tag to show or order the item. An
optional tag is carried and may be shown.

A kind `1201` event MUST NOT carry an `e` tag except as the NIP-22 parent of an item in a subagent's thread, beside its
`E` tag ([Extension](#extension-items-in-subagent-threads)). Anywhere else an `e` would read as an edit's target. A
sender MUST NOT send such an event. A receiver MUST NOT read such an `e` as a thread parent, a reply or an edit
target, and otherwise reads the item as usual.

### When an item is readable

An item is readable when its `v`, `state`, `title`, `harness`, `item_id`, `seq` and `fields` tags are each present
exactly once with a valid value; `session`, `turn` and `started_by` each appear at most once; `started_by` and every
`settles` hold an event id; and `fields` is a JSON object whose `type` member is a non-empty string. Anything else
makes the event an **unreadable item**: a client shows it, if at all, as it shows an event of an unknown kind.

A readable item whose `type` this document does not define, or whose `body` is missing or does not match its type, is
still readable: a client shows it by its `title`, `content` and `state` ([Unknown shapes](#unknown-unreadable-and-retired-shapes)).

### States

| State | Meaning |
| --- | --- |
| `running` | Under way |
| `waiting` | A person is needed: an approval or a question that has not been answered |
| `done` | Finished |
| `failed` | Ended in failure |
| `declined` | Did not happen because it was refused, such as a command a person denied |
| `cancelled` | Stopped before it finished, or closed because the agent could no longer follow it |

`done`, `failed`, `declined` and `cancelled` close an item. A closed item MAY be opened again by a later version, as a
subagent's `task` item is for each of its turns.

### Identity and ordering numbers

- **An item is identified by the event id of its first event.** A request names it by that id; every version of it
  names that id. No other id is needed.
- **`item_id` is the harness's id, not the item's identity.** Two items MAY carry the same `item_id`: an agent that
  can no longer edit an item (its first event expired under the group's [retention](../app-components/message-retention-v1.md))
  sends the next version as a new kind `1201` event, which is a new item from then on, with its version going on
  rising. A client MUST NOT merge items by `item_id`.
- **`seq`** numbers the events of one session, from `1`, in the order the agent produced them. It is not unique: an
  item's versions carry their own `seq`, and a notice the agent makes itself carries the highest `seq` its chat has
  shown, or `1`. Clients use the first event's `seq` only to order items within one second ([Where an item sits](#where-an-item-sits)).
- **`v`** numbers one item's versions, from `1`, and only rises.

## Item types and their fields

`fields` holds the item type and that type's own fields, as one JSON object:

```json
{"type": "tool", "body": {"kind": "command", "name": "shell", "command": "python3 greet.py"}}
```

`body` is a JSON object. A member that is absent has no value; a sender MUST leave it out rather than write `null`. A
reader SHOULD treat `null` as absent (the reference agent's own reader does for single values, and rejects `null`
for a list). A reader ignores a member
it does not know, so a newer agent's item stays readable to an older client. A reader that meets an enumerated value
it does not know (a tool `kind`, a notice `kind`, a step `state`) shows the item generically and does not drop it.

The eleven types:

| Type | What it shows | Fields |
| --- | --- | --- |
| `turn` | A turn started or ended | [turn](#turn) |
| `message` | Text the agent says | [message](#message) |
| `reasoning` | The agent's thinking | none: `{}` |
| `tool` | A tool the agent used | [tool](#tool) |
| `approval` | The agent wants permission for one action | [approval](#approval) |
| `question` | The agent asks a person something | [question](#question) |
| `plan` | The agent's plan or to-do list | [plan](#plan) |
| `task` | Work beside a turn or after it: a subagent, a background job | [task](#task) |
| `notice` | Something a person should know that is not the agent's own words | [notice](#notice) |
| `error` | Something failed outside any one item | [error](#error) |
| `session` | A session with the harness: what an app can set and do | [The session item](#the-session-item) |

In the tables below, "text" is a JSON string, "count" a non-negative JSON integer, and "item id" the harness's
`item_id` of another item in the same session, as a string. A field marked "yes" is required.

### turn

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `started_by` | `user`, `agent` or `control` | yes | What started the turn: a person's message, the agent's own background work, or a control such as compacting |
| `duration_ms` | count | | How long the turn took, once it has ended |
| `usage` | object | | Once ended, when the harness says: `input_tokens` and `output_tokens`, each an optional count |

The `turn` item's `started_by` tag, when present, names the person's chat message that started it. A turn that ends
`failed` needs a person ([Attention](#attention)).

### message

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `phase` | `commentary` or `final` | | A remark while working, or the answer, when the harness says |
| `parent` | item id | | For a subagent's message: the item it belongs to |

The agent's words are sent as chat messages ([The agent's words](#the-agents-words)), not as items. An agent SHOULD
NOT send a kind `1201` of type `message`; a client that receives one shows its `content`. The type is in the shared
vocabulary, but the reference agent never sends it as an item.

### tool

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | `command`, `edit`, `read`, `search`, `fetch`, `mcp`, `subagent` or `other` | yes | Which sort of tool |
| `name` | text | yes | The tool's own name, such as `shell` |
| `command` | text | | A command: what was run |
| `cwd` | text | | A command: the folder it ran in |
| `exit_code` | integer | | A command: its exit code, once finished |
| `duration_ms` | count | | How long the tool took, once finished |
| `output` | text | | What the tool printed or returned, once finished |
| `changes` | array | | An edit: the files it changed, each `{"path": text, "diff": text, "change": "add" \| "update" \| "delete"}`, `change` optional |
| `query` | text | | A search: what was searched for |
| `path` | text | | A file the tool read |
| `input` | any JSON | | Any other tool: what it was called with, as the harness gave it |
| `error` | text | | Why the tool failed, when the harness says |

Any field may appear with any `kind`: a command that only reads files has the kind `read` and still a `command`. A
subagent a harness does not tell apart from its parent is a `tool` of kind `subagent`, with no thread.

### approval

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `subject` | item id | | The item waiting for permission, such as the command |
| `choices` | array | yes | What a person may answer: each `{"id": text, "label": text, "effect": "allow" \| "deny"}` |
| `answer` | object | | Once answered: `{"choice": text}`, the id of the choice; `choice` is absent when the harness reports a decision the item did not offer |

A choice's `id` is the agent's own, not the harness's value for the choice. Choice ids in one item differ. A person
answers by sending a [`choice` request](#actions) naming one of them. A standing answer such as "allow for this
session" is an ordinary choice, and its `label` says what it covers.

### question

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `answer_via` | `request` or `message` | yes | `request`: answered by a [`questions` request](#actions) naming this item. `message`: the harness takes the person's next chat message as the answer, and no request is sent |
| `subject` | item id | | The item the question belongs to |
| `questions` | array | yes | One or more questions, below |
| `answer` | array | | Once answered: one entry per question answered, `{"question": text, "options": [text], "text": text}`, `options` and `text` optional |

Each question is:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | text | yes | The id an answer names. Ids in one item MUST differ |
| `header` | text | | A short heading |
| `text` | text | yes | The question |
| `options` | array | | The answers offered, each `{"id": text, "label": text, "description": text}`, `description` optional. Absent or empty: free text only |
| `multiple` | boolean | | Several options may be chosen. Default `false` |
| `allow_text` | boolean | | The person may type an answer of their own. Default `false` |
| `secret` | boolean | | The answer is a secret, such as a password. Default `false` |

An `answer` names only questions the item asked, and options by the ids it offered. For a `secret` question the entry
names the question and nothing else: no `options`, no `text`. A question item with any `secret` question carries a
`native` tag only while it is `waiting` and has no `answer`, since the harness's later messages may hold the answer.
A client SHOULD NOT offer to answer a secret question in a chat of more than two members, and says to answer it at
the agent instead. The agent refuses such an answer there whatever the client does
([Security](#security-and-privacy-considerations)).

### plan

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `text` | text | | The plan as text, or its explanation |
| `entries` | array | | The plan as steps, each `{"text": text, "state": "pending" \| "running" \| "done"}` |

### task

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | text | yes | The sort of task, in the harness's own word, such as `subagent` |
| `description` | text | | What the task is doing |
| `subject` | item id | | The item that started it |

A subagent's `task` item is the root of its thread when the agent tells subagents apart
([Extension](#extension-items-in-subagent-threads)).

### notice

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `kind` | `compaction`, `waiting`, `retry`, `warning`, `model_changed`, `command_output` or `refused` | yes | What the notice is about |
| `duration_ms` | count | | For `waiting`: how long the agent will wait |
| `reason` | text | | A word saying why. For `refused`, one of the reasons in [Settling a request](#settling-a-request); for `model_changed`, the harness's reason; for `warning`, `too_large` (one of its own items could not be sent whole) or `not_delivered` (one of its own items or messages may not have reached the chat) when the agent sends it about its own items. Both are **provisional** |

A `refused` notice is sent only by the agent's own program, never passed on from a harness.

### error

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `request` | text | | What was being attempted, such as the request the harness refused |
| `code` | integer | | The harness's error code |
| `will_retry` | boolean | | Whether the harness will try again by itself, when it says |

### native, left_out and cut

`native`'s second element is the harness's name for its message, such as `item/completed`; its third is the message
itself, the exact JSON text the harness sent, with its spacing, member order and number spellings kept. A client MAY
show it for a harness it knows and MUST NOT require it. `native` is absent when the sender left it out to fit the
limit (and says so with `left_out`), when the agent made the event up itself, on a question with a secret question
that is no longer waiting, and in a chat the owner does not send the agent's full activity
([Security](#security-and-privacy-considerations)).

`left_out` and `cut` say what the sender removed to fit the [size limit](#the-size-limit). `["cut", "output", <n>]`
gives a tool output's full length in bytes; `["cut", "diffs", <n>]` how many diffs were cut. **Provisional**: other
field kinds (`text`, `title`, `command`, `error`, `input`, `plan`, `steps`, `choices`, `questions`, `description`,
with the full length cut) and counts (`entries`, `changes` thinned in their middle, `descriptions` dropped from a
session's commands, `item` for a stand-in). A client MAY say that an item was shortened; it MUST NOT depend on these.

## The session item

A `session` item tells an app what it can set and do for this agent in this chat, before anyone presses anything, and
who may.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `harness_version` | text | yes | The harness's version. May be empty |
| `settings` | array | | What can be set. Default empty. Each below |
| `actions` | array | | The harness's own actions, such as compacting. Each `{"id": text, "label": text, "description": text}`, `description` optional |
| `commands` | array | | The harness's slash commands. Each `{"name": text, "hint": text, "description": text}`: `name` without its slash, `hint` what to type after it (empty when nothing), `description` optional |
| `title` | text | | The harness's own title for the session, when it gives one |
| `rights` | object | | Who in this chat may prompt and who may approve: `{"prompt": <holders>, "approve": <holders>}` |
| `label` | text | | The owner's name for this install, such as "laptop", when the owner set one |
| `owner` | account key | | The owner's key, when the owner chose to show it |

Each setting is:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | text | yes | The id a [`set` request](#actions) names |
| `label` | text | yes | What an app shows: "Model" |
| `value` | text | | The current value, when known |
| `options` | array of text | | The values it accepts. Absent: nobody has said |
| `approve` | boolean | | Changing it needs the right to approve rather than to prompt, as for a permission mode. Default `false` |

`<holders>` is the string `"everyone"`, or an array of account keys: the members of this chat who hold the right. The
lists name only members of this chat; the agent edits the item when the chat's members or the owner's settings change.

- **Who prompts and approves.** To prompt, answer a question, interrupt, start a new session, change a setting without
  `approve` or use one of the harness's actions needs the right to prompt. To answer an approval or change a setting
  with `approve` needs the right to approve. `rights` is the agent's statement of what it will enforce, for display: a
  client MUST NOT grant or deny anything on its strength ([Security](#security-and-privacy-considerations)). A client MAY
  use it to grey out what the viewer may not do, and to show whom an approval waits for. An item without `rights` says
  nothing about them.
- **First item on joining.** When an agent joins a chat, it sends that chat a `session` item at once, before anyone
  prompts: state `done`, no `session` tag, its `harness_version`, the settings its own program keeps (such as a
  coding agent's `folder`), `rights`, and `label` and `owner` if the owner turned them on. Its content says no session
  has started. A chat the agent was already in when it first ran this way gets one too.
- **Each session's item.** When a session starts in the chat, the agent sends a new `session` item, with the
  `session` tag, and edits it as settings change, as the title changes, and when the session ends. It takes the place
  of the earlier one.
- **The current session item** of an agent in a chat is the readable `session` item from that agent whose first
  event is the latest in the chat's order **[Inferred: the reference agent treats its newest session item as current,
  and the joining item as current until a session starts; no rule is written down for apps]**. A `set`, `own` or
  `new_session` request MAY name it.
- **An agent is a member that has sent a session item.** A client MAY mark such a member as an agent and offer its
  commands. The mark proves nothing: any member can send one ([Security](#security-and-privacy-considerations)).
  The reference agent never takes another agent's messages as prompts unless its owner listed that agent.

## Versions of an item (kind 1009)

A later version of an item is a kind `1009` edit of its first event. The edit carries the whole item again, `content`
and every tag in [Kind 1201](#tags), with a higher `v`, and one more tag: `["e", <first event id>]`.

This is an exception to the ordinary [message edit](../foundation/application-messages.md#message-edits-kind-1009),
for a target of kind `1201` only. Ordinary chat edits are unchanged.

### Accepting a version

A client accepts a kind `1009` event *E* as a version of the item whose first event is *F* when all of these hold:

1. *E* has exactly one `e` tag, and its value is *F*'s event id.
2. *E*'s tags without that `e` tag read as a [readable item](#when-an-item-is-readable), with no further `e` tag.
3. The account authenticated as *E*'s author is the account authenticated as *F*'s author, in the same group. Any
   device of that account may send it, as for any edit.
4. *E*'s `v` is greater than *F*'s `v`.
5. *E*'s author has not deleted *E*.

A kind `1009` that names a kind `1201` and fails any of these MUST NOT change the item. In particular an ordinary text
edit of an item (a kind `1009` whose tags are not a readable item) changes nothing.

### The current version

The **current version** of an item is its accepted version with the highest `v`; the first event is a version too. Two
accepted versions with the same `v` are ordered by their `created_at`, then by their event id, and the greater wins
**[Inferred: this is MDK's order; the agent never sends two versions with one `v`]**. The order the versions arrive
in, and their `created_at`, do not otherwise matter: `created_at` counts whole seconds, and an item often changes
twice in one. An older version that arrives late changes nothing the item shows, but it is still accepted, so its
`settles` tags still settle the requests they name ([Settling a request](#settling-a-request)).

The current version's `content` and tags replace the item's. A client:

- shows the item from its current version, in one row, at the place of its first event;
- MUST NOT mark the item as edited, and SHOULD NOT offer an edit history for it: its versions are its states, not
  corrections;
- MUST NOT treat a version as new conversation activity, an unread message or a chat-list preview, except as
  [Attention](#attention) allows;
- keeps the item's place in a thread from its first event, whatever thread tags a version carries
  ([Extension](#extension-items-in-subagent-threads)).

### A version that arrives before its item

A client cannot know a missing target's kind, so it judges such an edit by its own tags: a kind `1009` whose tags,
without its single `e` tag, read as a [readable item](#when-an-item-is-readable) is a version of an agent item. A client
MUST keep such an edit whose target it has not received, and apply it when the target arrives, for as long as it keeps
app events under the group's retention. It MUST NOT drop it merely because its target is missing. This replaces, for
these edits, the general rule that a client may drop an edit whose target it has not received; an ordinary text edit
whose target is missing may still be dropped.

### A member who joined after the item began

A member added to a group cannot read events sent before they joined, so they may hold versions of an item but never
its first event. Since every version carries the whole item, a client SHOULD show such an item from its versions:

- The item's row is identified by the target's event id, as named by the versions' `e` tag.
- Without the first event, nothing shows who the item's author is, and any member can send a readable edit that
  names the target. So a client MUST keep the versions of each authenticated author apart: one author's versions never
  change, replace or hide what another's show. A client SHOULD show only one author's versions, and SHOULD prefer an
  author it already knows as an agent in the chat (one that has sent a session item there); it MAY show each author's
  versions as a row of its own.
- An author's row is built from the **earliest** of that author's readable edits naming the target, that the author
  has not deleted, in the order the client received them, then by event id. Only that author's versions count (rule 3
  above).
- It sits at that version's place in the timeline, and shows that author's current version, chosen as above.
- A client SHOULD say that the item started before the viewer could see it.
- If the first event arrives later, as from another device's history, it takes the row's place, and only its author's
  versions apply to it, as usual; any other author's versions are dropped.
- Once the client has removed the item under the group's retention, a version of it that arrives later does not bring
  it back.

## Where an item sits

An item has one row, at its first event's place in the chat. A kind `1202` request has no row.

Within one second of `created_at`, clients SHOULD order items by their first event's `seq`, then by event id.
Rows without a `seq`, such as chat messages, order before items in the same second **[Inferred: this is what MDK's
order gives (rows without `seq` count as 0); it is not a stated rule, and it can put an agent's words before the
items of the same second that came first]**.

A client without a thread view SHOULD show, above a `turn` item, the chat message its `started_by` names, as it shows a
reply's target **[Inferred from what MDK quotes above an agent item]**.

## The agent's words

What the agent says to people is an ordinary kind `9` chat message, so every client shows it, and replies, reactions,
search and alerts work as for anyone's message. It carries up to three tags beyond the ordinary ones:

| Tag | Value | Cardinality |
| --- | --- | --- |
| `["turn", <text>]` | The turn it belongs to, as the turn item's `turn` tag | At most one |
| `["phase", "commentary"]` | A remark made while the agent works, not its answer | At most one |
| `["settles", <event id>]` | A request whose effect these words show | Any number |

A chat message with `["phase", "commentary"]` does not alert ([Attention](#attention)). Words the harness does not mark
as a remark carry no `phase` tag. When the words change after they were sent, the agent edits them as any chat message
is edited: the ordinary rules apply, unchanged. A subagent's words are a kind `1111` comment instead
([Extension](#extension-items-in-subagent-threads)).

The ordinary chat-message tag limits still bind the agent's words. An agent puts as many `settles` on its words as
those limits allow and settles the rest with its turn's next version **[Inferred: MDK caps a chat message at 64 tags
and 16 KiB of tag text, which the specification does not state; see notes]**.

## Kind 1202: answers and controls

A request is what a person's app sends to an agent. It changes nothing by itself: the agent decides what happens and
says so ([Settling a request](#settling-a-request)).

### Tags

| Part | Value | Cardinality |
| --- | --- | --- |
| `content` | A plain rendering: "Allow once", "Stop" | |
| `["p", <account key>]` | The agent it is for | Exactly one |
| `["e", <event id>]` | The first event of the item it acts on | At most one |
| `["details", <JSON>]` | What it asks: a JSON object with a string `action` and that action's fields | Exactly one |

A request is **for an agent** when it carries exactly one `p` tag and that tag names the agent's account. A request
with no `p`, with two or more, or naming another account is not for this agent, and the agent says nothing about it.
`p` here names the recipient; it is not a mention.

A request for an agent is **readable** when its `e`, if present, holds one event id, it has exactly one `details`, and
`details` is a JSON object whose `action` is a non-empty string. An `action` this document does not define is
readable and refused as `not_supported`; a known action whose fields are missing or of the wrong types is refused as
`invalid`. A request for the agent that is not readable is still settled ([Settling a request](#settling-a-request)).

### Actions

| `action` | Fields | `e` | Right needed | Acts on |
| --- | --- | --- | --- | --- |
| `choice` | `choice`: text, the id of one of the approval's choices | Required: the `approval` item | Approve | That approval |
| `questions` | `questions`: array, one entry per question answered, each `{"question": text, "options": [text], "text": text}`; `options` defaults to empty, `text` optional | Required: the `question` item | Prompt | That question |
| `interrupt` | none | Optional. An app's Stop in the main chat names the agent's last `turn` item | Prompt | Without `e`, or with `e` naming an item outside a subagent's thread: that item's turn (without `e`, the chat's running turn) and every subagent the agent started. With `e` naming a subagent's `task` item or an item in its thread: that subagent and those it started, where the agent can stop one alone, and otherwise the whole turn |
| `new_session` | none | Optional: the session item | Prompt | Ends the chat's session and starts another |
| `set` | `setting`: text, a setting's `id`; `value`: text | Optional: the session item | Prompt, or Approve for a setting with `approve` | Changes one setting |
| `own` | `id`: text, one of the session item's `actions` | Optional: the session item | Prompt | One of the harness's own actions |

A reader ignores fields of `details` it does not know. An action not in this table is **unknown**: an agent settles it
as `not_supported`, so an app newer than the agent learns that the agent cannot do it.

A slash command is never a request: a message that starts with `/` is a prompt, passed to the harness as typed. An
answer to a `question` whose `answer_via` is `message` is the person's next chat message, not a request.

### What a request is not

A request is not a row in the chat, does not alert, does not count as unread, and is not shown as chat. It is group
content like any other: every member receives and keeps it, so a group sees who pressed what.

## Settling a request

Only the agent knows whether the harness took a request: two people can answer at once. So the agent's own items are
the one record of what happened, and a client shows each request it sent as **pending** until it is settled.

### The agent's reply

An agent settles each request that is for it, exactly once, with one of:

- **the version that shows its effect**: an item version, or the agent's words, carrying `["settles", <request id>]`.
  The approval becomes "Answered: Allow once"; the turn becomes "Interrupted"; the session item shows the new model;
- **a `refused` notice**: a new kind `1201` item of type `notice` with `kind: "refused"`, a `reason`, a sentence in its
  `content`, and `["settles", <request id>]`.

A request is settled by the first event the client accepts that names it in `settles` and comes from the agent the
request was for. A client MUST NOT treat a request as settled by anything else. One event MAY settle several requests.
A client that never receives the settling event shows the request as pending; when the agent's machine is off, the
press stays pending and nothing is assumed.

The reasons of a `refused` notice:

| Reason | Meaning |
| --- | --- |
| `not_allowed` | The sender does not hold the right this action needs. Says nothing else about the item |
| `not_supported` | The agent or its harness cannot do this, including an unknown `action` |
| `invalid` | The request could not be read: no `details`, `details` that is not an action, missing or mistyped fields, or a repeated `e` or `details` |
| `unknown_item` | `e` names no item of this agent in this chat |
| `not_waiting` | An answer to an item that is no longer `waiting` |
| `already_answered` | An answer to an item another answer reached first |
| `nothing_to_do` | It names an item that is closed, or there is nothing to act on |
| `busy` | The agent cannot take it now |
| `no_effect` | The agent took it, and no effect showed within two minutes of its harness taking it |
| `failed` | The agent could not act on it, or the event that would have settled it could not be sent |

A reader MUST accept a reason it does not know and show the notice's `content`.

### Rules the agent applies

These are the agent's rules; a client cannot check them, and states them so that an app can say what will happen.

- **The right comes first.** Someone without the right an action needs is told `not_allowed` and nothing else. A
  request that cannot be read cannot say which right it needs: someone who holds neither right is told `not_allowed`;
  someone who holds either is told `invalid` or `not_supported`.
- **An answer counts only if it names the exact item**, the item is `waiting`, and nobody's answer reached it first.
  Ordinary text is never an answer to an approval. An answer never reaches the model as a prompt.
- **An answer names choices and options by the ids the item offered.**
- **A request that names an item acts only while that item is live**, except that a `set`, `own` or `new_session`
  request acts on the agent's [current session item](#the-session-item) whatever its state: the item sent on joining
  is `done`, and a setting such as the folder may be chosen before any session has started.
- **A request that names no item is dropped, unsettled, when it is more than five minutes old** when the agent reads
  it **[Inferred: measured from the event's `created_at`, as MDK records it]**.
- **Each request acts at most once**, however often it is delivered.
- **A request from another agent** (a member that has sent a session item) is refused as `not_allowed` unless the
  owner listed that agent.
- **An interrupt that reaches several subagents** is settled once, when the last of them has ended.

## Attention

This feature does not define notification policy. Which agent events may interrupt a person, and how a client turns
that into a sound or a banner, is the attention contract of
[marmot#412](https://github.com/marmot-protocol/marmot/issues/412). That is an issue, not a document yet, so this
section is written to be replaced by a pointer to it once it is. This section states only the facts about agent events that
contract needs, so that the two documents do not each define an alert policy.

- **A version needs a person** when it is an `approval` or a `question` whose state is `waiting`, or a `turn` whose
  state is `failed`. No other version of any item needs a person.
- **Whether an item needs a person is decided by its current version**, not by the version that arrived: a version
  that is not the current one needs nobody, and an item that a member sees from its versions after joining is
  decided the same way.
- **A request never needs a person**, and nor does a chat message tagged `["phase", "commentary"]`, nor the agent's
  own comment in a thread whose root is one of its items ([Extension](#extension-items-in-subagent-threads)).
- **The agent's other words**, kind `9` without `phase`, are ordinary chat messages.
- **Who is needed**: for an approval, the members who hold the right to approve in the current session item's
  `rights`; for a question, those who hold the right to prompt **[Inferred: no rule says this yet; it is what #412's
  "intended responder" would need]**.

Until the attention contract is adopted, a client SHOULD alert for a version that needs a person and for nothing else
of kinds `1201` and `1202`, keyed by the item's first event so that a later version replaces an earlier alert, and
SHOULD NOT alert for the other cases above. This is what MDK does today. It is not a second policy: it is the rule
#412's `actionable` and `passive` classes would carry over.

## The size limit

An agent item, a version of one, and a request is each at most **65,536 bytes**, measured as the UTF-8 JSON encoding of
the whole inner app event, with its `id`, `pubkey`, `created_at`, `kind`, `tags` and `content`, as it is placed in
the MLS application message.

- A sender MUST NOT send a larger one.
- When an item would be larger, the sender first leaves out `native` and adds `left_out`; then cuts a tool's output
  and an edit's diffs, keeping their start and end, and adds `cut`. Only after those two steps it MAY cut further
  (provisional; [native, left_out and cut](#native-left_out-and-cut)). When what cannot be cut (ids, names, hints,
  the values an answer names) is over the limit alone, it MAY send a stand-in: a `notice` of kind `warning` with the
  reason `too_large`, keeping the item's ids, state, version, target and `settles`. It never sends anything over the
  limit.
- A receiver does not reject an otherwise valid event for its size. It accepts a larger one and MAY decline to show
  it.

The limit carries every one of 16,841 tool outputs measured in real use. Encryption and encoding grow an event by about
a third on its way to a relay, so an item near the limit is about 86 KB on the wire; a relay that accepts less does not
take it, and the transport's rules for an event too large for a relay apply.

## Unknown, unreadable and retired shapes

| What arrives | A client that supports this feature | A client that does not |
| --- | --- | --- |
| A readable item of a known type | Shows it by type, from its current version | Shows it as an unknown kind: at most one generic row from the first event's `content`, which never updates |
| A readable item of an unknown type | One generic row: `title`, `content`, `state`; updates with its versions | The same as above |
| A readable item whose body does not match its type, or holds unknown values | One generic row, as for an unknown type. Unknown members of a body are ignored | The same as above |
| An unreadable item (missing or invalid required tag, an unknown `state`, the old shape) | As an unknown kind; its versions change nothing | The same |
| A kind `1009` naming an item, whose tags are not a readable item | Ignored | Applied, at most, as an ordinary text edit |
| A request (kind `1202`) | No row; settles from the agent's reply | As an unknown kind; SHOULD NOT show it as chat |
| A `refused` reason, a `cut` kind, or a tag this document does not name | Accepted; the notice's `content` is shown | Not applicable |
| Kind `1200` (retired agent text stream start) | Not shown, as [registries](../foundation/registries.md) says | Not shown |

A client MUST NOT reject an app payload for any of these: they are ordinary app events, delivered to the application
layer, which decides what to show.

**The old shapes.** Before this document, MDK's connectors sent kind `1201` with a `status` tag and JSON content, and
kind `1202` with `operation` tags. Neither is readable here (no `v`; no `p` and `details`), and nothing tells the two
apart beyond that. A client shows an old-shape event as it shows an unreadable one. A later version of this feature
that changes what a tag means MUST take new kind numbers rather than reuse these, as [layout.md](../layout.md#features)
requires an explicit versioning hook; adding a tag, an item type, a body member, a reason or an action is compatible
and needs none. There is no shape-version marker: new kind numbers are the hook, and `v` is an item's version, never
the shape's.

## Extension: items in subagent threads

This section is a separable extension. A client may support the rest of this document without it; an item that
carries these tags is then shown in the main chat, which loses nothing. **This section is non-normative.** The
Marmot specification does not yet define threads, kind `1111` or NIP-22 placement for any app event, and MDK has its
own contract for them. This section leans on NIP-22 directly, and becomes normative once a document of the
specification defines threads.

A harness that tells its subagents apart can show each subagent as a thread in the agent's own group, rooted at the
subagent's `task` item. The thread uses NIP-22's tags as
[NIP-22](https://github.com/nostr-protocol/nips/blob/master/22.md) defines them: the uppercase tags name the root of
the whole tree, the lowercase the immediate parent.

### Tags on an item's first event

| Tag | Names |
| --- | --- |
| `["E", <event id>, "", <agent key>]`, `["K", "1201"]`, `["P", <agent key>]` | The root: the first event of the **top-level** subagent's `task` item, the same at any depth |
| `["e", <event id>, "", <agent key>]`, `["k", "1201"]`, `["p", <agent key>]` | The parent: the first event of the `task` item of the subagent this item belongs to. For a top-level subagent's own items it is the root |

A top-level `task` item is in the main chat and carries none of these. A nested subagent's `task` item is in its
parent's thread, naming the top-level `task` item as root and its parent's `task` item as parent. Each item of a
subagent also carries `["subagent", <item_id of its task item>]` (provisional), so a client can find a nested
subagent's view from a version, which names only the root.

`E` holds one event id; the `e` here is allowed only beside an `E`, once. `p` names the event's own author and is not
a mention: a `p` that names its own event's author never mentions anyone.

### Versions in a thread

A version's one `e` tag is its target, so it cannot also carry the parent. A version repeats the root tags `E`, `K` and
`P` with the first event's values, and carries no `k` or `p`. An item never moves: it stays where its first event
placed it, whatever thread tags a version carries, and an item outside a thread cannot join one through a version's
`E`. A member who holds only versions places the item by the version's `E`, with the root as its parent; a nested
subagent's item then shows under the top-level subagent until its first event arrives.

### The subagent's words, and people in the thread

- A subagent's words are a kind `1111` NIP-22 comment with the root tags and the parent's `e` and `k`, and the `turn`
  tag. **[Inferred: the reference agent's words in a thread carry no parent `p`, as MDK writes comments.]**
- **The agent's own words in its threads never alert, wake anyone or count as unread.** A client decides this from
  the comment alone: it is a kind `1111` whose `E` names a root, whose `K` is `1201`, and whose `P` is the comment's
  own authenticated author. Items in the thread keep their own rule: a subagent's waiting approval needs a person.
- A person writing in the thread sends an ordinary NIP-22 comment, naming the top-level `task` item as root and the
  message answered as parent. Whether the agent takes it as a prompt for that subagent is the agent's rule.
- An `interrupt` request whose `e` names a subagent's `task` item, or an item in its thread, stops that subagent and
  those it started.

### What an app shows

An app opens a subagent's view by the items whose parent is its `task` item; a reply belongs to the view of the first
`task` item up its chain of parents. An app without threads shows a subagent's items as it shows any item and its
words inline, in the main chat. These are presentation, not protocol: the marmot-agents design page
[subagents as threads](https://github.com/marmot-protocol/marmot-agents/blob/master/docs/design/subagents.md) has the
running bar and the rest.

## Retention, deletion and convergence

Agent events are app payloads like any other: [convergence](../protocol-core/convergence.md),
[durability](../protocol-core/durability.md) and [message retention](../app-components/message-retention-v1.md)
govern them.

- **Convergence.** If convergence withdraws an item's first event or a version, a client recomputes the item's current
  version from what remains, as if the withdrawn event had never arrived **[Inferred: no source says this for items;
  it follows from those documents]**. A withdrawn request is no longer pending.
- **Retention.** An item's first event and its versions expire under the group's retention, each by its own time. A
  client that has removed an item's first event under retention does not show the item again from a later version.
  An agent that can no longer edit an expired item sends its next version as a new item.
- **Deletion.** An item, or a version, deleted by its author is handled as the author's deletion of any message is;
  a deleted version is not accepted. An agent does not delete its items in normal work.

## Security and privacy considerations

- **Everything an agent sends is group content.** Tool calls, their output, file paths, diffs and the harness's native
  messages go to every member and stay in their history. An owner who adds an agent to a group shares that. The
  reference agent sends a chat other than the owner's two-person chat, unless the owner lists it, only `turn`, the
  agent's own words, `approval`, `question`, `error`, `session`, and notices that settle a request, and no `native`.
  That is the agent's policy, not a protocol rule.
- **Rights are the agent's rule, kept on the owner's machine.** The agent checks every prompt and request against
  them. Other members' clients cannot enforce or verify them; `rights` in a session item is the agent's statement,
  for display. A client MUST NOT grant or deny anything on its strength.
- **A session item reveals the owner.** With the default rights, `rights` names the owner's key to every member of
  the chat; `owner` does too, when the owner turns it on. Both are inside the group's encryption, never in a public
  profile.
- **Nothing proves that a member is an agent, or whose it is.** This is a known limit of this version. Anyone can
  send these kinds: a member that sends a kind `1201` or a session item is not thereby an agent, a session item's
  `owner` or `rights` proves nothing about who runs it, and an approval item from a member proves nothing about a
  harness. MLS authenticates the author's account, and only that author's versions change an item; nothing more is
  proven. A client SHOULD show an item's author as it shows a message's, MAY mark a member that sent a session item
  as an agent, and MUST NOT grant or deny anything on the strength of a session item. How an owner's own client could
  know its owner's agents, for example by pairing with each at setup and keeping their keys in a private list synced
  only to the owner's devices, is left to a later version.
- **Secret answers.** A question marked `secret` can be answered from the chat only in a two-person chat, because a
  request is readable by every member, and an agent that refuses it has already let every member read it. A client
  SHOULD NOT offer to answer one in a chat of more than two members, and says to answer at the agent instead; the
  agent refuses such an answer whatever the client does. The agent's items never
  repeat a secret answer, and stop carrying `native` once the question is no longer waiting.
- **Approvals cannot be typed.** "Yes" in the chat is a prompt, never an approval. An agent whose harness accepts typed
  commands that approve or widen what it may do treats those messages as needing the right to approve.
- **A member who joined late cannot tell an item's author** from its versions alone, since they never hold its first
  event. Any member can send a readable edit naming an item, so a client keeps each author's versions apart
  ([A member who joined after the item began](#a-member-who-joined-after-the-item-began)); otherwise one member could
  hide a real approval or question from late joiners, or show a false one in its place.
- **Requests are not authenticated beyond MLS.** A request is as authentic as its author's group membership. An agent
  ignores requests named for another agent, and acts on each request once.

## Migration

- **Kinds `1201` and `1202` in the old connector shape** are replaced, not kept beside the new one. An old connector
  still running sends the old shape for a while; clients show it as an unreadable item.
- **The temporary kinds** marmot-agents used before MDK took this shape were never released.
- **Kind `1200`** stays retired; this feature does not use it.
- **Clients built before this feature** show each item once, in its first state, and ignore its versions; they show
  the agent's words normally and cannot approve, interrupt or change settings.

## Examples

[agents-in-chats-examples.json](./agents-in-chats-examples.json) holds one event for each shape above: every item type, first events and versions,
the session item on joining and in a session, every action, a settling version, `refused` notices, the agent's words,
items in a thread, and the unreadable shapes. Every id and key in it is a synthetic placeholder. Two of them, as they
are placed inside the MLS application message (id, pubkey and created_at as the envelope sets them):

```json
{"kind": 1201,
 "tags": [["v","1"],["state","waiting"],["title","Allow this command?"],["harness","codex"],
          ["item_id","approval-1"],["seq","4"],
          ["fields","{\"type\":\"approval\",\"body\":{\"subject\":\"call-1\",\"choices\":[{\"id\":\"allow_once\",\"label\":\"Allow once\",\"effect\":\"allow\"},{\"id\":\"deny\",\"label\":\"Deny\",\"effect\":\"deny\"}]}}"],
          ["session","sess-1"],["turn","turn-1"]],
 "content": "python3 greet.py"}
```

```json
{"kind": 1202,
 "tags": [["p","<agent account key>"],["details","{\"action\":\"choice\",\"choice\":\"allow_once\"}"],
          ["e","<the approval's first event id>"]],
 "content": "Allow once"}
```
