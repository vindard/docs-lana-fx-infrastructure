# Parallel Currency Representations in CALA

CALA's entry model stores a single `(currency, units)` pair per entry. When a ledger needs to represent the same economic event in multiple currencies — for example, recording both a 60 EUR deposit and its 66 USD book value — the application must create separate entries. This document examines whether that limitation matters, how major systems handle it, what workarounds exist today, and what it would take to close the gap.

---

## 1. What CALA Already Supports

CALA has strong multicurrency foundations. The gap is narrow and specific.

**Currency-agnostic accounts.** Accounts carry no currency field. Any account can receive entries in any currency. This is more flexible than most ERP systems, which bind accounts to a single currency.

**Per-currency balance tracking.** Balances are keyed by `(journal_id, account_id, currency)`. A single account can simultaneously hold USD, EUR, and BTC balances, each tracked independently with three layers (settled, pending, encumbrance).

**Multi-currency transactions.** A single transaction can contain entries in multiple currencies. Balance validation is per `(currency, layer)`: debits must equal credits for each currency on each layer independently.

**Entry-level metadata.** Each entry supports an arbitrary `metadata: Option<serde_json::Value>` field, persisted atomically with the entry and evaluable via CEL expressions in templates.

**The gap.** Each entry carries one `(currency, units)` pair. To record both "60 EUR was deposited" and "that 60 EUR is worth 66 USD," the application must create separate entries — one for the transaction-currency amount, another for the parallel equivalent. This has four structural consequences:

1. **Balance conflation.** Both entries feed into the same balance pipeline. A USD parallel balance (the book value of a EUR position) is summed with actual USD transaction balances on the same account, producing an incorrect result.
2. **Template proliferation.** Every template that touches foreign currency needs a variant with additional entries. Template count multiplies.
3. **Structural disconnection.** The transaction-currency entry and its parallel equivalent are independent rows with no intrinsic link. Correlating them requires application-level heuristics.
4. **Same-currency degeneracy.** When the parallel currency equals the transaction currency, the parallel entries are exact duplicates. The application must route to a different template or accept redundant posting.

---

## 2. Industry Comparison

ERP/GL systems and purpose-built ledger platforms take opposite approaches.

**ERP/GL systems store parallel currency amounts as columns on each entry row.** SAP's Universal Journal (ACDOCA) carries up to 10 currency amounts per row — transaction, local, group, object, and six user-defined currencies — all on a single line. Microsoft Dynamics 365 stores three amounts per entry: transaction, accounting, and reporting currency. Oracle GL stores entered and accounted amounts per journal line. In all three systems, the row count does not change based on how many currency representations are needed. Balances are maintained separately per currency type, computed from the parallel columns. When two currency types resolve to the same code, the columns hold the same value — no conditional logic, no extra rows.

**Ledger platforms use separate entries per currency.** Modern Treasury's model is more constrained than CALA: accounts are currency-bound (each has a mandatory `currency` field), so cross-currency transactions inherently require entries to different accounts. The exchange rate is stored as informational metadata on the transaction. This is structurally equivalent to the multiple-template approach (§3.1) without the conditional routing — currency-bound accounts force the multi-entry pattern. CALA takes the same multi-entry approach but with more flexibility, since accounts are currency-agnostic.

Neither Modern Treasury nor CALA supports parallel currency columns on entries.

| System | Transaction Amount | Parallel Amounts | Extra Rows per Currency? |
|--------|--------------------|------------------|--------------------------|
| SAP ACDOCA | `RWCUR/TSL` | Up to 9 parallel columns | No |
| Dynamics 365 | `TransactionCurrencyAmount` | 2 parallel columns | No |
| Oracle GL | `ENTERED_DR/CR` | 1 parallel column pair | No |
| Modern Treasury | Account-level currency | *(not available, rate in tx metadata)* | Yes |
| **CALA** | `currency/units` | *(not available)* | **Yes** |

---

## 3. Application-Level Approaches Without CALA Changes

