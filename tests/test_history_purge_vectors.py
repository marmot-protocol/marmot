"""Golden encoding/hash fixtures and malformed-byte rejection, not cryptography."""

import copy
import json
from pathlib import Path
import unittest

from scripts import history_purge_vectors as wire

FIXTURE = json.loads((Path(__file__).parent / "vectors/history-purge-v1.json").read_text())


class EncodingTest(unittest.TestCase):
    def test_fixed_golden_bytes_and_identity_preimages(self):
        self.assertEqual(wire.identities(FIXTURE["request"], FIXTURE["leaves"], FIXTURE["proof"]),
                         FIXTURE["expected"])
        core = bytes.fromhex(FIXTURE["expected"]["request_core_bytes"])
        self.assertEqual(wire.decode_request_core(core), FIXTURE["request"])
        self.assertEqual(len(core), 216)
        self.assertEqual(len(bytes.fromhex(FIXTURE["expected"]["proof_bytes"])), 104)
        self.assertEqual(len(bytes.fromhex(FIXTURE["expected"]["finalization_bytes"])), 137)

    def test_shortest_quic_prefixes_at_boundaries(self):
        cases = {0: "00", 63: "3f", 64: "4040", 16383: "7fff", 16384: "80004000",
                 2**30 - 1: "bfffffff", 2**30: "c000000040000000", 2**62-1: "ffffffffffffffff"}
        for value, expected in cases.items():
            self.assertEqual(wire.quic_length(value).hex(), expected)
        for value in (-1, 2**62):
            with self.assertRaises(ValueError):
                wire.quic_length(value)

    def test_noncanonical_truncated_and_trailing_bytes(self):
        core = bytes.fromhex(FIXTURE["expected"]["request_core_bytes"])
        for bad in (b"\x40\x0c" + core[1:], core[:-1], core + b"\x00", b"\x00" + core[13:]):
            with self.assertRaises(ValueError):
                wire.decode_request_core(bad)
        for length in (1, 12, 50, 117, 184):
            with self.assertRaises(ValueError):
                wire.decode_request_core(core[:length])

    def test_request_structural_bounds(self):
        changes = (
            {"parent_epoch": 2**64-1}, {"created_at": 0}, {"expires_at": 2**53},
            {"expires_at": FIXTURE["request"]["created_at"]},
            {"expires_at": FIXTURE["request"]["created_at"] + 604801},
            {"prior_retention_present": 2}, {"prior_retention_secs": 1},
            {"members": FIXTURE["request"]["members"][::-1]},
            {"members": [FIXTURE["request"]["members"][0]] * 2}, {"members": []},
            {"proposer_pubkey": "00" * 32}, {"group_id": ""}, {"group_id": "00" * 256},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                wire.encode_request_core({**FIXTURE["request"], **change})

    def test_partial_member_vector_is_rejected(self):
        core = bytes.fromhex(FIXTURE["expected"]["request_core_bytes"])
        offset = 13 + 8 + 32 + 32 + 8 + 8 + 1 + 8 + 8
        self.assertEqual(core[offset:offset+2], b"\x40\x40")
        malformed = core[:offset] + b"\x40\x3f" + core[offset+2:offset+2+63] + core[-32:]
        with self.assertRaises(ValueError):
            wire.decode_request_core(malformed)

    def test_maximum_vectors_and_capability_constraints(self):
        request = copy.deepcopy(FIXTURE["request"])
        request["members"] = [i.to_bytes(32, "big").hex() for i in range(1023)]
        request["members"].append(request["proposer_pubkey"])
        encoded = wire.encode_request_core(request)
        self.assertEqual(wire.decode_request_core(encoded), request)
        with self.assertRaises(ValueError):
            wire.encode_request_core({**request, "members": request["members"] + ["ff" * 32]})
        leaves = [{"leaf_index": i, "account_pubkey": FIXTURE["request"]["proposer_pubkey"],
                   "support": [1, 1, 1]} for i in range(1024)]
        encoded = wire.encode_capabilities(leaves)
        self.assertEqual(encoded[:4], bytes.fromhex("80009c00"))
        self.assertEqual(len(encoded), 39940)
        for bad in ([], leaves + [leaves[-1]], FIXTURE["leaves"][::-1],
                    [FIXTURE["leaves"][0]] * 2,
                    [{**FIXTURE["leaves"][0], "support": [1, 2, 1]}]):
            with self.assertRaises(ValueError):
                wire.encode_capabilities(bad)

    def test_proof_bounds_and_unknown_enums(self):
        for change in ({"created_at": 0}, {"created_at": 2**53}, {"signature": "00" * 63}):
            with self.assertRaises(ValueError):
                wire.encode_proof({**FIXTURE["proof"], **change})
        for change in ({"terminal": 0}, {"terminal": 6}, {"decision": 3}, {"outcome": "unknown"}):
            with self.assertRaises(ValueError):
                wire.identities(FIXTURE["request"], FIXTURE["leaves"], FIXTURE["proof"], **change)


if __name__ == "__main__":
    unittest.main()
