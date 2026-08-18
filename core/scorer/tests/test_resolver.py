"""Resolver seam (CONTRACT.md §8).

Two lanes, honestly separated:
- Unit lane (runs everywhere): KeArtifactResolver's own logic — store indexing,
  fail-closed lookup, verdict mapping — against a STUB binding injected via the
  constructor. The stub stands in for ke_artifact_py's surface only; it proves
  the resolver's logic, never the crypto.
- Wheel lane (Linux/CI only): the same resolver against the REAL wheel and the
  REAL rule-engine golden artifacts + contract inputs. Skips visibly where the wheel
  or the rule-engine checkout is absent — never faked green.
"""

import json
import os
from pathlib import Path

import pytest

from scorer.resolver import ArtifactResolver, KeArtifactResolver, NullResolver

# The pinned export instant the upstream rule-engine's contract test
# verifies at.
EXPORTED_AT = 1750000000


def test_null_resolver_is_a_marker_not_a_verifier():
    # NullResolver means "no resolver on this host". It must never be usable to
    # CLAIM verification: calling verify is a bug and must raise (the app's
    # catch-all then fails closed to UNEVALUABLE).
    with pytest.raises(Exception):
        NullResolver().verify("rh", "sh")


def test_protocol_accepts_structural_impls():
    class Impl:
        def verify(self, rule_artifact_hash, intent_spec_hash) -> bool:
            return True

    r: ArtifactResolver = Impl()
    assert r.verify("rh", "sh") is True


# --- unit lane: resolver logic against a stub binding -----------------------


class _StubArtifact:
    def __init__(self, artifact_hash: str) -> None:
        self.artifact_hash = artifact_hash


class _StubBinding:
    """ke_artifact_py surface double: from_bytes maps known byte strings to
    hashes (ValueError otherwise, like the real non-canonical decode error);
    verify_artifact returns the canned outcome for that artifact."""

    def __init__(self, artifacts: dict[bytes, str], outcomes: dict[str, dict]) -> None:
        self._artifacts = dict(artifacts)
        self._outcomes = dict(outcomes)
        self.verify_calls = 0

    def from_bytes(self, data: bytes) -> _StubArtifact:
        if bytes(data) not in self._artifacts:
            raise ValueError("non-canonical artifact bytes")
        return _StubArtifact(self._artifacts[bytes(data)])

    def verify_artifact(self, kew, keydir, ctx, policy, registry, exported_at):
        self.verify_calls += 1
        return self._outcomes[self._artifacts[bytes(kew)]]


def _verified_outcome(h: str) -> dict:
    return {"verdict": "verified", "content_hash": h, "provenance": {}}


def _store(tmp_path: Path, files: dict[str, bytes]) -> Path:
    d = tmp_path / "artifacts"
    d.mkdir()
    for name, data in files.items():
        sub = d / name
        sub.mkdir()
        (sub / "artifact.kew").write_bytes(data)
    return d


H_A = "aa" * 32
H_B = "bb" * 32


def _resolver(tmp_path, files, artifacts, outcomes) -> KeArtifactResolver:
    return KeArtifactResolver(
        _store(tmp_path, files),
        keydir_json="{}",
        context_json="{}",
        policy_json="{}",
        registry_json="{}",
        exported_at_unix=EXPORTED_AT,
        binding=_StubBinding(artifacts, outcomes),
    )


def test_verified_artifact_answers_true(tmp_path):
    r = _resolver(
        tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: _verified_outcome(H_A)}
    )
    assert r.verify(None, H_A) is True
    assert r.verify(H_A, None) is True


def test_absent_hash_fails_closed(tmp_path):
    r = _resolver(
        tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: _verified_outcome(H_A)}
    )
    assert r.verify(None, H_B) is False


def test_rejected_verdict_fails_closed(tmp_path):
    rejected = {"verdict": "rejected:HashMismatch", "content_hash": H_A}
    r = _resolver(tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: rejected})
    assert r.verify(None, H_A) is False


def test_readdressed_hash_mismatch_fails_closed(tmp_path):
    # verdict says verified but the re-addressed hash is not the one requested:
    # the resolver's promise is "THIS hash verifies", so this is False.
    r = _resolver(
        tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: _verified_outcome(H_B)}
    )
    assert r.verify(None, H_A) is False


def test_hashless_call_refuses(tmp_path):
    r = _resolver(
        tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: _verified_outcome(H_A)}
    )
    # The app only calls with a hash present; a hashless True would be a
    # fail-open edge.
    assert r.verify(None, None) is False


def test_both_hashes_must_verify(tmp_path):
    outcomes = {H_A: _verified_outcome(H_A), H_B: {"verdict": "rejected:Revoked"}}
    r = _resolver(
        tmp_path,
        {"a": b"kew-a", "b": b"kew-b"},
        {b"kew-a": H_A, b"kew-b": H_B},
        outcomes,
    )
    assert r.verify(H_A, H_B) is False
    assert r.verify(H_A, None) is True


def test_non_canonical_file_absent_from_index(tmp_path):
    # A corrupt .kew in the store must not break the others — and requesting
    # its would-be hash fails closed because it never enters the index.
    r = _resolver(
        tmp_path,
        {"a": b"kew-a", "junk": b"garbage"},
        {b"kew-a": H_A},
        {H_A: _verified_outcome(H_A)},
    )
    assert r.verify(None, H_A) is True
    assert r.verify(None, H_B) is False


def test_requested_hash_is_case_insensitive(tmp_path):
    r = _resolver(
        tmp_path, {"a": b"kew-a"}, {b"kew-a": H_A}, {H_A: _verified_outcome(H_A)}
    )
    assert r.verify(None, H_A.upper()) is True


