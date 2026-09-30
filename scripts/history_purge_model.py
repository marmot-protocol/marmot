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

    def __post_init__(self):
        if not 0 <= self.request_parent < 2**64 - 1:
            raise ValueError("opening epoch overflows")
        if not self.members or self.proposer not in self.members:
            raise ValueError("invalid cohort")
        if not 1 <= self.created_at < self.expires_at <= 2**53 - 1:
            raise ValueError("invalid proof interval")
        if self.expires_at - self.created_at > 604800:
            raise ValueError("response interval exceeds seven days")

    def vote(self, actor, timestamp, request_id="request"):
        if (self.terminal is not None or request_id != self.request_id
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
        if (self.terminal is not None or request_id != self.request_id or external
                or not self.selected or parent_epoch < self.request_parent + 1
                or parent_epoch >= 2**64 - 1):
            return False
        in_window = self.created_at <= timestamp <= self.expires_at
        rules = {
            "accepted": actor in self.admins and self.yes == set(self.members) and in_window,
            "rejected": actor in self.members and actor not in self.yes and in_window,
            "cancelled": actor == self.proposer and in_window,
            "expired": actor in self.admins and self.expires_at < timestamp <= 2**53 - 1,
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
        if terminal == "accepted":
            self.authorization_parent = parent_epoch
            self.activation = parent_epoch + 1
        return True

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
                or account in self.emitted or outcome not in {"applied", "failed"}):
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
