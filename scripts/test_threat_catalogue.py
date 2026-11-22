"""Check current scenario structure and references, not security correctness."""

from collections import Counter
from pathlib import Path
import re
import unittest


DOCUMENT = Path(__file__).resolve().parent.parent / "security-considerations.md"
FIELDS = {
    "Attacker and prerequisites", "Attack sequence", "Affected property and assumptions",
    "Mitigations", "Residual risk", "Normative owners", "Verification status",
}
STATUS_PREFIXES = ("Unverified — candidate check:", "External assumption —")


def validate(text: str) -> list[str]:
    errors = []
    heads = list(re.finditer(r"^### (SC-\d{3})\. (.+)$", text, re.M))
    ids = [match[1] for match in heads]
    counts = Counter(ids)
    if not heads:
        errors.append("empty scenario catalogue")
    if any(count != 1 for count in counts.values()):
        errors.append("duplicate current scenario identifier")
    index_start = text.find("| Scenarios | Subject |")
    index_end = text.find('\n<a id="sc-', index_start)
    index = text[index_start:index_end] if index_start != -1 and index_end != -1 else ""
    indexed = []
    for row in re.findall(r"^\| (.+?) \| .+ \|$", index, re.M):
        refs = re.findall(r"\[(SC-(\d{3}))\]\(#(sc-\d{3})\)", row)
        if not refs:
            continue
        if len(refs) == 2 and "–" in row:
            indexed.extend(f"SC-{n:03}" for n in range(int(refs[0][1]), int(refs[1][1]) + 1))
        else:
            indexed.extend(ref[0] for ref in refs)
    if Counter(indexed) != counts:
        errors.append("scenario index does not cover each current identifier exactly once")
    for label, anchor in re.findall(r"\[(SC-\d{3})\]\(#(sc-\d{3})\)", text):
        if label not in counts or label.lower() != anchor:
            errors.append("dangling or mismatched scenario reference")
    known = {f"A{i}" for i in range(1, 9)} | {f"G{i}" for i in range(1, 8)}
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else text.find("\n## ", head.end())
        body = text[head.end():end if end != -1 else len(text)]
        # The next entry's anchor is not part of this entry's final field.
        body = re.sub(r'\n<a id="sc-\d{3}"></a>\s*\Z', "", body)
        fields = Counter(re.findall(r"^- \*\*([^*]+):\*\*", body, re.M))
        if set(fields) != FIELDS or any(count != 1 for count in fields.values()):
            errors.append(f"{head[1]}: incomplete or duplicate scenario fields")
        values = dict(re.findall(r"^- \*\*([^*]+):\*\*[ \t]*([\s\S]*?)(?=\n- \*\*|\Z)", body, re.M))
        if any(not value.strip() for value in values.values()):
            errors.append(f"{head[1]}: empty scenario field")
        if not text[:head.start()].endswith(f'<a id="{head[1].lower()}"></a>\n\n'):
            errors.append(f"{head[1]}: missing stable anchor")
        status = values.get("Verification status", "").strip()
        if not any(status.startswith(prefix) and status[len(prefix):].strip() for prefix in STATUS_PREFIXES):
            errors.append(f"{head[1]}: unrecognized or empty verification status")
        owners = values.get("Normative owners", "")
        if not re.search(r"\]\((?:foundation|protocol-core|app-components|transports|features)/[^)#\s]+\.md(?:#[^)]*)?\)", owners):
            errors.append(f"{head[1]}: no linked owning protocol surface")
        if set(re.findall(r"\b[AG]\d+\b", body)) - known:
            errors.append(f"{head[1]}: unknown assumption/property identifier")
    return errors


class ThreatCatalogueContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCUMENT.read_text(encoding="utf-8")

    def test_document_has_complete_current_scenarios(self):
        self.assertEqual(validate(self.text), [])

    def test_empty_catalogue_is_rejected(self):
        self.assertIn("empty scenario catalogue", validate("No scenarios."))

    def test_missing_index_entry_is_rejected(self):
        mutated = self.text.replace("[SC-001](#sc-001)–[SC-010](#sc-010)", "[SC-002](#sc-002)–[SC-010](#sc-010)", 1)
        self.assertIn("scenario index does not cover each current identifier exactly once", validate(mutated))

    def test_removed_attack_path_is_rejected(self):
        mutated = self.text.replace("- **Attack sequence:**", "- **Unstructured note:**", 1)
        self.assertIn("SC-001: incomplete or duplicate scenario fields", validate(mutated))

    def test_duplicate_current_id_is_rejected(self):
        mutated = self.text.replace("### SC-002.", "### SC-001.", 1)
        self.assertIn("duplicate current scenario identifier", validate(mutated))

    def test_empty_attack_path_is_rejected(self):
        mutated = re.sub(r"(- \*\*Attack sequence:\*\*)[^\n]*(?:\n  [^\n]+)*", r"\1", self.text, count=1)
        self.assertIn("SC-001: empty scenario field", validate(mutated))

    def test_dangling_scenario_reference_is_rejected(self):
        mutated = self.text.replace("[SC-001](#sc-001)", "[SC-999](#sc-999)", 1)
        self.assertIn("dangling or mismatched scenario reference", validate(mutated))

    def test_unsupported_verified_claim_is_rejected(self):
        mutated = self.text.replace("**Verification status:** Unverified — candidate check:",
                                    "**Verification status:** Proven secure:", 1)
        self.assertIn("SC-001: unrecognized or empty verification status", validate(mutated))

    def test_empty_candidate_check_is_rejected(self):
        mutated = re.sub(r"(- \*\*Verification status:\*\* Unverified — candidate check:)[^\n]*(?:\n  [^\n]+)*",
                         r"\1", self.text, count=1)
        self.assertIn("SC-001: unrecognized or empty verification status", validate(mutated))

    def test_overview_self_link_is_not_an_owning_surface(self):
        mutated = re.sub(r"(- \*\*Normative owners:\*\*)[^\n]*(?:\n  [^\n]+)*",
                         r"\1 [Overview](security-considerations.md).", self.text, count=1)
        self.assertIn("SC-001: no linked owning protocol surface", validate(mutated))

    def test_missing_stable_anchor_is_rejected(self):
        mutated = self.text.replace('<a id="sc-001"></a>\n\n', "", 1)
        self.assertIn("SC-001: missing stable anchor", validate(mutated))


if __name__ == "__main__":
    unittest.main()
