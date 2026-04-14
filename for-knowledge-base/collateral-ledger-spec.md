# Collateral Ledger: Fixing the Omnibus Accounting Gap

**Status:** DRAFT | **Date:** 2026-04-14 | **Author:** @vindard

---

## 1. Problem

During review of PR #4959 (collateral lot tracking), @Nsandomeno asked where the bank collateral omnibus balance gets offset during liquidation. The answer is: it doesn't. This is a bug.

When a borrower deposits BTC collateral, two ledger entries record the event: a debit to the bank-wide Collateral Omnibus and a credit to the facility's Collateral account. When collateral is returned, these entries reverse. The omnibus balance always equals the sum of all facility collateral balances — this is the fundamental invariant of a control account.

Liquidation breaks this invariant. When collateral is sent to liquidation, the current implementation moves the BTC between two facility-level accounts (from Facility Collateral to Collateral In-Liquidation) but never touches the omnibus. The Facility Collateral account goes to zero, yet the omnibus still carries the original debit. After liquidation, querying the Collateral Omnibus for "total BTC held by the bank" returns an overstated number that includes BTC the bank has already sold.

This matters because the omnibus is the single account an operator, auditor, or report reads to understand the bank's aggregate collateral position. If it lies, everything downstream — risk calculations, regulatory reports, reconciliation — starts from a wrong number.

## 2. Root Cause

The collateral ledger has four omnibus accounts today. Two of them (Collateral Omnibus for BTC held, Liquidation Proceeds Omnibus for USD received) correctly pair with their facility-level accounts. The other two facility-level account categories — Collateral In-Liquidation and Liquidated Collateral — have no omnibus at all. When BTC moves into these unpaired accounts, the Collateral Omnibus retains a balance it should have released, and no other omnibus picks it up.

The current templates:

| Template | Entries | Accounts touched |
|----------|---------|-----------------|
| `ADD_COLLATERAL` | 2 | DR Collateral Omnibus, CR Facility Collateral |
| `REMOVE_COLLATERAL` | 2 | DR Facility Collateral, CR Collateral Omnibus |
| `SEND_COLLATERAL_TO_LIQUIDATION` | 2 | DR Facility Collateral, CR Collateral In-Liquidation |
| `RECEIVE_PROCEEDS_FROM_LIQUIDATION` | 4 | DR/CR on In-Liquidation → Liquidated (BTC), DR/CR on Proceeds Omnibus → Facility Proceeds (USD) |

`ADD_COLLATERAL` and `REMOVE_COLLATERAL` correctly maintain the omnibus. `SEND_COLLATERAL_TO_LIQUIDATION` and the BTC leg of `RECEIVE_PROCEEDS_FROM_LIQUIDATION` do not.

## 3. Solution

Introduce two new omnibus accounts — one for each unpaired facility-level category — so that every collateral state has a controlling omnibus. Then expand the two liquidation templates to move BTC between omnibus accounts in lockstep with the facility-level transfers.

The principle is simple: BTC collateral exists in exactly one of three states (held, in-liquidation, liquidated), and each state has exactly one omnibus whose balance equals the sum of its paired facility accounts. At any moment, reading these three omnibus balances tells you how much BTC is in each state across all facilities, with no derived arithmetic.

We considered the alternative of redefining the existing Collateral Omnibus as a cumulative "total collateral ever received" tracker. This would require no code changes but would make the omnibus unable to answer "how much BTC does the bank currently hold" — the most common question asked of this account. In a margin lending system where liquidation is an operational reality, not an edge case, that tradeoff is unacceptable.

## 4. Target State

### Account catalog

**Omnibus accounts** (bank-wide, one account each, all Off-Balance-Sheet, Debit normal balance):

| Account | Currency | Meaning |
|---------|----------|---------|
| Collateral Omnibus | BTC | Total BTC collateral currently held, not in liquidation |
| Collateral In-Liquidation Omnibus *(new)* | BTC | Total BTC currently being liquidated |
| Liquidated Collateral Omnibus *(new)* | BTC | Total BTC that has been sold historically |
| Liquidation Proceeds Omnibus | USD | Total USD proceeds received from all liquidations |

**Facility-level accounts** (one per facility, all Off-Balance-Sheet except Payment Holding, Credit normal balance):

| Account | Currency | Paired omnibus |
|---------|----------|---------------|
| Facility Collateral | BTC | Collateral Omnibus |
| Collateral In-Liquidation | BTC | Collateral In-Liquidation Omnibus |
| Liquidated Collateral | BTC | Liquidated Collateral Omnibus |
| Proceeds From Liquidation | USD | Liquidation Proceeds Omnibus |
| Payment Holding | USD | — (Asset category) |
| Uncovered Outstanding | USD | — |

### Transaction templates

**Deposit and withdrawal** (unchanged):

```
ADD_COLLATERAL (2 entries):
  DR  Collateral Omnibus               BTC
  CR  Facility Collateral              BTC

REMOVE_COLLATERAL (2 entries):
  DR  Facility Collateral              BTC
  CR  Collateral Omnibus               BTC
```

**Send collateral to liquidation** (expanded from 2 to 4 entries):

```
SEND_COLLATERAL_TO_LIQUIDATION (4 entries):
  DR  Facility Collateral              BTC   ─┐ removes from "held" pool
  CR  Collateral Omnibus               BTC   ─┘
  DR  Collateral In-Liq. Omnibus       BTC   ─┐ adds to "in-liquidation" pool
  CR  Collateral In-Liquidation        BTC   ─┘
```

Double-entry balanced: 2 DR = 2 CR.

**Receive proceeds from liquidation** (expanded from 4 to 6 entries):