# --- wheel lane: the real binding against the real rule-engine goldens ------------


def _goldens_dir() -> Path | None:
    # SCORER_GOLDENS_DIR is the lane's ONLY wiring (CONTRACT.md §8 env table):
    # explicit configuration, no filesystem-layout guessing. Unset => the lane
    # skips visibly below.
    env = os.environ.get("SCORER_GOLDENS_DIR")
    return Path(env) if env else None


def _wheel_lane():
    """Common wheel-lane preamble: the real binding + the rule-engine checkout, or a
    VISIBLE skip (a skipped wheel test is never a green one)."""
    binding = pytest.importorskip(
        "ke_artifact_py",
        reason="ke-artifact-py wheel absent (Linux/CI-only by design)",
    )
    goldens = _goldens_dir()
    if goldens is None:
        pytest.skip(
            "rule-engine goldens absent (set SCORER_GOLDENS_DIR to a goldens "
            "checkout)"
        )
    return binding, goldens


def _read_input(goldens: Path, name: str) -> str:
    return (goldens / "scripts" / "contract-inputs" / name).read_text(encoding="utf-8")


def _intentspec_env(goldens: Path) -> tuple[str, str]:
    """The IntentSpec verification environment, synthesized the same way the
    rule-engine side does: the upstream kind-aware IntentSpec policy
    (SourceFidelity + PublicationApproval, NO ScenarioCoverage) and a context
    whose current_legal_source_hash is THIS artifact's source_corpus_hash
    (the exact procedure of the upstream contract-input emitter). The shared
    contract-inputs policy/context are the RULE-artifact environment and
    reject an IntentSpec by construction."""
    policy = json.loads(_read_input(goldens, "policy.json"))
    policy["required_attestation_types"] = [
        t for t in policy["required_attestation_types"] if t != "ScenarioCoverage"
    ]
    policy["minimum_attestation_count_per_type"] = [
        c
        for c in policy["minimum_attestation_count_per_type"]
        if c["attestation_type"] != "ScenarioCoverage"
    ]
    manifest = json.loads(
        (goldens / "fixtures" / "artifacts" / "intentspec_payment" / "manifest.json")
        .read_text(encoding="utf-8")
    )
    context = json.loads(_read_input(goldens, "context.json"))
    context["current_legal_source_hash"] = manifest["source_corpus_hash"]
    return json.dumps(policy), json.dumps(context)


def _goldens_resolver(binding, goldens: Path, **overrides) -> KeArtifactResolver:
    policy_json, context_json = _intentspec_env(goldens)
    kwargs = dict(
        keydir_json=_read_input(goldens, "keydir.json"),
        context_json=context_json,
        policy_json=policy_json,
        registry_json=_read_input(goldens, "registry.json"),
        exported_at_unix=EXPORTED_AT,
    )
    kwargs.update(overrides)
    return KeArtifactResolver(goldens / "fixtures" / "artifacts", binding=binding, **kwargs)


def _golden_intentspec_hash(binding, goldens: Path) -> str:
    kew = (goldens / "fixtures" / "artifacts" / "intentspec_payment" / "artifact.kew").read_bytes()
    return binding.from_bytes(kew).artifact_hash


def test_wheel_lane_golden_intentspec_verifies():
    binding, goldens = _wheel_lane()
    r = _goldens_resolver(binding, goldens)
    h = _golden_intentspec_hash(binding, goldens)
    assert r.verify(None, h) is True


def test_wheel_lane_unknown_hash_fails_closed():
    binding, goldens = _wheel_lane()
    r = _goldens_resolver(binding, goldens)
    assert r.verify(None, "0" * 64) is False


def test_wheel_lane_unknown_registry_state_fails_closed():
    # Negative control proving the resolver consults VERIFICATION, not mere
    # file presence: the EXACT environment the happy-path test verifies under,
    # differing ONLY in registry evidence downgraded to Unknown => the folded
    # verdict must reject (upstream fail-closed verdict folding) and the
    # resolver answer False.
    # (Differing only in this one input keeps the control non-vacuous.)
    binding, goldens = _wheel_lane()
    registry = json.loads(_read_input(goldens, "registry.json"))
    registry["status"] = "Unknown"
    r = _goldens_resolver(binding, goldens, registry_json=json.dumps(registry))
    h = _golden_intentspec_hash(binding, goldens)
    assert r.verify(None, h) is False


def test_wheel_lane_rule_environment_rejects_intentspec():
    # Cross-kind honesty: under the UNMODIFIED shared contract-inputs (the
    # rule-artifact environment) the IntentSpec must fail closed — one static
    # environment verifies one kind. Mixed-kind requests in one deployment are
    # recorded debt (binding-side kind-aware policy), not a silent pass.
    binding, goldens = _wheel_lane()
    r = _goldens_resolver(
        binding,
        goldens,
        policy_json=_read_input(goldens, "policy.json"),
        context_json=_read_input(goldens, "context.json"),
    )
    h = _golden_intentspec_hash(binding, goldens)
    assert r.verify(None, h) is False


def test_wheel_lane_intent_spec_consumer_surface():
    # The upstream consumer surface this resolver's later extraction slice
    # will read: the golden IntentSpec payload projects criteria by name.
    binding, goldens = _wheel_lane()
    kew = (goldens / "fixtures" / "artifacts" / "intentspec_payment" / "artifact.kew").read_bytes()
    art = binding.from_bytes(kew)
    criteria = art.iter_criteria()
    assert criteria, "golden IntentSpec artifact must declare criteria"
    spec = art.intent_spec()
    assert spec is not None
    assert [c["name"] for c in spec["criteria"]] == criteria
