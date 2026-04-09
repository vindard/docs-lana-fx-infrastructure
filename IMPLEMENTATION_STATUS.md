# FX Infrastructure: Implementation Status & Gaps

*Living document — updated as gaps are resolved and new ones identified.*
*Originally consolidated 2026-03-30. Last updated 2026-04-09T01:13Z.*
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
| #4815 | Lakshyyaa | 2026-04-06 | Publish all withdrawal events to outbox |
| #4857 | Lakshyyaa | 2026-04-06 | Publish all disbursal events to outbox |
| #4703 | (credit) | 2026-04-06 | Do not emit events for closed facilities |
| #4556 | (dagster) | 2026-04-06 | Drive Dagster as an EOD process |
| #4709 | siddhart1o1 | 2026-04-08 | Split `ManualTransaction` into Draft and Transaction — accounting-adjacent refactor |

---

## Unmerged branches & open PRs

| PR / Branch | Author | Status | Relevance |
|-------------|--------|--------|-----------|
| #4430 `chore/trading-accounts` | vindard | Draft | **core/fx crate scaffolding:** Creates `core/fx` with primitives, FX ledger module, fiat conversion template, chart of accounts integration, CoreFx public API wiring, RBAC. Base for #4957. |
| #4957 `refactor/fx-position-foundation` | vindard | Draft | **Phase 3 foundation:** Domain primitives (`ExchangeRate`, `FxConversion`, `FunctionalRate`, `RealizedGainLoss`), event-sourced `FxPosition` entity with Selinger accumulator. Bases on #4430. Replaces #4552. No human review yet. |
| #4958 `refactor/fx-conversion-flow` | vindard | Draft | **Phase 3 orchestration:** CALA templates (`FiatFxConversionViaTrading`, `RealizedFxGainLoss`, `FxSettlement`), `CoreFx::convert_fiat_fx()` and `CoreFx::settle_fx()` orchestration. Bases on #4957. No human review yet. |
| #4970 `refactor/fx-settlement-book-value` | vindard | Draft | **Phase 3 completion (NEW):** Settlement book-value leg (FX_SETTLEMENT expanded 2→4 entries), `OutflowResult` struct from position outflow, `AnyReferenceRate` metadata on all 3 FX templates. Adds `core-price` dep to `core-fx`. Chain: #4430→#4957→#4958→**#4970**. Addresses Gap 5 and part of Gap 3. |
| #4960 `refactor--templates-with-rates` | nsandomeno | Draft | **Non-functional currency deposit template (NEW):** `AnyCurrencyRecordDeposit` template variant with dual-currency entry legs, separate `record_any_currency_deposit` use-case, spot vs historical rate separation in `core/price`. Addresses Gap 2. Active review from vindard (naming, omnibus account selection, rate API naming via IAS 21 "translation" concept). |
| #4923 `feat/exchange-rate-history` | Prabhat1308 | Draft | **Rate History exploration.** `AggregatePriceHandler` delivers to `exchange_rates` table and ephemeral outbox. Relevant to Gap 1 (historical rate lookup). Reviewers requested: nsandomeno, vindard. |
| #4959 `collateral-lot-tracking` | jirijakes | Draft | **Collateral lot tracking (NEW).** 2206 additions. Companion to #4821. Tangential but uses FX rate infrastructure. |
| #4697 `chore--use-calculation-amount` | nsandomeno | Draft | **Largely superseded by #4817.** Stalled since 2026-04-01. May still have residual naming/API changes not yet in #4817. |
| #4686 `refactor--deposit-multicurrency-w-export-sumsub-deposit` | nsandomeno | Draft | Follow-up to #4671: multi-currency support in sumsub deposit export. Stalled since 2026-03-30. |
| #4700 `feat/lana-admin-price-provider-control` | sebastienverreault | Draft | Admin UI for price provider configuration. Actively updated 2026-04-08. Tangential to FX infrastructure. |
| #4757 `task/lana-ec-impl-019d4a85` | bodymindarts | Draft | **Eventually consistent account sets with EOD recalculation.** Eliminates advisory-lock contention on account set balance rows. Infrastructure improvement tangential to FX but relevant to multi-currency throughput. |
| #4821 `btc-collateral-revaluation` | jirijakes | Open | **BTC collateral revaluation.** Uses FX rate infrastructure. Tangential but relevant. |
| #4350 `ExchangeRate<From, To>` | bodymindarts | Open | **Generic ExchangeRate type exploration.** Stale since 2026-03-14. Largely superseded by #4817. |
| #4365 `deposit currency field` | bodymindarts | Open | **Deposit account currency field.** Stale since 2026-03-16. Largely superseded by #4616/#4671. |

