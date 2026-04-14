# Collateral Ledger Accounts

**Status:** DRAFT | **Date:** 2026-04-15 | **Author:** @vindard

---

All collateral accounts are Off-Balance-Sheet. The bank holds BTC as custodian (agent), not owner — collateral never appears on the balance sheet.

## Omnibus Accounts

Bank-wide. One instance each. Debit-normal. Their balance should equal the sum of their paired facility accounts (control-account invariant).

### Collateral Omnibus (BTC)

| | |
|---|---|
| **Intended purpose** | Total BTC collateral the bank currently holds on behalf of all borrowers, excluding any collateral in or past liquidation. |
| **Current balance reflects** | Total BTC ever deposited minus total BTC withdrawn. Overstated — never reduced when collateral enters liquidation. |
| **Increased by** | `ADD_COLLATERAL` (DR this, CR Facility Collateral) |
| **Decreased by** | `REMOVE_COLLATERAL` (CR this, DR Facility Collateral) |
| **Contra accounts** | Facility Collateral (per-facility) |

### Liquidation Proceeds Omnibus (USD)

| | |
|---|---|
| **Intended purpose** | Total USD proceeds received from all liquidations across all facilities. |
| **Current balance reflects** | Matches intent. Correctly maintained. |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (DR this, CR Facility Proceeds) |
| **Decreased by** | Nothing currently. |
| **Contra accounts** | Facility Proceeds From Liquidation (per-facility) |

---

## Facility-Level Accounts

One instance per facility. Credit-normal.

### Facility Collateral (BTC)

| | |
|---|---|
| **Intended purpose** | BTC collateral currently held for this facility. |
| **Current balance reflects** | Correct when no liquidation has occurred. After liquidation, goes to zero as expected — but its paired omnibus does not adjust (see gap). |
| **Increased by** | `ADD_COLLATERAL` (CR this, DR Collateral Omnibus) |
| **Decreased by** | `REMOVE_COLLATERAL` (DR this, CR Collateral Omnibus), `SEND_COLLATERAL_TO_LIQUIDATION` (DR this, CR Collateral In-Liquidation) |
| **Contra accounts** | Collateral Omnibus (deposit/withdrawal), Collateral In-Liquidation (liquidation) |

### Collateral In-Liquidation (BTC)

| | |
|---|---|
| **Intended purpose** | BTC from this facility currently being liquidated (sold but proceeds not yet received). |
| **Current balance reflects** | Correct at facility level. No omnibus tracks the aggregate. |
| **Increased by** | `SEND_COLLATERAL_TO_LIQUIDATION` (CR this, DR Facility Collateral) |
| **Decreased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (DR this, CR Liquidated Collateral) |
| **Contra accounts** | Facility Collateral (entry), Liquidated Collateral (exit) |

### Liquidated Collateral (BTC)

| | |
|---|---|
| **Intended purpose** | BTC from this facility that has been sold. Historical record — balance only grows. |
| **Current balance reflects** | Correct at facility level. No omnibus tracks the aggregate. |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (CR this, DR Collateral In-Liquidation) |
| **Decreased by** | Nothing. |
| **Contra accounts** | Collateral In-Liquidation (entry) |

### Facility Proceeds From Liquidation (USD)

| | |
|---|---|
| **Intended purpose** | USD proceeds received from liquidating this facility's collateral. |
| **Current balance reflects** | Matches intent. Correctly maintained. |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (CR this, DR Liquidation Proceeds Omnibus) |
| **Decreased by** | Collection flow (proceeds applied against obligations via Payment Holding). |
| **Contra accounts** | Liquidation Proceeds Omnibus (entry), Payment Holding (collection) |

---

## Templates

