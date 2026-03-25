# EUR Deposit → Conversion → Revaluation → Withdrawal → Settlement: Full Walkthrough

End-to-end scenario exercising Group A (dual-currency entries), Phase 3 (trading account conversion + realized G/L), and Phase 4 (period-end revaluation with delta method across multiple periods). Functional currency: USD.

## Scenario

1. Customer deposits 100 EUR (spot rate 1.10 USD/EUR)
2. Bank converts 50 EUR → USD (rate 1.15)
3. End of period 1: rate moves to 1.20, revaluation runs
4. Customer withdraws 30 EUR
5. End of period 2: rate moves to 1.05, revaluation runs
6. Customer withdraws remaining 20 EUR
7. Bank settles conversion (delivers 50 EUR to FX counterparty)

## Entries and progressive trial balances

```
STEP 1 — Deposit 100 EUR (rate 1.10)
  ① Dr  EUR Deposit        100 EUR
  ② Dr  EUR Deposit        110 USD
  ③ Cr  EUR Omnibus        100 EUR
  ④ Cr  EUR Omnibus        110 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit      100                110
EUR Omnibus            Credit              100               110
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100       110      110  ✓

  EUR Deposit (Dr 100 EUR, Dr 110 USD):
    The bank's record of the customer's claim. 100 EUR deposited,
    booked at spot 1.10 = 110 USD.

  EUR Omnibus (Cr 100 EUR, Cr 110 USD):
    100 EUR received at the correspondent bank. Mirror of the deposit.
    Credit-normal because it is a liability — EUR held on behalf of
    the customer.


STEP 2 — Convert 50 EUR → USD (rate 1.15)
  ⑤ Dr  Trading             50 EUR
  ⑥ Cr  EUR Deposit         50 EUR
  ⑦ Dr  Trading             55 USD        ← book value leg
  ⑧ Cr  EUR Deposit         55 USD
  ⑨ Dr  USD Cash            57.50 USD
  ⑩ Cr  Trading             57.50 USD
  ⑪ Dr  Trading              2.50 USD     ← realized G/L clearing
  ⑫ Cr  Realized FX Gain     2.50 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 55
EUR Omnibus            Credit              100               110
Trading                Debit       50                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     112.50   112.50  ✓

  EUR Deposit (Dr 50 EUR, Dr 55 USD):
    Customer's remaining balance after conversion. 50 EUR at original
    book rate 1.10 = 55 USD.

  EUR Omnibus (Cr 100 EUR, Cr 110 USD):
    Unchanged. The EUR haven't physically left the correspondent bank
    yet — settlement is pending. Still holds all 100 EUR from the
    deposit.

  Trading (Dr 50 EUR, Dr 0 USD):
    Holds the 50 EUR acquired from the customer's deposit. USD is zero
    because book value in (55), sale proceeds out (57.50), and G/L
    clearing (2.50) net out: 55 − 57.50 + 2.50 = 0. The Selinger
    accumulator tracks the true book cost (55 USD) separately.

  USD Cash (Dr 57.50):
    Proceeds from selling 50 EUR at 1.15 on the FX market.

  Realized FX Gain (Cr 2.50):
    Locked-in profit from the conversion spread. Book cost 55 USD
    (50 EUR × 1.10), sold for 57.50 USD (50 EUR × 1.15).
    Difference = 2.50.


STEP 3 — Revaluation, period 1 (rate → 1.20)

  EUR Deposit (debit-normal, asset): 50 EUR, book 55, fair 60
  ⑬ Dr  EUR Deposit          5 USD
  ⑭ Cr  Unrealized FX Gain   5 USD

  EUR Omnibus (credit-normal, liability): 100 EUR, book 110, fair 120
  ⑮ Dr  Unrealized FX Gain  10 USD
  ⑯ Cr  EUR Omnibus         10 USD

  Trading (debit-normal, asset): 50 EUR, book 55 (accumulator), fair 60
  ⑰ Dr  Trading              5 USD
  ⑱ Cr  Unrealized FX Gain   5 USD

  Net unrealized: +5 − 10 + 5 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 60
EUR Omnibus            Credit              100               120
Trading                Debit       50                  5
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     122.50   122.50  ✓

  EUR Deposit (Dr 50 EUR, Dr 60 USD):
    Customer's 50 EUR marked to market. Book value 55 (at 1.10)
    adjusted to fair value 60 (at 1.20). The +5 is a temporary
    period-end adjustment.

  EUR Omnibus (Cr 100 EUR, Cr 120 USD):
    The 100 EUR liability revalued from 110 to 120. EUR appreciated,
    so the bank's obligation grew by 10 USD.

  Trading (Dr 50 EUR, Dr 5 USD):
    The 50 EUR position revalued from book 55 to fair 60. The Dr 5 is
    the balance-sheet side of the mark-to-market adjustment.

  USD Cash (Dr 57.50):
    Unchanged. Real cash, not subject to revaluation.

  Realized FX Gain (Cr 2.50):
    Unchanged. Revaluation does not affect realized gains.

  Unrealized FX Gain (0):
    Net zero. Asset-side gains (Deposit +5, Trading +5 = +10) exactly
    offset liability growth (Omnibus +10). The bank has no net EUR
    exposure — Deposit Dr 50 + Trading Dr 50 − Omnibus Cr 100 = 0
    net EUR — so net unrealized must be zero.


STEP 4 — Withdraw 30 EUR (rate 1.20)

  Unwind proportional deposit revaluation (30/50 × 5 = 3):
  ⑲ Dr  Unrealized FX Gain   3 USD
  ⑳ Cr  EUR Deposit          3 USD

  Withdrawal at book value (30 × 1.10 = 33):
  ㉑ Dr  EUR Omnibus         30 EUR
  ㉒ Dr  EUR Omnibus         33 USD
  ㉓ Cr  EUR Deposit         30 EUR
  ㉔ Cr  EUR Deposit         33 USD

  Unwind proportional omnibus revaluation (30/100 × 10 = 3):
  ㉕ Dr  EUR Omnibus          3 USD
  ㉖ Cr  Unrealized FX Gain   3 USD

  Net unrealized from step 4: −3 + 3 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 24
EUR Omnibus            Credit                70               84
Trading                Debit       50                  5
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     86.50    86.50  ✓

  Verify: Deposit 20 EUR = 22 book + 2 reval = 24  ✓
          Omnibus 70 EUR = 77 book + 7 reval = 84  ✓

  EUR Deposit (Dr 20 EUR, Dr 24 USD):
    20 EUR remaining. Book value 22 (20 × 1.10) plus residual
    revaluation 2 (proportional: 20/50 × 5). The reval for the
    withdrawn 30 EUR was unwound — withdrawal is not a realization
    event.

  EUR Omnibus (Cr 70 EUR, Cr 84 USD):
    70 EUR remaining at correspondent (100 deposited − 30 withdrawn).
    Book value 77 (70 × 1.10) plus residual revaluation 7
    (proportional: 70/100 × 10). The reval on the withdrawn portion
    was unwound symmetrically with the deposit unwind.

  Trading (Dr 50 EUR, Dr 5 USD):
    Unchanged. Withdrawals do not affect the trading position.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.50):
    Unchanged. Withdrawal generates no realized gain.

  Unrealized FX Gain (0):
    Still zero. The deposit unwind (−3) and omnibus unwind (+3)
    cancel. Net EUR exposure unchanged (Deposit 20 + Trading 50 −
    Omnibus 70 = 0), so net unrealized remains zero.


STEP 5 — Revaluation, period 2 (rate → 1.05)

  Delta method: adjustment = (balance × new_rate) − current_USD_balance.
  Each account's USD balance already includes period 1 reval; the delta
  method posts only the incremental change from the previous state.

  EUR Deposit (debit-normal, asset): 20 EUR, current 24, fair 21
  ㉗ Dr  Unrealized FX Gain   3 USD
  ㉘ Cr  EUR Deposit          3 USD

  EUR Omnibus (credit-normal, liability): 70 EUR, current 84, fair 73.50
  Liability decreased by 10.50 (EUR depreciated → bank owes less):
  ㉙ Dr  EUR Omnibus         10.50 USD
  ㉚ Cr  Unrealized FX Gain  10.50 USD

  Trading (debit-normal, asset): 50 EUR, delta from prev closing rate
  50 × (1.05 − 1.20) = −7.50:
  ㉛ Dr  Unrealized FX Gain   7.50 USD
  ㉜ Cr  Trading              7.50 USD

  Net unrealized from step 5: −3 + 10.50 − 7.50 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 21
EUR Omnibus            Credit                70               73.50
Trading                Debit       50                          2.50
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     78.50    78.50  ✓

  Verify: Deposit 20 EUR = 22 book − 1 reval = 21  ✓
          Omnibus 70 EUR = 77 book − 3.50 reval = 73.50  ✓
          Trading 50 EUR: accumulator 55, reval −2.50, ledger −2.50  ✓

  EUR Deposit (Dr 20 EUR, Dr 21 USD):
    20 EUR marked to market at new closing rate. Book value 22 (at
    1.10), previous fair value 24 (at 1.20), new fair value 21 (at
    1.05). Delta method posts only the incremental change: 21 − 24 =
    −3. The EUR has now depreciated below the original booking rate.

  EUR Omnibus (Cr 70 EUR, Cr 73.50 USD):
    70 EUR liability revalued from 84 to 73.50. EUR depreciated, so
    the bank's obligation decreased by 10.50 USD. This is a gain for
    the bank — the inverse of period 1's loss.

  Trading (Dr 50 EUR, Cr 2.50 USD):
    50 EUR position revalued from fair 60 (at 1.20) to 52.50 (at
    1.05). Delta = −7.50. The credit USD balance means the position's
    fair value (52.50) is below book cost (55). The Selinger
    accumulator still reads 55; the ledger reflects 0 (post-G/L
    clearing) + 5 (period 1) − 7.50 (period 2 delta) = −2.50.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.50):
    Unchanged.

  Unrealized FX Gain (0):
    Still zero. Period 1 gains (+10 on assets, −10 on liability)
    exactly reversed by period 2 losses (−10.50 on assets, +10.50 on
    liability). The invariant holds: net EUR exposure = 0 → net
    unrealized = 0, regardless of rate direction.


STEP 6 — Withdraw remaining 20 EUR (rate 1.05)

  Unwind remaining deposit revaluation (reval = −1, i.e., 1 below book):
  ㉝ Dr  EUR Deposit          1 USD
  ㉞ Cr  Unrealized FX Gain   1 USD

  Withdrawal at book value (20 × 1.10 = 22):
  ㉟ Dr  EUR Omnibus         20 EUR
  ㊱ Dr  EUR Omnibus         22 USD
  ㊲ Cr  EUR Deposit         20 EUR
  ㊳ Cr  EUR Deposit         22 USD

  Unwind proportional omnibus revaluation (20/70 × (−3.50) = −1):
  ㊴ Dr  Unrealized FX Gain   1 USD
  ㊵ Cr  EUR Omnibus          1 USD

  Net unrealized from step 6: +1 − 1 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit                50               52.50
Trading                Debit       50                          2.50
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             50       50     57.50    57.50  ✓

  Verify: Omnibus 50 EUR = 55 book − 2.50 reval = 52.50  ✓
          (remaining reval: −3.50 + 1 unwound = −2.50)
          Trading unchanged: accumulator 55, reval −2.50  ✓

  EUR Deposit (0 EUR, 0 USD):
    Fully closed. All EUR withdrawn, all revaluation unwound.

  EUR Omnibus (Cr 50 EUR, Cr 52.50 USD):
    50 EUR remain at the correspondent. These are the EUR from the
    conversion that haven't been physically delivered yet. Book value
    55 (50 × 1.10) minus residual revaluation 2.50 (the remaining
    portion of the period 2 adverse adjustment). Fair value at 1.05 =
    52.50 confirms consistency.

  Trading (Dr 50 EUR, Cr 2.50 USD):
    Unchanged. Still holds the unsettled conversion position. The
    Dr 50 EUR mirrors the Omnibus Cr 50 EUR — these are two views of
    the same 50 EUR awaiting delivery.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.50):
    Unchanged.

  Unrealized FX Gain (0):
    Still zero. Net EUR exposure: Trading 50 − Omnibus 50 = 0. The
    Cr 2.50 on Trading is exactly offset by the Cr 2.50 reval
    reduction on Omnibus (52.50 vs book 55).


STEP 7 — Settle conversion (deliver 50 EUR to FX counterparty)

  EUR delivery:
  ㊶ Dr  EUR Omnibus         50 EUR
  ㊷ Cr  Trading             50 EUR

  Reverse Trading revaluation (position closed — sale was at 1.15,
  not 1.05, so the mark-to-market unwinds):
  ㊸ Dr  Trading              2.50 USD
  ㊹ Cr  Unrealized FX Gain   2.50 USD

  Unwind remaining omnibus revaluation (50/50 × (−2.50) = −2.50):
  ㊺ Dr  Unrealized FX Gain   2.50 USD
  ㊻ Cr  EUR Omnibus          2.50 USD

  Net unrealized from step 7: +2.50 − 2.50 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit        0                 55
Trading                Debit        0                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                              0        0     57.50    57.50  ✓

  EUR Deposit (0 EUR, 0 USD):
    Already closed in step 6.

  EUR Omnibus (0 EUR, Cr 55 USD):
    All EUR delivered (100 deposited − 30 withdrawn − 20 withdrawn −
    50 settled = 0). The Cr 55 USD is the orphaned book value: the
    customer gave up 50 EUR worth 55 USD (at 1.10) in the conversion
    and should have received USD in return. This residual is the
    customer's unmodeled USD entitlement — the scenario does not
    include a Customer USD Deposit account.

  Trading (0 EUR, 0 USD):
    Fully closed. EUR delivered to counterparty, mark-to-market
    reversed. The bank's gain was locked in at the conversion rate
    (1.15), not the revaluation rate. The reval was a temporary
    adjustment that unwound on settlement — whether the rate was
    above book (period 1: 1.20) or below (period 2: 1.05).

  USD Cash (Dr 57.50):
    Unchanged throughout. The 57.50 USD from the FX sale is the only
    real cash the bank holds.

  Realized FX Gain (Cr 2.50):
    Unchanged. Total realized = 2.50 (sold 50 EUR at 1.15, book cost
    at 1.10). Neither revaluation period affected the realized gain —
    the sale price was already locked in.

  Unrealized FX Gain (0):
    Zero throughout every step. The bank never had net EUR exposure,
    so unrealized gain was always zero.

  USD Cash (Dr 57.50) = Omnibus residual (Cr 55) + Realized (Cr 2.50):
    The bank holds 57.50 USD. Of that, 55 is the customer's converted
    principal (book value of 50 EUR at 1.10) and 2.50 is the bank's
    profit (conversion spread).
```

