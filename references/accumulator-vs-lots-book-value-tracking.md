# Book Value Tracking: Accumulator vs Lot-Based Approaches

## The Problem

We are evaluating the best approach to tracking multicurrency values and facilitating operations like period-end revaluation, realized G/L on disposal, and proportional unwind on partial removal. The core challenge: when the bank holds foreign currency acquired across multiple conversions at different rates, the system must be able to answer three questions at any point:

1. **How much EUR do we hold?** (foreign balance)
2. **What did it cost us in USD?** (book value)
3. **What is it worth now?** (fair value at closing rate)

The difference between (3) and (2) is unrealized G/L. The difference between sale proceeds and (2) on disposal is realized G/L. Both require knowing the book value.

We are evaluating two approaches to maintaining this book value:

- **Accumulator model** (Selinger-style) — collapse all inflows into two running scalars (total foreign amount, total functional-currency cost). Partial removal uses proportional weighted-average allocation. This is what PR #4552 implements.
- **Lot-based model** — track each inflow as a discrete record with its own rate, date, and cost basis. Partial removal requires a cost-flow policy (FIFO, LIFO, specific identification, or weighted average) to determine which lots are consumed.

## Why External State Is Needed

Every foreign-currency account carries two balances: a foreign-currency balance and a functional-currency (USD) balance, established by Group A's dual-currency entries. The USD balance starts as the book value — what the foreign currency cost us. But it doesn't stay that way.

**Revaluation overwrites book cost with fair value.** When the revaluation job runs, it posts an adjustment that brings the USD balance to fair value at the closing rate. A 100 EUR deposit at rate 1.10 starts with USD balance = 110 (book cost). After revaluation to rate 1.20, the balance becomes 120 — the original 110 is no longer readable from the running balance. After a second revaluation to 1.05, it becomes 105. Each revaluation replaces the previous carrying value with the new fair value.

This is fine for **revaluation itself** — the delta method computes `(foreign_balance × closing_rate) − current_usd_balance`, posting only the incremental change. It doesn't need book cost because it always adjusts from the current carrying value to the new fair value.

But it creates a problem for **any operation that needs the original book cost**. Withdrawal reval unwind, for example, must separate the book portion from the reval portion of the USD balance to reverse only the reval on the withdrawn amount. The running balance (120) doesn't tell you how much is book (110) vs reval (+10). This information still exists in the ledger entry history — the original 110 transaction entry and the +10 revaluation entry are separate records — but extracting it requires entry-level reconstruction, not just reading the running balance.

On regular accounts (Deposit, Omnibus), this is manageable. The book cost is **preserved in the entry history** even though the running balance has been overwritten. The problem escalates when currency is **converted**. A customer's 50 EUR (booked at 1.10, cost = 55 USD) is sold on the FX market at 1.15, yielding 57.50 USD. The bank needs to recognize the 2.50 USD spread as realized gain — a permanent P&L item, separate from the temporary unrealized adjustments that revaluation produces. This requires isolating the realized G/L into its own account.

The **Trading Account** is the mechanism for this isolation. The conversion flows through it as an intermediary, and a G/L clearing entry extracts the realized gain:

```
Convert 50 EUR at rate 1.15 (from walkthrough Step 2):

  Dr  Trading           50 EUR           ← acquire EUR from customer
  Cr  EUR Deposit       50 EUR

  Dr  Trading           55 USD           ← book value leg (50 × 1.10)
  Cr  EUR Deposit       55 USD

  Dr  USD Cash          57.50 USD        ← sale proceeds (50 × 1.15)
  Cr  Trading           57.50 USD

  Dr  Trading           2.50 USD         ← G/L clearing
  Cr  Realized FX Gain  2.50 USD
```

The G/L clearing works: realized gain is isolated in its own P&L account. But it has a side effect — Trading's USD ledger balance is now `55 − 57.50 + 2.50 = 0`. The book cost of 55 USD has been zeroed out. The Trading Account holds 50 EUR but the ledger has no record of what they cost.

After a second conversion adds 30 EUR at rate 1.25 (book cost 33 USD), the ledger shows Trading at `Dr 80 EUR, Dr 0 USD`. The true book cost of 88 USD (55 + 33) is gone. The revaluation formula `(80 × closing_rate) − 0` would post the full fair value as unrealized gain instead of just the delta from book cost.

**Something external must track book value for the Trading Account.** The G/L clearing that makes realized gain isolation work is the same mechanism that destroys the book value the system needs for revaluation, partial settlement, and reval unwind. Both the accumulator and lot-based approaches restore this — they differ in how.

## The Two Approaches

The ledger layer is identical under both approaches: the same Trading Account, the same G/L clearing, the same revaluation entries. Both require application-layer state outside the ledger. They differ in what that external state looks like and how it behaves.

### Accumulator

**External state:** two running scalars per currency.