---

## Gap 1: `exchange_rate_as_of()` only handles identity pairs

**Module:** `core/price/src/lib.rs`
**Severity:** Significant — needed for production but does not block template work
**Layer:** Application service (not template/ledger layer)

`Price::exchange_rate_as_of()` returns `Err(UnsupportedExchangeRatePair)` for any pair where base != quote. The method signature takes `impl StaticCurrency`, which only covers the compile-time `Usd` and `Btc` types. It cannot accept fiat currencies (EUR, GBP, etc.) represented via the newer `CurrencyCode` / `AnyCurrency` types from `lib/money`.

**Progress since last update (2026-04-08T14:35Z):**
- **#4817 (merged 2026-04-03)** significantly advances this gap: introduces generic `ExchangeRate<Base, Quote>` with `StaticCurrency` type params, `AnyReferenceRate` for currency-generic rate handling, `PriceClient` trait for per-provider fetching, and `Rate` enum (base vs quote expression). The old `PriceOfOneBTC` newtype is replaced by typed exchange rates.
- **#4869 (closed 2026-04-07 without merge)** explored rate lookup separation: `find_nearest_historical_exchange_rate` for historical lookups vs spot. Approach may be reattempted differently.
- **#4960 (draft, nsandomeno)** introduces spot vs historical rate separation in `core/price` with `find_nearest_historical_exchange_rate` and separate use-cases. vindard reviewed naming, suggesting IAS 21 "translation" terminology (`CurrencyTranslation` instead of `ReferenceRate`, `translation_at_nearest_historical_rate` instead of `find_nearest_historical_rate`).
- **#4923 (draft, Prabhat1308)** exploring rate history: `AggregatePriceHandler` now delivers aggregated prices to `exchange_rates` table and ephemeral outbox.

**What still needs to happen:**
- Support arbitrary fiat pairs (EUR/USD, GBP/USD, etc.) — the new `ExchangeRate<Base, Quote>` type supports this structurally, but no fiat rate source adapter exists yet (only BTC price providers)
- A fiat rate source adapter (or multiple) should supply fiat FX rates
- Historical rate storage and lookup — #4960 and #4923 both actively exploring this from different angles
- `as_of: None` → latest rate; `as_of: Some(...)` → historical lookup
- Naming convention alignment — vindard's review on #4960 proposes IAS 21 "translation" terminology to disambiguate rate lookup from rate-applied-to-amount

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

**Progress since last update (2026-04-08T14:35Z):**
- **#4960 (draft, nsandomeno)** directly addresses this gap: introduces `AnyCurrencyRecordDeposit` template variant with dual-currency entry legs and a separate `record_any_currency_deposit` use-case in `CoreDeposit`. 743 additions. Active review from vindard covering:
  - Omnibus account selection should key on transaction currency code (not functional currency) — fix pushed in `bd33bf3`
  - Account set specs could be generated from a cross-product of enabled currencies rather than manual constants
  - Need a `validate_account_for_deposit` function for currency correctness checks
  - Template naming: `AnyCurrency` prefix under discussion (vindard suggested `MultiCurrency`)

---

## Gap 3: Missing book-value leg on FX conversion and settlement templates

**Module:** `core/fx/src/ledger/templates/fiat_fx_conversion.rs`, `core/fx/src/ledger/templates/fx_settlement.rs`
**Severity:** Blocking — accumulator records wrong cost basis
**Depends on:** Nothing at the template layer (receives `book_value` as a parameter)
**Runtime data dependency:** Gap 2 (omnibus must have USD balances for the application service to compute meaningful book values)
**PRs:** #4958 adds the book-value leg to the conversion template; **#4970 adds the settlement book-value leg**; runtime correctness still depends on Gap 2