## Design observations

1. **Omnibus must be revalued.** The Omnibus is a credit-normal EUR liability. EUR appreciation increases it (unrealized loss for the bank); EUR depreciation decreases it (unrealized gain). Without Omnibus revaluation, the system incorrectly reports non-zero unrealized gains even when net EUR exposure is zero.

2. **Withdrawal unwinds revaluation, does not realize it.** A withdrawal returns EUR to the customer — it is not a market transaction. The proportional revaluation on both the Deposit (asset) and Omnibus (liability) is reversed. The two unwinds always cancel, keeping net unrealized at zero. This follows from the Selinger model: realization only occurs through the Trading Account (conversions), never through withdrawals.

3. **Net EUR exposure determines net unrealized.** At every step, Deposit Dr + Trading Dr − Omnibus Cr = 0 net EUR. Therefore net unrealized is always zero. This is the fundamental invariant: unrealized FX gain/loss reflects open currency exposure, and this scenario has none (every EUR asset is backed by a EUR liability).

4. **Settlement reverses mark-to-market.** When the Trading position closes via delivery, the revaluation is reversed — not reclassified to realized. The bank sold EUR at 1.15; the subsequent rate movements (1.20 then 1.05) are irrelevant to the bank's gain. The only realized gain is the conversion spread (2.50).

