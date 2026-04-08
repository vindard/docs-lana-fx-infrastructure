# FX Infrastructure: Implementation Status & Gaps

*Living document — updated as gaps are resolved and new ones identified.*
*Originally consolidated 2026-03-30. Last updated 2026-04-07.*
*Supersedes `group-b-waiting-on-group-a.md` in this directory and the date-stamped gap/dependency docs in `ephemeral/2026-03-24/`, `2026-03-25/`, `2026-03-29/`.*

### Architectural principles for this document

When evaluating dependencies between gaps, respect the layered architecture:

1. **Template / ledger layer**: Templates receive all values (rates, amounts, book
   values) as parameters. They never call other services or read balances. Template
   work should not be listed as dependent on service-layer gaps.
2. **Application service layer**: Orchestrates calls to rate services, computes
   derived values (e.g. proportional book cost), and passes them to templates.
3. **Runtime data dependencies**: Distinct from template dependencies. A template
   can be built and tested with placeholder values even if the runtime data source
   (e.g. USD balances from dual-currency entries) doesn't exist yet.

When adding or updating gaps, always classify which layer a dependency belongs to
and avoid conflating template-design dependencies with service-layer or runtime-data
dependencies.

---

## Current state of main

These PRs have merged and form the foundation for the remaining work:

| PR | Author | Merged | What it delivered |
|----|--------|--------|-------------------|
| #4497 | thevaibhav-dixit | 2026-03-23 | Modularised money crate, simplified Currency trait, added `AnyCurrency` |
| #4531 | thevaibhav-dixit | 2026-03-23 | Removed currency-specific proxy methods from money |
| #4414 | bodymindarts | 2026-03-18 | Added `CurrencyCode`, `CurrencySet`, `CurrencyMap`, `RestrictedCurrencyMap` |
| #4561 | nsandomeno | 2026-03-25 | Made `DepositAccountSetCatalog` currency-aware |
| #4591 | nsandomeno | 2026-03-26 | Replaced account set resolution with local CALA account set ID |
| #4616 | thevaibhav-dixit | 2026-03-27 | Currency-aware deposit account entity |
| #4559 | nsandomeno | 2026-03-27 | **Group A partial:** `ExchangeRate`, `ReferenceRate`, `SourcedRateValue` in `core/price`; `ReferenceRate` JSON param on `RECORD_DEPOSIT`; `Price::exchange_rate_as_of()` (identity only); `QuantizationPolicy` in `lib/money` |
| #4421 | Prabhat1308 | 2026-03-28 | `CalculationAmount<C>` type for high-precision financial calculations |
| #4668 | (latest) | 2026-03-29 | `try_from_major_truncated` for precision-tolerant conversions |
| #4671 | thevaibhav-dixit | 2026-04-01 | **Multi-currency deposit threading:** `AnyCurrencyUnits`, currency-aware ledger templates, deposit/withdrawal entity currency threading, migration from `UsdCents` to flexible JSON-based amount representation. Unblocks Gap 2. |
| #4817 | bodymindarts | 2026-04-03 | **Per-provider price fetch + typed ExchangeRate:** Introduces generic `ExchangeRate<Base, Quote>` using `CalculationAmount`, `PriceClient` trait for per-provider fetch jobs, `ReferenceRate` and `AnyReferenceRate` for currency-generic rate handling, `Rate` enum (base vs quote expression), stores `reference_rate` in ledger transaction metadata. Subsumes most of #4697's work. 62 files, 1479 insertions. Replaces `PriceOfOneBTC` newtype with typed exchange rate. Rollup schemas migrated to JSONB for price fields. |
| #4815 | (deposit) | 2026-04-03 | Publish all withdrawal events to outbox |
| #4703 | (credit) | 2026-04-07 | Do not emit events for closed facilities |
| #4556 | (dagster) | 2026-04-07 | Drive Dagster as an EOD process |

---

## Unmerged branches & open PRs