The walkthrough requires 8 entries on conversion; the template has 4. Missing entries 7-8:

```
⑦ Dr  Trading           55.40 USD    ← proportional book cost
⑧ Cr  EUR Omnibus       55.40 USD
```

The book value (`55.40`) is computed by the application service as `(converted_eur / total_eur_in_omnibus) × omnibus_usd_balance` and passed to the template as a parameter. The template itself does not read account balances or call other services.

This is the core of shortcoming #1 from the branch review: the accumulator currently records the conversion-rate amount (57.50) as functional cost instead of the book-value amount (55.00). The 2.50 difference is realized G/L that should not be in the cost basis.

**Progress since last update (2026-04-08T14:35Z):**
- **#4970 (draft, vindard)** adds the settlement book-value leg: FX_SETTLEMENT expanded from 2→4 entries — original foreign-currency delivery plus new USD book-value transfer (Dr Counterparty / Cr Trading in functional currency). New `OutflowResult { realized_gain_loss, proportional_book_value }` struct returned from `record_outflow`, threading `settlement_book_value` from position outflow → ledger → `FxSettlementResult`.
- Conversion template book-value leg remains in #4958.

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
**PRs:** ~~#4958 (templates exist but metadata params not yet added)~~ → **#4970 addresses this**
**Layer:** Template layer (template design) + Application service (constructing metadata structs)

`post_fx_conversion_in_op` has no `reference_rate` in its metadata JSON. Should follow the pattern #4559 established on `RECORD_DEPOSIT`. Also needed on `FX_SETTLEMENT` and `REALIZED_FX_GAIN_LOSS` templates.

**Progress since last update (2026-04-08T14:35Z):**
- **#4970 (draft, vindard)** adds `AnyReferenceRate` to `FiatFxConversionParams`, `RealizedFxGainLossParams`, and `FxSettlementParams`. Serialized into transaction `meta` JSON as `"reference_rate"`, matching the deposit template pattern from #4559. Adds `core-price` dependency to `core-fx`. **This gap is addressed at the template layer pending merge of #4970.**

Gap 4 (type migration) still affects where the application service *constructs* the metadata struct, not how the template receives it.

---

## Gap 6: FxConversion has no access to rate service

**Module:** `core/fx/src/lib.rs`, `core/fx/src/primitives.rs`
**Severity:** Significant
**Depends on:** Gap 4 (at the service layer — rate types must live in core/fx for the orchestrator to use them)
**PRs:** #4957 introduces `ExchangeRate` and `FxConversion` primitives in core/fx; Gap 4 migration still needed for full rate service access
**Layer:** Application service

`FxConversion::new()` takes the local `ExchangeRate` (computation type). Once rate types live in `core/fx`, the orchestrator can use the fx module's own rate service to look up rates and pass both the computation rate and the metadata rate into the conversion flow.

---

## Branch-specific shortcomings (from #4552, tracked for #4957/#4958)

The original #4552 branch had these issues. #4957 and #4958 address several; remaining items are tracked here.

| # | Shortcoming | Severity | Status |
|---|-------------|----------|--------|
| S1 | Position records conversion rate as cost basis, not book value | Critical | Open (needs Gap 3 template + Gap 2 runtime data) |
| S2 | No realized G/L for foreign→functional conversions (EUR→USD only triggers inflow, not outflow) | Critical | Open (needs Gap 3 template + Gap 2 runtime data) |
| S3 | Foreign→foreign conversions corrupt accumulator (GBP passed as "functional amount") | Critical | **Addressed in #4957** — `FxConversion` rejects BTC and same-currency pairs; verify Fgn→Fgn handling |
| S4 | No settlement template | Significant | **Resolved in #4958** — `FxSettlement` template added |
| S5 | No guard against same-currency conversion | Minor | **Resolved in #4957** — `FxConversion` rejects same-currency |
| S6 | Position uses `String` for currency instead of typed `Currency` | Minor | **Addressed in #4957** — uses typed domain primitives |
| S7 | No `Idempotent<T>` / `idempotency_guard!` on position commands | Minor | **Resolved** (`f646a6a62`) |