5. **Omnibus USD residual reveals unmodeled account.** After settlement, the Omnibus retains Cr 55 USD with no EUR backing. This is the customer's USD entitlement from the conversion — the scenario omits the Customer USD Deposit account. In a complete model, Step 2 would include `Cr Customer USD Deposit 57.50 USD` and the Omnibus residual (55) plus Realized Gain (2.50) would exactly fund it (57.50).

6. **Two book value sources.** Regular foreign-currency accounts (EUR Deposit, EUR Omnibus) get their book value from the Group A ledger USD balance. The trading account gets its book value from the position accumulator — its ledger USD balance is 0 after realized G/L clearing, so the ledger balance cannot serve as book value for revaluation. The SPEC's delta method formula (`foreign_balance × closing_rate − functional_currency_balance`) works for regular accounts but must be adapted for Trading: the revaluation job uses the accumulator as the base instead of the ledger balance.

7. **Book value leg on conversions.** The conversion template needs a third leg (entries ⑦-⑧) to transfer the proportional USD book value from the source account to the trading account. This requires a `source_book_value` parameter computed by the orchestrator from the source account's ledger USD balance before posting.

8. **Position accumulator survives Group A.** Group A eliminates the need for external book value tracking on all regular accounts, but the trading account still needs the position accumulator because its ledger USD balance gets zeroed by realized G/L clearing.

