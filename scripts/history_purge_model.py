"""Limited executable reference model for history-purge V1.

Inputs assume authenticated MLS actors, valid class-bound signatures and an
already selected candidate branch. This is not MLS, signature verification,
convergence, storage erasure, or a production implementation.
"""

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Purge:
    request_parent: int
    members: frozenset[str]
    admins: frozenset[str]
    proposer: str
    created_at: int = 100
    expires_at: int = 200
    request_id: str = "request"
    yes: set[str] = field(default_factory=set)
    terminal: str | None = None
    activation: int | None = None
    authorization_parent: int | None = None
    selected: bool = True
    cleaned: bool = False
    emitted: dict[str, str] = field(default_factory=dict)
    receipts: dict[str, set[str]] = field(default_factory=dict)
    opened: bool = False
    closure_obligation: bool = False
    attempt_by: int | None = None

    def __post_init__(self):
        if not 0 <= self.request_parent < 2**64 - 1:
            raise ValueError("opening epoch overflows")
        if not self.members or self.proposer not in self.members or not self.admins <= self.members:
            raise ValueError("invalid cohort")
        if not 1 <= self.created_at < self.expires_at <= 2**53 - 1:
            raise ValueError("invalid proof interval")
        if self.expires_at - self.created_at > 604800:
            raise ValueError("response interval exceeds seven days")

    def open(self, actor, candidate_parent=None, capable=True, proposals=None, proposal_sender=None):
        expected = ["add_request", "add_requirement"]
        if (self.opened or self.terminal is not None or actor not in self.admins or self.yes or not capable
                or (proposal_sender is not None and proposal_sender not in self.admins)
                or (candidate_parent is not None and candidate_parent != self.request_parent)
                or Counter(expected if proposals is None else proposals) != Counter(expected)):
            return False
        self.opened = True
        return True

    def vote(self, actor, timestamp, request_id="request"):
        if (not self.opened or self.terminal is not None or request_id != self.request_id
                or actor not in self.members or actor in self.yes
                or not self.created_at <= timestamp <= self.expires_at):
            return False
        self.yes.add(actor)
        return True

    @staticmethod
    def proposals(terminal, change=None):
        values = ["remove_request", "remove_requirement", "terminal"]
        if terminal == "accepted":
            values.append("retention")
        if terminal == "superseded" and change:
            values.append(change)
        return values

    def finalize(self, terminal, actor, timestamp, parent_epoch, proposals,
                 request_id="request", change=None, change_authorized=False,
                 external=False, receiver_clock=None):
        # receiver_clock deliberately cannot affect canonical validity.
        if (not self.opened or self.terminal is not None or request_id != self.request_id or external
                or not self.selected or parent_epoch < self.request_parent + 1
                or parent_epoch >= 2**64 - 1):
            return False
        in_window = self.created_at <= timestamp <= self.expires_at
        # change_authorized externalizes the normal authority for the causing change;
        # it must be false for a non-admin Add, unrelated list mutation, or no-op supersession.
        rules = {
            "accepted": actor in self.admins and self.yes == set(self.members) and in_window,
            "rejected": actor in self.members and actor not in self.yes and in_window,
            "cancelled": actor == self.proposer and in_window,
            "expired": actor in self.members and 1 <= timestamp <= 2**53 - 1
                and (timestamp >= self.expires_at or self.created_at - timestamp > 300),
            "superseded": actor in self.members and change_authorized and change in
                {"membership", "identity", "capability", "admin", "retention"}
                and (change not in {"admin", "retention"} or actor in self.admins)
                and 1 <= timestamp <= 2**53 - 1,
        }
        if not rules.get(terminal, False):
            return False
        expected = Counter(self.proposals(terminal, change))
        if Counter(proposals) != expected:
            return False
        self.terminal = terminal
        self.closure_obligation = False
        if terminal == "accepted":
            self.authorization_parent = parent_epoch
            self.activation = parent_epoch + 1
        return True

    def schedule_closure(self, now, online=True, usable=True, signing=True):
        if not self.opened or self.terminal is not None:
            return None
        if now >= self.expires_at or self.created_at - now > 300:
            self.closure_obligation = True
        if self.closure_obligation and online and usable and signing and self.attempt_by is None:
            self.attempt_by = now + 60
        return self.attempt_by

    @property
    def boundary(self):
        return self.request_parent + 1

    def suppresses(self, source_epoch, recovery_material=False):
        return (self.selected and self.terminal == "accepted" and not recovery_material
                and source_epoch < self.boundary)

    def deletion_eligible(self, tip, horizon, settled=True):
        return (self.selected and self.terminal == "accepted" and settled
                and tip - self.authorization_parent > horizon)

    def cleanup(self, tip, horizon, settled=True):
        if not self.deletion_eligible(tip, horizon, settled):
            return False
        self.cleaned = True
        return True

    def rollback(self):
        if self.cleaned:
            raise ValueError("model forbids rollback after irreversible cleanup")
        self.selected = False

    def emit_receipt(self, account, outcome, all_stores_complete, coordinated):
        if (self.terminal != "accepted" or not self.selected or account not in self.members
                or account in self.emitted or outcome not in {"applied", "failed"} or not coordinated):
            return False
        if outcome == "applied" and not (self.cleaned and all_stores_complete and coordinated):
            return False
        self.emitted[account] = outcome
        return True

    def observe_receipt(self, account, outcome, canonical=True):
        if (self.terminal != "accepted" or not self.selected or not canonical
                or account not in self.members or outcome not in {"applied", "failed"}):
            return False
        self.receipts.setdefault(account, set()).add(outcome)
        return True

    @property
    def group_complete(self):
        return (self.selected and self.terminal == "accepted"
                and all(self.receipts.get(account) == {"applied"} for account in self.members))


@dataclass
class OpeningPolicy:
    """Local producer policy, deliberately separate from canonical validation."""

    cooldown_until: int = 0
    recovery_pending: bool = False
    selected_terminals: set[str] = field(default_factory=set)

    def can_open(self, now, created, expires, admin):
        return (admin and abs(now - created) <= 300 and now < expires
                and now >= self.cooldown_until and not self.recovery_pending)

    def terminal_selected(self, identity, now):
        if identity not in self.selected_terminals:
            self.selected_terminals.add(identity)
            self.cooldown_until = now + 300

    def lost_cooldown_after_restart(self, now):
        self.cooldown_until = now + 300