```rust
struct FxPosition {
    accumulated_foreign: Decimal,     // total EUR held
    accumulated_functional: Decimal,  // total USD book cost
}
```

**On conversion (inflow):**

The orchestrator reads the source account's USD ledger balance to compute proportional book value, posts ledger entries, and adds to the accumulator:

```
accumulated_foreign += foreign_amount
accumulated_functional += functional_amount
```

After two conversions:
```
Inflow 1: 50 EUR, book cost 55 USD  →  accumulator: (50, 55)
Inflow 2: 30 EUR, book cost 33 USD  →  accumulator: (80, 88)
```

**On settlement (outflow):**

The orchestrator reads the accumulator for proportional book cost, reads the ledger for proportional reval to unwind, posts ledger entries, and reduces the accumulator:

```
proportion = foreign_amount / accumulated_foreign
book_cost_removed = proportion × accumulated_functional
realized_gl = sale_proceeds − book_cost_removed

accumulated_foreign -= foreign_amount
accumulated_functional -= book_cost_removed
```

Example — settle 40 EUR at 1.20 (proceeds = 48 USD):
```
weighted_avg_rate = 88 / 80 = 1.10
book_cost_removed = (40 / 80) × 88 = 44
realized_gl = 48 − 44 = +4

accumulator after: (40, 44)   ← avg rate still 1.10
```

One formula, one outcome, no choices. This is weighted-average cost (WAC) by construction.

**For revaluation:**

The revaluation job reads `accumulated_functional` as book value. The delta method formula for the Trading Account becomes:

```
fair_value = accumulated_foreign × closing_rate       ← from accumulator + market
book_value = accumulated_functional                    ← from accumulator
prior_reval = trading_account_usd_ledger_balance       ← from ledger (which is ONLY reval)
adjustment = fair_value − (book_value + prior_reval)
```

The revaluation job must branch: regular accounts read book value from the ledger; the Trading Account reads from the accumulator.

**For reval unwind on partial settlement:**

```
reval_to_unwind = (settled_foreign / accumulated_foreign) × trading_usd_ledger_balance
```

Proportional to the blended position — no lot selection needed.

### Lot-based

**External state:** a table of per-inflow records.

```
{lot_id, foreign_amount, functional_amount, rate, acquired_at,
 remaining_foreign, remaining_functional, reval_state}
```

Plus a configured cost-flow policy (FIFO, LIFO, specific identification, or WAC).

**On conversion (inflow):**

The orchestrator reads the source account's USD ledger balance (same as accumulator), posts ledger entries (same as accumulator), and creates a new lot record:

```
Lot 1: 50 EUR at 1.10 → book cost 55 USD, acquired 2026-01-15
Lot 2: 30 EUR at 1.25 → book cost 37.50 USD, acquired 2026-02-10
```

**On settlement (outflow):**

The orchestrator must select lots according to policy, split any partially consumed lot, compute book cost as the sum of consumed lot costs, compute per-lot reval to unwind, post ledger entries, and update/close lot records.

Example — settle 40 EUR, same position as above:

**FIFO:** Consume 40 from Lot 1 → book cost 44, G/L = +4
**LIFO:** Consume 30 from Lot 2 + 10 from Lot 1 → book cost 48.50, G/L = −0.50
**WAC:** Average rate 1.15625 → book cost 46.25, G/L = +1.75

Three policies, three different realized G/L, three different remaining positions. Note that the lot-based WAC result (46.25) differs from the accumulator's result (44) because lots preserve per-inflow rates while the accumulator blends them on entry. They converge only when all inflows share the same rate.

**For revaluation:**

The revaluation job must also branch (same as accumulator — the ledger balance is not book value regardless). With lots, the job must either:
- Sum `remaining_functional` across all lots to get total book value (equivalent to what the accumulator provides in one read), or
- Revalue each lot individually (more precise but higher complexity, and the ledger entries are still posted at the account level, not per-lot)

**For reval unwind on partial settlement:**

Each lot carries its own revaluation state:

```
Lot 1: 50 EUR, book 55, reval +5 (from period 1 at rate 1.20)
Lot 2: 30 EUR, book 37.50, reval +1.50 (acquired mid-period, partial reval)
```

Reval unwind follows the same consumption policy. A FIFO removal of 40 EUR touches Lot 1 only, unwinding `(40/50) × 5 = 4` of its reval. A LIFO removal touches both lots and produces a different unwind amount.

### Summary comparison

