# FX Infrastructure: Summary

> For the full specification with schemas, code examples, and accounting details, see [SPEC.md](SPEC.md).

## The Problem

Lana's entire FX capability is a single struct — `PriceOfOneBTC` — that fetches a live BTC/USD spot rate from one provider (Bitfinex) and discards it. There is no rate history, no record of which rate was used for any transaction, no gain/loss tracking, no revaluation process, and no support for currency pairs beyond BTC/USD. Any multicurrency expansion or accounting compliance (IAS 21 for fiat FX, ASU 2023-08 for BTC fair value) is impossible on this foundation.

## Why FX Infrastructure Is Required

A multicurrency lending platform that holds BTC collateral and transacts in multiple fiat currencies has obligations that a simple spot-rate converter cannot meet. These fall into three categories:

**Accounting compliance demands rate history and per-transaction recording.**

Fiat foreign-currency balances must be revalued at period-end closing rates under IAS 21 / ASC 830 — this requires a historical rate record that exists independently of any transaction. Separately, every journal entry that crosses currencies must capture the exact rate that produced its amounts, because that rate becomes the baseline from which all future revaluation deltas are computed. Without both, financial statements cannot be produced correctly.

**BTC and fiat follow fundamentally different regimes.**

BTC is not a foreign currency — under FASB ASU 2023-08 it is an intangible asset measured at fair value through net income. Fiat FX uses closing-rate revaluation with unrealized/realized gain/loss separation (IAS 21). These two regimes require separate account structures, separate revaluation logic, and must never be commingled in the same intermediary accounts. A platform that treats BTC-to-USD the same as EUR-to-USD will produce incoherent financial statements.

**Custodied BTC creates an agent relationship with its own accounting rules.** 

When the platform holds BTC collateral on behalf of borrowers, price movements affect both the asset and the obligation equally — there is no P&L impact. This is economically and legally distinct from BTC the platform owns. Commingling the two, or failing to reconcile on-chain balances against the ledger, creates the kind of segregation failure that brought down platforms like Celsius.

**Operational resilience requires multi-source rates with safety controls.**

A single price feed with no staleness checks, no circuit breakers, and no fallback means that one provider outage or one bad data point can silently corrupt every conversion, LTV calculation, and collateral valuation in the system. Rate infrastructure must be hardened before it underpins accounting entries.

## The Plan

### Component 1 — Exchange Rate Storage

Replace the ephemeral spot-rate fetch with a persistent `exchange_rates` table supporting multiple currency pairs, rate types (spot and closing), source tracking, and historical lookups including inverse and cross-rate triangulation via USD.

### Component 2 — Multi-Source Rate Aggregation

Eliminate the single-provider dependency by aggregating rates from multiple sources (Bitfinex, Coinbase, Kraken) using a median strategy with tolerance band filtering. Each source implements a common adapter trait; the existing Bitfinex feed becomes one adapter among several.

### Component 3 — Rate-Per-Transaction Recording

Store the exact exchange rate used on every cross-currency journal entry (and the spot rate on single-currency non-functional-currency transactions). This provides the authoritative audit trail and the baseline for future revaluation calculations.

### Component 4 — Trading Accounts (Selinger Model)

Introduce an FX Trading Account as the intermediary for fiat-to-fiat conversions. Its running balance represents cumulative unrealized FX exposure. BTC is explicitly excluded — it follows a separate fair value regime. New chart-of-accounts entries cover realized/unrealized FX gain/loss and rounding differences.

### Component 5 — Period-End Revaluation

Two separate revaluation regimes run as daily jobs:
- **Fiat FX (IAS 21):** Revalue foreign-currency monetary balances at the closing rate using the delta method, posting to unrealized gain/loss accounts.
- **BTC Fair Value (ASU 2023-08):** Adjust platform-owned BTC to current fair value with cumulative P&L entries — no reversals, no unrealized/realized distinction.

### Component 6 — BTC Collateral Accounting

Handle custodied BTC under the agent relationship: both the asset (collateral held) and liability (obligation to return) move together on price changes, producing no P&L impact. Includes cost basis / lot tracking for liquidation events, segregation controls via CALA template restrictions, and on-chain/ledger reconciliation with proof-of-reserves attestation.

### Component 7 — Job Orchestration

All FX operations plug into the existing `EndOfDay` event and job framework (handler → collector → worker pattern). Three independent job chains run daily for fiat FX revaluation, BTC fair value revaluation, and collateral revaluation. LTV monitoring runs at higher frequency, triggered by price update events.

### Component 8 — Regulatory and Reporting

The above components collectively satisfy audit trail requirements, rate methodology documentation, ASC 830 cash flow statement translation, and segregation/proof-of-reserves obligations.

## Implementation Phases

All groups are independent — no cross-group dependencies. They can run in any order or in parallel.

| Group | Phase | What | Dependencies |
|-------|-------|------|--------------|
| **A** *(independent)* | | Rate-per-transaction recording (C3) | None — can be picked up by any workstream or bundled into B |
| **B** *(parallel)* | **3** | Fiat FX trading account + realized gain/loss (C4) | None — fires inline on each conversion, no jobs |
| | **4** | Fiat FX revaluation, unrealized (C4 remainder, C5 fiat, C7) | None — period-end mark-to-market of foreign-currency balances |
| **C** *(parallel)* | **2** | Collateral revaluation (C6 partial, C7 minimal) | None — one template, one job chain, immediate LTV accuracy |
| | **5** | BTC fair value revaluation (C5 BTC, C7) | **Phase 2** — collateral boundary must exist. Also needs ASU 2023-08 sign-off |
| **Deferred** | Rate storage + multi-source aggregation + robustness (C1, C2) | Full historical storage and multi-provider resilience — build when operational needs demand it |
| **Deferred** | Regulatory and reporting (C8) | Reporting capabilities that consume the infrastructure built above |
| **Deferred** | Segregation controls + on-chain reconciliation (C6 remainder) | Enforcement/verification layers on top of Phase 2 collateral accounting — build when regulatory attestation demands it |
