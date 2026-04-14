# FX Infrastructure: Progress Overview

*Derived from SPEC.md and IMPLEMENTATION_STATUS.md. Not a source of truth — see those documents for details.*
*Last updated: 2026-04-14T18:59Z*

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

## Overall Progress — ~35% of non-deferred SPEC

| Stage | SPEC Components | Weight | Progress | Weighted |
|-------|----------------|--------|----------|----------|
| Shared Foundation | §2 current state | ~10% | 100% | 10% |
| Dual-Currency Entries | C3 (partial) | ~10% | ~80% | 8% |
| Trading Account + G/L | C4 | ~20% | ~55% | 11% |
| Fiat Revaluation | C5 fiat, C7 fiat jobs | ~20% | 0% | 0% |
| Collateral Revaluation | C6 | ~12% | ~30% | 3.5% |
| BTC Fair Value Reval | C5 BTC, C7 BTC jobs | ~10% | 0% | 0% |
| Closing Rate Storage | C1 minimal | ~6% | ~10% | 0.5% |
| Rate Type Migration | C3/C4 architectural | ~5% | ~20% | 1% |
| Job Orchestration | C7 (shared infra) | ~7% | ~5% | 0.5% |
| **Total (non-deferred)** | | **100%** | | **~35%** |

*Deferred items (full C1/C2, segregation, on-chain reconciliation, regulatory) are excluded — they are trigger-gated and not sequenced. Against the full SPEC including deferred work, overall completion is closer to ~21–25%. The non-deferred figure is used here because deferred items each have specific trigger conditions and no one should be sequencing them yet.*

*Methodology: weights reflect relative implementation effort estimated from SPEC pseudocode volume and dependency complexity. Progress percentages are derived from per-stage item counts and status symbols. Updated each status cycle.*

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
│  █████████████████░░░ │ ~85%             │  ██████░░░░░░░░░░░░░░ │ ~30%
└───────────┬───────────┘                  └───────────┬───────────┘
            │                                          │
            │ revaluation needs                        │ fair-value collector
            │ book-value baselines                     │ must exclude collateral
            ▼                                          ▼
┌───────────────────────┐                  ┌───────────────────────┐
│  Trading Account      │                  │  Fair Value           │
│  + Realized G/L       │                  │  Revaluation          │
│  ███████████░░░░░░░░░ │ ~55%             │  ░░░░░░░░░░░░░░░░░░░░ │ 0%
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
| `CurrencyCode`, `CurrencySet`, `CurrencyMap`, `AnyCurrency` | #4497, #4531, #4414 | bodymindarts, thevaibhav-dixit |
| `MinorUnits` safety: generic `Mul`, checked arithmetic, `FormatCurrency` trait | #4524, #4553, #4584 | thevaibhav-dixit |
| `CalculationAmount<C>` — high-precision financial arithmetic | #4421 | bodymindarts |
| `QuantizationPolicy` — currency-specific rounding/precision | #4668 | bodymindarts |
| `ExchangeRate<B,Q>` generics + `ReferenceRate` + `AnyReferenceRate` | #4817 | bodymindarts |
| `PriceClient` trait — per-provider price fetch with aggregation | #4817 | bodymindarts |

