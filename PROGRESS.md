# FX Infrastructure: Progress Overview

*Derived from SPEC.md and IMPLEMENTATION_STATUS.md. Not a source of truth — see those documents for details.*
*Last updated: 2026-04-15T04:35Z*

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
| Dual-Currency Entries | C3 (partial) | ~10% | ~85% | 8.5% |
| Trading Account + G/L | C4 | ~20% | ~55% | 11% |
| Fiat Revaluation | C5 fiat, C7 fiat jobs | ~20% | 0% | 0% |
| Collateral Revaluation | C6 | ~12% | ~30% | 3.5% |
| BTC Fair Value Reval | C5 BTC, C7 BTC jobs | ~10% | 0% | 0% |
| Closing Rate Storage | C1 minimal | ~6% | ~10% | 0.5% |
| Rate Type Migration | C3/C4 architectural | ~5% | ~30% | 1.5% |
| Job Orchestration | C7 (shared infra) | ~7% | ~5% | 0.5% |
| **Total (non-deferred)** | | **100%** | | **~36%** |

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
│  ██████████████████░░ │ ~85%             │  ██████░░░░░░░░░░░░░░ │ ~30%
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
│  ██░░░░░░░░░░░░░░░░░░ │   │  ██████░░░░░░░░░░░░░░   │
│  ~10%                 │   │  ~30%                   │
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

