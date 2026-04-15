# Collateral Ledger Accounts

**Status:** DRAFT | **Date:** 2026-04-15 | **Author:** @vindard

---

## Problem

The collateral ledger's omnibus accounts do not reflect the true aggregate position of BTC held by the bank. When collateral enters liquidation, facility-level accounts update correctly but the bank-wide Collateral Omnibus is never adjusted. It overstates the bank's held collateral by the amount of any BTC that has been sent to or completed liquidation. Two of the four facility-level account categories have no omnibus at all, meaning there is no single account to query for "total BTC in liquidation" or "total BTC historically sold."

---

## Gaps

### The control-account invariant

The control-account invariant is a foundational accounting principle: **the balance of a control account must equal the sum of the balances in its subsidiary ledger at all times.** This is not a design preference — it is how double-entry bookkeeping maintains integrity between summary and detail views.

In standard accounting practice, the control account (here: an omnibus) and the subsidiary accounts (here: per-facility accounts) are always posted in the same transaction. When an asset moves between categories in the subsidiary ledger, both the source and destination control accounts must be updated in lockstep. If they are not, the control account lies about the aggregate position.

**How other systems enforce this:**

- **Fundamental accounting principle.** Per standard financial accounting curricula: "The ending balance in the control account must equal the sum of all subsidiary account balances." A mismatch indicates an error requiring investigation. ([Lumen Learning — Subsidiary Ledgers and Control Accounts](https://courses.lumenlearning.com/suny-finaccounting/chapter/subsidiary-ledgers-and-control-accounts/))

- **SEC Rule 15c3-3 (Customer Protection Rule).** Broker-dealers holding customer securities must maintain daily reconciliation between aggregate (omnibus) and individual customer positions. A "verifiable, daily detailed audit trail" must reconcile the excess/deficit from the prior day's stock record. The rule requires firms to "at all times maintain in segregation an amount equal to the sum" of customer balances. ([FINRA — SEA Rule 15c3-3](https://www.finra.org/rules-guidance/guidance/interpretations-financial-operational-rules/sea-rule-15c3-3-and-related-interpretations))

- **CFTC Rule 1.20 (Segregated Funds).** Futures commission merchants must "separately account for all futures customer funds" and submit daily segregated funds computations. The aggregate must equal the sum of all individual customer net liquidating equities. ([17 CFR § 1.20](https://www.law.cornell.edu/cfr/text/17/1.20))

- **US GAAP ASC 860-30 (Collateral).** When a secured party holds noncash collateral (our case: BTC), the standard requires the secured party to recognize its obligation to return the collateral and, if the collateral is sold, to "recognize the proceeds from the sale and its obligation to return the collateral." The collateral must be tracked through its lifecycle — held, sold, or re-pledged — not frozen at receipt. ([Deloitte DART — ASC 860-30, Collateral in a Secured Borrowing](https://dart.deloitte.com/USDART/home/codification/broad-transactions/asc860-10/roadmap-transfers-financial-assets/chapter-5-secured-borrowing-accounting/5-3-collateral-in-a-secured))

- **Digital asset custody (omnibus model).** Fidelity Digital Assets describes the standard omnibus custody model: the custodian "establishes client by client segregation at the books and records level" while assets are pooled operationally. "Externally audited financial control environments and client statements provide additional assurance that funds are secure and data accurate." The books-and-records layer must reflect the true state of each asset at all times. ([Fidelity Digital Assets — The Omnibus Model for Custody](https://www.fidelitydigitalassets.com/research-and-insights/omnibus-model-custody))

- **Thought Machine Vault Core.** A modern core banking platform used by institutions like Lloyds and JPMorgan. Every transaction "automatically creates balanced debit and credit entries across accounts, ensuring accounting integrity at all times" via an immutable, append-only ledger. The system "can slice and dice balances into any structure while giving banks unrestricted visibility." The principle: every state of every asset is queryable at every level of aggregation. ([Thought Machine — Vault Core](https://www.thoughtmachine.net/vault-core))

**Our current violation:** When `SEND_COLLATERAL_TO_LIQUIDATION` moves BTC from Facility Collateral to Collateral In-Liquidation, only the facility-level accounts are posted. The Collateral Omnibus retains a debit it should have released. No other omnibus receives the corresponding debit. The control-account invariant is broken: the omnibus says the bank holds X BTC, but the sum of facility collateral accounts says it holds less.

---

### Gap 1: Collateral Omnibus overstated after liquidation

BTC moves from Facility Collateral → Collateral In-Liquidation at the facility level, but the Collateral Omnibus is never credited. Its balance includes BTC the bank no longer holds as active collateral.

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

Defined but never initialized or called. Its apparent purpose — reserving outstanding loan amounts against expected liquidation proceeds — is not wired into any workflow.

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

---

## Appendix: Account Reference

All collateral accounts are Off-Balance-Sheet. The bank holds BTC as custodian (agent), not owner — collateral never appears on the balance sheet.

### Omnibus Accounts

Bank-wide. One instance each. Debit-normal. Their balance should equal the sum of their paired facility accounts (control-account invariant).

#### Collateral Omnibus (BTC)

| | |
|---|---|
| **Intended purpose** | Total BTC collateral the bank currently holds on behalf of all borrowers, excluding any collateral in or past liquidation. |
| **Current balance reflects** | Total BTC ever deposited minus total BTC withdrawn. Overstated — never reduced when collateral enters liquidation. |
| **Increased by** | `ADD_COLLATERAL` (DR this, CR Facility Collateral) |
| **Decreased by** | `REMOVE_COLLATERAL` (CR this, DR Facility Collateral) |
| **Contra accounts** | Facility Collateral (per-facility) |

#### Liquidation Proceeds Omnibus (USD)

| | |
|---|---|
| **Intended purpose** | Total USD proceeds received from all liquidations across all facilities. |
| **Current balance reflects** | Matches intent. Correctly maintained. |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (DR this, CR Facility Proceeds) |
| **Decreased by** | Nothing currently. |
| **Contra accounts** | Facility Proceeds From Liquidation (per-facility) |

### Facility-Level Accounts

One instance per facility. Credit-normal.

#### Facility Collateral (BTC)

| | |
|---|---|
| **Intended purpose** | BTC collateral currently held for this facility. |
| **Current balance reflects** | Correct when no liquidation has occurred. After liquidation, goes to zero as expected — but its paired omnibus does not adjust (see Gap 1). |
| **Increased by** | `ADD_COLLATERAL` (CR this, DR Collateral Omnibus) |
| **Decreased by** | `REMOVE_COLLATERAL` (DR this, CR Collateral Omnibus), `SEND_COLLATERAL_TO_LIQUIDATION` (DR this, CR Collateral In-Liquidation) |
| **Contra accounts** | Collateral Omnibus (deposit/withdrawal), Collateral In-Liquidation (liquidation) |

#### Collateral In-Liquidation (BTC)

| | |
|---|---|
| **Intended purpose** | BTC from this facility currently being liquidated (sold but proceeds not yet received). |
| **Current balance reflects** | Correct at facility level. No omnibus tracks the aggregate (see Gap 2). |
| **Increased by** | `SEND_COLLATERAL_TO_LIQUIDATION` (CR this, DR Facility Collateral) |
| **Decreased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (DR this, CR Liquidated Collateral) |
| **Contra accounts** | Facility Collateral (entry), Liquidated Collateral (exit) |

#### Liquidated Collateral (BTC)

| | |
|---|---|
| **Intended purpose** | BTC from this facility that has been sold. Historical record — balance only grows. |
| **Current balance reflects** | Correct at facility level. No omnibus tracks the aggregate (see Gap 2). |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (CR this, DR Collateral In-Liquidation) |
| **Decreased by** | Nothing. |
| **Contra accounts** | Collateral In-Liquidation (entry) |

#### Facility Proceeds From Liquidation (USD)

| | |
|---|---|
| **Intended purpose** | USD proceeds received from liquidating this facility's collateral. |
| **Current balance reflects** | Matches intent. Correctly maintained. |
| **Increased by** | `RECEIVE_PROCEEDS_FROM_LIQUIDATION` (CR this, DR Liquidation Proceeds Omnibus) |
| **Decreased by** | Collection flow (proceeds applied against obligations via Payment Holding). |
| **Contra accounts** | Liquidation Proceeds Omnibus (entry), Payment Holding (collection) |

### Current Templates

| Template | Entries | DR | CR | Currency |
|----------|:---:|---|---|:---:|
| `ADD_COLLATERAL` | 2 | Collateral Omnibus | Facility Collateral | BTC |
| `REMOVE_COLLATERAL` | 2 | Facility Collateral | Collateral Omnibus | BTC |
| `SEND_COLLATERAL_TO_LIQUIDATION` | 2 | Facility Collateral | Collateral In-Liquidation | BTC |
| `RECEIVE_PROCEEDS_FROM_LIQUIDATION` | 4 | Collateral In-Liquidation | Liquidated Collateral | BTC |
| | | Liquidation Proceeds Omnibus | Facility Proceeds | USD |
| `RESERVE_FOR_LIQUIDATION` | 2 | Liquidation Omnibus | Facility Liquidation | USD |

`RESERVE_FOR_LIQUIDATION` is defined but never initialized or called — dead code.
