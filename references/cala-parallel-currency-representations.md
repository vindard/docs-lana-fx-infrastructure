# Parallel Currency Representations in CALA: Industry Comparison & Requirements

## 1. Problem Statement

Ledger entries frequently need to carry amounts in more than one currency. Common use cases include:

- **Functional/accounting currency:** Recording the book value of a foreign-currency transaction in the entity's home currency (IAS 21).
- **Group/consolidation currency:** Recording the amount in a parent company's reporting currency for consolidated financial statements.
- **Reporting currency:** A secondary currency required by regulators or internal policy.
- **Object currency:** A currency tied to a cost object or profit center.

This document describes what CALA already supports for multicurrency, identifies the specific gap relative to major ERP/GL systems, and derives requirements for closing it.

---

## 2. What CALA Already Supports

CALA has strong multicurrency foundations. Understanding what already exists clarifies that the gap is narrow and specific.

### 2.1 Currency-Agnostic Accounts

CALA accounts carry no currency field. An account is defined by its `id`, `code`, `name`, `normal_balance_type`, and metadata — but not by a currency. This means any account can receive entries in any currency without constraint. This is more flexible than most ERP systems, which typically bind accounts to a single currency or currency pair.

### 2.2 Per-Currency Balance Tracking

Balances are keyed by `(journal_id, account_id, currency)`. Each unique combination maintains its own independent balance with three layers (settled, pending, encumbrance). This means a single account can simultaneously hold a USD balance, a EUR balance, and a BTC balance — all tracked separately with full layer support.

### 2.3 Multi-Currency Transactions

A single CALA transaction can contain entries in multiple currencies. The balance validation rule is per `(currency, layer)`: debits must equal credits for each currency on each layer independently. This already supports use cases like currency conversion, where a transaction debits BTC and credits USD in a single atomic operation.

### 2.4 The Gap

What CALA lacks is the ability to carry **parallel currency representations on a single entry**. Each entry stores one `(currency, units)` pair. To record both "60 EUR was deposited" and "that 60 EUR is worth 66 USD" on the same economic event, the application must create separate entries — one for the transaction currency amount and another for the parallel currency equivalent.

This works, but has structural consequences:

- **Template proliferation.** Every template that touches foreign currency needs a variant with additional entries for the parallel amounts. Template count multiplies.
- **Structural disconnection.** The transaction-currency entry and its parallel-currency equivalent are independent rows that happen to share a transaction. There is no intrinsic link between them — correlating "what is the USD equivalent of this EUR entry?" requires application-level heuristics.
- **Same-currency degeneracy.** When the parallel currency equals the transaction currency, the parallel entries are exact duplicates. The application must either route to a different template or accept redundant double-posting.
- **Balance conflation risk.** Both the transaction-currency entries and the parallel-currency entries feed into the same balance pipeline, keyed by `(journal, account, currency)`. A USD parallel balance (representing the book value of a EUR position) would be summed with actual USD transaction balances on the same account — producing an incorrect result.

The industry pattern (§3) solves this by treating parallel currency amounts as **columns on the entry**, not as additional entries.

---

## 3. Industry Comparison

### 3.1 SAP S/4HANA — ACDOCA (Universal Journal)

SAP's Universal Journal stores **up to 10 parallel currency amounts per journal entry line**:

| Column | Purpose |
|--------|---------|
| `RHCUR` / `HSL` | Local (company code) currency |
| `RWCUR` / `TSL` | Transaction currency |
| `RKCUR` / `KSL` | Group currency |
| `ROCUR` / `OSL` | Object currency |
| `R2CUR` – `R0CUR` | User-defined parallel currencies |

Every posting to ACDOCA writes one row. That single row carries the transaction amount and up to nine parallel currency equivalents. Currency type is a **column-level concept** — the row count does not change based on how many currency representations are needed.

**Balance computation:** SAP maintains separate balance aggregations per currency type. Balances are computed from the parallel currency columns, not from separate entry rows.

