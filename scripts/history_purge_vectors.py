"""Encoding/hash reference helpers; no signature or MLS verification."""

import hashlib


def quic_length(value):
    for width, limit, tag in ((1, 64, 0), (2, 16384, 1), (4, 2**30, 2), (8, 2**62, 3)):
        if 0 <= value < limit:
            return (value | tag << (8 * width - 2)).to_bytes(width, "big")
    raise ValueError("invalid QUIC length")


def vector(body):
    return quic_length(len(body)) + body


class Reader:
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def take(self, size):
        if self.offset + size > len(self.data):
            raise ValueError("truncated bytes")
        result = self.data[self.offset:self.offset + size]
        self.offset += size
        return result

    def integer(self, size):
        return int.from_bytes(self.take(size), "big")

    def vector(self, minimum, maximum):
        first = self.take(1)
        width = 1 << (first[0] >> 6)
        prefix = first + self.take(width - 1)
        length = int.from_bytes(prefix, "big") & ((1 << (8 * width - 2)) - 1)
        if prefix != quic_length(length) or not minimum <= length <= maximum:
            raise ValueError("noncanonical prefix or vector bounds")
        return self.take(length)

    def finish(self):
        if self.offset != len(self.data):
            raise ValueError("trailing bytes")


def fixed(hex_value, size):
    data = bytes.fromhex(hex_value)
    if len(data) != size:
        raise ValueError("fixed-width field")
    return data


def u64(value):
    if not 0 <= value < 2**64:
        raise ValueError("uint64 bound")
    return value.to_bytes(8, "big")


def encode_capabilities(leaves):
    if not 1 <= len(leaves) <= 1024:
        raise ValueError("capability leaf count")
    body = b""
    previous = -1
    for leaf in leaves:
        index = leaf["leaf_index"]
        flags = leaf["support"]
        if not previous < index < 2**32 or len(flags) != 3 or any(v not in (0, 1) for v in flags):
            raise ValueError("capability ordering or flags")
        body += index.to_bytes(4, "big") + fixed(leaf["account_pubkey"], 32) + bytes(flags)
        previous = index
    return vector(body)


def encode_request_core(request):
    group = bytes.fromhex(request["group_id"])
    body = vector(group) + u64(request["parent_epoch"])
    body += fixed(request["parent_group_context_hash"], 32) + fixed(request["proposer_pubkey"], 32)
    body += u64(request["created_at"]) + u64(request["expires_at"])
    body += bytes([request["prior_retention_present"]]) + u64(request["prior_retention_secs"])
    body += u64(request["target_retention_secs"])
    body += vector(b"".join(fixed(v, 32) for v in request["members"]))
    body += fixed(request["capability_state_hash"], 32)
    decode_request_core(body)
    return body


def decode_request_core(data):
    reader = Reader(data)
    result = {"group_id": reader.vector(1, 255).hex(), "parent_epoch": reader.integer(8),
              "parent_group_context_hash": reader.take(32).hex(), "proposer_pubkey": reader.take(32).hex(),
              "created_at": reader.integer(8), "expires_at": reader.integer(8),
              "prior_retention_present": reader.integer(1), "prior_retention_secs": reader.integer(8),
              "target_retention_secs": reader.integer(8)}
    members = reader.vector(32, 32768)
    if len(members) % 32:
        raise ValueError("partial member")
    result["members"] = [members[i:i+32].hex() for i in range(0, len(members), 32)]
    result["capability_state_hash"] = reader.take(32).hex()
    reader.finish()
    if (result["parent_epoch"] == 2**64 - 1 or result["prior_retention_present"] not in (0, 1)
            or (result["prior_retention_present"] == 0 and result["prior_retention_secs"] != 0)
            or result["members"] != sorted(set(result["members"]))
            or result["proposer_pubkey"] not in result["members"]
            or not 1 <= result["created_at"] < result["expires_at"] <= 2**53 - 1
            or result["expires_at"] - result["created_at"] > 604800):
        raise ValueError("request structural bounds")
    return result


def encode_proof(proof):
    if not 1 <= proof["created_at"] <= 2**53 - 1:
        raise ValueError("proof timestamp")
    return fixed(proof["signer_pubkey"], 32) + u64(proof["created_at"]) + fixed(proof["signature"], 64)


def digest(domain, *parts):
    return hashlib.sha256(domain.encode("ascii") + b"\0" + b"".join(parts)).digest()


def proof_event(request, proof, kind, decision="yes", terminal="accepted"):
    """Unsigned signing-template fixture; all parent bindings use request core."""
    request_id = digest("marmot-history-purge-request-v1", encode_request_core(request)).hex()
    domains = {454: "decision", 455: "request", 456: "cancellation", 457: "terminal"}
    if kind not in domains:
        raise ValueError("unknown proof kind")
    tags = [["d", f"marmot-history-purge-{domains[kind]}-v1"], ["component", "0x800d"],
            ["group_id", request["group_id"]], ["parent_epoch", str(request["parent_epoch"])],
            ["request", request_id]]
    content = ""
    if kind == 455:
        content = hashlib.sha256(encode_request_core(request)).hexdigest()
    elif kind == 454:
        if decision not in ("yes", "no"):
            raise ValueError("unknown decision")
        tags.append(["decision", decision])
    elif kind == 457:
        values = {"accepted": 1, "expired": 4, "superseded": 5}
        if terminal not in values:
            raise ValueError("unknown signing terminal")
        tags.append(["terminal", terminal])
        content = hashlib.sha256(bytes.fromhex(request_id) + bytes([values[terminal]])).hexdigest()
    return {"pubkey": proof["signer_pubkey"], "created_at": proof["created_at"], "kind": kind,
            "tags": tags, "content": content}


def identities(request, leaves, proof, terminal=1, decision=1, outcome="applied"):
    if terminal not in range(1, 6) or decision not in (1, 2) or outcome not in ("applied", "failed"):
        raise ValueError("unknown enum")
    core = encode_request_core(request)
    request_id = digest("marmot-history-purge-request-v1", core)
    proof_bytes = encode_proof(proof)
    finalization = request_id + bytes([terminal]) + proof_bytes
    finalization_id = digest("marmot-history-purge-finalization-v1", finalization)
    return {
        "capability_bytes": encode_capabilities(leaves).hex(),
        "capability_state_hash": digest("marmot-history-purge-capabilities-v1", encode_capabilities(leaves)).hex(),
        "request_core_bytes": core.hex(), "request_id": request_id.hex(),
        "proof_bytes": proof_bytes.hex(),
        "response_id": digest("marmot-history-purge-response-v1", request_id, bytes([decision]), proof_bytes).hex(),
        "cancellation_id": digest("marmot-history-purge-cancellation-v1", request_id, proof_bytes).hex(),
        "finalization_bytes": finalization.hex(), "finalization_id": finalization_id.hex(),
        "receipt_id": digest("marmot-history-purge-receipt-v1", finalization_id,
                             fixed(proof["signer_pubkey"], 32), outcome.encode("ascii")).hex(),
    }
