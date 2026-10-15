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

    def test_signing_templates_bind_request_parent_for_every_proof_kind(self):
        for kind, event in FIXTURE["signing_templates"].items():
            proof = FIXTURE["proof"] if kind != "455" else {**FIXTURE["proof"], "created_at": FIXTURE["request"]["created_at"]}
            self.assertEqual(wire.proof_event(FIXTURE["request"], proof, int(kind)), event)
            self.assertIn(["parent_epoch", "7"], event["tags"])
        self.assertEqual(wire.proof_event(FIXTURE["request"], FIXTURE["proof"], 454, decision="no"),
                         FIXTURE["no_template"])

    def test_full_structures_fixed_bytes_and_decode(self):
        expected = FIXTURE["structures"]
        proof = {**FIXTURE["proof"], "created_at": FIXTURE["request"]["created_at"]}
        request = {"core": FIXTURE["request"], "proposer_proof": proof}
        encoded = wire.encode_request(request)
        self.assertEqual(encoded.hex(), expected["request_bytes"])
        self.assertEqual(wire.decode_request(encoded), request)
        records = [{"decision": 1, "proof": {**FIXTURE["proof"], "signer_pubkey": key}}
                   for key in FIXTURE["request"]["members"]]
        state = {"request": request, "yes_decisions": records}
        encoded = wire.encode_open_state(state)
        self.assertEqual(encoded.hex(), expected["open_state_bytes"])
        self.assertEqual(wire.decode_open_state(encoded), state)
        self.assertEqual(wire.encode_open_state({**state, "yes_decisions": []}).hex(),
                         expected["empty_open_state_bytes"])
        final = bytes.fromhex(FIXTURE["expected"]["finalization_bytes"])
        self.assertEqual(wire.decode_finalization(final),
                         {"request_id": FIXTURE["expected"]["request_id"], "terminal": 1,
                          "authorization": FIXTURE["proof"]})

    def test_full_structure_mutations_reject(self):
        request = bytes.fromhex(FIXTURE["structures"]["request_bytes"])
        opened = bytes.fromhex(FIXTURE["structures"]["open_state_bytes"])
        final = bytes.fromhex(FIXTURE["expected"]["finalization_bytes"])
        for decoder, encoded in ((wire.decode_request, request), (wire.decode_open_state, opened),
                                 (wire.decode_finalization, final)):
            for malformed in (encoded[:-1], encoded+b"\x00"):
                with self.assertRaises(ValueError):
                    decoder(malformed)
        for malformed in (final[:32]+b"\x00"+final[33:], final[:32]+b"\x06"+final[33:]):
            with self.assertRaises(ValueError):
                wire.decode_finalization(malformed)
        with self.assertRaises(ValueError):
            wire.decode_request(request[:-104]+bytes.fromhex(FIXTURE["request"]["members"][1])+request[-72:])
        state = wire.decode_open_state(opened)
        records = state["yes_decisions"]
        for bad in (records[::-1], [records[0]]*2, [{**records[0], "decision": 2}],
                    [{**records[0], "proof": {**records[0]["proof"], "created_at": 1700003601}}]):
            with self.assertRaises(ValueError):
                wire.encode_open_state({**state, "yes_decisions": bad})
        with self.assertRaises(ValueError):
            wire.decode_open_state(request+wire.vector(bytes(107521)))

    def test_maximum_open_state_yes_vector(self):
        core = copy.deepcopy(FIXTURE["request"])
        core["group_id"] = "11" * 255
        core["members"] = [i.to_bytes(32, "big").hex() for i in range(1023)] + [core["proposer_pubkey"]]
        request = {"core": core, "proposer_proof": {**FIXTURE["proof"], "created_at": core["created_at"]}}
        state = {"request": request, "yes_decisions": [
            {"decision": 1, "proof": {**FIXTURE["proof"], "signer_pubkey": key}} for key in core["members"]]}
        encoded = wire.encode_open_state(state)
        offset = len(wire.encode_request(request))
        self.assertEqual(encoded[offset:offset+4], wire.quic_length(107520))
        self.assertEqual(len(encoded)-offset-4, 107520)
        self.assertEqual(len(encoded), 140794)
        self.assertEqual(wire.decode_open_state(encoded), state)


if __name__ == "__main__":
    unittest.main()