```
RECEIVE_PROCEEDS_FROM_LIQUIDATION (6 entries):
  DR  Collateral In-Liquidation        BTC   ─┐ removes from "in-liquidation" pool
  CR  Collateral In-Liq. Omnibus       BTC   ─┘
  DR  Liquidated Collateral Omnibus    BTC   ─┐ adds to "liquidated" pool
  CR  Liquidated Collateral            BTC   ─┘
  DR  Liquidation Proceeds Omnibus     USD   ─┐ records USD proceeds
  CR  Facility Proceeds               USD   ─┘
```

Double-entry balanced: 3 DR = 3 CR (BTC and USD sides balance independently).

### Worked example

A facility deposits 10 BTC, all of it is liquidated, and $300k in proceeds is received.

| Step | Coll. Omnibus | Fac. Coll. | In-Liq. Omnibus | In-Liq. | Liq'd Omnibus | Liq'd | Proceeds Omnibus | Fac. Proceeds |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| After ADD_COLLATERAL | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| After SEND_TO_LIQ | **0** | **0** | **10** | **10** | 0 | 0 | 0 | 0 |
| After RECEIVE_PROCEEDS | 0 | 0 | **0** | **0** | **10** | **10** | **$300k** | **$300k** |

At every step, each omnibus equals the sum of its paired facility accounts. The bank's aggregate BTC position is readable directly: held = 0, in liquidation = 0, liquidated = 10.

### Proceeds application

After `RECEIVE_PROCEEDS_FROM_LIQUIDATION`, USD proceeds flow through the collection module: Facility Proceeds From Liquidation (source) → Payment Holding (temporary) → applied against obligations → Uncovered Outstanding (reduced). This flow is unchanged by this proposal.

## 5. Current Gaps (main @ 39dbf11e7)

**Gap 1 — Missing omnibus accounts.** The In-Liquidation and Liquidated Collateral facility-level accounts have no controlling omnibus. Without these, no bank-wide aggregate view exists for BTC in those states, and the control-account invariant cannot hold.

Files to change: `core/credit/src/primitives/account_sets.rs` (add two omnibus specs), `core/credit/src/chart_of_accounts_integration/config.rs` (add parent code fields), `core/credit/collateral/src/ledger/mod.rs` (wire account IDs).

**Gap 2 — Liquidation templates don't touch omnibus accounts.** `SEND_COLLATERAL_TO_LIQUIDATION` has 2 entries instead of 4. `RECEIVE_PROCEEDS_FROM_LIQUIDATION` has 4 entries instead of 6. The Collateral Omnibus is never credited when BTC enters liquidation.

Files to change: `core/credit/collateral/src/ledger/templates/send_collateral_to_liquidation.rs` (add 2 entries + 2 params), `core/credit/collateral/src/ledger/templates/receive_proceeds_from_liquidation.rs` (add 2 entries + 2 params), plus callers that construct the template params.

**Gap 3 — RESERVE_FOR_LIQUIDATION is dead code.** The template is defined in `core/credit/src/ledger/templates/reserve_for_liquidation.rs` but never initialized or called from the credit ledger module. It should be wired in or removed.

## 6. Implementation Plan

**Phase 1 — New omnibus account sets.** Add `CreditCollateralInLiquidationOmnibus` and `CreditLiquidatedCollateralOmnibus` to the account set catalog in `account_sets.rs`. Add corresponding config fields and wire account creation in the collateral ledger module.

**Phase 2 — Update SEND_COLLATERAL_TO_LIQUIDATION.** Add `bank_collateral_account_id` and `collateral_in_liquidation_omnibus_account_id` as template params. Add the two new entries (CR Collateral Omnibus, DR In-Liquidation Omnibus). Update all callers.

**Phase 3 — Update RECEIVE_PROCEEDS_FROM_LIQUIDATION.** Add `collateral_in_liquidation_omnibus_account_id` and `liquidated_collateral_omnibus_account_id` as template params. Add the two new BTC-leg entries (CR In-Liquidation Omnibus, DR Liquidated Collateral Omnibus). Update all callers.

**Phase 4 — Finalize.** Run `make sqlx-prepare` and `make sdl`. Update the ledger docs. Resolve RESERVE_FOR_LIQUIDATION (Gap 3).

Not yet in production — no data migration needed. All changes apply cleanly on next `make reset-deps`.

## 7. FAQ

**Why not keep a single omnibus and redefine its meaning?** A single cumulative omnibus (tracking all collateral ever received, net of removals) would require no code changes. But its balance could not answer "how much BTC does the bank hold right now" without subtracting the liquidated amounts — a derived calculation that every consumer would need to implement independently. Three omnibus accounts make each question a single balance read.

**Why not credit the omnibus without a new debit-side account (3-entry transaction)?** Double-entry requires total debits to equal total credits within a transaction. Crediting the Collateral Omnibus without a corresponding debit somewhere would create an unbalanced entry. The In-Liquidation Omnibus is the natural debit-side counterpart.

**Does this change the USD proceeds flow?** No. The Liquidation Proceeds Omnibus and Facility Proceeds From Liquidation account already pair correctly. The only changes are on the BTC side.

**What about partial liquidations?** The templates already accept an amount parameter. A partial liquidation moves only the liquidated amount through the state transitions. The omnibus balances reflect the partial amounts correctly — some BTC stays in "held" while the rest moves to "in-liquidation."

**What is RESERVE_FOR_LIQUIDATION for?** It appears to be planned work for reserving an outstanding loan amount against expected liquidation proceeds. It is not called anywhere today. This proposal does not depend on it, but it should be resolved separately.
