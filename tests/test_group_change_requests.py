"""Bounded encoding/projection fixtures, not an MLS or component implementation.

Source-authority and Commit-matching facts are supplied inputs. The model checks
their use, not their cryptographic derivation. Component decoding, account-key
validity and package discovery are outside this reference model.
"""
import base64
import hashlib
import itertools
import json
from pathlib import Path
import re
import unittest


HEX = re.compile(r"[0-9a-f]{64}\Z")
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
PUBKEY = "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
NONCE = bytes(range(32)).hex()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def require(ok):
    if not ok:
        raise ValueError("invalid fixture")


def text(value, limit):
    require(isinstance(value, str))
    require(len(value.encode("utf-8")) <= limit)


def hex64(value):
    require(isinstance(value, str) and HEX.fullmatch(value))


def content_shape(raw):
    require(len(raw.encode("utf-8")) <= 65536)
    value = json.loads(raw, object_pairs_hook=unique_object)
    require(isinstance(value, dict))
    require(type(value.get("v")) is int and value["v"] == 1)
    action = value.get("action")
    if action == "request":
        require(set(value) == {"v", "action", "nonce", "operation", "data"})
        hex64(value["nonce"])
        data = value["data"]
        require(isinstance(data, dict))
        operation = value["operation"]
        if operation == "invite_account":
            require(set(data) == {"pubkey"})
            hex64(data["pubkey"])
            # Mathematical key validity is the foundation identity check.
        else:
            require(set(data) == {"expected", "value"})
            require(data["value"] is not None)
            if operation in {"set_name", "set_description"}:
                limit = 256 if operation == "set_name" else 4096
                text(data["value"], limit)
                if data["expected"] is not None:
                    text(data["expected"], limit)
            elif operation == "set_retention":
                for item in (data["expected"], data["value"]):
                    if item is not None:
                        require(isinstance(item, str) and DECIMAL.fullmatch(item))
                        require(int(item) <= 2**64 - 1)
            elif operation in {"set_avatar_url", "set_blossom_image"}:
                for item in (data["expected"], data["value"]):
                    if item is not None:
                        require(isinstance(item, str) and item != "")
                        decoded = base64.b64decode(item, validate=True)
                        require(len(decoded) <= 4096)
                        require(base64.b64encode(decoded).decode("ascii") == item)
                        # Owning component validation is an external input.
            else:
                raise ValueError("unknown operation")
    elif action == "rejected":
        require(set(value) == {"v", "action", "request", "reason"})
        hex64(value["request"])
        text(value["reason"], 1024)
    elif action == "withdrawn":
        require(set(value) == {"v", "action", "request"})
        hex64(value["request"])
    elif action == "applied":
        require(set(value) == {"v", "action", "request", "commit"})
        hex64(value["request"])
        hex64(value["commit"])
    else:
        raise ValueError("unknown action")
    require(raw == canonical(value))
    return value


def request(operation="invite_account", data=None, nonce=NONCE):
    return {"v": 1, "action": "request", "nonce": nonce, "operation": operation,
            "data": {"pubkey": PUBKEY} if data is None else data}