Five approaches are available today for tracking parallel currency amounts using CALA as-is. Each avoids modifying the ledger library but introduces trade-offs that matter in a banking application, where balance correctness and auditability are fundamental requirements.

### 3.1 Multiple Templates with Conditional Routing

Create separate templates for same-currency and cross-currency cases. A USD deposit uses `RECORD_DEPOSIT` (2 entries); a EUR deposit uses `RECORD_DEPOSIT_FX` (4 entries — 2 in EUR, 2 in USD). The application routes to the appropriate template at posting time.

Parallel amounts participate in the balance pipeline — but **balance conflation** is the primary concern. The parallel USD entries land in the same `(journal, account, USD)` balance as actual USD transaction entries. A balance that cannot cleanly answer either "how many USD does this account hold?" or "what is the USD book value of the EUR position?" is a correctness problem. Beyond conflation, every template that involves foreign currency needs a variant (doubling template count), and the transaction-currency entries and their parallel equivalents are structurally independent with no intrinsic link.

### 3.2 Entry or Transaction Metadata

Store the parallel currency amount, currency code, and/or exchange rate in CALA's existing metadata fields. No additional entries are created.

```json
{
  "parallel_currency": "USD",
  "parallel_amount": "66.00",
  "exchange_rate": "1.10"
}
```

This is the simplest approach — zero template proliferation, zero balance conflation, one template for all currency cases — but **the ledger is not the source of truth for parallel-currency positions.** Book value exists only in metadata, outside the balance pipeline, unqueryable, and not subject to CALA's balance validation or integrity guarantees. Revaluation must scan entry metadata and aggregate book value externally, duplicating logic the balance pipeline already provides. Every consumer that needs book value must know to look in metadata rather than balances — a convention that must be maintained across the entire application.

### 3.3 External Entity

Like §3.2, this keeps book value outside the balance pipeline — but moves it outside CALA entirely into an application-level domain entity. The distinction matters for atomicity: with metadata (§3.2), book value is persisted atomically with the entry. With an external entity, the CALA posting and the entity update are separate writes that must be explicitly coordinated.

**Split source of truth** is the primary concern. Transaction-currency balances live in CALA; parallel-currency book values live in an application entity. If one updates without the other, the financial picture is inconsistent. The entity update and CALA posting must share a database transaction to prevent drift, adding infrastructure complexity. Audit trails must span two systems — the ledger alone does not provide a complete picture of financial position.

### 3.4 Separate Accounts

Create parallel account pairs: `EUR Deposit (transactional)` receives EUR entries; `EUR Deposit (parallel/USD)` receives USD book-value entries. A single template posts to both.

This is the approach Modern Treasury enforces by design (see §2). Their currency-bound accounts make separate accounts per currency mandatory. CALA can model the same pattern by convention — creating one account per currency and only posting matching entries. Balance conflation is structurally prevented because book-value entries and transaction entries live on different accounts.

The cost is **chart-of-accounts integrity.** The conceptual identity of an account is split across two objects. Every query, report, and audit must join account pairs. The chart doubles for every foreign-currency account. And unlike Modern Treasury, where the one-account-per-currency rule is structural (the system rejects mismatched postings), in CALA it is a convention the application must enforce — nothing prevents posting a USD entry to an account intended for EUR.

### 3.5 Separate Layers

Use CALA's layer mechanism to distinguish transaction-currency entries from parallel-currency equivalents. Transaction entries post on `SETTLED`; parallel equivalents post on a repurposed layer (e.g. `ENCUMBRANCE`).

**Semantic corruption of the balance model** is the primary concern. CALA's `available()` rollup sums across layers: `available(Layer::Encumbrance) = settled + pending + encumbrance`. If encumbrance is repurposed for parallel currency, this rollup produces nonsensical cross-currency sums. A balance query that silently returns an incorrect number is worse than one that returns no data — it can drive incorrect decisions downstream. Layers are designed for settlement lifecycle, not currency representation. Overloading them means every consumer must carry the convention of which layer means what, and a consumed layer slot cannot be used for actual encumbrance tracking later.

