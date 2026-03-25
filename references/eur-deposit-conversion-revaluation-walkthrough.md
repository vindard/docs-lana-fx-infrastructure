# EUR Deposit → Conversion → Revaluation → Withdrawal: Full Walkthrough

End-to-end scenario exercising Group A (dual-currency entries), Phase 3 (trading account conversion + realized G/L), and Phase 4 (period-end revaluation). Functional currency: USD.

## Scenario

1. Customer deposits 100 EUR (spot rate 1.10 USD/EUR)
2. Bank converts 50 EUR → USD (rate 1.15)
3. End of day: rate moves to 1.20, revaluation runs
4. Customer withdraws remaining 50 EUR (rate 1.20)

## All entries by step

```
STEP 1 — Deposit 100 EUR (rate 1.10)
  ① Dr  EUR Deposit        100 EUR
  ② Dr  EUR Deposit        110 USD
  ③ Cr  EUR Omnibus        100 EUR
  ④ Cr  EUR Omnibus        110 USD

STEP 2 — Convert 50 EUR → USD (rate 1.15)
  ⑤ Dr  Trading             50 EUR
  ⑥ Cr  EUR Deposit         50 EUR
  ⑦ Dr  USD Cash            57.50 USD
  ⑧ Cr  Trading             57.50 USD
  ⑨ Dr  Trading             55 USD        ← book value leg
  ⑩ Cr  EUR Deposit         55 USD
  ⑪ Dr  Trading              2.50 USD     ← realized G/L clearing
  ⑫ Cr  Realized FX Gain     2.50 USD

STEP 3 — Revaluation (rate → 1.20)
  ⑬ Dr  EUR Deposit          5 USD
  ⑭ Cr  Unrealized FX Gain   5 USD
  ⑮ Dr  Trading              5 USD
  ⑯ Cr  Unrealized FX Gain   5 USD

STEP 4 — Withdraw 50 EUR (rate 1.20)
  ⑰ Dr  EUR Omnibus         50 EUR
  ⑱ Dr  EUR Omnibus         60 USD
  ⑲ Cr  EUR Deposit         50 EUR
  ⑳ Cr  EUR Deposit         60 USD
```

## T-Accounts

```
                        EUR Deposit Account
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
     ①    100 EUR   deposit     │   50 EUR   → trading        ⑥
     ②    110 USD   deposit     │   55 USD   book val → trad  ⑩
     ⑬      5 USD   reval       │   50 EUR   withdrawal       ⑲
                                │   60 USD   withdrawal       ⑳
          ──────────────────────┼────────────────────
          EUR: 100 - 100 = 0    │  USD: 115 - 115 = 0
```

```
                        EUR Omnibus
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
     ⑰     50 EUR   withdrawal  │  100 EUR   deposit          ③
     ⑱     60 USD   withdrawal  │  110 USD   deposit          ④
          ──────────────────────┼────────────────────
          EUR: 50 - 100 = (50)  │  USD: 60 - 110 = (50)
```

```
                        Trading Account
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
     ⑤     50 EUR   ← deposit   │   57.50 USD  → USD Cash     ⑧
     ⑨     55 USD   book value  │
     ⑪      2.50 USD  G/L clear │
     ⑮      5 USD   reval       │
          ──────────────────────┼────────────────────
          EUR: 50               │  USD: 62.50 - 57.50 = 5
```

```
                        USD Cash
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
     ⑦     57.50 USD  proceeds  │
          ──────────────────────┼────────────────────
          USD: 57.50            │
```

```
                     Realized FX Gain (4200)
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
                                │    2.50 USD                 ⑫
          ──────────────────────┼────────────────────
          USD: (2.50)           │
```

```
                    Unrealized FX Gain (6100)
          ───────────────────────────────────────────
          Dr                    │  Cr
          ──────────────────────┼────────────────────
                                │    5 USD   deposit reval    ⑭
                                │    5 USD   trading reval    ⑯
          ──────────────────────┼────────────────────
          USD: (10)             │
```

## Trial balance

```
                          EUR         USD
                       ───────    ─────────
EUR Deposit               0           0
EUR Omnibus             (50)         (50)
Trading                  50           5
USD Cash                  —         57.50
Realized FX Gain          —         (2.50)
Unrealized FX Gain        —          (10)
                       ───────    ─────────
Total                     0           0       ✓
```