9. **Delta method across periods.** The second revaluation (Step 5) demonstrates the SPEC's recommended delta approach: each period computes `new_value − current_book_value` where current_book_value includes all prior revaluation adjustments. Only the incremental difference is posted; no reversals are needed. Running revaluation twice at the same rate produces a zero adjustment on the second run (idempotent).

10. **Adverse rate movement inverts asset/liability reval directions.** When EUR depreciates below the original booking rate (1.05 < 1.10), asset revaluations produce losses (Deposit −3, Trading −7.50) and liability revaluations produce gains (Omnibus +10.50) — the inverse of period 1. The net remains zero because net EUR exposure hasn't changed. The Trading account's USD balance goes negative (credit on a debit-normal account), reflecting a position fair value (52.50) below book cost (55).

11. **Path independence of final state.** Despite two revaluation periods at different rates (1.20 and 1.05), the final trial balance is identical to what it would be with no revaluation, or with any other intermediate rates. Revaluation entries are temporary mark-to-market adjustments that fully unwind on settlement or withdrawal. The final state depends only on the original booking rate (1.10) and the conversion rate (1.15).

12. **Single vs split Unrealized accounts.** The SPEC specifies separate Unrealized FX Gain (6100) and Unrealized FX Loss (6200) accounts. This walkthrough uses a single account for clarity, since the net is always zero in this scenario. In production, splitting by direction enables separate reporting of unrealized gains and losses as required by IAS 21 financial statement presentation.

## Templates used

| Step | Template | Module |
|---|---|---|
| 1 — Deposit | Deposit template (with Group A dual-currency entries) | Deposit layer |
| 2 — Conversion | `FIAT_FX_CONVERSION_VIA_TRADING` (with book value leg) | Phase 3 |
| 2 — Realized G/L | `REALIZED_FX_GAIN_LOSS` | Phase 3 |
| 3, 5 — Revaluation | Revaluation template (Deposit + Omnibus + Trading, delta method) | Phase 4 |
| 4, 6 — Withdrawal | Withdrawal template (with reval unwind on both Deposit and Omnibus) | Deposit layer |
| 7 — Settlement | Settlement template (EUR delivery + reval reversal) | Phase 3 |
