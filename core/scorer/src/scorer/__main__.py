"""Run the service: python -m scorer (host/port via SCORER_HOST/SCORER_PORT).

Resolver configuration (all-or-nothing; CONTRACT.md §8):
  SCORER_ARTIFACT_DIR        directory of .kew artifacts (indexed by content hash)
  SCORER_VERIFY_INPUTS_DIR    keydir.json / context.json / policy.json / registry.json
  SCORER_EXPORTED_AT_UNIX    explicit export instant (no wallclock)
Unset => NullResolver (verification skipped, visibly noted in basis).
Partially set, or set without the ke-artifact-py wheel => refuse to boot: a
server the operator configured to verify must never silently not-verify.

Facts: SCORER_FACTS_JSON (a criterion -> number JSON object). Unset means an
EMPTY fact map — every criterion is UNEVALUABLE and the gate refuses
everything (fail-closed). A demo deployment injects its own facts file here
(see the repo root for a worked example). Either way it is a StaticFactSource
— static configuration, NOT a live fact source (that is a later slice; do not
fake one).
"""

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


def facts_from_env() -> FactSource | None:
    raw = os.environ.get("SCORER_FACTS_JSON")
    if raw is None:
        return None  # create_app falls back to the empty fact map (fail-closed)
    facts = json.loads(raw)
    if not isinstance(facts, dict):
        raise SystemExit("SCORER_FACTS_JSON must be a JSON object of criterion -> number")
    return StaticFactSource({k: float(v) for k, v in facts.items()})


def main() -> None:
    uvicorn.run(
        create_app(facts=facts_from_env(), resolver=resolver_from_env()),
        host=os.environ.get("SCORER_HOST", "127.0.0.1"),
        port=int(os.environ.get("SCORER_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
