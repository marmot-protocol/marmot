"""Check catalogue structure and historical accounting, not security correctness.

The digest pins the ordered T.x.y ids/titles from threat_model.md at
21a67b24ffbfe14fc52022769aff77495402d728, without network or Git history in CI.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest


DOCUMENT = Path(__file__).resolve().parent.parent / "security-considerations.md"
HISTORICAL_SIZES = {1: 4, 2: 3, 3: 6, 4: 8, 5: 8, 6: 4, 7: 7, 8: 4, 9: 6, 10: 7, 11: 12, 12: 10, 13: 8}
HISTORICAL_DIGEST = "87e8c14e458da82cfba004be81528fc703f4658f300c542d46fe31da29b5d03a"
FIELDS = {
    "Attacker and prerequisites", "Attack sequence", "Affected property and assumptions",
    "Mitigations", "Residual risk", "Normative owners", "Verification status",
}


def validate(text: str) -> list[str]:
    errors = []
    heads = list(re.finditer(r"^### (SC-\d{3})\. (.+)$", text, re.M))
    ids = [match[1] for match in heads]
    counts = Counter(ids)
    if any(count != 1 for count in counts.values()):
        errors.append("duplicate current scenario identifier")
    # Preserve this revision's ids; later additions can append new ones.
    if not {f"SC-{i:03}" for i in range(1, 69)} <= set(ids):
        errors.append("missing current scenario identifier")
    known = {f"A{i}" for i in range(1, 9)} | {f"G{i}" for i in range(1, 8)}
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else text.find("\n## ", head.end())
        body = text[head.end():end if end != -1 else len(text)]
        fields = Counter(re.findall(r"^- \*\*([^*]+):\*\*", body, re.M))
        if set(fields) != FIELDS or any(count != 1 for count in fields.values()):
            errors.append(f"{head[1]}: incomplete or duplicate scenario fields")
        values = re.findall(r"^- \*\*([^*]+):\*\*[ \t]*([\s\S]*?)(?=\n- \*\*|\Z)", body, re.M)
        if any(not value.strip() for _, value in values):
            errors.append(f"{head[1]}: empty scenario field")
        if not text[:head.start()].endswith(f'<a id="{head[1].lower()}"></a>\n\n'):
            errors.append(f"{head[1]}: missing stable anchor")
        status = re.search(r"^- \*\*Verification status:\*\* (.+)$", body, re.M)
        if not status or not status[1].startswith(("Unverified — candidate check:", "External assumption —")):
            errors.append(f"{head[1]}: unrecognized verification status")
        owners = re.search(r"^- \*\*Normative owners:\*\* ([\s\S]*?)(?=\n- \*\*|\Z)", body, re.M)
        if not owners or not re.search(r"\]\([^)]*\.md(?:#[^)]*)?\)", owners[1]):
            errors.append(f"{head[1]}: no linked normative owner")
        if set(re.findall(r"\b[AG]\d+\b", body)) - known:
            errors.append(f"{head[1]}: unknown assumption/property identifier")
    rows = re.findall(r"^\| (T\.\d+\.\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", text, re.M)
    historical_ids = [row[0] for row in rows]
    expected = {f"T.{family}.{n}" for family, size in HISTORICAL_SIZES.items() for n in range(1, size + 1)}
    if len(rows) != 87 or set(historical_ids) != expected or len(set(historical_ids)) != len(rows):
        errors.append("historical inventory must account for all 87 identifiers exactly once")
    payload = [[row[0], row[1].strip()] for row in rows]
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if digest != HISTORICAL_DIGEST:
        errors.append("historical identifier/title inventory differs from the pinned source")
    for old_id, _, disposition, target, reason in rows:
        if disposition.strip() not in {"Retained", "Updated", "Merged", "Superseded", "Excluded"}:
            errors.append(f"{old_id}: unknown disposition")
        links = re.findall(r"\[(SC-\d{3})\]\(#(sc-\d{3})\)", target)
        if disposition.strip() != "Excluded" and not links:
            errors.append(f"{old_id}: no current scenario mapping")
        for label, anchor in links:
            if label not in counts or label.lower() != anchor:
                errors.append(f"{old_id}: dangling or mismatched current scenario mapping")
        if len(reason.strip()) < 20:
            errors.append(f"{old_id}: missing disposition rationale")
    return errors


class ThreatCatalogueContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCUMENT.read_text(encoding="utf-8")

    def test_document_has_complete_scenarios_and_historical_accounting(self):
        self.assertEqual(validate(self.text), [])

    def test_dropped_historical_row_is_rejected(self):
        mutated = re.sub(r"^\| T\.1\.1 \|.*\n", "", self.text, flags=re.M)
        self.assertIn("historical inventory must account for all 87 identifiers exactly once", validate(mutated))

    def test_rewritten_historical_title_is_rejected(self):
        mutated = self.text.replace("| Invalid Key Package Publication |", "| Different historical threat |", 1)
        self.assertIn("historical identifier/title inventory differs from the pinned source", validate(mutated))

    def test_removed_attack_path_is_rejected(self):
        mutated = self.text.replace("- **Attack sequence:**", "- **Unstructured note:**", 1)
        self.assertIn("SC-001: incomplete or duplicate scenario fields", validate(mutated))

    def test_duplicate_current_id_is_rejected(self):
        mutated = self.text.replace("### SC-002.", "### SC-001.", 1)
        self.assertIn("duplicate current scenario identifier", validate(mutated))

    def test_empty_attack_path_is_rejected(self):
        mutated = re.sub(r"(- \*\*Attack sequence:\*\*)[^\n]*(?:\n  [^\n]+)*", r"\1", self.text, count=1)
        self.assertIn("SC-001: empty scenario field", validate(mutated))

    def test_dangling_historical_mapping_is_rejected(self):
        mutated = self.text.replace("| [SC-001](#sc-001) |", "| [SC-999](#sc-999) |", 1)
        self.assertIn("T.1.1: dangling or mismatched current scenario mapping", validate(mutated))

    def test_unsupported_verified_claim_is_rejected(self):
        mutated = self.text.replace("**Verification status:** Unverified — candidate check:",
                                    "**Verification status:** Proven secure:", 1)
        self.assertIn("SC-001: unrecognized verification status", validate(mutated))

    def test_missing_stable_anchor_is_rejected(self):
        mutated = self.text.replace('<a id="sc-001"></a>\n\n', "", 1)
        self.assertIn("SC-001: missing stable anchor", validate(mutated))


if __name__ == "__main__":
    unittest.main()