**Same-currency handling:** When two currency types resolve to the same currency code, their columns hold the same value. No conditional logic, no extra rows.

### 3.2 Microsoft Dynamics 365 Finance

Every General Ledger entry in Dynamics 365 stores **three amounts**:

| Field | Purpose |
|-------|---------|
| `TransactionCurrencyAmount` | Original transaction currency |
| `AccountingCurrencyAmount` | Accounting currency (company-level) |
| `ReportingCurrencyAmount` | Optional secondary reporting currency |

Amounts are computed independently using the transaction-date rate. The GL stores all three on every entry — there is no conditional inclusion.

**Balance computation:** Dynamics maintains trial balances per currency type, computed from their respective columns.

**Same-currency handling:** When currencies match, the columns hold identical values. The column still exists and is populated.

### 3.3 Oracle General Ledger

Oracle GL stores entries with:

| Field | Purpose |
|-------|---------|
| `ENTERED_DR` / `ENTERED_CR` | Transaction (entered) currency amounts |
| `ACCOUNTED_DR` / `ACCOUNTED_CR` | Accounted currency amounts |
| `CURRENCY_CODE` | Transaction currency |

Every journal line has both entered and accounted amounts.

**Same-currency handling:** `ENTERED == ACCOUNTED` when currencies match.

### 3.4 Common Pattern

All three systems share the same structural solution:

> **Multiple currency columns per entry row, not multiple entry rows per currency.**

| System | Transaction Amount | Parallel Amounts | Extra Rows per Currency? |
|--------|--------------------|------------------|--------------------------|
| SAP ACDOCA | `RWCUR/TSL` | Up to 9 parallel columns | No |
| Dynamics 365 | `TransactionCurrencyAmount` | 2 parallel columns | No |
| Oracle GL | `ENTERED_DR/CR` | 1 parallel column pair | No |
| **CALA (current)** | `currency/units` | *(not available)* | **Yes — must add separate entries** |

---

## 4. Recommendation

**Extend CALA to support optional parallel currency amounts on entries.**

This aligns CALA with the universal industry pattern where each entry row carries the transaction-currency amount plus one or more parallel currency equivalents. It eliminates the need for template proliferation, application-layer routing heuristics, and structural workarounds.

The extension should be **additive and backward-compatible**: existing entries carry no parallel amounts, and all current behavior is preserved. Parallel currency amounts participate in separate balance pipelines that track each currency type's balances independently.

---

## 5. Requirements (Derived from Industry Standards)

The following requirements capture what CALA must support to align with the parallel currency entry model used by SAP, Dynamics 365, and Oracle GL. These are stated as behavioral requirements, not implementation prescriptions.

### 5.1 Parallel Currency Amounts on Entries

**REQ-1: Each entry must be able to carry one or more parallel currency amounts alongside its transaction-currency amount.**

An entry records a transaction in its original currency (e.g. 60 EUR). The ledger must also be able to record, on the same entry, equivalent amounts in other currencies (e.g. 66 USD, 57 GBP). This is a column-level concept — it must not require additional entry rows.

- Each parallel amount consists of a currency code and a decimal amount, supplied as a pair.
- Parallel amounts are always positive; they inherit their debit/credit direction from the entry.
- When a parallel currency equals the transaction currency, the parallel amount equals the transaction amount.
- Entries that carry no parallel amounts behave identically to entries today (backward compatibility).

**Industry basis:** SAP carries up to 10 currency amounts per ACDOCA row. Dynamics 365 carries 3 per GL entry. Oracle carries 2 per journal line. None create additional rows for currency representations.

### 5.2 Template-Driven Parallel Amounts

**REQ-2: Transaction templates must be able to specify parallel currency amounts as expressions, evaluated at post time.**

CALA templates define entries using CEL expressions (e.g. `params.amount`, `params.currency`). Parallel currency fields must follow the same pattern — optional expressions that, when present, are evaluated alongside the existing fields.

This eliminates the need for separate template variants per currency combination. A single template handles any number of parallel currency representations by accepting the appropriate parameters.

