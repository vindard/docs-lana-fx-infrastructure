# Evaluating Industry Revaluation Practice Against This Spec

## Context

```
Q:
In context of core banking systems with multi-currency accounting, what kinds of accounts are usuaally subject to mark-to-market daily revaluation? Is it all accounts (internal bank's, customer's etc.) or only some? What is the common practice in popular core-banking platforms?

A:
In multi-currency core banking, **daily mark-to-market / FX revaluation is usually applied only to accounts or balances that are denominated in a foreign currency relative to the entity’s accounting or functional currency, and even then not always to every such account**.

The short answer is:

- **Not all accounts are revalued**
- **Not all customer accounts are treated the same way**
- **Common practice is rule-based revaluation by product, GL class, balance type, and accounting policy**

## What is typically revalued

Usually, banks revalue **foreign-currency monetary items** at end of day or end of period. In practice this often includes:

- **Nostro / vostro accounts**
- **Cash and due-from / due-to bank accounts**
- **Foreign-currency loans and deposits**
- **Accrued interest receivable/payable in foreign currency**
- **FX position accounts**
- **Suspense, settlement, clearing, payable, receivable accounts in foreign currency**
- **Off-balance sheet FX contracts**, depending on platform and accounting setup
- **Internal bank GL accounts** held in foreign currency

If a customer account is a real foreign-currency liability or asset on the bank’s books, then from accounting perspective it is often part of what may need revaluation.

## What is usually not revalued

Common exclusions:

- **Accounts already denominated in local/accounting currency**
- **Non-monetary items** carried at historical cost
- **Memo or statistical accounts**
- **Certain equity accounts**
- **Fixed asset accounts**, unless accounting rules require a specific treatment
- **Accounts where FX effect is realized elsewhere rather than by balance revaluation**
- **Products configured to maintain both account currency and local currency using fixed historical booking logic**

## Important distinction: customer account vs accounting ledger

This is where confusion often happens.

A bank may have:

- a **customer subledger/account balance** in USD
- and a corresponding **general ledger representation** in local currency

In many core banking systems, the **customer account itself remains in account currency** and is not “changed” by revaluation. Instead:

- the **local currency equivalent** is recalculated
- the **GL valuation adjustment** is posted
- unrealized FX gain/loss goes to dedicated P&L accounts

So even if people say “customer accounts are revalued,” operationally the system may actually be revaluing the **accounting view**, not altering the customer-facing foreign currency balance.

## Common practice in core banking platforms

Popular core banking platforms generally do **selective revaluation**, not blanket revaluation of everything.

Typical setup is:

- define a **base/local/accounting currency**
- identify **foreign-currency balances**
- classify accounts by:
  - asset/liability
  - monetary/non-monetary
  - customer/internal
  - on-balance/off-balance
  - product type
  - branch/legal entity
- assign **revaluation rules**
- run **end-of-day or end-of-period batch**
- post:
  - unrealized FX gain/loss
  - valuation adjustment entries
  - reversal logic if required next day or next period

## In practice by account type

### Internal bank accounts
These are **most commonly revalued daily**.

Examples:

- nostro accounts
- treasury position accounts
- interbranch foreign-currency accounts
- foreign-currency GL balances
- accrual and settlement accounts

These directly affect the bank’s own financial statements and risk position.

### Customer deposit accounts
These are **often included**, but the treatment varies by architecture.

Common approaches:

- **Revalue corresponding GL balances daily**
- Keep customer ledger in original currency, only update local equivalent
- Post unrealized gain/loss to bank P&L
- Sometimes revalue only for financial reporting, not for operational customer accounting

For example, a USD customer deposit in a bank whose functional currency is PYG may remain USD 1,000 for the customer, while the bank’s liability equivalent in PYG is revalued daily.

### Customer loan accounts
Also **commonly revalued** when denominated in foreign currency.

This may affect:

- principal outstanding in local reporting currency
- accrued interest
- overdue balances
- provisions, depending on accounting policy

Again, customer contractual currency often stays unchanged; what changes is the local-currency carrying value.

### Off-balance sheet items
These are often handled by a **separate treasury / trade finance / contingent liability module** rather than generic account revaluation.

Examples:

- forwards
- swaps
- guarantees
- letters of credit

These may be revalued or fair-valued under separate rules.

## Why not “all accounts”

Because revaluation depends on **accounting meaning**, not just currency.

Two foreign-currency accounts may be treated differently if one is:

- a monetary balance subject to closing-rate revaluation
- and the other is a non-monetary or historical-cost item

Also, many systems separate:

- **transaction currency**
- **account currency**
- **local currency**
- **reporting currency**

Not every balance in a non-local currency triggers a daily accounting revaluation entry.

## Typical system design in major platforms

Across major core systems, the common pattern is:

- **Account holds original currency balance**
- **System stores local currency equivalent**
- **EOD batch reads official FX rates**
- **Only configured account classes / GLs are revalued**
- **Adjustment postings go to revaluation gain/loss and balance-sheet adjustment accounts**
- **Detailed audit trail is maintained**
- **Regulatory and IFRS/local GAAP reporting use revalued local equivalents**

This is broadly common in large platforms such as universal core banking suites, though names differ by vendor.

## A practical rule of thumb

In most banks, daily FX revaluation usually applies to:

- **all foreign-currency monetary GL balances**
- **internal bank foreign-currency accounts**
- **customer asset/liability balances represented in GL**
- **related accruals and settlement balances**

It usually does **not** apply to:

- every customer account in a customer-visible sense
- every ledger indiscriminately
- non-monetary historical-cost items
- purely memo/statistical balances

## The most common answer in one sentence

**Common practice is to revalue selected foreign-currency monetary balances—especially GL, treasury, nostro, loans, deposits, accruals, and settlement accounts—rather than every account indiscriminately; customer balances usually remain in account currency while the bank revalues their local-currency accounting equivalent.**

## If you want the accounting-policy view

The exact scope depends on:

- local GAAP vs IFRS
- functional currency of the legal entity
- whether the bank uses subledger-only or GL-driven revaluation
- whether revaluation is daily operationally or only month-end for finance
- product processor capabilities of the core platform
- integration with treasury, trade finance, and finance systems

If you want, I can also give you:

- a **table by account type** showing “usually revalued / sometimes / usually not”
- or a **sample end-of-day revaluation design** for a core banking system.
```