**Fiat FX chain also has** chain-specific foundation work already merged: currency-aware deposit infrastructure (#4561, #4591, #4616, #4671), rate metadata on deposits (#4559), `core/fx` crate scaffolding (#4430), and deposit public event multicurrency migration (#5055, approved — pending un-draft). These are reflected in the Fiat FX stages above rather than here because the BTC chain does not depend on them.

---

## Fiat FX Chain

### Dual-Currency Entries                                              ~85%
```
█████████████████████████░░░░░
```

| Item | Status | Owner |
|------|--------|-------|
| Rate primitives (`ExchangeRate<B,Q>`, `AnyReferenceRate`, `Rate`) | ✅ Merged | bodymindarts |
| Per-provider price fetch (`PriceClient` trait) | ✅ Merged | bodymindarts |
| Rate metadata on `RECORD_DEPOSIT` | ✅ Merged | nsandomeno |
| Spot vs historical rate separation | ✅ Merged (#4960) | nsandomeno |
| Dual-currency `RECORD_DEPOSIT` (4-entry variant) | ✅ Merged (#4960) | nsandomeno |
| Dual-currency `RECORD_WITHDRAWAL` (5 templates + use-cases) | 🔵 Written, no review (#5078) | nsandomeno |

**Next action:** Review #5078 (withdrawal templates). #5055 (deposit public events → AnyMinorUnits) approved by nsandomeno, jirijakes commented.

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

**PR chain:** ~~#4957~~ ✅ → ~~#5048~~ ✅ → ~~#5072~~ ❌ (closed) → #4958 (**open, ready for review**) → #4970 (draft). Foundation chain fully merged; #5072 dropped, chain simplified.
**Also needs:** Rate Type Migration (cross-cutting) for full rate service wiring (Gaps 5, 6). #5080 starts the rename.
**Next action:** jirijakes to review #4958, then #4970.

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

### Rate Type Migration (`core/price` → `core/fx`)                    ~30%
```
█████████░░░░░░░░░░░░░░░░░░░░░
```

SPEC designates `core/fx` as the domain owner of FX infrastructure. Rate metadata types currently live in `core/price` and need to migrate. See IMPLEMENTATION_STATUS Gap 4.

| Item | Status | Owner |
|------|--------|-------|
| Prerequisite type refactoring (`ExchangeRate<B,Q>`, generics) | ✅ Merged (#4817) | bodymindarts |
| Rename `ExchangeRate` → `ConversionRate` in `core/fx` (disambiguate) | 🔵 Written, no review (#5080) | vindard |
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

**Next action:** **Deprioritized** — BTC revaluation is on hold until fiat revaluation is complete and there is more clarity on what BTC the bank will carry. #4959 (lot entity) and #5064 (liquidation calculator) are merged foundations. jirijakes redirected to Closing Rate Storage and Fiat Revaluation.

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
| #5077 | RBAC snake_case permission set names (collateral) | ✅ Merged 2026-04-15 | Collateral module authz fix |
| #5063 | Bump cala 0.15.2, job 0.6.18, obix 0.2.21 | ✅ Merged 2026-04-14 | Dependency updates |
| #5064 | Liquidation calculator robustness | ✅ Merged 2026-04-14 | Clamp-based calc, premium sign fix |
| #5060 | Bank price snapshots to DW | 🔵 Open (sandipndev) | Historical price data in DW |
| #4757 | Eventually consistent account sets | 🔶 Draft (cala-ledger upgraded to 0.15.0, 24 commits) | Multi-currency throughput |
| ~~#5041~~ | ~~Bump cala-ledger to 0.15.1~~ | ❌ Closed 2026-04-13 | — |

---

## Critical Path (Fiat FX)

```
 #4960 ✅ ──► #4957 ✅ ──► #5048 ✅ ──► #4958 open ──► #4970 draft ──► Merge ──► Reval ──► Done
 (merged)     (merged)     (merged)     (ready for      (no review)    (~2 PRs)   (all new)
                                         review)
```

#5072 closed, chain simplified. #4958 un-drafted and ready for review. Bottleneck is now jirijakes reviewing #4958 → #4970. In parallel: #5078 (withdrawal templates, nsandomeno) and #5080 (ConversionRate rename, vindard).

---

## Risks & Acceleration

### Unowned work
The three largest 0%-complete stages have **no owner and no started code**:
- **Fiat Revaluation** (~20% of total) — 7 items, blocked upstream but SPEC has full pseudocode (Component 5)
- **BTC Fair Value Revaluation** (~10% of total) — 4 items, blocked by collateral boundary + ASU 2023-08 sign-off
- **Fiat rate source adapter** — hard prerequisite for fiat revaluation in production; no EUR/USD or GBP/USD rates exist today

### Review bottleneck
jirijakes is the primary reviewer for the FX chain. 5 written-but-unreviewed items in Trading Account (#4958, #4970) are waiting on him. With BTC revaluation deprioritized, jirijakes is redirected to Closing Rate Storage (with Prabhat1308). Fiat Revaluation is split: vindard (core job chain, tracker, worker) + nsandomeno (withdrawal/settlement reval-unwind). Prabhat1308 is available as a second reviewer for #4958/#4970.

### Highest-leverage actions (ordered)
1. **Review and merge #4958 → #4970** — Trading Account 55% → ~90%. Unblocks fiat revaluation. #4958 is open and ready for review. (jirijakes)
2. **Closing Rate Storage (jirijakes leading Prabhat1308)** — hard prerequisite for both revaluation chains. Revive #4923, add closing rate capture (EOD snapshot), rate lookup by `(pair, date, rate_type)`, fiat rate source adapter. Without rate storage, revaluation code has nothing to read from.
3. **Review #5078 (withdrawal templates)** — Dual-Currency Entries 85% → ~100%. nsandomeno already writing; needs review.
4. **Fiat Revaluation (vindard + nsandomeno)** — vindard owns core job chain, cumulative_reval tracker, delta method worker (extends his core/fx work). nsandomeno owns withdrawal/settlement reval-unwind (extends his withdrawal template work).

---

## Next Actions by Person

*Updated 2026-04-15.*

### vindard
1. ~~**Un-draft and merge #4978**~~ — ✅ merged 2026-04-10.
2. ~~**Un-draft #4957 and #5048 for merge**~~ — ✅ both merged 2026-04-14.
3. ~~**Un-draft #4958**~~ — ✅ un-drafted 2026-04-14, ready for review.
4. **Get #5080 reviewed (ConversionRate rename)** — Gap 4 step 1, small mechanical rename in `core/fx`.
5. **Un-draft #4970 once #4958 merges** — settlement book-value leg + rate metadata.
6. **Continue Rate Type Migration (Gap 4)** — after #5080 merges, migrate `ReferenceRate`/`AnyReferenceRate` from `core/price` → `core/fx`.
7. **Fiat Revaluation ownership** — once #4970 merges and Gap 4 migration lands: cumulative_reval tracker (event-sourced entity), delta method worker, revaluation template (6100/6200 accounts), revaluation job chain (handler → collector → worker). Natural extension of core/fx work. SPEC Component 5 has full pseudocode.

### nsandomeno
1. **Finish #5078 (withdrawal dual-currency templates)** — 13 commits, 5 templates + use-cases. Get review.
2. ~~**Review #5055**~~ — ✅ approved 2026-04-15.
3. **Withdrawal reval-unwind + settlement reval-unwind** — after #5078 merges. nsandomeno owns the withdrawal flow (#4960, #5078) so the 3-phase proportional reval-unwind on withdrawal and settlement fits naturally. Pairs with vindard's revaluation work.

### thevaibhav-dixit
1. **Un-draft #5055 (deposit public events → AnyMinorUnits)** — approved by nsandomeno. jirijakes noted `is_fiat()` exists on `Currency` from #5048, which may resolve the Sumsub concern.
2. **Continue deposit multicurrency migration** — follow-ups likely needed for full `PublicDeposit`/`PublicWithdrawal` multicurrency support.

### Prabhat1308
1. **Closing Rate Storage (led by jirijakes)** — revive #4923 (`exchange_rates` table + outbox delivery), extend with closing rate capture and `(pair, date, rate_type)` lookup. Prabhat built `CalculationAmount<C>` (#4421) which underpins the rate types; jirijakes drives the API surface and integration requirements.
2. **Fiat rate source adapter** — implement EUR/USD, GBP/USD provider (e.g. ECB reference rates) behind the `PriceClient` trait from #4817. No fiat rate source exists today — this is a hard prerequisite for fiat revaluation in production.
3. **Review FX chain PRs** — available as reviewer for #4958/#4970.

### jirijakes
1. ~~**Merge #4959 (collateral lot tracking)**~~ — ✅ merged 2026-04-14.
2. ~~**Review #5048 (AnyCurrency refactor)**~~ — ✅ approved 2026-04-14.
3. **Review #4958 and #4970** — next in the FX chain. #4958 is open and ready for review. Conversion orchestration and settlement book-value leg.
4. **Lead Closing Rate Storage (with Prabhat1308)** — hard prerequisite for fiat revaluation. Revive #4923, add EOD closing rate snapshot triggered by `CoreTimeEvent::EndOfDay`, rate lookup by `(pair, date, rate_type)`. Guide fiat rate source adapter work.
5. ~~**Continue #4821 (BTC collateral revaluation)**~~ — deprioritized until fiat revaluation is complete and BTC holdings strategy has more clarity.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Merged — on main |
| 🟢 | Approved — ready to merge, not yet landed |
| 🔵 | Code written and tested — awaiting human review |
| 🔶 | In progress or exploratory — not yet review-ready |
| ⬜ | Not started |
