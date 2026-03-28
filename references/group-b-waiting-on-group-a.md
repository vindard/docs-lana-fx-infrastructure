# Group B gaps waiting on Group A (dual-currency entries)

Phase 3 (Group B) is implemented in PRs #4430 and #4552. The position accumulator, realized G/L, and settlement logic are complete — but the conversion template is missing a functional-currency book-value leg because that leg depends on Group A's dual-currency entry infrastructure existing first. This doc describes the dependency chain.

## What Group A delivers

Group A adds **dual-currency entries** to every foreign-currency transaction. When a customer deposits 60 EUR at spot rate 1.10, the ledger currently posts only the EUR leg:

```
Dr  EUR Deposit     60 EUR
Cr  EUR Omnibus     60 EUR
```

After Group A, each template also posts a functional-currency (USD) leg alongside:

```
Dr  EUR Deposit     60 EUR
Dr  EUR Deposit     66 USD      ← 60 × 1.10, new
Cr  EUR Omnibus     60 EUR
Cr  EUR Omnibus     66 USD      ← new
```

This establishes the **book value baseline** directly in the ledger. The USD balance on each account represents its functional-currency carrying value — the number that revaluation computes deltas against and that conversion needs to read when computing proportional book cost.

Group A also stores **rate metadata** (via `ReferenceRate` from core-price) on every cross-currency transaction, providing the audit trail of which rate produced which amounts.

### Affected templates

Group A must add USD legs to at minimum:
- `RECORD_DEPOSIT` (already has `ReferenceRate` metadata from #4559, needs USD entries)
- `RECORD_WITHDRAWAL`
- Any other template that moves foreign-currency balances (omnibus transfers, etc.)

The `FIAT_FX_CONVERSION_VIA_TRADING` template (from #4430) also needs a USD leg — but that leg has a different source than the others, described below.

## What Group A enables in Group B

### 1. Book-value leg on the conversion template

The EUR walkthrough (Steps 6 ⑦-⑧) shows that when the bank converts 50 EUR through the trading account, the template must transfer not just the EUR but also the **proportional USD book value** from the source account:

```
Step 6 — Convert 50 of 100 EUR (rate 1.15)

  ⑤ Dr  Trading           50 EUR
  ⑥ Cr  EUR Omnibus       50 EUR
  ⑦ Dr  Trading           55.40 USD     ← book value, not market value
  ⑧ Cr  EUR Omnibus       55.40 USD
  ⑨ Dr  USD Cash          57.50 USD     ← market proceeds (50 × 1.15)
  ⑩ Cr  Trading           57.50 USD
  ⑪ Dr  Trading            2.10 USD     ← realized G/L clearing
  ⑫ Cr  Realized FX Gain   2.10 USD
```

The 55.40 on entries ⑦-⑧ is the **proportional book cost** of 50 EUR out of the 100 EUR held in Omnibus. It's computed as:

```
book_value_transferred = (converted_eur / total_eur_in_omnibus) × omnibus_usd_balance
```

This computation requires Omnibus to **have** a USD balance — which only exists after Group A's dual-currency entries are in place. Without Group A, `omnibus_usd_balance` is zero and there is no book value to transfer.

The book-value amount serves two purposes:
- **Ledger:** entries ⑦-⑧ move the cost basis from Omnibus into Trading, keeping the ledger's USD balances meaningful
- **Accumulator:** the same amount becomes `functional_amount` in `FxPosition::record_inflow`, establishing the position's book cost for future realized G/L computation

Currently, `record_inflow` accepts a `functional_amount` parameter, but the orchestrator has no way to source it — the upstream account has no USD balance to read from. Once Group A is in place, the orchestrator reads `omnibus_usd_balance`, computes proportional book cost, and passes it to both the template and the accumulator.

### 2. Accurate accumulator book cost

The accumulator's `accumulated_functional` is only meaningful if the `functional_amount` recorded on each inflow reflects the actual USD cost of acquiring that foreign currency. Today's implementation passes the functional-currency equivalent computed from the conversion rate (`source_amount × source_to_functional`), which approximates the book cost using the current rate.

After Group A, the correct flow is:
1. Group A establishes USD book value on deposit accounts at the original transaction rate
2. Revaluation (Phase 4) may adjust that USD balance over time
3. On conversion, the orchestrator reads the **current USD balance** (which includes any accumulated revaluation) and computes proportional book cost
4. Reval unwind reverses the revaluation portion before transfer (requires cumulative reval tracker — Phase 4)
5. The reval-stripped book cost flows into the accumulator

Steps 3-4 produce a clean book cost that reflects the original acquisition rates (blended if multiple deposits), not the rate at conversion time. This is what makes the accumulator's realized G/L computation accurate against the walkthrough's expected values.

### 3. Rate metadata on FX templates

The `ReferenceRate` pattern established by #4559 on `RECORD_DEPOSIT` should extend to:
- `FIAT_FX_CONVERSION_VIA_TRADING` — the exchange rate used for conversion
- `FX_SETTLEMENT` — the rate at which settlement proceeds are computed
- `REALIZED_FX_GAIN_LOSS` — the rate differential that produced the gain/loss

This is mechanical — the template `Params` structs already have a `meta` JSON field. Group A establishes the convention; extending it to FX templates is straightforward.

## What does NOT depend on Group A

These Phase 3 capabilities work correctly today without dual-currency entries:

- **Position accumulator structure** — `FxPosition` entity with `record_inflow`/`record_outflow` and proportional WAC allocation
- **Realized G/L computation** — given correct `functional_amount` inputs, the math is right
- **G/L clearing via templates** — `REALIZED_FX_GAIN_LOSS` and `FX_ROUNDING_ADJUSTMENT` templates post correctly
- **Settlement flow** — `settle_fx` records outflow, computes G/L, posts settlement + G/L entries
- **BTC exclusion** — `NonFiatCurrency` validation
- **Same-currency rejection** — `SameCurrencyConversion` validation

The accumulator and templates are structurally complete. The gap is in the **data flow**: the functional amounts flowing into the accumulator don't yet come from the ledger's book-value baseline because that baseline doesn't exist yet.

## Sequencing

```
Group A: dual-currency entries on deposit/withdrawal/omnibus templates
    │
    ├──► Enables: book-value leg on FIAT_FX_CONVERSION_VIA_TRADING (⑦-⑧)
    │        └──► Enables: accurate accumulated_functional in FxPosition
    │
    ├──► Enables: rate metadata on FX templates (extend ReferenceRate pattern)
    │
    └──► Enables: Phase 4 revaluation (delta method reads USD balance as carrying value)
             │
             ├──► Enables: cumulative_reval tracker (per-account scalar)
             │        └──► Enables: reval unwind on withdrawal and settlement
             │
             └──► Enables: Trading Account revaluation (reads book value from accumulator)
```

Phase 3 (this branch) sits at the first level — it needs Group A's USD balances to source the book-value leg. Phase 4 sits at the second level — it needs both Group A's USD balances and Phase 3's accumulator.
