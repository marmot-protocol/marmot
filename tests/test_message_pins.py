"""Bounded reference fixtures for draft message-pins component bytes and rules.

These fixtures assume authenticated candidate-parent inputs. They do not
implement MLS, branch selection, publication, or runtime durability.
"""

from dataclasses import dataclass
import unittest


@dataclass(frozen=True)
class Pins:
    permission: int
    targets: tuple[bytes, ...] = ()


def decode(data: bytes) -> Pins:
    if len(data) < 2 or data[0] not in (0, 1):
        raise ValueError("invalid permission or incomplete state")
    width = 1 << (data[1] >> 6)
    if len(data) < 1 + width:
        raise ValueError("incomplete length")
    prefix = data[1:1 + width]
    length = int.from_bytes(prefix, "big") & ((1 << (8 * width - 2)) - 1)
    minimum = {1: 0, 2: 64, 4: 16384, 8: 1073741824}[width]
    if length < minimum or length > 2048 or length % 32:
        raise ValueError("invalid vector length")
    body = data[1 + width:]
    if len(body) != length:
        raise ValueError("incomplete vector or trailing bytes")
    targets = tuple(body[i:i + 32] for i in range(0, length, 32))
    if any(a >= b for a, b in zip(targets, targets[1:])):
        raise ValueError("unsorted or duplicate reference")
    return Pins(data[0], targets)


def encode(state: Pins) -> bytes:
    body = b"".join(state.targets)
    if any(len(x) != 32 for x in state.targets):
        raise ValueError("wrong reference width")
    if len(body) < 64:
        prefix = bytes([len(body)])
    elif len(body) <= 2048:
        prefix = (0x4000 | len(body)).to_bytes(2, "big")
    else:
        raise ValueError("pin limit")
    value = bytes([state.permission]) + prefix + body
    decode(value)
    return value


@dataclass(frozen=True)
class Leaf:
    account: str
    supports_pins: bool = True


@dataclass(frozen=True)
class Parent:
    state: Pins | None
    required: bool
    leaves: tuple[Leaf, ...] = (Leaf("admin"), Leaf("member"))
    admins: frozenset[str] = frozenset({"admin"})


def transition(parent, sender, operation, replacement=None, *,
               required=None, leaves=None, inline=True, unrelated_admin_action=False):
    """Only the component contract; caller supplies authenticated MLS facts."""
    member = any(x.account == sender for x in parent.leaves)
    admin = member and sender in parent.admins
    if not member:
        raise PermissionError("not a parent member")
    if unrelated_admin_action and not admin:
        raise PermissionError("member exception does not cover another operation")
    if operation != "none" and not inline:
        raise ValueError("standalone or by-reference proposal")
    next_required = parent.required if required is None else required
    next_leaves = parent.leaves if leaves is None else leaves
    if next_required != parent.required and not admin:
        raise PermissionError("required-component change")
    if operation == "add":
        if parent.state is not None or replacement is None or replacement.targets:
            raise ValueError("activation requires absent entry and empty pins")
        if not admin:
            raise PermissionError("activation")
        state = replacement
    elif operation == "replace":
        if parent.state is None or replacement is None:
            raise ValueError("replacement requires prior state")
        if (replacement.permission != parent.state.permission or
                parent.state.permission == 1) and not admin:
            raise PermissionError("permission or admin-only pins")
        state = replacement
    elif operation == "remove":
        if parent.state is None:
            raise ValueError("remove requires prior state")
        if not admin:
            raise PermissionError("removal")
        state = None
    elif operation == "none":
        state = parent.state
    else:
        raise ValueError("unknown operation")
    if (state is not None) != next_required:
        raise ValueError("presence/requirement mismatch")
    if state is not None:
        encode(state)
        if not all(x.supports_pins for x in next_leaves):
            raise ValueError("unsupported resulting leaf")
    return Parent(state, next_required, next_leaves, parent.admins)


def prepare_target_action(state, target, pin):
    targets = set(state.targets)
    if pin:
        targets.add(target)
    else:
        targets.discard(target)
    result = Pins(state.permission, tuple(sorted(targets)))
    encode(result)
    return result


A = bytes.fromhex("11" * 32)
B = bytes.fromhex("22" * 32)


class EncodingFixtures(unittest.TestCase):
    def test_fixed_vectors(self):
        vectors = [
            ("0000", Pins(0)),
            ("0100", Pins(1)),
            ("0020" + "11" * 32, Pins(0, (A,))),
            ("014040" + "11" * 32 + "22" * 32, Pins(1, (A, B))),
        ]
        for value, expected in vectors:
            with self.subTest(value=value):
                self.assertEqual(decode(bytes.fromhex(value)), expected)
                self.assertEqual(encode(expected).hex(), value)

    def test_malformed_vectors(self):
        values = ["", "00", "0200", "004000", "000111", "0000ff",
                  "0080000000", "00c000000000000000", "0020" + "11" * 31,
                  "004040" + "22" * 32 + "11" * 32,
                  "004040" + "11" * 64, "004820" + "11" * (65 * 32)]
        for value in values:
            with self.subTest(value=value[:20]):
                with self.assertRaises(ValueError):
                    decode(bytes.fromhex(value))

    def test_full_bound(self):
        state = Pins(0, tuple(i.to_bytes(32, "big") for i in range(64)))
        value = encode(state)
        self.assertEqual(value[:3], bytes.fromhex("004800"))
        self.assertEqual(len(value), 2051)
        self.assertEqual(decode(value), state)
        with self.assertRaises(ValueError):
            prepare_target_action(state, (64).to_bytes(32, "big"), True)

    def test_exhaustive_defined_counts_and_permissions(self):
        for permission in (0, 1):
            for count in range(65):
                state = Pins(permission, tuple(i.to_bytes(32, "big") for i in range(count)))
                self.assertEqual(decode(encode(state)), state)