**Industry basis:** All three systems compute parallel currency amounts at posting time using the transaction-date exchange rate. The posting rule defines where each parallel amount goes — there is no separate "FX variant" of a posting rule.

### 5.3 Parallel Currency Balance Validation

**REQ-3: Transactions must balance in each parallel currency independently, not just in the transaction currency.**

CALA currently validates that every transaction balances per `(currency, layer)` — debits equal credits for each currency on each layer. The same invariant must hold for parallel currency amounts: for each parallel currency type present in the transaction, debits must equal credits per `(parallel_currency, layer)`.

**Industry basis:** SAP, Dynamics 365, and Oracle all enforce that journal entries balance independently in each currency type they carry.

### 5.4 Separate Balance Pipeline per Currency Type

**REQ-4: The ledger must maintain balances for each parallel currency type separately from transaction-currency balances.**

Transaction-currency balances answer: "How many EUR does this account hold?" A parallel currency balance answers a different question — e.g. "What is the USD book value of this account's EUR position?" or "What is this position worth in group reporting currency?" These are distinct quantities that must not be conflated.

- Parallel currency balances must be keyed by `(journal, account, currency_type, currency)` or equivalent, stored in a pipeline that is separate from transaction-currency balances.
- Parallel currency balances must track the same layer structure (settled, pending, encumbrance) as transaction-currency balances.
- Parallel currency balance updates must occur atomically within the same database transaction as the entry post.

**Why separate?** If a parallel USD balance (e.g. the book value of a EUR position) and a transaction USD balance (actual USD holdings) shared the same aggregation, they would be summed together — producing an incorrect result.

**Industry basis:** SAP maintains separate balance aggregations per currency type. Dynamics 365 computes trial balances per currency type from their respective columns. Oracle reads accounted balances from `ACCOUNTED_DR/CR`, not from `ENTERED_DR/CR`.

### 5.5 Parallel Currency Balance Query API

**REQ-5: The ledger must expose a query interface for parallel currency balances.**

Consumers need to retrieve the current balance for a specific currency type on an account. The query must return the balance with the same layer structure as transaction-currency balance queries.

Example — a revaluation consumer would query:
```
book_value  = parallel_balance(journal, account, "functional", USD).settled
fair_value  = transaction_balance(journal, account, EUR).settled × closing_rate
adjustment  = fair_value − book_value
```

**Industry basis:** All three systems provide direct query paths for each currency type's balances.

### 5.6 Backward Compatibility

**REQ-6: All changes must be additive. Existing templates, entries, balances, and queries must continue to work without modification.**

- Existing entries (already persisted) must deserialize correctly with parallel currency fields absent.
- Existing templates that do not specify parallel currency expressions must produce entries identical to today.
- Existing transaction-currency balance tables and queries must be unaffected.
- Entry creation without parallel currency fields must work exactly as before.

**Industry basis:** SAP's additional currency columns are optional/nullable. Dynamics 365's `ReportingCurrencyAmount` is optional. The pattern is inherently additive.

---

## 6. Open Questions

1. **Velocity controls:** Should parallel currency amounts participate in velocity limit checks? Initial recommendation: no — velocity limits are typically about transaction-currency exposure.

2. **Account sets:** Should parallel currency balances be queryable through account sets? Likely yes for reporting, but can be deferred.

3. **How many parallel currencies per entry?** SAP supports up to 10. These requirements are stated generically. An initial implementation could support one parallel currency per entry and extend later, or support N from the start. The requirements are compatible with either approach.

4. **Adjustment-only entries:** Some use cases (e.g. revaluation) adjust only a parallel currency balance without changing the transaction-currency balance. These entries would carry parallel amounts but have `units = 0` in the transaction currency (or omit the transaction leg entirely). Need to decide whether to allow parallel-only entries or require a zero-valued transaction leg.

5. **Effective balances:** Should period-bucketed effective balances also support parallel currency types? Needed for period-end reporting but can be deferred.
