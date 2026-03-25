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

