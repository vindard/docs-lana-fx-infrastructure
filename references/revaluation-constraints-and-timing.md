# How the Spec Addresses Revaluation Constraints and Timing

The spec addresses both concerns — that revaluation may have different constraints and may happen at different times — through its **three-regime separation**, where each regime has its own constraints and its own timing.

## Different constraints by regime

| | Fiat FX | BTC (platform-owned) | BTC (collateral) |
|---|---|---|---|
| **Standard** | IAS 21 | ASU 2023-08 | Agent relationship |
| **What moves** | Local-currency equivalent of foreign-currency monetary balances | Fair value of intangible asset | Both sides (asset + obligation) move together |
| **P&L treatment** | Unrealized gain/loss (6100/6200), reversible | All changes → P&L (7100/7200), cumulative, no reversal | Zero P&L impact (net zero) |
| **Method** | Delta or full-reversal against historical transaction rate | Delta from last recorded carrying value | Both-sides template revaluation |
| **Rate type** | Closing rate (end-of-day capture) | Fair value (spot) | Closing rate for BTC |
| **Accounts touched** | Only fiat non-functional-currency monetary balances | Only platform-**owned** BTC (excludes collateral) | Only custodied BTC per-facility |

The collector jobs enforce these constraints structurally — the fiat collector filters `balance_currency != functional_currency`, the BTC fair value collector explicitly excludes collateral accounts, and the collateral collector only processes facility-level custodied BTC. Three separate job chains, three separate sets of CoA accounts, no possibility of commingling.

## Different timing by regime

| | Fiat FX | BTC (platform-owned) | BTC (collateral) |
|---|---|---|---|
| **Revaluation cadence** | Period-end (daily or monthly) | Continuous — daily, hourly, or on every price update | At minimum monthly, ideally daily |
| **Trigger** | `CoreTimeEvent::EndOfDay` | `CoreTimeEvent::EndOfDay` or `CorePriceEvent::PriceUpdated` | `CoreTimeEvent::EndOfDay` |
| **Rate staleness tolerance** | Transaction: 5 min; Reporting: 1 hour | Transaction: 60 sec; Reporting: 5 min | Uses closing rate (same as fiat cadence) |
| **LTV monitoring** | N/A | N/A | Higher frequency — event-driven on price updates or polling every N seconds |

The spec explicitly calls out that the industry-standard "daily EOD batch" assumption is too narrow. BTC fair value can be updated at any frequency because ASU 2023-08 adjustments are cumulative with no reversals — posting more frequently just means smaller deltas. Fiat FX revaluation is inherently period-end because of the reversal/delta accounting pattern tied to closing rates. Collateral revaluation for accounting purposes runs daily, but LTV monitoring (an operational concern, not an accounting entry) runs at much higher frequency to catch margin calls.

The key insight: timing isn't a configuration knob applied uniformly — it's a consequence of the accounting standard governing each regime.