| PR / Branch | Author | Status | Relevance |
|-------------|--------|--------|-----------|
| #4552 `refactor/fx-accumulator-model` | vindard | Draft | **Phase 3:** FxPosition accumulator, FxConversion, trading account templates, settlement. Rebased 2026-03-31 (7 commits). Has structural gaps listed below. |
| #4430 `chore/trading-accounts` | (multiple) | Draft | **core/fx crate scaffolding:** Creates `core/fx` with primitives, FX ledger module, fiat conversion template, chart of accounts integration, CoreFx public API wiring, RBAC. Prerequisite for #4552. |
| #4697 `chore--use-calculation-amount` | nsandomeno | Draft | **Largely superseded by #4817.** Originally refactored `ExchangeRate` and `ReferenceRate` with generics, `Rate` enum, `CalculationAmount` arithmetic. #4817 landed most of this work (generic `ExchangeRate<Base, Quote>`, `Rate` enum, `AnyReferenceRate`). Review discussion (jirijakes: rounding outside conversion, rename `carrying_amount_for`; Prabhat1308: rounding strategy) was incorporated into #4817. May still have residual naming/API changes not yet in #4817. |
| #4735 `refactor/currency-denomination-split` | (unknown) | Closed | Explored separating currency identity from ISO denomination (spawned from #4697 discussion). Concluded ISO decimal precision belongs on currency; rounding strategy does not. Closed without merge but informed #4697/#4817 direction. |
| #4686 `refactor--deposit-multicurrency-w-export-sumsub-deposit` | nsandomeno | Draft | Follow-up to #4671: multi-currency support in sumsub deposit export. |
| #4700 `feat/lana-admin-price-provider-control` | sebastienverreault | Draft | Admin UI for price provider configuration. Tangential to FX infrastructure. |
| #4869 `refactor--breakout-rate-lookup-use-cases` | nsandomeno | Closed | **Closed 2026-04-07 without merge.** Was separating historical rate lookup from spot lookup using `ADD_COLLATERAL` as iteration surface. Introduced `find_nearest_historical_exchange_rate`. See closed PRs table for context. |
| #4757 `task/lana-ec-impl-019d4a85` | bodymindarts | Draft | **Eventually consistent account sets with EOD recalculation.** Pins cala-ledger to EC branch, sets `eventually_consistent(true)` on all account sets, adds `RecalculateAccountSetBalances` as last EOD phase. Eliminates advisory-lock contention on account set balance rows. Infrastructure improvement tangential to FX but relevant to multi-currency throughput. |

---

## Gap 1: `exchange_rate_as_of()` only handles identity pairs

**Module:** `core/price/src/lib.rs`
**Severity:** Significant — needed for production but does not block template work
**Layer:** Application service (not template/ledger layer)

`Price::exchange_rate_as_of()` returns `Err(UnsupportedExchangeRatePair)` for any pair where base != quote. The method signature takes `impl StaticCurrency`, which only covers the compile-time `Usd` and `Btc` types. It cannot accept fiat currencies (EUR, GBP, etc.) represented via the newer `CurrencyCode` / `AnyCurrency` types from `lib/money`.

**Progress since last update:**
- **#4817 (merged 2026-04-03)** significantly advances this gap: introduces generic `ExchangeRate<Base, Quote>` with `StaticCurrency` type params, `AnyReferenceRate` for currency-generic rate handling, `PriceClient` trait for per-provider fetching, and `Rate` enum (base vs quote expression). The old `PriceOfOneBTC` newtype is replaced by typed exchange rates.
- **#4869 (closed 2026-04-07 without merge)** explored rate lookup separation: `find_nearest_historical_exchange_rate` for historical lookups vs spot. Approach may be reattempted differently.

