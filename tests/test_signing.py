"""AUD-33: person-only approvals that work from a cloud session. The fixtures are real OpenSSH 9.6 `ssh-keygen -Y sign`
signatures (public keys only are committed); the verifier is pure Python and is cross-checked with ssh-keygen."""
import shutil
import subprocess
from pathlib import Path

import pytest

from ulac import signing

F = Path(__file__).resolve().parent / "fixtures" / "signing"
AS = F / "allowed_signers"
needs_ssh = pytest.mark.skipif(not shutil.which("ssh-keygen"), reason="ssh-keygen not installed")


def test_a_real_ssh_keygen_signature_verifies_with_the_openssh_fingerprint():
    r = signing.verify((F / "statement.txt").read_bytes(), (F / "statement.txt.sig").read_text(), "producer@example", AS)
    assert r["fingerprint"] == "SHA256:/lEpYnEuZgVcwnt6Pm12KVuMdbGKOqke12cVloCaEwM"     # as printed by ssh-keygen -Y verify


@pytest.mark.parametrize("sig,msg,who,why", [
    ("statement.other_key.sig", "statement.txt", "producer@example", "not registered"),   # someone else's key
    ("ns.txt.sig", "ns.txt", "producer@example", "namespace"),                            # signed for another purpose
    ("statement.txt.sig", "statement.txt", "agent@example", "not registered"),            # another principal
])
def test_signatures_from_other_keys_namespaces_or_principals_are_refused(sig, msg, who, why):
    with pytest.raises(signing.SignatureError, match=why):
        signing.verify((F / msg).read_bytes(), (F / sig).read_text(), who, AS)


def test_a_changed_statement_or_a_garbled_signature_is_refused(tmp_path):
    good = (F / "statement.txt").read_bytes()
    with pytest.raises(signing.SignatureError, match="does not match"):
        signing.verify(good.replace(b"four", b"five"), (F / "statement.txt.sig").read_text(), "producer@example", AS)
    with pytest.raises(signing.SignatureError, match="armored"):
        signing.verify(good, "I approve", "producer@example", AS)
    opt = tmp_path / "allowed_signers"
    opt.write_text('producer@example namespaces="file" ssh-ed25519 AAAA\n')
    with pytest.raises(signing.SignatureError, match="options"):
        signing.verify(good, (F / "statement.txt.sig").read_text(), "producer@example", opt)


@needs_ssh
def test_the_statement_a_person_signs_verifies_here_and_with_ssh_keygen(tmp_path):
    key = tmp_path / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "t", "-f", str(key)], check=True)
    (tmp_path / "allowed_signers").write_text("glenn " + " ".join(key.with_suffix(".pub").read_text().split()[:2]) + "\n")
    msg = signing.statement(project="EP06", action="contract_approved", kind="storyboard",
                            items=[("SEQ_001", "a" * 64)], by="glenn", text="checked hands and facing")
    (tmp_path / "s.txt").write_bytes(msg)
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "ulac-approval", str(tmp_path / "s.txt")],
                   check=True, capture_output=True)
    sig = (tmp_path / "s.txt.sig").read_text()
    assert signing.verify(msg, sig, "glenn", tmp_path / "allowed_signers")["principal"] == "glenn"
    ok = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(tmp_path / "allowed_signers"), "-I", "glenn", "-n",
                         "ulac-approval", "-s", str(tmp_path / "s.txt.sig")], input=msg, capture_output=True)
    assert ok.returncode == 0


@needs_ssh
def test_a_signed_contract_approval_is_bound_to_the_hash_it_names(tmp_path, monkeypatch):
    """The approval statement carries the contract hashes. A signature over another version is refused when it is
    recorded, and a stored signature that no longer verifies voids the approval when it is read."""
    import json
    from conftest import clean_episode, sign_cast
    from ulac import contracts as C, firewall
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "t"}))
    samples, sil = clean_episode(tmp_path, ["SEQ_001", "SEQ_002"])
    sign_cast(tmp_path)
    C.build(tmp_path, samples=samples, sil=sil)
    key = tmp_path / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "t", "-f", str(key)], check=True)
    signers = tmp_path / "allowed_signers"
    signers.write_text("glenn " + " ".join(key.with_suffix(".pub").read_text().split()[:2]) + "\n")
    monkeypatch.setattr(signing, "SIGNERS", signers)
    st = "listened to every cut and checked the word timings against the waveform"

    def sign(sha):
        msg = signing.statement(project=tmp_path.name, action="contract_approved", kind="audio",
                                items=[("audio_ledger", sha)], by="glenn", text=st)
        f = tmp_path / f"s_{sha[:8]}.txt"                       # ssh-keygen never overwrites an existing .sig
        f.write_bytes(msg)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "ulac-approval", str(f)],
                       check=True, capture_output=True)
        return Path(str(f) + ".sig").read_text()
    with pytest.raises(C.ContractError, match="does not verify"):
        C.approve(tmp_path, kind="audio", ids=None, by="glenn", statement=st, signature=sign("b" * 64))
    sha = C.load(tmp_path, "audio_ledger")["sha256"]
    rec = C.approve(tmp_path, kind="audio", ids=None, by="glenn", statement=st, signature=sign(sha))[0]
    assert rec["signer"].startswith("SHA256:") and C.current(tmp_path, "audio_ledger", "audio_ledger") == []
    signers.write_text("")                                          # the key is withdrawn: the approval stops holding
    assert "no longer verifies" in " ".join(C.current(tmp_path, "audio_ledger", "audio_ledger"))