## Verdict: Largely aligned, but the spec makes sharper distinctions

The industry description is a solid general-purpose explanation. Most of it holds up. But there are specific areas where the spec goes further, diverges, or renders parts of the description less relevant.

## Where the industry description aligns well

1. **"Not all accounts are revalued."** Correct. The spec has three entirely separate regimes (fiat FX, BTC fair value, BTC collateral) with different rules, and only specific account classes participate in each.

2. **Customer balance stays in account currency; local-currency equivalent is what changes.** This is exactly what the spec describes. The trading account absorbs the delta, and revaluation adjusts GL-level local-currency equivalents.

3. **Selective/rule-based revaluation by product type.** The spec uses CALA template-based controls and separate collector jobs that explicitly include/exclude account classes. Same concept.

4. **Separation of monetary vs non-monetary items.** The spec's BTC collateral regime (both-sides, no P&L impact) is effectively a non-monetary treatment, while fiat FX balances get standard monetary-item closing-rate revaluation.

## Where the spec is sharper or different

### BTC is not treated as a foreign currency at all

The industry description lumps everything under "FX revaluation." The spec explicitly separates BTC fair value (ASU 2023-08, intangible asset, direct P&L, no unrealized/realized distinction, no trading account) from fiat FX (IAS 21, closing-rate revaluation, trading account intermediary). Commingling them would produce "incoherent financial statements" per the spec.

### BTC collateral has zero P&L impact

The industry description mentions off-balance sheet items and contingent liabilities but doesn't capture the spec's agent-relationship model where both sides of the balance sheet move together—asset and obligation revalue identically, netting to zero P&L. This is a distinct third regime, not a variant of the other two.

### The "daily" assumption is too narrow

The industry description defaults to "daily/EOD." The spec allows BTC fair value to be updated continuously (hourly, on price events), while fiat closing-rate revaluation is period-end. The cadence is regime-dependent, not uniformly daily.

### Trading account as core infrastructure

The industry description mentions "FX position accounts" in passing. The spec elevates the fiat FX trading account (Selinger model) to a first-class architectural component—it's the intermediary for all fiat cross-currency conversions and the accumulator of unrealized FX exposure. More central than the industry description suggests.

### No nostro/vostro terminology

The industry description uses banking-standard terms (nostro, vostro, interbranch). The spec deliberately avoids these, focusing on functional roles (source, target, trading, collateral accounts). Not wrong—just not the vocabulary of this design.

## What the industry description misses that matters here

- **The three-regime separation** is the single most important design decision in this spec and the industry description doesn't surface it.
- **Configurable functional currency**—the spec doesn't assume USD; any deployment currency works, which affects what counts as "foreign."
- **Rate staleness enforcement**—consumer-side freshness checks (60s for BTC transactions, 5min for fiat) are part of the revaluation design, not just an operational concern.
- **Per-transaction rate recording** as a distinct requirement from revaluation rates.

## Bottom line

The industry description is a good **general banking reference** but would need significant refinement to serve as design guidance for this system. The key gap is that it treats FX revaluation as one regime with variations, while the spec's core insight is that there are **three fundamentally different regimes** (fiat FX, BTC fair value, BTC collateral) governed by different accounting standards, with different cadences, different P&L treatments, and strict prohibitions against mixing them.

The spec already covers the fiat-FX portion of what the industry description captures, but intentionally goes beyond it by recognizing that BTC doesn't fit the traditional FX revaluation model at all.
