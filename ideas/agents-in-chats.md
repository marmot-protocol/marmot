# Agents in chats

Status: idea (non-normative). Nothing here is part of the Marmot protocol. See [README.md](./README.md).

This idea covers working with an AI agent through a Marmot chat: asking it to do something, watching what it does,
approving what it asks to do, and steering it, all from a phone. It describes the experience and the direction we have
agreed on. The protocol details come later, surface by surface.

The goal is that a person can do from a chat what they could do sitting at the agent's terminal, and that a group can
share one agent.

The design work behind this page is in the
[marmot-agents](https://github.com/marmot-protocol/marmot-agents) repository: every decision with its reason
([decisions](https://github.com/marmot-protocol/marmot-agents/blob/master/docs/decisions.md)), and 123 recorded
sessions of four agent programs that the design was checked against. This page is the short version, for feedback.

## At a glance

- **An agent is an ordinary member with its own account.** It joins a chat like anyone else. Nothing about the group
  changes.
- **What the agent says is an ordinary chat message.** Every Marmot client already shows it, and replies, reactions,
  search and alerts work with no extra effort.
- **What the agent does is an agent item.** A turn, a tool call, a request for permission, a question, a plan: each is
  one item, with a type and a state. All of them travel as one new kind of app event.
- **An item changes by being edited.** A tool call is sent when it starts and edited when it finishes, using the edit
  mechanism Marmot already has. The chat shows one row that updates.
- **People answer and steer with one more kind of event.** "Allow once", "interrupt" and "switch model" are requests.
  The agent's own reply says what happened.
- **A phone buzzes only when a person is needed or the work is done.** A final answer, a request that is waiting, and a
  failed turn alert. Nothing else does.
- **Every item can be read by any client.** It carries a plain line of text, and beside it the agent program's own
  message, untouched, for a client that wants to show more.
- **Everyone in the chat sees everything the agent does.** The owner decides who may ask it for things and who may
  approve what it does.

## Words used here

| Term | Meaning |
| --- | --- |
| Agent | An AI program that takes requests in a chat and acts on them: runs commands, edits files, searches, answers. |
| Harness | The program that runs the agent, such as Codex, Claude Code, Hermes or OpenClaw. Each has its own way of reporting what the agent does. |
| Owner | The person who runs the agent on their own machine and decides who may use it. |
| Connector | The program on the owner's machine between the harness and Marmot. It holds the agent's Marmot account and translates in both directions. |
| Turn | One piece of work: from a request until the agent stops. |
| Item | One thing the agent did or asked during a turn, shown as one row in the chat. |
| State | Where an item stands: running, waiting for a person, done, failed, declined or cancelled. |
| Session | The harness's memory of one conversation. A chat has one current session with an agent, and can start a new one. |
| Answer | A person's response to something the agent asked. |
| Control | Something a person does unasked: interrupt, start a new session, change a setting. |

## What this does and does not protect

- **Everything the agent does is group content.** Tool calls, their output and the agent's reasoning go to every member
  and stay in their history. Output from the owner's machine can hold secrets. An owner who adds an agent to a group is
  sharing what it does with that group.
- **Who may use the agent is the owner's rule, kept on the owner's machine.** The owner sets who may prompt the agent
  and, separately, who may approve what it does. Both start as the owner alone. The connector checks every request
  against those rules before the harness sees it. Other members' clients do not enforce them and cannot verify them.
- **An approval counts only as a real answer.** It points at the exact request and comes from someone allowed to give
  it. A "yes" typed in the chat is never an approval, and an answer never reaches the model as a prompt.
- **Some agent programs can be told to stop asking.** Two of the four recorded programs accept a typed command that
  switches approvals off, and one of them accepts it anywhere in a message. The connector has to know those commands
  and refuse them from anyone who may not approve.
- **A secret answer is taken only in a two-person chat.** A harness can mark a question's answer as secret, for
  something like a password. In a group every member could read it, so there the question can only be answered at the
  terminal.
- **The agent's machine is trusted completely.** The connector holds the agent's key and reads every message in every
  chat the agent is in. Compromise of that machine is out of scope.
- **This does not hide that an account is an agent**, or how many agents a group has.

## Scene 1: Alice asks her agent to run the tests

![Alice's phone shows her message, a turn row, a command row and the agent's reply. Her message and the reply travel
as ordinary chat messages. The turn and the command travel as agent items, each sent when it started and edited when it
finished.](agents-in-chats/scene-1-a-turn.svg)

**What Alice sees:** she writes "run the tests" in her chat with the agent. A row appears saying the agent is working,
then a row for the command it ran. The command row fills in its result. The agent's answer arrives as a normal message:
"All 42 tests pass." Her phone alerts her for that message and for nothing before it.

**What happens:**

- Her message is an ordinary chat message. The connector on her laptop receives it, checks that she may prompt this
  agent, and hands it to the harness.
- The harness starts a turn. The connector turns each thing the harness reports into either a chat message or an agent
  item.
- The agent's words go out as chat messages. Each carries a mark naming the turn it belongs to, so an app can group it
  with the rest of the turn.
- Everything else goes out as agent items: here, one for the turn and one for the command.

**Why the agent's words are chat messages:** a client that has never heard of agents still shows the conversation.

There are eleven item types. Each one has the same parts and differs only in its own details:

| Type | What it shows |
| --- | --- |
| Turn | A turn started or ended, what started it, how it ended and what it used |
| Message | Text the agent says to the people in the chat. This is the one sent as a chat message |
| Reasoning | The agent's thinking, when the harness provides it |
| Tool | A tool the agent used: a command, a file edit, a search, and so on |
| Approval | The agent wants permission for one action, with the choices offered |
| Question | The agent asks the person something |
| Plan | The agent's plan or to-do list |
| Task | Work that runs beside a turn or outlives it, such as a background job |
| Notice | Something worth knowing that is not work: the conversation was compacted, a retry, a warning |
| Error | Something failed outside any one item |
| Session | A session with the harness, and what it lets a person set and do (Scene 4) |

## Scene 2: A row changes while she watches

![The agent sends an agent item saying a command is running, then an edit that points at it and says the command
finished. The chat shows one row that changed in place.](agents-in-chats/scene-2-an-edit.svg)

**What Alice sees:** the command row says "Running a command", then becomes "Ran a command" with its result. It stays
where it first appeared. There is never a second row.

**What happens:** the first event of an item is an agent item. To change it, the agent sends an edit that points at
that first event. This is the edit Marmot already has for chat messages, with three additions for agent items:

| Addition | Why |
| --- | --- |
| An edit can target an agent item, and then replaces its details as well as its text | An item's state and details are not in its text. Today an edit replaces text only, and only on a chat message |
| An edit of an agent item carries a version number, and the highest wins | Edits are ordered by a timestamp in whole seconds. A tool can start and finish within one second |
| A client holds an edit whose item has not arrived yet | Today a client can drop it, which would leave an item showing "running" for good |

Each edit carries the whole item again, so a client that missed an earlier edit loses nothing. The item is identified
by the id of its first event, so nothing else is needed to name it. Only the agent that sent an item can edit it,
because edits already require the same author.

**The cost:** an edit means nothing without the event it points at. Someone added to the chat in the middle of a turn
sees nothing of the items that began before they joined. They do see the agent's answer, because that is a chat
message, and every item that starts afterwards. *(Since settled: a member who joined late is shown an item built from
its versions; see [the feature document](../features/agents-in-chats.md#a-member-who-joined-after-the-item-began).)*

## Scene 3: The agent asks permission

![Alice's phone shows an approval card for the command rm -rf build with Allow once and Deny. Pressing Allow once
sends an answer that names the agent and points at the approval item. The agent's machine checks that Alice may
approve and that the approval is still waiting, passes the answer to the harness, and edits the approval item to say
who answered.](agents-in-chats/scene-3-an-approval.svg)

**What Alice sees:** she asks the agent to clean the build folder. Her phone alerts her: the agent wants to run
`rm -rf build`, with the choices its harness offers. She presses **Allow once**. The card shows the press as pending for
a moment, then says "Answered: Allow once, by Alice", and the command runs.

**What happens:**

- The approval is an agent item in the state "waiting". That state is one of the three things that alert a phone.
- Her press sends an answer. It names the agent it is for and points at the approval item.
- The answer changes nothing by itself. The connector checks it, passes it to the harness, and edits the approval item.
  That edit is what every member's app shows.
- If two people answer at once, the first valid answer the agent receives wins. The other person is told it was
  already answered. Only the agent knows which answer the harness took, which is why the agent's reply is the record.
- If the agent's machine is off, the press stays pending and nothing is assumed.

A question works the same way, and can hold several questions, several selections, or free text. An answer is not a
row in the chat, alerts nobody and does not count as unread.

**What a person needs for each action:** the owner hands out two rights, and every action needs one of them.

| Action | Right needed |
| --- | --- |
| Send a request to the agent, or one of the harness's slash commands | Prompt |
| Answer a question | Prompt |
| Interrupt, start a new session, change an ordinary setting | Prompt |
| Answer an approval, including "always" | Approve |
| Change how much the agent may do without asking | Approve |

Someone without the right is told so. Their request does not reach the harness.

## Scene 4: Steering the agent

![The app shows a session sheet with the model, the reasoning effort and the permission mode, an Interrupt button, a
New session button and the harness's slash commands. It draws these from a session item the agent sent. Changing the
model sends a control, and the agent answers by editing the session item.](agents-in-chats/scene-4-controls.svg)

**What Alice sees:** a sheet for the session with this harness: its model, its other settings, a button to interrupt
and one to start a new session. The settings are this harness's own, with its own names and values. She picks another
model and the sheet shows it.

**What happens:**

- Three controls mean the same thing for every harness: **interrupt** stops the running turn, **new session** starts a
  fresh one in this chat, and **set** changes one setting.
- Everything else comes from the harness. The agent sends a session item that lists the settings with their current
  values and the values each accepts, the harness's own actions, and its slash commands. An app draws its controls
  from that list and never checks which harness it is talking to.
- A setting that decides how much the agent may do without asking is marked, and changing it needs the right to
  approve.
- A control is a request like an answer. The agent replies by editing the session item, or with a notice saying why
  nothing happened: not allowed, not supported, nothing to act on.
- A message that starts with a slash is passed to the harness exactly as typed. It is the harness's own command. Marmot
  has no typed commands of its own for agents, so the two can never collide.
- A message sent while a turn is running goes straight to the harness, which does what it does natively: some fold it
  into the turn, some end the turn and start another, some hold it until the turn ends.

**Why no shared list of models and modes:** each harness has its own, and they change with every release. One of the
recorded harnesses listed eight models on one day and ten on the next.

## Scene 5: A shared agent in a group

**What the group sees:** Alice adds her agent to the family chat. Everyone sees what it does, in full. By default only
Alice can ask it for things and only Alice can approve. She can let named people, or everyone, prompt it, and
separately let people approve.

- **The agent answers only when it is addressed.** The current thinking is that in a group this means a mention or a
  reply to it, and that in a two-person chat it always answers.
- **Bob, who may not prompt it, is told so** when he tries. His message is still an ordinary message to the group.
- **An approval is visible to everyone**, and so is who gave it.
- **Each agent program is its own contact.** Codex, Claude Code and Hermes on one laptop are three accounts. A person
  addresses the one they want, and no command is needed to switch between them.

This scene has the most product work still to do. See [Open questions](#open-questions).

## Scene 6: A client that does not know about agents

![Three phones show the same turn. An app that knows about agents shows the turn and the command as rows that updated.
An app on today's library shows each item once in its first state. A client that hides unknown kinds shows only
Alice's message and the agent's reply.](agents-in-chats/scene-6-other-clients.svg)

The conversation always reads normally, because the agent's words are chat messages.

- **A client that shows unknown kinds as plain rows** shows each item once, by its plain text, in its first state. It
  applies edits only to chat messages, so it ignores the edits and nothing appears twice. A tool call stays at
  "running".
- **A client that hides unknown kinds** shows nothing of the agent's activity.
- **Neither can approve, interrupt or change settings.** A person on such a client can still prompt the agent and use
  its slash commands, because those are messages.

## Under the hood

**What an agent item carries.** A plain line of text any client can show. Its type and state. The turn and session it
belongs to. Its position within the turn, as a number, because several items are often produced in one second. The
harness and its version. The type's own details, such as a command and its exit code. And the harness's native
message, unchanged.

**Why both a plain text and the native message.** The plain text and the shared types let any client draw whatever
arrives without knowing the harness. The native message keeps everything the harness said, for a client that wants to
show more for a harness it knows. Nothing is generalised away.

**What is never sent.** Text as it is being written, typing signals and bookkeeping. Depending on the harness they
are between a third and four fifths of what it emits. Items are sent when they start and when they change, not word by
word.

**What an answer or a control carries.** The agent it is for, the item it acts on, which action it is, the details of
the action, and a plain line such as "Allow once".

**Late and repeated requests.** One that points at an item acts only while that item is live. One that points at
nothing, such as "new session", is dropped when it is more than a few minutes old. Each acts at most once.

**Who gets alerted.** The agent's final answer, an approval or question that is waiting, and a turn that failed. A
failed turn arrives as an edit, so it is the one edit that alerts.

**What the connector does.** It is the only part that knows the harness. It checks the owner's rules, turns harness
reports into chat messages, items and edits, numbers them, applies the size limit, and reports the result of every
answer and control. It also closes what the harness leaves open: no recorded harness says clearly that a session is
over, and one that is killed mid-turn says nothing at all.

## Numbers

Checked against 123 recorded sessions of Codex, Claude Code, Hermes and OpenClaw:

| | |
| --- | --- |
| Messages the four harnesses emitted | 15,800 |
| Chat messages, agent items and edits they became | 1,309 |
| Harness messages with no rule | 0 |
| Item types needed | 11 |
| States needed | 6 |

The size of an agent item is at most 64 KB. Tool output is the part that can be large. These are sizes from four days
of one developer's real use of one harness, 16,841 tool outputs; lengths only were measured.

| | Typical | 9 in 10 are under | 99 in 100 are under | Largest |
| --- | --- | --- | --- | --- |
| A tool's output | 0.8 KB | 6 KB | 19 KB | 56 KB |

| Limit | Outputs it would cut |
| --- | --- |
| 16 KB | 1 in 70 |
| 32 KB | 1 in 1,000 |
| 64 KB | None |

When an item would be larger, the native message is left out first, then the output is cut, keeping its start and its
end, and the item says so. An item near the limit reaches a relay about a third larger, so a relay that accepts only
64 KB events will not take it. We accept that and want relays to accept more.

In the same real use a turn averaged about 12 tool calls, 7 pieces of reasoning and 3 or 4 pieces of text. With each
tool call sent once and edited once, that is about 35 events for a turn.

## Open questions

- **How much activity is too much.** About 35 events a turn is a lot of history for every member. A setting for how
  much detail an agent sends, and a single summary row that updates, are both on the table. This needs product work.
- **Sensitive output.** Whether an owner gets a per-chat setting for what is shared, and what the default is.
- **Getting the full output when it was cut.** Fetch it from the agent on request, or attach it as a file. Attachments
  exist only on chat messages today.
- **A file the agent sends**, such as a report or a patch. There is no item for it yet.
- **Several agents in one group.** Every agent in a group reads every message. How they are set up, named and kept
  from answering at once needs product work.
- **Changing the owner's rules from the chat.**
- **Word-by-word text.** This design does not need it. The earlier
  [agent text streams](../features/agent-text-streams-quic.md) feature is retired; any later word-by-word design would
  use new ids.
- **Whose rules win in a gateway.** Hermes and OpenClaw have their own lists of who may speak and who may use
  commands, separate from the owner's rules in the connector.

## Path into the spec

The feature document is [features/agents-in-chats.md](../features/agents-in-chats.md). It takes kinds `1201`
and `1202`, and defines the tags, the version rules and the request shapes this section asks for.

Nothing here assigns an id or defines bytes. When the direction is agreed, the rules would move into these surfaces:

1. **The agent item, and the answer or control.** Two new kinds of app event. The registry in
   [../foundation/registries.md](../foundation/registries.md) already holds two kinds in reserve for agent events;
   whether these take them is for the spec change to decide. Their exact contents need an owning document.
2. **The three additions to edits**, in [../foundation/application-messages.md](../foundation/application-messages.md)
   ("Message edits").
3. **The mark on a chat message naming its turn**, in the same document.
4. **Which events alert**, wherever [push notifications](../features/push-notifications.md) and client behaviour
   decide that.
5. **A feature document** for the flow as a whole, like the other optional features.

Details to pick while writing the spec, rather than product questions:

- the exact tags, and the form of the version number;
- how a client that does not support agent items is expected to treat one;
- the wording of the size limit.

## What this replaces

- **One-shot agent decisions** ([marmot#503](https://github.com/marmot-protocol/marmot/pull/503), an open pull
  request). It specifies approvals and single-choice questions as a strict protocol with its own lifecycle, for
  two-person chats. This idea keeps its rules about who may answer: an answer is tied to the exact request, only
  permitted people count, a bare "yes" never counts, and an answer never reaches the model. It drops the lifecycle,
  which needs an acknowledgement that harnesses do not give, and it covers groups and everything else an agent does.
- **The two agent kinds as the agent text streams feature describes them**, "agent activity/status" and "agent
  operation event". Under this idea one carries every agent item and the other carries answers and controls.
- **The rule in today's connectors that reasoning and tool output are never shown.** The aim here is the opposite: to
  be true to what the agent is doing.
