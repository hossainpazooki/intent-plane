# Handoff index

Pointers only; state and evidence live in the dated entries. Entries are
immutable once written — a later session writes a new entry, never edits an
old one. Pick up with `/rigor:pickup`, which re-verifies a brief's claims
instead of trusting them.

| brief | scope | one-line hook |
|---|---|---|
| [2026-07-13-atlas-treasury-payment-loop.md](2026-07-13-atlas-treasury-payment-loop.md) | tic + RRE + COMPASS | reader slice merged, ADR-0022/PR #14 merged, Stage C(b) at PR #7, full loop probed green live; next = merge #7, KV ledger, extraction slice |
| [2026-08-02-intent-plane-gate-interface.md](2026-08-02-intent-plane-gate-interface.md) | tic | thin-spec defense (empty-criteria + volatility, red-first), boundary+vocab gates, CONTRACT-INTERFACE, P1 falsified in pitch register; commits pending operator |
