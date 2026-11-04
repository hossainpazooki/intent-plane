"""Run the service: python -m scorer (host/port via SCORER_HOST/SCORER_PORT).

Resolver configuration (all-or-nothing; CONTRACT.md §8):
  SCORER_ARTIFACT_DIR        directory of .kew artifacts (indexed by content hash)
  SCORER_VERIFY_INPUTS_DIR    keydir.json / context.json / policy.json / registry.json
  SCORER_EXPORTED_AT_UNIX    explicit export instant (no wallclock)
Unset => NullResolver (verification skipped, visibly noted in basis).
Partially set, or set without the ke-artifact-py wheel => refuse to boot: a
server the operator configured to verify must never silently not-verify.

SCORER_VERIFY_HASHES (CONTRACT.md §2.4): "all" (default) hands the resolver
every hash on the request; "rule" hands it rule_artifact_hash alone (the spec
hash is the plane's own payload hash). "rule" needs the resolver block.

Facts: SCORER_FACTS_JSON (a criterion -> number JSON object) builds the static
map; unset means an EMPTY map (every criterion UNEVALUABLE, fail-closed).
SCORER_FACTS_MODULE names an importable module whose
fact_source_from_env(fallback) receives that static map and returns the
FactSource the service scores from -- the only way a LIVE fact source enters
this process. A module that does not import, or has no factory, refuses the
boot.
"""

import importlib
import json
import os

import uvicorn

from .app import create_app
from .facts import FactSource, StaticFactSource
from .resolver import ArtifactResolver


def resolver_from_env() -> ArtifactResolver | None:
    artifact_dir = os.environ.get("SCORER_ARTIFACT_DIR")
    inputs_dir = os.environ.get("SCORER_VERIFY_INPUTS_DIR")
    exported_at = os.environ.get("SCORER_EXPORTED_AT_UNIX")
    if not (artifact_dir or inputs_dir or exported_at):
        return None  # NullResolver default: skip is visible on the wire
    if not (artifact_dir and inputs_dir and exported_at):
        raise SystemExit(
            "resolver config incomplete: set ALL of SCORER_ARTIFACT_DIR, "
            "SCORER_VERIFY_INPUTS_DIR, SCORER_EXPORTED_AT_UNIX — or none"
        )
    # Import (and thereby require the wheel) only on the configured path; an
    # absent wheel here must crash the boot loudly, never downgrade to a skip.
    from .resolver import KeArtifactResolver

    return KeArtifactResolver.from_paths(artifact_dir, inputs_dir, int(exported_at))


def verify_hashes_from_env(resolver_configured: bool) -> str:
    mode = os.environ.get("SCORER_VERIFY_HASHES", "all")
    if mode not in ("all", "rule"):
        raise SystemExit("SCORER_VERIFY_HASHES must be 'all' or 'rule', got %r" % mode)
    if mode == "rule" and not resolver_configured:
        raise SystemExit(
            "SCORER_VERIFY_HASHES=rule needs the resolver block (SCORER_ARTIFACT_DIR, "
            "SCORER_VERIFY_INPUTS_DIR, SCORER_EXPORTED_AT_UNIX)"
        )
    return mode


def static_facts_from_env() -> FactSource | None:
    raw = os.environ.get("SCORER_FACTS_JSON")
    if raw is None:
        return None  # create_app falls back to the empty fact map (fail-closed)
    facts = json.loads(raw)
    if not isinstance(facts, dict):
        raise SystemExit("SCORER_FACTS_JSON must be a JSON object of criterion -> number")
    return StaticFactSource({k: float(v) for k, v in facts.items()})


def facts_from_env() -> FactSource | None:
    static = static_facts_from_env()
    module_name = os.environ.get("SCORER_FACTS_MODULE")
    if module_name is None:
        return static
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit("SCORER_FACTS_MODULE=%r is not importable: %s" % (module_name, exc))
    factory = getattr(module, "fact_source_from_env", None)
    if not callable(factory):
        raise SystemExit("SCORER_FACTS_MODULE=%r has no fact_source_from_env(fallback)" % module_name)
    return factory(static)


def main() -> None:
    resolver = resolver_from_env()
    uvicorn.run(
        create_app(
            facts=facts_from_env(),
            resolver=resolver,
            verify_hashes=verify_hashes_from_env(resolver is not None),
        ),
        host=os.environ.get("SCORER_HOST", "127.0.0.1"),
        port=int(os.environ.get("SCORER_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
