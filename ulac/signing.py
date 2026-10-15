"""Person-only approvals that work from a cloud session (AUD-33).

The person signs a canonical approval statement on their own machine with their SSH key, in the `ulac-approval`
namespace:

  ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n ulac-approval statement.txt      # writes statement.txt.sig

The agent holds no private key, so it cannot produce such a signature; it can only carry it. The approval functions
rebuild the statement from the current contract hashes and verify the signature against `docs/production/allowed_signers`
(OpenSSH allowed_signers format: `<principal> ssh-ed25519 <base64 key>`), so a signature over a changed contract fails.

Verification is pure Python (Ed25519 from `cryptography`), so it works where OpenSSH is not installed. The fixtures in
tests/fixtures/signing were made by OpenSSH 9.6 `ssh-keygen -Y sign`, and the tests cross-check with `ssh-keygen -Y
verify` when it is available.

  python3 -m ulac.signing statement project/<EP> --kind storyboard --ids SEQ_001,SEQ_002 --by <principal> --statement "..."
  python3 -m ulac.signing verify <statement.txt> <statement.txt.sig> --by <principal> [--signers <allowed_signers>]
"""
from __future__ import annotations

import base64
import hashlib
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAMESPACE = "ulac-approval"
SIGNERS = REPO / "docs" / "production" / "allowed_signers"
MAGIC = b"SSHSIG"


class SignatureError(RuntimeError):
    pass


def statement(*, project: str, action: str, kind: str, items: list[tuple[str, str]], by: str, text: str) -> bytes:
    """The exact bytes a person signs: one field per line, the approved hashes included, so the signature covers the
    contents that were checked and nothing else."""
    fields = [("project", project), ("action", action), ("kind", kind), ("by", by), ("statement", " ".join(str(text).split()))]
    for k, v in fields:
        if not str(v).strip() or "\n" in str(v):
            raise SignatureError(f"statement field {k!r} must be one non-empty line")
    lines = ["ulac-approval v1"] + [f"{k}: {v}" for k, v in fields[:4]]
    lines += [f"approve: {i} sha256 {h}" for i, h in sorted(items)]
    lines.append(f"statement: {fields[4][1]}")
    return ("\n".join(lines) + "\n").encode()


def _string(buf: bytes, off: int) -> tuple[bytes, int]:
    if off + 4 > len(buf):
        raise SignatureError("truncated signature")
    (n,) = struct.unpack(">I", buf[off:off + 4])
    if off + 4 + n > len(buf):
        raise SignatureError("truncated signature")
    return buf[off + 4:off + 4 + n], off + 4 + n


def _pack(b: bytes) -> bytes:
    return struct.pack(">I", len(b)) + b


def fingerprint(key_blob: bytes) -> str:
    return "SHA256:" + base64.b64encode(hashlib.sha256(key_blob).digest()).decode().rstrip("=")


def parse(armored: str) -> dict:
    lines = [ln.strip() for ln in str(armored).strip().splitlines()]
    if not lines or lines[0] != "-----BEGIN SSH SIGNATURE-----" or lines[-1] != "-----END SSH SIGNATURE-----":
        raise SignatureError("not an armored SSH signature (ssh-keygen -Y sign)")
    try:
        blob = base64.b64decode("".join(lines[1:-1]), validate=True)
    except ValueError as e:
        raise SignatureError(f"signature is not base64: {e}") from e
    if blob[:6] != MAGIC:
        raise SignatureError("not an SSHSIG signature")
    (version,) = struct.unpack(">I", blob[6:10])
    if version != 1:
        raise SignatureError(f"unsupported SSHSIG version {version}")
    off = 10
    out = {}
    for k in ("publickey", "namespace", "reserved", "hash_algorithm", "signature"):
        out[k], off = _string(blob, off)
    return out


def allowed_keys(path: Path, principal: str) -> list[bytes]:
    """Key blobs the allowed_signers file grants to `principal` (exact principal names; options are not supported, so a
    line carrying them is refused rather than half-read)."""
    keys = []
    p = Path(path)
    if not p.is_file():
        return keys
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        if len(parts) < 3 or not parts[1].startswith("ssh-"):
            raise SignatureError(f"unsupported allowed_signers line (options are not accepted): {ln[:60]}")
        if principal in parts[0].split(","):
            keys.append(base64.b64decode(parts[2]))
    return keys


def verify(message: bytes, armored: str, principal: str, signers: Path | None = None) -> dict:
    """Raise SignatureError unless `armored` is an ulac-approval Ed25519 signature over `message` by a key that
    `signers` grants to `principal`. Returns the signer's fingerprint."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    signers = Path(signers or SIGNERS)
    s = parse(armored)
    if s["namespace"].decode(errors="replace") != NAMESPACE:
        raise SignatureError(f"signature namespace is {s['namespace']!r}, not {NAMESPACE!r}")
    keytype, off = _string(s["publickey"], 0)
    if keytype != b"ssh-ed25519":
        raise SignatureError(f"only ssh-ed25519 keys are accepted, not {keytype!r}")
    raw, _ = _string(s["publickey"], off)
    if s["publickey"] not in allowed_keys(signers, principal):
        raise SignatureError(f"the signing key {fingerprint(s['publickey'])} is not registered for {principal!r} in {signers}")
    alg = s["hash_algorithm"].decode(errors="replace")
    if alg not in ("sha512", "sha256"):
        raise SignatureError(f"unsupported hash algorithm {alg!r}")
    digest = hashlib.new(alg, message).digest()
    signed = MAGIC + _pack(s["namespace"]) + _pack(s["reserved"]) + _pack(s["hash_algorithm"]) + _pack(digest)
    sigtype, off = _string(s["signature"], 0)
    sig, _ = _string(s["signature"], off)
    if sigtype != b"ssh-ed25519":
        raise SignatureError(f"signature type {sigtype!r} does not match the key")
    try:
        Ed25519PublicKey.from_public_bytes(raw).verify(sig, signed)
    except InvalidSignature as e:
        raise SignatureError("the signature does not match this statement") from e
    return {"principal": principal, "fingerprint": fingerprint(s["publickey"]), "namespace": NAMESPACE}


def main(argv: list[str]) -> int:
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    if argv[:1] == ["verify"]:
        r = verify(Path(argv[1]).read_bytes(), Path(argv[2]).read_text(), get("--by"), Path(get("--signers", SIGNERS)))
        print(r)
        return 0
    if argv[:1] == ["statement"]:
        from . import contracts
        root = Path(argv[1])
        kind = get("--kind")
        ids = get("--ids", "").split(",") if get("--ids") else ["audio_ledger"]
        name = {"audio": lambda i: "audio_ledger", "storyboard": contracts.sb_name, "continuity": contracts.cc_name}[kind]
        items = [(i, contracts.load(root, name(i))["sha256"]) for i in ids]
        sys.stdout.write(statement(project=root.name, action="contract_approved", kind=kind, items=items,
                                   by=get("--by"), text=get("--statement")).decode())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