| Template | Entries | DR | CR | Currency |
|----------|:---:|---|---|:---:|
| `ADD_COLLATERAL` | 2 | Collateral Omnibus | Facility Collateral | BTC |
| `REMOVE_COLLATERAL` | 2 | Facility Collateral | Collateral Omnibus | BTC |
| `SEND_COLLATERAL_TO_LIQUIDATION` | 2 | Facility Collateral | Collateral In-Liquidation | BTC |
| `RECEIVE_PROCEEDS_FROM_LIQUIDATION` | 4 | Collateral In-Liquidation | Liquidated Collateral | BTC |
| | | Liquidation Proceeds Omnibus | Facility Proceeds | USD |
| `RESERVE_FOR_LIQUIDATION` | 2 | Liquidation Omnibus | Facility Liquidation | USD |

`RESERVE_FOR_LIQUIDATION` is defined but never initialized or called — dead code.

---

## Gaps

### Gap 1: Collateral Omnibus overstated after liquidation

BTC moves from Facility Collateral → Collateral In-Liquidation at the facility level, but the Collateral Omnibus is never credited. Its balance includes BTC the bank no longer holds.

**Expected behavior (standard control-account practice):** When a sub-ledger transfer changes the category of an asset, both the source and destination control accounts must be updated in the same transaction. A bank's aggregate position in each asset state must be readable from a single omnibus balance without derived arithmetic.

**Fix:** `SEND_COLLATERAL_TO_LIQUIDATION` should expand from 2 to 4 entries:

```
SEND_COLLATERAL_TO_LIQUIDATION (4 entries):
  DR  Facility Collateral              BTC  ─┐ release from "held"
  CR  Collateral Omnibus               BTC  ─┘
  DR  Collateral In-Liq. Omnibus *     BTC  ─┐ receive into "in-liquidation"
  CR  Collateral In-Liquidation        BTC  ─┘
```

*Requires new omnibus account: Collateral In-Liquidation Omnibus (BTC, OBS, Debit-normal).

### Gap 2: No aggregate view of BTC in or past liquidation

Collateral In-Liquidation and Liquidated Collateral exist at facility level but have no paired omnibus. There is no single account to query for "total BTC currently being liquidated" or "total BTC historically sold" across all facilities.

**Expected behavior:** Every category of custodial asset should have a control account. Regulators and auditors expect to read aggregate positions directly, not sum across facilities.

**Fix:** Add two omnibus accounts:
- **Collateral In-Liquidation Omnibus** (BTC, OBS, Debit-normal) — paired with Collateral In-Liquidation
- **Liquidated Collateral Omnibus** (BTC, OBS, Debit-normal) — paired with Liquidated Collateral

Then expand `RECEIVE_PROCEEDS_FROM_LIQUIDATION` from 4 to 6 entries:

```
RECEIVE_PROCEEDS_FROM_LIQUIDATION (6 entries):
  DR  Collateral In-Liquidation        BTC  ─┐ release from "in-liquidation"
  CR  Collateral In-Liq. Omnibus       BTC  ─┘
  DR  Liquidated Collateral Omnibus    BTC  ─┐ receive into "liquidated"
  CR  Liquidated Collateral            BTC  ─┘
  DR  Liquidation Proceeds Omnibus     USD  ─┐ record proceeds (unchanged)
  CR  Facility Proceeds               USD  ─┘
```

### Gap 3: RESERVE_FOR_LIQUIDATION is dead code

Defined in `core/credit/src/ledger/templates/reserve_for_liquidation.rs`. Never initialized in the credit ledger module, never called. Its apparent purpose — reserving outstanding loan amounts against expected liquidation proceeds — is not wired into any workflow.

**Fix:** Wire it in with a clear trigger (e.g., when liquidation is initiated) or remove it.

---

## Target State (after fixes)

BTC collateral exists in exactly one of three states. Each state has one omnibus whose balance equals the sum of its paired facility accounts.

| State | Omnibus | Facility account | Meaning |
|-------|---------|-----------------|---------|
| Held | Collateral Omnibus | Facility Collateral | Bank currently holds this BTC |
| In liquidation | Collateral In-Liq. Omnibus | Collateral In-Liquidation | BTC sent to market, awaiting proceeds |
| Liquidated | Liquidated Collateral Omnibus | Liquidated Collateral | BTC sold, proceeds received |

At any moment: `Held + In-Liquidation + Liquidated = total BTC ever deposited − total BTC withdrawn`.