**What still needs to happen:**
- Support arbitrary fiat pairs (EUR/USD, GBP/USD, etc.) — the new `ExchangeRate<Base, Quote>` type supports this structurally, but no fiat rate source adapter exists yet (only BTC price providers)
- A fiat rate source adapter (or multiple) should supply fiat FX rates
- Historical rate storage and lookup — #4869 explored `find_nearest_historical_exchange_rate` but was closed without merge; this remains an open problem
- `as_of: None` → latest rate; `as_of: Some(...)` → historical lookup (no active PR)

**Important:** This is an application-service-layer concern, not a template dependency. Ledger templates receive rate values as parameters — they do not call rate services. Templates (Gap 2, Gap 3) can be built and tested with placeholder rate values without Gap 1 being resolved. Gap 1 is needed when the application service orchestrates real conversions in production.

**Note:** This logic currently lives in `core/price` but per the SPEC should ultimately live in `core/fx` (see Gap 4). The typed `ExchangeRate<Base, Quote>` and `AnyReferenceRate` from #4817 provide a much cleaner foundation for the eventual migration.

---

## Gap 2: Dual-currency (functional-currency book-value) entries not posted

**Module:** `core/deposit/src/ledger/templates/`
**Severity:** Blocking for Phase 4 (revaluation)
**Depends on:** ~~#4671 (multi-currency deposit threading)~~ **UNBLOCKED** — #4671 merged 2026-04-01

Group A requires functional-currency (USD) legs alongside every foreign-currency entry:

```
Dr  EUR Deposit Omnibus   60 EUR
Cr  Customer EUR Account  60 EUR
Dr  EUR Deposit Omnibus   66 USD    ← MISSING
Cr  Customer EUR Account  66 USD    ← MISSING
```

Without these, `balance_functional` doesn't exist in the ledger. Revaluation needs it for `adjustment = fair_value - book_value`.