| Component | Accumulator | Lot-based |
|---|---|---|
| Ledger structure | Identical | Identical |
| External state needed? | Yes — G/L clearing destroys book value either way | Yes — same reason |
| External data structure | 2 scalars per currency | N records per currency (unbounded) |
| Cost-flow policy | None (WAC by construction) | Required (FIFO/LIFO/specific ID/WAC) |
| Revaluation job divergence | Read book value from accumulator instead of ledger | Read book value by summing lots (or revalue per-lot) |
| Outflow complexity | O(1) — proportional math on 2 scalars | O(n) — select, split, consume lots |
| Partial lot handling | N/A | Required (split lot records on partial consumption) |
| Per-inflow audit trail | Not preserved (blended on entry) | Preserved (each lot retains its rate and date) |

The critical insight: **both approaches require application-layer infrastructure outside the ledger**. The accumulator is not a workaround for a deficiency that lots would avoid — the ledger's G/L clearing makes external book value tracking necessary regardless. The choice is between minimal external state (two scalars) with WAC-only semantics, or richer external state (lot records) with policy flexibility.

## Trade-offs

### When lots are needed

**Policy flexibility.** If accounting policy requires FIFO or specific identification (common for tax optimization or regulatory reasons), lots are mandatory. The accumulator produces weighted-average results only — it cannot reconstruct which EUR were acquired at which rate.

**Per-lot audit trail.** Each lot has a creation date, source transaction, and individual cost basis. This matters for tax reporting (holding period rules, short-term vs long-term gains).

**Precise reval attribution.** If lots were acquired at different points in the revaluation cycle, their individual reval states differ. The accumulator can only compute proportional reval for the blended position.

The SPEC already uses lot-based tracking for BTC collateral (Component 6, `CollateralLot` struct) — tax reporting demands specific identification and per-deposit cost basis on liquidation. This may extend beyond collateral: platform-owned BTC under ASU 2023-08 uses direct fair value booking (no trading account), but disposing of platform-owned BTC (e.g., selling treasury BTC or BTC received as fee income) is a taxable event that requires cost basis. If the platform acquires BTC across multiple transactions at different prices, lot-based tracking with specific identification or FIFO may be needed to compute the correct gain/loss on disposal. The SPEC does not explicitly address this — it covers collateral lots but not platform-owned BTC lots. This is a gap worth flagging for the ASU 2023-08 compliance review.

### When the accumulator is sufficient

**Flow-through intermediaries.** The Trading Account is not a long-held investment portfolio. Positions enter via conversion and exit via settlement, typically within days. The scenarios where FIFO vs LIFO produces materially different results — long holding periods, widely varying acquisition rates, tax-sensitive disposals — don't apply to fiat FX.

**IAS 21 compatibility.** The standard does not mandate a specific cost-flow assumption for monetary items. Weighted average is an acceptable policy.

**Operational simplicity.** Two scalars instead of an unbounded list. O(1) operations instead of O(n) lot consumption. No lot-splitting, no policy configuration, no consumption-order disputes.

**Deterministic replay.** The event-sourced accumulator rebuilds to the same state regardless of replay order. Lot-based systems with FIFO/LIFO can produce different results if events arrive out of order.

The Selinger model's core insight (from the selinger doc, section 7.1) is precisely this transformation:

> From a **matching problem** (lots, FIFO, pairing) to a **flow + accumulation problem** (deltas into a residual account).

## Current Implementation Status (PR #4552)

PR #4552 implements the accumulator approach. Current state:

| Capability | Status |
|---|---|
| Data structure (`FxPosition` entity) | Implemented |
| Event sourcing + persistence | Implemented |
| `record_inflow` (conversion entry) | Implemented |
| `record_outflow` (settlement, realized G/L) | Implemented |
| Proportional weighted-average allocation | Implemented |
| Hydration from event replay | Implemented |
| Orchestrator wiring (`convert_fiat_fx`) | Implemented |

### What is still missing

**1. Revaluation consuming the accumulator (Phase 4)**

No revaluation code exists yet. When it's built, the revaluation worker must branch: regular accounts read book value from the ledger; the Trading Account reads `accumulated_functional` from the accumulator.

**2. Reval unwind on partial settlement**

When part of the Trading Account position is settled, the accumulated revaluation on that portion must be reversed. PR #4552's `record_outflow` handles the realized G/L side but doesn't post reval reversal entries — that requires the revaluation infrastructure to exist first.

**3. Book value leg on the conversion template**

The CALA template `FIAT_FX_CONVERSION_VIA_TRADING` is missing the book-value transfer (entries ⑦-⑧ in the walkthrough). Without it, the accumulator's `record_inflow` has no `functional_amount` to record — the orchestrator needs to read the source account's USD balance, compute the proportional book value of the EUR being converted, and pass it both to the template (for the ledger leg) and to the accumulator.

**4. Withdrawal reval-unwind coordination**

Withdrawals from Deposit/Omnibus don't touch the Trading Account or its accumulator — they use the ledger's own book value. But the withdrawal template needs proportional reval unwind entries on both the Deposit and Omnibus sides. This is a template gap, not an accumulator gap, but it's part of the same "partial removal" problem space.