def event_id(content, created_at=1700000000):
    # NIP-01 fixture with no unsupported numeric or string values.
    preimage = json.dumps([0, PUBKEY, created_at, 458, [], content],
                          ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def evidence(action, **changes):
    result = {"action": action, "request": "request-a", "group": "group-a", "sender": "admin-account",
              "source_admin": True, "selected_branch": True, "request_seen": True,
              "commit_matches": True, "commit_accepted": True, "receipt_causal": True}
    result.update(changes)
    return result


def project(records, target="request-a", group="group-a", requester="member-account", committer="admin-account"):
    effects = set()
    for item in records:
        if (item["request"] != target or item["group"] != group
                or not item["selected_branch"] or not item["request_seen"]):
            continue
        action = item["action"]
        if action == "applied":
            if (item["source_admin"] and item["sender"] == committer
                    and item["commit_matches"] and item["commit_accepted"] and item["receipt_causal"]):
                effects.add("matching_applied")
        elif action == "rejected" and item["source_admin"]:
            effects.add("rejected")
        elif action == "withdrawn" and item["sender"] == requester:
            effects.add("withdrawn")
    for effect, status in (("matching_applied", "Applied"),
                           ("withdrawn", "Withdrawn"), ("rejected", "Rejected")):
        if effect in effects:
            return status
    return "Pending"


class Fixtures(unittest.TestCase):
    def test_document_examples_are_canonical_shapes(self):
        doc = Path(__file__).resolve().parents[1] / "features/group-change-requests.md"
        examples = re.findall(r"```json\n(.*?)\n```", doc.read_text(), re.S)
        self.assertEqual(len(examples), 4)
        for example in examples:
            content_shape(example)

    def test_invitation_has_only_account_data(self):
        for extra in ("key_package", "key_package_ref", "publication", "relay", "device"):
            value = request()
            value["data"][extra] = "ignored"
            with self.assertRaises(ValueError):
                content_shape(canonical(value))

    def test_version_and_unknown_actions(self):
        for field, item in (("v", True), ("v", 2), ("action", "approved"),
                            ("operation", "promote_admin")):
            value = request()
            value[field] = item
            with self.assertRaises(ValueError):
                content_shape(canonical(value))

    def test_duplicate_keys_and_noncanonical_content(self):
        for raw in ('{"v":1,"v":1}', json.dumps(request()),
                    canonical(request()).replace('"pubkey":', '"pubkey": ')):
            with self.assertRaises(ValueError):
                content_shape(raw)

    def test_unicode_bounds_and_no_normalization(self):
        good = request("set_name", {"expected": "e\u0301", "value": "é" * 128})
        self.assertNotEqual(good["data"]["expected"], "é")
        content_shape(canonical(good))
        good["data"]["value"] += "é"
        with self.assertRaises(ValueError):
            content_shape(canonical(good))

    def test_non_scalar_strings_are_invalid(self):
        # UnicodeEncodeError is a ValueError; escaped and raw surrogates both fail.
        value = request("set_name", {"expected": "", "value": "\ud800"})
        for raw in (json.dumps(value, sort_keys=True, separators=(",", ":")), canonical(value)):
            with self.assertRaises(ValueError):
                content_shape(raw)

    def test_component_limit_alignment(self):
        root = Path(__file__).resolve().parents[1]
        profile = (root / "app-components/group-profile-v1.md").read_text()
        retention = (root / "app-components/message-retention-v1.md").read_text()
        self.assertIn("opaque name<0..256>", profile)
        self.assertIn("opaque description<0..4096>", profile)
        self.assertIn("uint64 disappearing_message_secs", retention)
        for filename, expected in (("group-avatar-url-v1.md", 2566),
                                   ("group-blossom-image-v1.md", 242)):
            source = (root / "app-components" / filename).read_text()
            schema = re.search(r"```text\n(.*?)\n```", source, re.S).group(1)
            limits = [int(n) for n in re.findall(r"opaque \w+<0\.\.(\d+)>", schema)]
            maximum = sum(n + (1 if n <= 63 else 2 if n <= 16383 else 4) for n in limits)
            self.assertEqual(maximum, expected)
            self.assertLessEqual(maximum, 4096)

    def test_description_named_escapes_fit_envelope(self):
        content_shape(canonical(request("set_description",
                                        {"expected": "\n" * 4096, "value": "\t" * 4096})))

    def test_existing_control_characters_round_trip(self):
        for operation, limit in (("set_name", 256), ("set_description", 4096)):
            value = request(operation, {"expected": "\0" * limit, "value": "\x01" * limit})
            self.assertEqual(content_shape(canonical(value)), value)

    def test_decimal_full_range_and_null(self):
        for old in (None, "0"):
            content_shape(canonical(request("set_retention",
                                            {"expected": old, "value": str(2**64 - 1)})))
        for bad in ("00", "+1", " 1", "1.0", str(2**64), 1, None):
            with self.assertRaises(ValueError):
                content_shape(canonical(request("set_retention", {"expected": "0", "value": bad})))

    def test_absent_differs_from_present_empty(self):
        absent = request("set_name", {"expected": None, "value": "club"})
        empty = request("set_name", {"expected": "", "value": "club"})
        self.assertNotEqual(event_id(canonical(absent)), event_id(canonical(empty)))

    def test_image_base64_encoding_not_component_validity(self):
        # URL-avatar empty state: three zero-length vectors.
        content_shape(canonical(request("set_avatar_url", {"expected": None, "value": "AAAA"})))
        for bad in ("", "AA", "AB==", "AA==\n", "_A=="):
            with self.assertRaises(ValueError):
                content_shape(canonical(request("set_avatar_url", {"expected": None, "value": bad})))

    def test_same_second_intents_and_retries(self):
        first = canonical(request())
        second = canonical(request(nonce="f" * 64))
        self.assertEqual(event_id(first), event_id(first))
        self.assertNotEqual(event_id(first), event_id(second))

    def test_fixed_app_event_id(self):
        self.assertEqual(event_id(canonical(request())),
                         "e5ab295cece5e1a951e8d0c591f42f4a0666c26f9f7f7d34d9e09fe21ab36d31")

    def test_delivery_order_does_not_select_status(self):
        effects = [evidence("applied"), evidence("rejected"),
                   evidence("withdrawn", sender="member-account")]
        for order in itertools.permutations(effects):
            self.assertEqual(project(order), "Applied")

    def test_unresolved_or_invalid_authority_is_not_applied(self):
        for field, value in (("request", "request-b"), ("group", "group-b"), ("sender", "another-admin"),
                             ("source_admin", False), ("selected_branch", False),
                             ("request_seen", False), ("commit_matches", False),
                             ("commit_accepted", False), ("receipt_causal", False)):
            self.assertEqual(project([evidence("applied", **{field: value})]), "Pending", field)
        self.assertEqual(project([evidence("rejected", source_admin=False)]), "Pending")
        self.assertEqual(project([evidence("withdrawn", sender="another-member")]), "Pending")
        self.assertEqual(project([evidence("rejected"),
                                  evidence("withdrawn", sender="member-account")]), "Withdrawn")

    def test_two_requests_have_independent_status(self):
        records = [evidence("applied", request="request-a"),
                   evidence("rejected", request="request-b")]
        self.assertEqual(project(records, target="request-a"), "Applied")
        self.assertEqual(project(records, target="request-b"), "Rejected")
        self.assertEqual(project(records, target="request-c"), "Pending")

    def test_reorg_withdraws_only_supported_effects(self):
        effects = [evidence("applied"), evidence("rejected")]
        self.assertEqual(project(effects), "Applied")
        effects[0]["commit_accepted"] = False
        self.assertEqual(project(effects), "Rejected")
        # Restart from the same retained facts produces the same view.
        self.assertEqual(project(json.loads(json.dumps(effects))), "Rejected")


if __name__ == "__main__":
    unittest.main()
