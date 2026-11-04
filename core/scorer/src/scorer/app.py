"""FastAPI service: POST /ml/evaluate + GET /healthz (CONTRACT.md §2.4/§8).

Service errors are still evaluations: for a well-formed request every failure —
unknown criterion, missing fact, resolver failure, internal exception — answers
200 with UNEVALUABLE. Non-2xx is reserved for malformed requests (FastAPI's 422)
and infrastructure; the Go client maps those to Unevaluable anyway, so both
paths fail closed (spec invariant 2 across the network).
"""

import asyncio

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from .evaluator import evaluate
from .facts import FactSource, StaticFactSource
from .models import EvalRequest, EvalResponse
from .resolver import ArtifactResolver, NullResolver

SKIP_NOTE = "resolver=null: verification skipped; "
UNBOUND_NOTE = "rule-artifact: unbound; "
VERIFY_MODES = ("all", "rule")


def create_app(
    facts: FactSource | None = None,
    resolver: ArtifactResolver | None = None,
    verify_hashes: str = "all",
) -> FastAPI:
    if verify_hashes not in VERIFY_MODES:
        raise ValueError(
            f"verify_hashes must be one of {VERIFY_MODES}, got {verify_hashes!r}"
        )
    fact_source: FactSource = (
        facts if facts is not None else StaticFactSource({})
    )
    artifact_resolver: ArtifactResolver = (
        resolver if resolver is not None else NullResolver()
    )

    app = FastAPI(title="intent-scorer")

    @app.get("/healthz")
    def healthz() -> PlainTextResponse:
        return PlainTextResponse("ok")

    @app.post("/ml/evaluate", response_model=EvalResponse, response_model_exclude_none=True)
    async def ml_evaluate(req: EvalRequest) -> EvalResponse:
        try:
            note = ""
            if verify_hashes == "rule":
                # The spec hash is the plane's own payload hash (§2.6); no
                # artifact store holds it, so it is never handed over.
                to_verify = (req.rule_artifact_hash, None)
                if not req.rule_artifact_hash:
                    note = UNBOUND_NOTE
            else:
                to_verify = (req.rule_artifact_hash, req.intent_spec_hash)
            if any(to_verify):
                if isinstance(artifact_resolver, NullResolver):
                    # No resolver on this host: skip, but say so on the wire.
                    note = SKIP_NOTE
                else:
                    # verify() holds the GIL through crypto in the wheel-backed
                    # impl: run it off the event loop so a concurrent
                    # /ml/evaluate is never stalled (recorded GIL caveat).
                    ok = await asyncio.get_running_loop().run_in_executor(
                        None, artifact_resolver.verify, *to_verify
                    )
                    if not ok:
                        return EvalResponse(
                            result="UNEVALUABLE", basis="artifact verification failed"
                        )
            resp = evaluate(req, fact_source.get(req.criterion, req.intent_id))
            if note:
                resp = EvalResponse(result=resp.result, basis=note + (resp.basis or ""))
            return resp
        except Exception as exc:  # noqa: BLE001 — the catch-all IS the contract:
            # every internal failure is an evaluation that answers UNEVALUABLE.
            return EvalResponse(
                result="UNEVALUABLE", basis=f"internal error: {type(exc).__name__}"
            )

    return app
