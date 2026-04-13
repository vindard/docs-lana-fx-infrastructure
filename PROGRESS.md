# FX Infrastructure: Progress Overview

*Derived from SPEC.md and IMPLEMENTATION_STATUS.md. Not a source of truth — see those documents for details.*
*Last updated: 2026-04-13T15:08Z*

## Naming Map

This document uses descriptive names. The SPEC and IMPLEMENTATION_STATUS use legacy Group/Phase labels from a broader multicurrency roadmap. The mapping:

| This document | SPEC label | IMPLEMENTATION_STATUS gaps |
|---------------|------------|---------------------------|
| Shared Foundation | Current State (SPEC §2) | — (all merged) |
| Fiat FX > Dual-Currency Entries | Group A | Gap 1, Gap 2 |
| Fiat FX > Trading Account + Realized G/L | Phase 3 (Group B) | Gap 3 |
| Fiat FX > Revaluation | Phase 4 (Group B) | — |
| BTC > Collateral Revaluation | Phase 2 (Group C) | — |
| BTC > Fair Value Revaluation | Phase 5 (Group C) | — |
| Cross-Cutting > Closing Rate Storage | Deferred C1 (minimal subset) | Gap 1 (partial) |
| Cross-Cutting > Rate Type Migration | — | Gap 4, Gap 5, Gap 6 |

---

## Dependency Graph

```
                    SHARED FOUNDATION ✅ 100%
                    ════════════════════════
                    ┌───────────────────────────────────────────────┐
                    │  Currency types, ExchangeRate<B,Q> generics,  │
                    │  PriceClient trait, CalculationAmount,        │
                    │  precision/quantization infrastructure        │
                    │  ████████████████████ │ 100% — all merged     │
                    └──────────────┬────────┬───────────────────────┘
                                   │        │
                      ┌────────────┘        └────────────┐
                      ▼                                  ▼
FIAT FX CHAIN                              BTC CHAIN
═══════════                                ═════════

┌───────────────────────┐                  ┌───────────────────────┐
│  Dual-Currency        │                  │  Collateral           │
│  Entries              │                  │  Revaluation          │
│  █████████████████░░░ │ ~85%             │  █████░░░░░░░░░░░░░░░ │ ~25%
└───────────┬───────────┘                  └───────────┬───────────┘
            │                                          │
            │ revaluation needs                        │ fair-value collector
            │ book-value baselines                     │ must exclude collateral
            ▼                                          ▼
┌───────────────────────┐                  ┌───────────────────────┐
│  Trading Account      │                  │  Fair Value           │
│  + Realized G/L       │                  │  Revaluation          │
│  ██████████░░░░░░░░░░ │ ~50%             │  ░░░░░░░░░░░░░░░░░░░░ │ 0%
└───────────┬───────────┘                  └───────────────────────┘
            │
            │ revaluation reads from
            │ accumulator + ledger
            ▼
┌───────────────────────┐
│  Revaluation          │
│  (Unrealized)         │◄──── needs Closing Rate Storage
│  ░░░░░░░░░░░░░░░░░░░░ │ 0%       (cross-cutting)
└───────────────────────┘

The two chains are fully independent but both
build on the shared foundation merged to main.

CROSS-CUTTING (needed by specific stages)
══════════════
┌───────────────────────┐   ┌─────────────────────────┐
│  Closing Rate         │   │  Rate Type Migration    │
│  Storage              │   │  (core/price → core/fx) │
│  ██░░░░░░░░░░░░░░░░░░ │   │  ████░░░░░░░░░░░░░░░░   │
│  ~10%                 │   │  ~20%                   │
└───────────────────────┘   └─────────────────────────┘
 Minimal C1 subset for       Gap 4 — needed for Trading
 fiat + BTC revaluation      Account (Gap 5, Gap 6)

DEFERRED (trigger-gated, not sequenced)
════════
┌─────────────────────────────────────────────────────┐
│  Full rate storage · Multi-source aggregation       │
│  Rate health · Segregation controls                 │
│  On-chain reconciliation · Regulatory/reporting     │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└─────────────────────────────────────────────────────┘
 Not blocked — each item has its own trigger condition.
 See Deferred table below for details.
```