class AuthorizationFixtures(unittest.TestCase):
    def test_member_can_pin_and_unpin_another_members_reference(self):
        prior = Parent(Pins(0, (A,)), True)
        result = transition(prior, "member", "replace", Pins(0, (B,)))
        self.assertEqual(result.state, Pins(0, (B,)))

    def test_admins_mode_and_policy_changes(self):
        for before, after in [(Pins(1), Pins(1, (A,))), (Pins(0), Pins(1)),
                              (Pins(1), Pins(0))]:
            with self.assertRaises(PermissionError):
                transition(Parent(before, True), "member", "replace", after)
            self.assertEqual(transition(Parent(before, True), "admin", "replace", after).state,
                             after)

    def test_removed_or_nonmember_sender_has_no_authority(self):
        prior = Parent(Pins(0), True, (Leaf("admin"),))
        with self.assertRaises(PermissionError):
            transition(prior, "member", "replace", Pins(0, (A,)))

    def test_parent_authority_cannot_be_granted_by_resulting_promotion(self):
        prior = Parent(Pins(1), True)
        with self.assertRaises(PermissionError):
            transition(prior, "member", "replace", Pins(1, (A,)))
        # Authority attaches to the supplied authenticated parent, not a later admin list.
        prior_admin = Parent(Pins(1), True, admins=frozenset({"admin", "member"}))
        self.assertEqual(transition(prior_admin, "member", "replace", Pins(1, (A,))).state,
                         Pins(1, (A,)))

    def test_member_exception_does_not_authorize_unrelated_actions(self):
        with self.assertRaises(PermissionError):
            transition(Parent(Pins(0), True), "member", "replace", Pins(0, (A,)),
                       unrelated_admin_action=True)

    def test_standalone_and_by_reference_operations_are_rejected(self):
        with self.assertRaises(ValueError):
            transition(Parent(Pins(0), True), "admin", "replace", Pins(0, (A,)), inline=False)

    def test_authorized_noop_preserves_state(self):
        prior = Parent(Pins(0, (A,)), True)
        self.assertEqual(transition(prior, "member", "replace", prior.state), prior)
        with self.assertRaises(PermissionError):
            transition(Parent(Pins(1), True), "member", "replace", Pins(1))


class PresenceAndActionFixtures(unittest.TestCase):
    def test_activation_is_empty_admin_authorized_and_required(self):
        prior = Parent(None, False)
        self.assertEqual(transition(prior, "admin", "add", Pins(0), required=True).state, Pins(0))
        with self.assertRaises(PermissionError):
            transition(prior, "member", "add", Pins(0), required=True)
        with self.assertRaises(ValueError):
            transition(prior, "admin", "add", Pins(0, (A,)), required=True)
        with self.assertRaises(ValueError):
            transition(prior, "admin", "add", Pins(0))

    def test_every_resulting_leaf_must_support_feature(self):
        leaves = (Leaf("admin"), Leaf("member"), Leaf("member", False))
        with self.assertRaises(ValueError):
            transition(Parent(None, False), "admin", "add", Pins(0), required=True, leaves=leaves)
        with self.assertRaises(ValueError):
            transition(Parent(Pins(0), True), "admin", "none", leaves=leaves)

    def test_requirement_cannot_be_dropped_with_entry_present(self):
        with self.assertRaises(ValueError):
            transition(Parent(Pins(0), True), "admin", "none", required=False)
        with self.assertRaises(ValueError):
            transition(Parent(None, False), "admin", "none", required=True)

    def test_removal_and_reactivation(self):
        prior = Parent(Pins(0, (A, B)), True)
        with self.assertRaises(PermissionError):
            transition(prior, "member", "remove", required=False)
        with self.assertRaises(ValueError):
            transition(prior, "admin", "remove")
        removed = transition(prior, "admin", "remove", required=False)
        self.assertIsNone(removed.state)
        self.assertEqual(transition(removed, "admin", "add", Pins(0), required=True).state, Pins(0))

    def test_unknown_target_does_not_change_commit_validity(self):
        # No message availability, kind, expiry or local clock is an input to validation.
        arbitrary_id = bytes.fromhex("ff" * 32)
        result = transition(Parent(Pins(0), True), "member", "replace", Pins(0, (arbitrary_id,)))
        self.assertEqual(result.state.targets, (arbitrary_id,))

    def test_rebased_action_preserves_intervening_unrelated_pins(self):
        selected = Pins(0, (B,))
        self.assertEqual(prepare_target_action(selected, A, True), Pins(0, (A, B)))
        self.assertEqual(prepare_target_action(Pins(0, (A, B)), A, False), Pins(0, (B,)))

    def test_repeated_pin_and_unpin_are_locally_satisfied(self):
        selected = Pins(0, (A,))
        self.assertEqual(prepare_target_action(selected, A, True), selected)
        self.assertEqual(prepare_target_action(selected, B, False), selected)


if __name__ == "__main__":
    unittest.main()