**Fiat FX chain also has** chain-specific foundation work already merged: currency-aware deposit infrastructure (#4561, #4591, #4616, #4671), rate metadata on deposits (#4559), `core/fx` crate scaffolding (#4430), and deposit public event multicurrency migration (#5055, in progress). These are reflected in the Fiat FX stages above rather than here because the BTC chain does not depend on them.

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

### Trading Account + Realized G/L                                     ~55%
```
████████████████░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| `core/fx` crate scaffolding + CoA (3200, 4200, 5100) | ✅ Merged | vindard |
| Domain primitives (`FxConversion`, `FunctionalRate`, etc.) | ✅ Merged (#4957, 2026-04-14) | vindard |
| `FxPosition` entity (Selinger accumulator) | ✅ Merged (#4957, 2026-04-14) | vindard |
| `AnyCurrency` integration (replaces `CurrencyCode` + manual precision) | ✅ Merged (#5048, 2026-04-14) | vindard |
| CALA templates (conversion 6-entry, G/L clearing, settlement 4-entry) | 🔵 Written, no review (#4958) | vindard |
| `CoreFx::convert_fiat_fx()` + `settle_fx()` orchestration | 🔵 Written, no review (#4958) | vindard |
| Settlement book-value leg + `OutflowResult` | 🔵 Written, no review (#4970) | vindard |
| Rate metadata on all 3 FX templates | 🔵 Written, no review (#4970) | vindard |
| Integration tests (conversion + settlement) | 🔵 Written, no review (#4970) | vindard |

**PR chain:** ~~#4957~~ ✅ → ~~#5048~~ ✅ → #5072 (currency registry macro, draft) → #4958 (draft) → #4970 (draft). Foundation chain fully merged. #5072 is a new intermediate cleanup PR.
**Also needs:** Rate Type Migration (cross-cutting) for full rate service wiring (Gaps 5, 6).
**Next action:** vindard to un-draft #5072, then #4958/#4970 for review. jirijakes to review #4958 and #4970.

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

### Collateral Revaluation                                             ~30%
```
█████████░░░░░░░░░░░░░░░░░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| Collateral lot tracking (`CollateralLot` entity, PR #4959) | ✅ Merged (2026-04-14) | jirijakes |
| BTC collateral revaluation (PR #4821) | 🔶 Open, early | jirijakes |
| Both-sides revaluation template (`collateral_revalue`) | ⬜ Not started | — |
| Collateral EndOfDay job chain | ⬜ Not started | — |
| Collateral-vs-owned BTC boundary (for Fair Value Reval) | ⬜ Not started | — |

**Next action:** #4959 merged 2026-04-14 (approved by Prabhat1308, vindard, nsandomeno). #5064 merged 2026-04-14 (liquidation calculator robustness). #4821 (BTC collateral revaluation) is now unblocked — jirijakes can build on the lot entity. No activity on #4821 since 2026-04-07. Template and jobs can proceed in parallel.

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
| #5063 | Bump cala 0.15.2, job 0.6.18, obix 0.2.21 | ✅ Merged 2026-04-14 | Dependency updates |
| #5064 | Liquidation calculator robustness | ✅ Merged 2026-04-14 | Clamp-based calc, premium sign fix |
| #5060 | Bank price snapshots to DW | 🔵 Open (sandipndev) | Historical price data in DW |
| #4757 | Eventually consistent account sets | 🔶 Draft (cala-ledger upgraded to 0.15.0, 24 commits) | Multi-currency throughput |
| ~~#5041~~ | ~~Bump cala-ledger to 0.15.1~~ | ❌ Closed 2026-04-13 | — |

---

## Critical Path (Fiat FX)

```
 #4960 ✅ ──► #4957 ✅ ──► #5048 ✅ ──► #5072 draft ──► #4958/#4970 review ──► Merge ──► Reval ──► Done
 (merged)     (merged)     (merged)     (new cleanup)   (no review yet)        (~2 PRs)   (all new)
```

Major milestone: #4957 and #5048 both merged today. The foundation chain is fully on main. Bottleneck is now #5072 (small cleanup) → #4958/#4970 review by jirijakes.

---

## Risks & Acceleration

### Unowned work
The three largest 0%-complete stages have **no owner and no started code**:
- **Fiat Revaluation** (~20% of total) — 7 items, blocked upstream but SPEC has full pseudocode (Component 5)
- **BTC Fair Value Revaluation** (~10% of total) — 4 items, blocked by collateral boundary + ASU 2023-08 sign-off
- **Fiat rate source adapter** — hard prerequisite for fiat revaluation in production; no EUR/USD or GBP/USD rates exist today

### Review bottleneck
jirijakes is the primary reviewer for the FX chain and also the sole developer on the BTC chain. 5 written-but-unreviewed items in Trading Account (#4958, #4970) are waiting on him. Prabhat1308 is available as a second reviewer.

### Highest-leverage actions (ordered)
1. **Merge #5072 → #4958 → #4970** — Trading Account 55% → ~90%. Unblocks fiat revaluation.
2. **Build dual-currency RECORD_WITHDRAWAL** — Dual-Currency Entries 80% → 100%. Removes last Gap 2 blocker.
3. **Revive #4923 (rate history)** — Closing Rate Storage is a prerequisite for both revaluation chains. Stale 1 week.
4. **Assign fiat revaluation owner** — the largest remaining body of work with no one driving it.

---

## Next Actions by Person

*Updated 2026-04-14.*

### vindard
1. ~~**Un-draft and merge #4978**~~ — ✅ merged 2026-04-10.
2. ~~**Respond to jirijakes' latest feedback on #4957**~~ — ✅ responded 2026-04-13, opened #5048.
3. ~~**Review #4959 (collateral lot tracking)**~~ — ✅ approved 2026-04-13, merged 2026-04-14.
4. ~~**Un-draft #4957 and #5048 for merge**~~ — ✅ both merged 2026-04-14.
5. **Un-draft #5072 (currency registry macro)** — small cleanup, then un-draft #4958/#4970 for review.
6. **Rate Type Migration (Gap 4)** — now unblocked since #4957 chain is on main. `ExchangeRate` → `ConversionRate` rename target exists on main.

### nsandomeno
1. **Dual-currency `RECORD_WITHDRAWAL`** — deposit side (#4960) is merged; withdrawal is the natural follow-up to complete Gap 2.

### thevaibhav-dixit
1. **Finish #5055 (deposit public events → AnyMinorUnits)** — address nsandomeno's review feedback on Sumsub `currencyType` needing dynamic resolution from `CurrencyCode`.
2. **Dual-currency `RECORD_WITHDRAWAL`** — could pair with nsandomeno on this; #5055 advances the deposit module's multicurrency migration which is prerequisite context.
3. **Continue deposit multicurrency migration** — #5055 is the first step; follow-ups likely needed for full `PublicDeposit`/`PublicWithdrawal` multicurrency support.

### Prabhat1308
1. **Revive #4923 (Rate History)** — stale since 2026-04-07. `AggregatePriceHandler` delivering to `exchange_rates` table + outbox. Relevant to Gap 1 (historical rate lookup). Requested reviewers: nsandomeno, vindard.
2. **Review FX chain PRs** — available as reviewer for #4958/#4970 given familiarity with `CalculationAmount<C>` (#4421) which underpins the exchange rate types.

### jirijakes
1. ~~**Merge #4959 (collateral lot tracking)**~~ — ✅ merged 2026-04-14.
2. ~~**Review #5048 (AnyCurrency refactor)**~~ — ✅ approved 2026-04-14.
3. **Review #4958 and #4970** — next in the FX chain. Foundation is merged; these are conversion orchestration and settlement book-value leg.
4. **Continue #4821 (BTC collateral revaluation)** — unblocked by #4959 merge. No updates since 2026-04-07.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Merged — on main |
| 🟢 | Approved — ready to merge, not yet landed |
| 🔵 | Code written and tested — awaiting human review |
| 🔶 | In progress or exploratory — not yet review-ready |
| ⬜ | Not started |
