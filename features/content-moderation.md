# Group content moderation v1

Status: draft.

Members report a chat message with a category and optional explanation. Reports refer to a particular revision and
cover the whole message, including its attachments and completed agent content. All members can inspect reports,
including reporter identity. Group encryption provides no admin-only confidentiality for this information.

Admins share a review list and either keep the content by dismissing selected reports or remove the entire message.
Keeping content leaves a reviewed indication. New logical reports reopen review unless the message has been removed;
editing alone does not clear reports. Removal closes pending review for all revisions. Admins can also remove unreported
messages. There is no restore or undo flow in this version.

The owning wire and authorization contract is
[application-messages.md](../foundation/application-messages.md#content-reports-and-shared-review-v1).
It defines reports (kind 1984), dismissal labels on reports (kind 1985), and admin removals of messages (kind 4891),
including deduplication, revision references, validation, and unavailable dependencies. Kind 5 is the separate
author-deletion path.
The existing [admin policy](../app-components/admin-policy-v1.md) supplies authority; this feature adds no component.
[Convergence](../protocol-core/convergence.md), [retained history](../protocol-core/retained-history.md), and
[message retention](../app-components/message-retention-v1.md) continue to govern delivered app payloads and content
lifetime.
No transport change is required; these events use normal group messaging.

Clients can activate this optional application behavior without changing group state. Compatible clients display pending,
reviewed, and removed states and can show pending counts without creating chat unread activity or report push notifications.
User gestures, localized labels, and review-screen layout are application choices. Every group member receives the same
report and review events; restricting review actions is an authorization rule, not an information-access boundary.

Older clients do not automatically gain these interpretations. Mixed-client groups require coordinated client updates
before presenting consistent moderation as a group-wide guarantee. This feature does not change membership or prevent
an author from sending a new message after removal.
