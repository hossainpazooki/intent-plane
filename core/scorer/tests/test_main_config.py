"""Boot-time env configuration (`python -m scorer`): the all-or-nothing resolver
config and the StaticFactSource override. These are the fail-loud seams — a
server configured to verify must never silently not-verify — tested without
starting a server."""

import pytest

from scorer.__main__ import facts_from_env, resolver_from_env, verify_hashes_from_env

RESOLVER_VARS = ("SCORER_ARTIFACT_DIR", "SCORER_VERIFY_INPUTS_DIR", "SCORER_EXPORTED_AT_UNIX")
OTHER_VARS = ("SCORER_FACTS_JSON", "SCORER_FACTS_MODULE", "SCORER_VERIFY_HASHES")


def _clear(monkeypatch):
    for var in RESOLVER_VARS + OTHER_VARS:
        monkeypatch.delenv(var, raising=False)


def test_no_env_means_null_resolver_default(monkeypatch):
    _clear(monkeypatch)
    assert resolver_from_env() is None


@pytest.mark.parametrize("present", RESOLVER_VARS)
def test_partial_resolver_config_refuses_to_boot(monkeypatch, present):
    _clear(monkeypatch)
    monkeypatch.setenv(present, "some-value")
    with pytest.raises(SystemExit):
        resolver_from_env()


def test_no_facts_env_returns_none(monkeypatch):
    _clear(monkeypatch)
    assert facts_from_env() is None


def test_facts_env_builds_static_source(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SCORER_FACTS_JSON", '{"amount_under_ceiling": 2000000}')
    facts = facts_from_env()
    assert facts is not None
    assert facts.get("amount_under_ceiling", "any-intent") == 2000000.0
    assert facts.get("unknown", "any-intent") is None


def test_facts_env_non_object_refuses(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SCORER_FACTS_JSON", "[1, 2]")
    with pytest.raises(SystemExit):
        facts_from_env()


# --- SCORER_FACTS_MODULE (CONTRACT.md §8, 2026-11-03) --------------------------


def test_facts_module_receives_the_static_fallback(monkeypatch, tmp_path):
    _clear(monkeypatch)
    (tmp_path / "hookmod.py").write_text(
        "captured = {}\n"
        "class Src:\n"
        "    def get(self, criterion, intent_id):\n"
        "        return 1.0 if criterion == 'hooked' else None\n"
        "def fact_source_from_env(fallback):\n"
        "    captured['fallback'] = fallback\n"
        "    return Src()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("SCORER_FACTS_JSON", '{"alpha": 2}')
    monkeypatch.setenv("SCORER_FACTS_MODULE", "hookmod")
    src = facts_from_env()
    import hookmod  # noqa: E402 — the module the hook just loaded

    assert src.get("hooked", "i") == 1.0
    assert hookmod.captured["fallback"].get("alpha", "i") == 2.0


def test_facts_module_not_importable_refuses(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SCORER_FACTS_MODULE", "no_such_module_anywhere")
    with pytest.raises(SystemExit):
        facts_from_env()


def test_facts_module_without_factory_refuses(monkeypatch, tmp_path):
    _clear(monkeypatch)
    (tmp_path / "nofactory.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("SCORER_FACTS_MODULE", "nofactory")
    with pytest.raises(SystemExit):
        facts_from_env()


# --- SCORER_VERIFY_HASHES (CONTRACT.md §8, 2026-11-03) -------------------------


def test_verify_mode_defaults_to_all(monkeypatch):
    _clear(monkeypatch)
    assert verify_hashes_from_env(False) == "all"
    assert verify_hashes_from_env(True) == "all"


def test_verify_mode_rule_requires_the_resolver_block(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SCORER_VERIFY_HASHES", "rule")
    assert verify_hashes_from_env(True) == "rule"
    with pytest.raises(SystemExit):
        verify_hashes_from_env(False)


def test_verify_mode_unknown_refuses(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SCORER_VERIFY_HASHES", "both")
    with pytest.raises(SystemExit):
        verify_hashes_from_env(True)