S1 and S2 remain blocked on Gap 2 + Gap 3 runtime data.

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
- Gap 2 — **actively in progress** via #4960 (nsandomeno): `AnyCurrencyRecordDeposit` with dual-currency legs
- Gap 3 — conversion book-value leg in #4958; settlement book-value leg in #4970
- Gap 5 — **addressed** in #4970: rate metadata on all 3 FX templates (pending merge)

**Parallelizable now (other layers):**
- Gap 1 (application-layer — #4817 landed typed rate infrastructure; #4960 adding spot/historical separation; #4923 exploring rate history; fiat rate source adapter still needed)
- Gap 4 (architectural, no runtime dependency — prerequisite cleanup landed in #4817, migration itself remains)

**PR chain in review:**
- #4430 (core/fx scaffolding) ← #4957 (foundation types) ← #4958 (orchestration) ← #4970 (settlement book-value + rate metadata)
- All drafts, no human review yet on #4957/#4958/#4970
- #4960 (deposit dual-currency template) has active review from vindard

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

**Gap 2** — **IN PROGRESS** via #4960 (nsandomeno):
- `AnyCurrencyRecordDeposit` template with dual-currency entry legs — draft open, under review
- Remaining: RECORD_WITHDRAWAL, FIAT_FX_CONVERSION_VIA_TRADING still need dual-currency legs
- Open design questions from review: template naming (`AnyCurrency` vs `MultiCurrency`), account set spec generation from currency cross-product, deposit validation function
- #4671 delivered currency-aware templates and `AnyCurrencyUnits` — build on this foundation

**Gap 3** — **PARTIALLY ADDRESSED** via #4958 + #4970:
- Conversion book-value leg (entries ㉓-㉔, ㉗-㉘) in #4958
- Settlement book-value leg (FX_SETTLEMENT 2→4 entries) in #4970
- `OutflowResult` struct threads `proportional_book_value` from position → ledger
- Test with placeholder book values — runtime correctness blocked on Gap 2

**Gap 5** — **ADDRESSED** in #4970 (pending merge):
- `AnyReferenceRate` added to all 3 FX template params, serialized as `"reference_rate"` in `meta` JSON
- Follows pattern from #4559 on RECORD_DEPOSIT
- Adds `core-price` dependency to `core-fx`

### Application service layer — wiring real values

**Gap 1** (cross-currency rate lookup):
- ~~Generalize rate types to accept generic currency pairs~~ — **done** via #4817 (`ExchangeRate<Base, Quote>`, `AnyReferenceRate`)
- ~~Separate historical from spot lookup~~ — **in progress** via #4960 (spot vs historical use-cases in `core/price`)
- Naming alignment needed — vindard proposed IAS 21 "translation" terminology on #4960 review
- Historical rate storage — #4923 (Prabhat1308) exploring `exchange_rates` table + outbox delivery
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

### Rounding adjustment decision

Analysis (see walkthrough Addendum A) concluded that direct single-rate conversions produce no
rounding residual — G/L clearing on the rounded settlement amount already zeroes Trading. The
3210 account and `FX_ROUNDING_ADJUSTMENT` template have been removed from the SPEC and walkthrough.
#4957/#4958 are already clean: no rounding adjustment template, account, or ledger posting references.
The only rounding code is `ExchangeRate::convert()` returning a `rounding_diff` as part of core
conversion arithmetic (intentionally unused by `FxConversion`). If cross-rate triangulation or
multi-line translation scenarios arise later, a rounding account can be reintroduced.

### Branch fixes

- **S3**: Verify Fgn→Fgn handling in #4957 — `FxConversion` rejects BTC and same-currency but confirm cross-foreign pairs work correctly
- **S1/S2**: Remain blocked on Gap 2 + Gap 3 runtime data

---

## Closed PRs (not merged, context only)

| PR | Title | Why closed |
|----|-------|-----------|
| #4552 | feat(fx): add FX conversion domain logic with position tracking and realized G/L | **Closed 2026-04-08.** Superseded by #4957 (foundation types) + #4958 (orchestration). Split into two stacked PRs for reviewability. |
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