---

## Shared Foundation                                                     100%
```
██████████████████████████████
```

Infrastructure merged to main that both chains build upon.

| Item | PR | Owner |
|------|----|-------|
| `CurrencyCode`, `CurrencySet`, `CurrencyMap`, `AnyCurrency` | #4497, #4531, #4414 | bodymindarts |
| `CalculationAmount<C>` — high-precision financial arithmetic | #4421 | bodymindarts |
| `QuantizationPolicy` — currency-specific rounding/precision | #4668 | bodymindarts |
| `ExchangeRate<B,Q>` generics + `ReferenceRate` + `AnyReferenceRate` | #4817 | bodymindarts |
| `PriceClient` trait — per-provider price fetch with aggregation | #4817 | bodymindarts |

**Fiat FX chain also has** chain-specific foundation work already merged: currency-aware deposit infrastructure (#4561, #4591, #4616, #4671), rate metadata on deposits (#4559), and `core/fx` crate scaffolding (#4430). These are reflected in the Fiat FX stages above rather than here because the BTC chain does not depend on them.

---

## Fiat FX Chain

### Dual-Currency Entries                                              ~80%
```
████████████████████████░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| Rate primitives (`ExchangeRate<B,Q>`, `AnyReferenceRate`, `Rate`) | ✅ Merged | bodymindarts |
| Per-provider price fetch (`PriceClient` trait) | ✅ Merged | bodymindarts |
| Rate metadata on `RECORD_DEPOSIT` | ✅ Merged | nsandomeno |
| Spot vs historical rate separation | ✅ Merged (#4960) | nsandomeno |
| Dual-currency `RECORD_DEPOSIT` (4-entry variant) | ✅ Merged (#4960) | nsandomeno |
| Dual-currency `RECORD_WITHDRAWAL` | ⬜ Not started | — |

**Next action:** Build withdrawal dual-currency variant.

---

### Trading Account + Realized G/L                                     ~50%
```
██████████████░░░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| `core/fx` crate scaffolding + CoA (3200, 4200, 5100) | ✅ Merged | vindard |
| Domain primitives (`FxConversion`, `FunctionalRate`, etc.) | 🔶 Review in progress (jirijakes) | vindard |
| `FxPosition` entity (Selinger accumulator) | 🔶 Review in progress (jirijakes) | vindard |
| CALA templates (conversion 6-entry, G/L clearing, settlement 4-entry) | 🔵 Written, no review | vindard |
| `CoreFx::convert_fiat_fx()` + `settle_fx()` orchestration | 🔵 Written, no review | vindard |
| Settlement book-value leg + `OutflowResult` | 🔵 Written, no review | vindard |
| Rate metadata on all 3 FX templates | 🔵 Written, no review | vindard |
| Integration tests (conversion + settlement) | 🔵 Written, no review | vindard |

**PR chain:** #4957 → #4958 → #4970 (all draft, rebased 2026-04-11). #4957 review in progress — jirijakes gave initial feedback (2026-04-10); vindard responded with 6 follow-up commits. **Latest (2026-04-11T12:05Z):** jirijakes suggests `is_fiat()` should be a property of `Currency` rather than `CurrencyCode` — vindard has not yet responded.
**Also needs:** Rate Type Migration (cross-cutting) for full rate service wiring (Gaps 5, 6).
**Next action:** Vindard to respond to jirijakes' latest feedback on `Currency` vs `CurrencyCode` for `is_fiat()`, then continue review iteration.

---

### Revaluation (Unrealized)                                           0%
```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| Unrealized FX accounts (6100/6200) in CoA | ⬜ Not started | — |
| Fiat FX revaluation job chain (handler → collector → worker) | ⬜ Not started | — |
| Delta method worker (branch: regular acct vs Trading acct) | ⬜ Not started | — |
| Cumulative revaluation tracker (`cumulative_reval` per account) | ⬜ Not started | — |
| Withdrawal reval-unwind (3-phase proportional reverse) | ⬜ Not started | — |
| Settlement reval-unwind | ⬜ Not started | — |
| Reconciliation job | ⬜ Not started | — |

**Blocked by:** Dual-Currency Entries (book values in ledger) + Trading Account (accumulator) + Closing Rate Storage (cross-cutting).
**Open question:** OQ-1 — orphaned USD on Omnibus after partial settlement (see SPEC.md).
**Reference:** SPEC Component 5 has full job code; walkthrough has expected values for all 9 reval steps.

---

## Cross-Cutting

These aren't part of either chain but are prerequisites that both chains (or stages within them) depend on.

### Closing Rate Storage                                               ~10%
```
███░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

A minimal subset of SPEC Component 1 — just enough to persist and look up closing rates for revaluation. Not the full `exchange_rates` table with triangulation, multi-source aggregation, and staleness enforcement (those remain deferred).

| Item | Status | Owner |
|------|--------|-------|
| `ExchangeRate<B,Q>` type with persistence support | ✅ Merged (in `core/price`) | bodymindarts |
| Closing rate capture (EOD snapshot of spot rate) | ⬜ Not started | — |
| Rate lookup by `(pair, date, rate_type)` | 🔶 Explored (#4923, stale) | Prabhat1308 |
| Fiat rate source adapter (EUR/USD, GBP/USD) | ⬜ Not started | — |

**Needed by:** Fiat FX Revaluation (closing rates for delta method), BTC revaluation stages (BTC closing rate — currently uses `PriceOfOneBTC` which works for now but has no persistence).
**Note:** BTC revaluation can start with the existing price feed. Fiat revaluation cannot — there is no fiat rate source today.

---

### Rate Type Migration (`core/price` → `core/fx`)                    ~20%
```
██████░░░░░░░░░░░░░░░░░░░░░░░░
```

SPEC designates `core/fx` as the domain owner of FX infrastructure. Rate metadata types currently live in `core/price` and need to migrate. See IMPLEMENTATION_STATUS Gap 4.

| Item | Status | Owner |
|------|--------|-------|
| Prerequisite type refactoring (`ExchangeRate<B,Q>`, generics) | ✅ Merged (#4817) | bodymindarts |
| Rename `ExchangeRate` → `ConversionRate` in `core/fx` (disambiguate) | ⬜ Not started | — |
| Migrate `ReferenceRate`, `AnyReferenceRate`, `RateType` to `core/fx` | ⬜ Not started | — |
| Wire `core/price` as a rate source adapter behind `core/fx` | ⬜ Not started | — |

**Needed by:** Trading Account stage (Gap 5 service-layer metadata construction, Gap 6 rate service wiring).
**Can be done independently** — no runtime dependency, purely architectural.

---

## BTC Chain

### Collateral Revaluation                                             ~25%
```
████████░░░░░░░░░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| Collateral lot tracking (`CollateralLot` entity, PR #4959) | 🟢 Approved by Prabhat1308 (2026-04-13), 13 commits | jirijakes |
| BTC collateral revaluation (PR #4821) | 🔶 Open, early | jirijakes |
| Both-sides revaluation template (`collateral_revalue`) | ⬜ Not started | — |
| Collateral EndOfDay job chain | ⬜ Not started | — |
| Collateral-vs-owned BTC boundary (for Fair Value Reval) | ⬜ Not started | — |

**Next action:** #4959 (lot tracking) approved by Prabhat1308 (2026-04-13) — 13 commits, rebased 2026-04-13. New work: amount validation, status inside events, panic guards. Ready to merge (needs second approval or maintainer merge). Template and jobs can proceed in parallel.

---

### Fair Value Revaluation                                             0%
```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| BTC Fair Value Gain/Loss accounts (7100/7200) in CoA | ⬜ Not started | — |
| BTC fair value revaluation job chain | ⬜ Not started | — |
| Collector excludes collateral accounts | ⬜ Not started | — |
| ASU 2023-08 compliance review | ⬜ Not started | — |

**Blocked by:** Collateral Revaluation (boundary). Also needs ASU 2023-08 sign-off.
**Open question:** OQ-2 — platform-owned BTC lot tracking for disposals (see SPEC.md).

---

## Deferred

| Area | What | Trigger to build |
|------|------|------------------|
| Full rate storage (C1 beyond minimal) | Historical lookups, inverse/cross-rate triangulation, `ExchangeRateService` | Multi-pair production support needed |
| Multi-source aggregation (C2) | Coinbase/Kraken adapters, median aggregator, tolerance bands | Operational resilience priority |
| Rate health (C2) | Staleness enforcement, circuit breakers, monitoring job | Multi-source aggregation exists |
| Segregation controls (C6) | CALA template restrictions on collateral accounts | Regulatory attestation requirement |
| On-chain reconciliation (C6) | Custody wallet ↔ ledger balance comparison | Custody API available |
| Regulatory/reporting (C8) | Audit trail, rate methodology docs, ASC 830 cash flow | Core infrastructure in place |

---

## Infrastructure PRs

| PR | What | Status | Impact |
|----|------|--------|--------|
| #4978 | Bitfinex price poller fix (11th field) | ✅ Merged 2026-04-10 | BTC/USD rates restored on staging |
| #4757 | Eventually consistent account sets | 🔶 Draft (cala-ledger upgraded to 0.15.0) | Multi-currency throughput |
| #5041 | Bump cala-ledger to 0.15.1 | 🔶 Draft (Lakshyyaa, 2026-04-13) | Ledger infrastructure |

---

## Critical Path (Fiat FX)

```
 #4960 ✅ ──► #4957 review ──► #4958/#4970 review ──► Merge chain ──► Revaluation ──► Done
 (merged)     (in progress)    (no review yet)        (~2200 lines)   (all new work)
```

The bottleneck is human review of vindard's #4957→#4958→#4970 chain. #4957 review is actively iterating with jirijakes (6 follow-up commits pushed 2026-04-11).

---

## Next Actions by Person

*Updated 2026-04-13.*

### vindard
1. ~~**Un-draft and merge #4978**~~ — ✅ merged 2026-04-10.
2. **Respond to jirijakes' latest feedback on #4957** — jirijakes (2026-04-11T12:05Z) suggests `is_fiat()` should be on `Currency` not `CurrencyCode`. Unaddressed. Bottleneck for entire Fiat FX chain (~2200 lines across #4957→#4958→#4970).
3. **Rate Type Migration (Gap 4) — deferred until #4957 chain lands.**
   Premature because rename target (`ExchangeRate` → `ConversionRate`) only exists in #4957, not on main. See previous rationale.

### nsandomeno
1. **Dual-currency `RECORD_WITHDRAWAL`** — deposit side (#4960) is merged; withdrawal is the natural follow-up to complete Gap 2.

### jirijakes
1. **Merge #4959 (collateral lot tracking)** — approved by Prabhat1308 (2026-04-13), 13 commits. Ready for merge or second approval. Gates BTC collateral revaluation (#4821).
2. **Continue reviewing #4957 chain** — latest feedback posted (2026-04-11); awaiting vindard's response before continuing.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Merged — on main |
| 🟢 | Approved — ready to merge, not yet landed |
| 🔵 | Code written and tested — awaiting human review |
| 🔶 | In progress or exploratory — not yet review-ready |
| ⬜ | Not started |