**Affected templates:** `RECORD_DEPOSIT` (has `ReferenceRate` metadata from #4559, needs USD entry legs), `RECORD_WITHDRAWAL`, `FIAT_FX_CONVERSION_VIA_TRADING` (unique: USD leg source is proportional book cost, not spot rate).

---

## Gap 3: Missing book-value leg on FX conversion template

**Module:** `core/fx/src/ledger/templates/fiat_fx_conversion.rs`
**Severity:** Blocking — accumulator records wrong cost basis
**Depends on:** Nothing at the template layer (receives `book_value` as a parameter)
**Runtime data dependency:** Gap 2 (omnibus must have USD balances for the application service to compute meaningful book values)
**Branch:** `refactor/fx-accumulator-model`

The walkthrough requires 8 entries on conversion; the template has 4. Missing entries 7-8:

```
⑦ Dr  Trading           55.40 USD    ← proportional book cost
⑧ Cr  EUR Omnibus       55.40 USD
```

The book value (`55.40`) is computed by the application service as `(converted_eur / total_eur_in_omnibus) × omnibus_usd_balance` and passed to the template as a parameter. The template itself does not read account balances or call other services.

This is the core of shortcoming #1 from the branch review: the accumulator currently records the conversion-rate amount (57.50) as functional cost instead of the book-value amount (55.00). The 2.50 difference is realized G/L that should not be in the cost basis.

**Template can be built and tested now with placeholder book values.** Correct runtime values require Gap 2's dual-currency entries so the omnibus has a USD balance to read.

---

## Gap 4: Rate types are in the wrong module

**Modules:** `core/price/src/primitives.rs`, `core/fx/src/primitives.rs`
**Severity:** Architectural misalignment with SPEC
**Depends on:** Nothing — can be done independently

Per the SPEC (Components 1-3), `core/fx` is the domain owner of FX infrastructure: exchange rate storage, multi-source aggregation, and rate-per-transaction recording all belong in `core/fx`. The `core/price` module should be a **rate source adapter** (one provider among several).

PR #4559 placed the metadata types in `core/price`. They need to move to `core/fx`:

**Types to migrate `core/price` → `core/fx`:**
- `ExchangeRate` (metadata: base/quote currency, sourced_value, rate_type, timestamp)
- `ReferenceRate`, `SourcedRateValue`, `RateType`
- `exchange_rate_as_of()` and `reference_rate_as_of()` logic

**What stays in `core/price`:**
- `PriceOfOneBTC`, price providers, Bitfinex feed — becomes a source adapter

**Name collision:** `core/fx` already has its own `ExchangeRate` — a computation primitive (rate + precision, `convert()`, `inverse()`). This is a different type serving a different purpose. Rename it to `ConversionRate` to disambiguate.

**Progress since last update:** #4817 (merged 2026-04-03) landed the prerequisite refactoring that was previously in-progress via #4697: generic `ExchangeRate<Base, Quote>`, `ReferenceRate`, `AnyReferenceRate`, `Rate` enum, `CalculationAmount` arithmetic — all in `core/price`. The review feedback from jirijakes and Prabhat1308 on rounding and naming was incorporated. This makes the eventual migration to `core/fx` cleaner since the types now have well-defined generic signatures. #4697 is largely superseded.

**Dependency graph change:**
```
Before:  core/price ← core/deposit, core/credit, core/fx
After:   core/price ← core/fx ← core/deposit, core/credit
```

---

## Gap 5: No rate metadata on FX templates

**Module:** `core/fx/src/ledger/mod.rs`
**Severity:** Significant — no audit trail on FX transactions
**Depends on:** Nothing at the template layer (metadata is JSON params on CALA templates)
**Branch:** `refactor/fx-accumulator-model`
**Layer:** Template layer (template design) + Application service (constructing metadata structs)

`post_fx_conversion_in_op` has no `reference_rate` in its metadata JSON. Should follow the pattern #4559 established on `RECORD_DEPOSIT`. Also needed on `FX_SETTLEMENT`, `REALIZED_FX_GAIN_LOSS`, and `FX_ROUNDING_ADJUSTMENT` templates.

**Template can be built now** — add JSON metadata params to accept rate info. Gap 4 (type migration) affects where the application service *constructs* the metadata struct, not how the template receives it.

---

## Gap 6: FxConversion has no access to rate service

**Module:** `core/fx/src/lib.rs`, `core/fx/src/primitives.rs`
**Severity:** Significant
**Depends on:** Gap 4 (at the service layer — rate types must live in core/fx for the orchestrator to use them)
**Branch:** `refactor/fx-accumulator-model`
**Layer:** Application service

`FxConversion::new()` takes the local `ExchangeRate` (computation type). Once rate types live in `core/fx`, the orchestrator can use the fx module's own rate service to look up rates and pass both the computation rate and the metadata rate into the conversion flow.

---

## Branch-specific shortcomings (`refactor/fx-accumulator-model`)

Beyond the Group A gaps above, the unmerged fx branch has these issues:

| # | Shortcoming | Severity | Status |
|---|-------------|----------|--------|
| S1 | Position records conversion rate as cost basis, not book value | Critical | Open (needs Gap 3 template + Gap 2 runtime data) |
| S2 | No realized G/L for foreign→functional conversions (EUR→USD only triggers inflow, not outflow) | Critical | Open (needs Gap 3 template + Gap 2 runtime data) |
| S3 | Foreign→foreign conversions corrupt accumulator (GBP passed as "functional amount") | Critical | Open |
| S4 | No settlement template | Significant | **Resolved** (added in later commits on branch) |
| S5 | No guard against same-currency conversion | Minor | **Resolved** |
| S6 | Position uses `String` for currency instead of typed `Currency` | Minor | Open |
| S7 | No `Idempotent<T>` / `idempotency_guard!` on position commands | Minor | **Resolved** (`f646a6a62`) |

S3 is independent of Group A and can be fixed on the branch now. S2 is blocked by Gap 3 (see "Position accumulator routing reference" below).

---

## Dependency chain

```
Template / ledger layer (all receive values as params, don't call services):

    Gap 2 (dual-currency entry legs)       ← UNBLOCKED (#4671 merged 2026-04-01)
    Gap 3 (book-value leg on FX conversion) ← no template dependency, accepts book_value param
    Gap 5 (rate metadata on FX templates)   ← no template dependency, accepts JSON params

    All three can be designed/tested with placeholder values independently.

Runtime data dependency (correct values at runtime):

    Gap 2 entries must exist ──► so omnibus has USD balances
                                      │
                                      ▼
                               application service can compute book_value
                               for Gap 3 and correct cost basis for S1/S2

Application service layer:

    Gap 1 (cross-currency rate lookup) ──► provides real rate values to
                                           Gap 2 and Gap 3 templates
    Gap 6 (FxConversion rate service)  ──► orchestrator passes both computation
                                           rate and metadata rate

Architectural:

    Gap 4 (migrate rate types to core/fx) ──► Gap 5 (service constructs metadata)
    Gap 4 ──► Gap 6 (FxConversion uses fx rate service)
    ✅ #4817 landed prerequisite type refactoring for Gap 4
```

**Parallelizable now (template layer):**
- Gap 2 (**now unblocked** — #4671 merged, can add dual-currency entry legs)
- Gap 3 (no template dependency — accepts book_value as parameter)
- Gap 5 (no template dependency — add JSON metadata params)
- S3 (branch fix, independent of Group A)

**Parallelizable now (other layers):**
- Gap 1 (application-layer — #4817 landed typed rate infrastructure; fiat rate source adapter and historical lookup still needed)
- Gap 4 (architectural, no runtime dependency — prerequisite cleanup landed in #4817, migration itself remains)
- #4430 (core/fx crate scaffolding — prerequisite for #4552)

---

## Position accumulator routing reference

The position accumulator tracks foreign currency held in the trading account.
It mirrors the trading account's physical balance: source-foreign = inflow,
target-foreign = outflow.

| Conversion       | Trading receives | Trading gives | Source position  | Target position     |
|------------------|-----------------|---------------|-----------------|---------------------|
| USD→EUR (F→Fgn)  | USD             | EUR           | skip (func)     | **outflow** (G/L)   |
| EUR→USD (Fgn→F)  | EUR             | USD           | **inflow**      | skip (func)         |
| EUR→GBP (Fgn→Fgn)| EUR            | GBP           | **inflow**      | **outflow** (G/L)   |
| settle_fx(EUR)   | —               | EUR           | —               | **outflow** (G/L)   |

**Rule**: foreign currency entering trading = inflow; foreign currency leaving = outflow.
Realized G/L is computed only on outflow (disposal).

### Why EUR→USD is inflow (not outflow)

EUR→USD conversion moves EUR INTO the trading account (Dr Trading EUR).
The EUR remains in trading until delivered to an FX counterparty via
settle_fx(). This is an acquisition of EUR by the trading desk, not a disposal.

The missing realized G/L on EUR→USD is not a routing problem — it's because
the **book-value leg** (walkthrough Step 6, entries ㉓-㉘) is not yet implemented.
In the full model, G/L at conversion time comes from:

    G/L = conversion_proceeds − book_value_of_EUR

This requires Gap 2 (dual-currency entries on deposit templates, so EUR accounts
carry a USD book value) and Gap 3 (book-value leg on the FX conversion template).

### Two-phase G/L model (full walkthrough)

1. **At conversion** (Gap 2 + Gap 3): G/L = proceeds − book_value. Accumulator
   records book cost. EUR stays in trading.
2. **At settlement**: EUR delivered to counterparty. Accumulator reduced
   proportionally. **No additional G/L** — already recognized at conversion.

The current branch back-loads G/L to settlement (accumulator outflow). The
full model front-loads it to conversion (book-value leg). Both models use
inflow for EUR→USD at the position level.

---

## Actionable steps

### Template layer — buildable now with placeholder values

**Gap 2** (**UNBLOCKED** — #4671 merged 2026-04-01):
- Add functional-currency (USD) entry legs to RECORD_DEPOSIT, RECORD_WITHDRAWAL,
  FIAT_FX_CONVERSION_VIA_TRADING
- Template receives the converted USD amount as a parameter
- Test with hardcoded rate values
- #4671 delivered currency-aware templates and `AnyCurrencyUnits` — build on this foundation

**Gap 3** (no template dependency):
- Add entries ㉓-㉔ (book-value transfer) and ㉗-㉘ (G/L clearing) to the
  FIAT_FX_CONVERSION_VIA_TRADING template
- Template receives `book_value` as a parameter
- G/L = conversion_proceeds − book_value
- Test with placeholder book values

**Gap 5** (no template dependency):
- Add `reference_rate` JSON metadata params to FX_CONVERSION, FX_SETTLEMENT,
  REALIZED_FX_GAIN_LOSS, and FX_ROUNDING_ADJUSTMENT templates
- Follow pattern from #4559 on RECORD_DEPOSIT

### Application service layer — wiring real values

**Gap 1** (cross-currency rate lookup):
- ~~Generalize rate types to accept generic currency pairs~~ — **done** via #4817 (`ExchangeRate<Base, Quote>`, `AnyReferenceRate`)
- Separate historical from spot lookup — #4869 explored this but was closed without merge; needs new approach
- Add a fiat rate source adapter for EUR/USD, GBP/USD, etc. (separate from the BTC price providers)
- Enables: application service passes real rate values to Gap 2/Gap 3 templates

**After Gap 2 runtime data exists** (USD balances in omnibus):
- Application service can compute `book_value = (converted_eur / total_eur) ×
  omnibus_usd_balance` and pass to Gap 3 template
- Fixes S1: accumulator records book_value (not conversion_rate) as cost basis
- Fixes S2: realized G/L posted at conversion time via the book-value leg
- Update settle_fx(): settlement becomes delivery-only (no G/L from accumulator)

### Architectural

**Gap 4** (prerequisite cleanup landed in #4817):
- ~~Refactor ExchangeRate/ReferenceRate generics and CalculationAmount integration~~ — **done** via #4817
- Rename `ExchangeRate` → `ConversionRate` in core/fx to disambiguate
- Migrate rate metadata types from core/price → core/fx
- Wire core/price as a rate source adapter
- Enables: Gap 5 service layer (constructing metadata structs), Gap 6

### Branch fixes

- **S3**: Foreign→foreign accumulator corruption — independent, fixable now
- **S6**: Position uses `String` for currency instead of typed `Currency` — independent

---

## Closed PRs (not merged, context only)

| PR | Title | Why closed |
|----|-------|-----------|
| #4642 | feat(price): price snapshot with provider provenance tracking | Deferred — sandipndev noted "would need to implement better price fetching first" |
| #4463 | explore: rate per transaction (FX Infrastructure Component #3) | Exploratory — superseded by #4559 approach |
| #4560 | chore(fx): add lot-based FIFO position tracking | Superseded by accumulator approach in #4552 |
| #4735 | refactor(money,price): separate currency identity from ISO denomination | Informed #4697/#4817 direction; conclusions folded into `QuantizationPolicy` simplification |
| #4788 | refactor(price): per-provider fetch jobs with aggregation handler | Merged then immediately reverted; re-landed as #4817 |
| #4869 | refactor: breakout rate lookup use cases | Explored separating historical vs spot rate lookup using `ADD_COLLATERAL` as iteration surface; closed 2026-04-07 without merge |

---

## Sources

This doc consolidates:
- `group-b-waiting-on-group-a.md` (removed from this directory)
- `.arvin/ephemeral/2026-03-25/2026-03-25--fx-branch-shortcomings.md`
- `.arvin/ephemeral/2026-03-24/2026-03-24--integration-analysis-to-rate-per-transaction.md`
- `.arvin/ephemeral/2026-03-29/2026-03-29--price-cross-currency-exchange-rate.md`

Primary reference: `../SPEC.md`