### Summary

| Approach | Templates | Balance Conflation | Book Value in Ledger | Auditability | Complexity |
|----------|-----------|-------------------|---------------------|--------------|------------|
| 3.1 Multiple templates | 2x per FX template | **Yes** | Yes | Full | High (routing) |
| 3.2 Entry metadata | 1x | No | **No** (metadata only) | Partial | Low |
| 3.3 External entity | 1x | No | **No** | Partial (split) | Medium (sync) |
| 3.4 Separate accounts | 1x | No | Yes | Full | High (pairs) |
| 3.5 Separate layers | 1x | No | Yes (overloaded) | Full | Medium (convention) |

Approaches 3.1, 3.4, and 3.5 put book value inside the balance pipeline but introduce structural overhead — conflated balances, proliferated accounts, or corrupted layer semantics. Approaches 3.2 and 3.3 keep CALA clean but move book value outside the ledger, requiring the application to own aggregation and accept a split source of truth.

---

## 4. Recommendation

**Extend CALA to support optional parallel currency amounts on entries.**

The application-level workarounds in §3 each compromise either balance correctness (§3.1), ledger-as-source-of-truth (§3.2, §3.3), chart-of-accounts integrity (§3.4), or balance-model semantics (§3.5). The ERP/GL pattern — parallel currency columns on the entry, with a separate balance pipeline per currency type — avoids all five. The extension should be additive and backward-compatible: existing entries carry no parallel amounts, and all current behavior is preserved.

---

## 5. Requirements

The following requirements capture what CALA must support to align with the parallel currency entry model used by SAP, Dynamics 365, and Oracle GL.

**REQ-1: Each entry must be able to carry one or more parallel currency amounts alongside its transaction-currency amount.** Each parallel amount consists of a currency code and a decimal amount, supplied as a pair. Parallel amounts are always positive and inherit their debit/credit direction from the entry. When a parallel currency equals the transaction currency, the parallel amount equals the transaction amount. Entries that carry no parallel amounts behave identically to entries today.

**REQ-2: Transaction templates must be able to specify parallel currency amounts as expressions, evaluated at post time.** Parallel currency fields follow the same CEL expression pattern as existing entry fields. A single template handles any number of parallel currency representations, eliminating the need for FX template variants.

**REQ-3: Transactions must balance in each parallel currency independently.** The existing validation rule — debits equal credits per `(currency, layer)` — extends to parallel currencies: for each parallel currency present in the transaction, debits must equal credits per `(parallel_currency, layer)`.

**REQ-4: The ledger must maintain balances for each parallel currency type separately from transaction-currency balances.** Transaction-currency balances answer "how many EUR does this account hold?" Parallel-currency balances answer "what is the USD book value of this EUR position?" These are distinct quantities that must not be conflated. Parallel-currency balances must track the same layer structure and update atomically within the same database transaction as the entry post.

**REQ-5: The ledger must expose a query interface for parallel currency balances.** The query accepts `(journal, account, currency_type, currency)` and returns balances with the same layer structure as transaction-currency queries.

**REQ-6: All changes must be additive.** Existing entries, templates, balance tables, and queries continue to work without modification.

---

## 6. Open Questions

1. **Velocity controls.** Should parallel currency amounts participate in velocity limit checks? Initial recommendation: no — velocity limits are typically about transaction-currency exposure.

2. **Account sets.** Should parallel currency balances be queryable through account sets? Likely yes for reporting, but can be deferred.

3. **How many parallel currencies per entry?** SAP supports up to 10. An initial implementation could support one and extend later, or support N from the start.

4. **Adjustment-only entries.** Revaluation adjustments touch only the parallel-currency balance, not the transaction-currency balance. Should these post as entries with `units = 0` and parallel amounts, or should entries be allowed to carry only parallel amounts? The latter requires relaxing the paired constraint in REQ-1.

5. **Effective balances.** Should period-bucketed effective balances also support parallel currency types? Needed for period-end reporting but can be deferred.
