"""Concrete authorization and deletion regressions for the limited model."""

import copy
import unittest

from scripts.history_purge_model import Purge


def unanimous():
    state = Purge(10, frozenset({"alice", "bob"}), frozenset({"alice"}), "bob")
    assert state.vote("alice", 110)
    assert state.vote("bob", 120)
    return state


def accepted(parent=13, clock=130):
    state = unanimous()
    assert state.finalize("accepted", "alice", 130, parent, Purge.proposals("accepted"),
                          receiver_clock=clock)
    return state


class PurgeSafetyTest(unittest.TestCase):
    def test_request_parent_leaves_horizon_before_authorization_parent(self):
        state = accepted()
        self.assertFalse(state.cleanup(15, 2))
        self.assertFalse(state.cleanup(16, 2, settled=False))
        self.assertTrue(state.cleanup(16, 2))

    def test_delayed_backdated_acceptance_cannot_expand_target(self):
        for clock in (0, 150, 10**10):
            state = accepted(parent=1000, clock=clock)
            self.assertEqual(state.boundary, 11)
            self.assertTrue(state.suppresses(10))
            for epoch in (11, 12, 1000, 1001):
                self.assertFalse(state.suppresses(epoch))
            self.assertFalse(state.suppresses(10, recovery_material=True))

    def test_restart_rollback_and_late_delivery(self):
        state = copy.deepcopy(accepted())
        self.assertTrue(state.suppresses(9))
        self.assertFalse(state.cleanup(15, 2))
        state.rollback()
        self.assertFalse(state.suppresses(9))
        self.assertFalse(state.cleanup(100, 2))
        state = accepted()
        self.assertTrue(state.cleanup(16, 2))
        state = copy.deepcopy(state)
        self.assertTrue(state.cleanup(17, 2))
        self.assertTrue(state.suppresses(9))

    def test_unanimity_membership_and_single_decisions(self):
        state = Purge(10, frozenset({"alice", "bob"}), frozenset({"alice"}), "bob")
        self.assertFalse(state.vote("outsider", 110))
        self.assertFalse(state.vote("alice", 201))
        self.assertTrue(state.vote("alice", 110))
        self.assertFalse(state.vote("alice", 111))
        self.assertFalse(state.finalize("accepted", "alice", 130, 13, Purge.proposals("accepted")))
        self.assertFalse(state.finalize("rejected", "alice", 130, 13, Purge.proposals("rejected")))
        self.assertTrue(state.finalize("rejected", "bob", 130, 13, Purge.proposals("rejected")))
        self.assertFalse(state.vote("bob", 140))

    def test_every_terminal_actor_and_exact_proposal_set(self):
        cases = [
            ("accepted", "alice", 130, None),
            ("rejected", "bob", 130, None),
            ("cancelled", "bob", 130, None),
            ("expired", "alice", 201, None),
            ("superseded", "alice", 130, "retention"),
        ]
        for terminal, actor, timestamp, change in cases:
            proposals = Purge.proposals(terminal, change)
            for malformed in ([*proposals, "unrelated_requirement"],
                              *[proposals[:i] + proposals[i+1:] for i in range(len(proposals))],
                              *[[*proposals, p] for p in proposals]):
                state = unanimous()
                if terminal == "rejected":
                    state.yes.remove("bob")
                self.assertFalse(state.finalize(terminal, actor, timestamp, 13, malformed,
                                               change=change, change_authorized=True))
            state = unanimous()
            if terminal == "rejected":
                state.yes.remove("bob")
            self.assertFalse(state.finalize(terminal, "outsider", timestamp, 13, proposals,
                                           change=change, change_authorized=True))
            self.assertTrue(state.finalize(terminal, actor, timestamp, 13, proposals,
                                          change=change, change_authorized=True))
            self.assertFalse(state.finalize(terminal, actor, timestamp, 13, proposals,
                                           change=change, change_authorized=True))

    def test_external_commit_and_wrong_request_cannot_close_open_state(self):
        for options in ({"external": True}, {"request_id": "other"}):
            state = unanimous()
            self.assertFalse(state.finalize("accepted", "alice", 130, 13,
                                           Purge.proposals("accepted"), **options))
            self.assertIsNone(state.terminal)

    def test_active_members_do_not_gain_unrelated_admin_authority(self):
        for terminal, actor, timestamp, change in (
            ("accepted", "bob", 130, None),
            ("cancelled", "alice", 130, None),
            ("superseded", "bob", 130, "retention"),
            ("superseded", "bob", 130, "admin"),
        ):
            self.assertFalse(unanimous().finalize(
                terminal, actor, timestamp, 13, Purge.proposals(terminal, change),
                change=change, change_authorized=True))
        self.assertFalse(unanimous().finalize(
            "superseded", "alice", 130, 13, Purge.proposals("superseded", "retention"),
            change="retention", change_authorized=False))

    def test_expiry_without_online_admin_can_unblock_recovery(self):
        state = unanimous()
        state.admins = frozenset()
        self.assertFalse(state.finalize("expired", "bob", 200, 13, Purge.proposals("expired")))
        self.assertFalse(state.finalize("expired", "outsider", 201, 13, Purge.proposals("expired")))
        self.assertTrue(state.finalize("expired", "bob", 201, 13, Purge.proposals("expired")))
        self.assertFalse(state.suppresses(9))
        self.assertFalse(state.cleanup(100, 2))

    def test_selected_terminal_race_never_uses_receipt_order(self):
        for first, second in (("accepted", "cancelled"), ("cancelled", "accepted")):
            state = unanimous()
            actor = "alice" if first == "accepted" else "bob"
            self.assertTrue(state.finalize(first, actor, 130, 13, Purge.proposals(first)))
            actor = "alice" if second == "accepted" else "bob"
            self.assertFalse(state.finalize(second, actor, 130, 14, Purge.proposals(second)))
            self.assertEqual(state.terminal, first)

    def test_receipts_fail_closed_and_conflicts_are_order_independent(self):
        state = accepted()
        self.assertFalse(state.emit_receipt("alice", "applied", True, True))
        state.cleanup(16, 2)
        self.assertFalse(state.emit_receipt("alice", "applied", False, True))
        self.assertFalse(state.emit_receipt("alice", "applied", True, False))
        self.assertTrue(state.emit_receipt("alice", "applied", True, True))
        self.assertFalse(state.emit_receipt("alice", "failed", True, True))
        self.assertFalse(state.observe_receipt("alice", "applied", canonical=False))
        for order in (("applied", "failed"), ("failed", "applied")):
            state = accepted()
            state.observe_receipt("bob", "applied")
            for outcome in order:
                state.observe_receipt("alice", outcome)
                state.observe_receipt("alice", outcome)
            self.assertFalse(state.group_complete)
        state = accepted()
        state.observe_receipt("alice", "applied")
        self.assertFalse(state.group_complete)
        state.observe_receipt("bob", "applied")
        self.assertTrue(state.group_complete)

    def test_request_bounds(self):
        for parent, created, expires in ((2**64-1, 100, 200), (10, 100, 604901),
                                         (10, 0, 200), (10, 100, 100)):
            with self.assertRaises(ValueError):
                Purge(parent, frozenset({"alice"}), frozenset({"alice"}), "alice",
                      created_at=created, expires_at=expires)


if __name__ == "__main__":
    unittest.main()