## Residual balance explanations

**EUR Deposit: 0 EUR, 0 USD** — Fully zeroed out. The customer deposited 100 EUR, then 50 EUR went to the trading account (conversion) and 50 EUR were withdrawn. On the USD side: 110 USD came in at deposit (100 EUR × 1.10), +5 USD from revaluation, minus 55 USD book value transferred to trading, minus 60 USD on withdrawal (50 EUR × 1.20). Net zero.

**EUR Omnibus: (50) EUR, (50) USD** — Represents the bank's net position with the outside world. 100 EUR came in on deposit but only 50 EUR went out on withdrawal. The remaining 50 EUR credit balance represents the EUR the bank received from the customer that were converted to USD — those EUR left the bank's internal books via the conversion but the omnibus still reflects the original inflow vs outflow with the external counterparty. The (50) USD balance arises from the withdrawal-rate USD equivalent (60) minus the deposit-rate equivalent (110): 60 − 110 = (50).

**Trading Account: 50 EUR, 5 USD** — The 50 EUR received from the conversion haven't left the trading account (no external settlement was modeled for the EUR side), representing the bank's open EUR position. The 5 USD is the unrealized gain on that position: the 50 EUR were acquired at a book value of 55 USD (50 × 1.10) but after revaluation at 1.20 they're worth 60 USD. The ledger confirms: 55 (book value) + 2.50 (G/L clearing) + 5 (reval) − 57.50 (cash proceeds) = 5 USD.

**USD Cash: 57.50 USD** — The actual USD proceeds from selling 50 EUR at the conversion rate of 1.15 (50 × 1.15 = 57.50). This is real cash the bank now holds.

**Realized FX Gain: (2.50) USD** — Profit locked in on the conversion. The 50 EUR had a book value of 55 USD (carried at the 1.10 deposit rate) but were sold for 57.50 USD (at 1.15). The 2.50 difference is realized gain. Credit balance because it is income.

**Unrealized FX Gain: (10) USD** — Two components: 5 USD from revaluing the EUR Deposit account (the remaining 50 EUR went from book value 55 USD at 1.10 to fair value 60 USD at 1.20), and 5 USD from revaluing the Trading Account (the 50 EUR position likewise went from 55 to 60 USD). Credit balance because it is unreported income that will either reverse or convert to realized gain when positions close.

**Total: 0 EUR, 0 USD** — The balanced totals confirm all entries are correct. The economic story: the bank started with nothing, received 100 EUR, converted half to 57.50 USD cash, still holds 50 EUR, and the favorable rate movement produced 2.50 realized + 10 unrealized = 12.50 total USD in gains, which exactly accounts for the difference between historical and current values across all positions.

## Templates used

| Step | Template | Module |
|---|---|---|
| 1 — Deposit | Deposit template (with Group A dual-currency entries) | Deposit layer |
| 2 — Conversion | `FIAT_FX_CONVERSION_VIA_TRADING` (expanded with book value leg) | Phase 3 |
| 2 — Realized G/L | `REALIZED_FX_GAIN_LOSS` | Phase 3 |
| 3 — Revaluation | Phase 4 revaluation template (not yet built) | Phase 4 |
| 4 — Withdrawal | Withdrawal template (with Group A dual-currency entries) | Deposit layer |

## Design observations

1. **Two book value sources.** Regular foreign-currency accounts (EUR Deposit) get their book value from the Group A ledger USD balance. The trading account gets its book value from the position accumulator — its ledger USD balance is 0 after realized G/L clearing, so the ledger balance cannot serve as book value for revaluation. The Phase 4 revaluation job must handle this asymmetry.

2. **Book value leg on conversions.** The conversion template needs a third leg (entries ⑨-⑩) to transfer the proportional USD book value from the source account to the trading account. This requires a new `source_book_value` parameter computed by the orchestrator from the source account's ledger USD balance before posting.

3. **Position accumulator survives Group A.** Group A eliminates the need for external book value tracking on all regular accounts, but the trading account still needs the position accumulator because its ledger USD balance gets zeroed by realized G/L clearing.

