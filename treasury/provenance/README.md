# Provenance pack

Two published rule artifacts from an authoring plane's regime pack
(`mica_2023`), with the four verifier inputs (`inputs/keydir.json`,
`context.json`, `policy.json`, `registry.json`) they are checked under at
export instant `1750000000`. Vendored bytes; the scorer's resolver indexes
them by content hash (CONTRACT.md §8) when the quickstart boots with
`SCORER_VERIFY_HASHES=rule` on a host where `ke-artifact-py` imports.

| artifact | content hash | verdict under `inputs/` |
|---|---|---|
| `rule_reserve_assets/artifact.kew` | `13a414cf7f6b25c6b6049c0953a83ff5697044aabafbd44b87e87fc4ed90f8a9` | verified |
| `rule_significant_thresholds/artifact.kew` | `72a60976bcd55fc9a9b088cada4aae10cfbb4aabf066a8e85c403dbeae893d94` | rejected (legal-source hashes changed; required attestations missing) |

Probe 17 (`../probes/provenance_root_live.py`) cites the first on a
declaration that scores and the second on one that is refused before any fact
is looked up. The origin repository and per-file digests are recorded in the
maintainers' private notes, not here.
