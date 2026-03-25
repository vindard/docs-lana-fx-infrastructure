# EUR Deposit → Conversion → Revaluation → Withdrawal → Settlement: Full Walkthrough

End-to-end scenario exercising Group A (dual-currency entries), Phase 3 (trading account conversion + realized G/L), and Phase 4 (period-end revaluation with delta method across multiple periods). Functional currency: USD.

## Scenario

1. Customer deposits 60 EUR (spot rate 1.10 USD/EUR)
2. Customer deposits 40 EUR (spot rate 1.12 USD/EUR)
3. Bank converts 50 EUR → USD (rate 1.15)
4. End of period 1: rate moves to 1.20, revaluation runs
5. Customer withdraws 30 EUR (spot rate has moved to 1.22)
6. End of period 2: rate moves to 1.05, revaluation runs
7. Customer withdraws remaining 20 EUR (spot rate has moved to 1.02)
8. Bank settles conversion (delivers 50 EUR to FX counterparty)

## Entries and progressive trial balances

```
STEP 1 — Deposit 60 EUR (rate 1.10)
  ① Dr  EUR Deposit        60 EUR
  ② Dr  EUR Deposit        66 USD
  ③ Cr  EUR Omnibus        60 EUR
  ④ Cr  EUR Omnibus        66 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       60                 66
EUR Omnibus            Credit               60                66
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             60       60        66       66  ✓

  EUR Deposit (Dr 60 EUR, Dr 66 USD):
    The bank's record of the customer's claim. 60 EUR deposited,
    booked at spot 1.10 = 66 USD.

  EUR Omnibus (Cr 60 EUR, Cr 66 USD):
    60 EUR received at the correspondent bank. Mirror of the deposit.
    Credit-normal because it is a liability — EUR held on behalf of
    the customer.


STEP 2 — Deposit 40 EUR (rate 1.12)
  ⑤ Dr  EUR Deposit        40 EUR
  ⑥ Dr  EUR Deposit        44.80 USD
  ⑦ Cr  EUR Omnibus        40 EUR
  ⑧ Cr  EUR Omnibus        44.80 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit      100                110.80
EUR Omnibus            Credit              100               110.80
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     110.80   110.80  ✓

  EUR Deposit (Dr 100 EUR, Dr 110.80 USD):
    Customer's total claim after both deposits. 60 EUR at 1.10 (66 USD)
    plus 40 EUR at 1.12 (44.80 USD). The blended weighted-average book
    rate is 110.80 / 100 = 1.108 USD/EUR.

  EUR Omnibus (Cr 100 EUR, Cr 110.80 USD):
    100 EUR received at the correspondent bank across two deposits.
    The USD balance reflects the blended book value of all EUR held.


STEP 3 — Convert 50 EUR → USD (rate 1.15)

  Book value of 50 EUR at blended rate: 50 × 1.108 = 55.40

  ⑨ Dr  Trading             50 EUR
  ⑩ Cr  EUR Deposit         50 EUR
  ⑪ Dr  Trading             55.40 USD       ← book value leg
  ⑫ Cr  EUR Deposit         55.40 USD
  ⑬ Dr  USD Cash            57.50 USD
  ⑭ Cr  Trading             57.50 USD
  ⑮ Dr  Trading              2.10 USD       ← realized G/L clearing
  ⑯ Cr  Realized FX Gain     2.10 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 55.40
EUR Omnibus            Credit              100               110.80
Trading                Debit       50                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     112.90   112.90  ✓

  EUR Deposit (Dr 50 EUR, Dr 55.40 USD):
    Customer's remaining balance after conversion. 50 EUR at blended
    book rate 1.108 = 55.40 USD.

  EUR Omnibus (Cr 100 EUR, Cr 110.80 USD):
    Unchanged. The EUR haven't physically left the correspondent bank
    yet — settlement is pending. Still holds all 100 EUR from the
    deposits.

  Trading (Dr 50 EUR, Dr 0 USD):
    Holds the 50 EUR acquired from the customer's deposit. USD is zero
    because book value in (55.40), sale proceeds out (57.50), and G/L
    clearing (2.10) net out: 55.40 − 57.50 + 2.10 = 0. The Selinger
    accumulator tracks the true book cost (55.40 USD) separately.

  USD Cash (Dr 57.50):
    Proceeds from selling 50 EUR at 1.15 on the FX market.

  Realized FX Gain (Cr 2.10):
    Locked-in profit from the conversion spread. Book cost 55.40 USD
    (50 EUR × 1.108), sold for 57.50 USD (50 EUR × 1.15).
    Difference = 2.10.


STEP 4 — Revaluation, period 1 (rate → 1.20)

  EUR Deposit (debit-normal, asset): 50 EUR, book 55.40, fair 60
  ⑰ Dr  EUR Deposit          4.60 USD
  ⑱ Cr  Unrealized FX Gain   4.60 USD

  EUR Omnibus (credit-normal, liability): 100 EUR, book 110.80, fair 120
  ⑲ Dr  Unrealized FX Gain   9.20 USD
  ⑳ Cr  EUR Omnibus          9.20 USD

  Trading (debit-normal, asset): 50 EUR, book 55.40 (accumulator), fair 60
  ㉑ Dr  Trading              4.60 USD
  ㉒ Cr  Unrealized FX Gain   4.60 USD

  Net unrealized: +4.60 − 9.20 + 4.60 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 60
EUR Omnibus            Credit              100               120
Trading                Debit       50                  4.60
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     122.10   122.10  ✓

  EUR Deposit (Dr 50 EUR, Dr 60 USD):
    Customer's 50 EUR marked to market. Book value 55.40 (at 1.108)
    adjusted to fair value 60 (at 1.20). The +4.60 is a temporary
    period-end adjustment.

  EUR Omnibus (Cr 100 EUR, Cr 120 USD):
    The 100 EUR liability revalued from 110.80 to 120. EUR appreciated,
    so the bank's obligation grew by 9.20 USD.

  Trading (Dr 50 EUR, Dr 4.60 USD):
    The 50 EUR position revalued from book 55.40 to fair 60. The Dr 4.60
    is the balance-sheet side of the mark-to-market adjustment.

  USD Cash (Dr 57.50):
    Unchanged. Real cash, not subject to revaluation.

  Realized FX Gain (Cr 2.10):
    Unchanged. Revaluation does not affect realized gains.

  Unrealized FX Gain (0):
    Net zero. Asset-side gains (Deposit +4.60, Trading +4.60 = +9.20)
    exactly offset liability growth (Omnibus +9.20). The bank has no net
    EUR exposure — Deposit Dr 50 + Trading Dr 50 − Omnibus Cr 100 = 0
    net EUR — so net unrealized must be zero.


STEP 5 — Withdraw 30 EUR (spot rate 1.22)

  The spot rate has moved to 1.22 since the period 1 close at 1.20.
  Withdrawal entries use book value and proportional reval unwind — the
  current spot rate does not affect the accounting. The account balances
  after this step still reflect the 1.20 reval, not the current 1.22 spot.

  Unwind proportional deposit revaluation (30/50 × 4.60 = 2.76):
  ㉓ Dr  Unrealized FX Gain   2.76 USD
  ㉔ Cr  EUR Deposit          2.76 USD

  Withdrawal at book value (30 × 1.108 = 33.24):
  ㉕ Dr  EUR Omnibus         30 EUR
  ㉖ Dr  EUR Omnibus         33.24 USD
  ㉗ Cr  EUR Deposit         30 EUR
  ㉘ Cr  EUR Deposit         33.24 USD

  Unwind proportional omnibus revaluation (30/100 × 9.20 = 2.76):
  ㉙ Dr  EUR Omnibus          2.76 USD
  ㉚ Cr  Unrealized FX Gain   2.76 USD

  Net unrealized from step 5: −2.76 + 2.76 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 24
EUR Omnibus            Credit                70               84
Trading                Debit       50                  4.60
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     86.10    86.10  ✓

  Verify: Deposit 20 EUR = 22.16 book + 1.84 reval = 24  ✓
          Omnibus 70 EUR = 77.56 book + 6.44 reval = 84  ✓
          At spot 1.22: Deposit fair = 24.40, Omnibus fair = 85.40
          Balances (24 / 84) reflect last reval rate (1.20), not current
          spot (1.22). The 0.40 / 1.40 gaps are unrecognized intra-period
          rate changes — they will be captured by the next revaluation run.

  EUR Deposit (Dr 20 EUR, Dr 24 USD):
    20 EUR remaining. Book value 22.16 (20 × 1.108) plus residual
    revaluation 1.84 (proportional: 20/50 × 4.60). The reval for the
    withdrawn 30 EUR was unwound — withdrawal is not a realization
    event.

  EUR Omnibus (Cr 70 EUR, Cr 84 USD):
    70 EUR remaining at correspondent (100 deposited − 30 withdrawn).
    Book value 77.56 (70 × 1.108) plus residual revaluation 6.44
    (proportional: 70/100 × 9.20). The reval on the withdrawn portion
    was unwound symmetrically with the deposit unwind.

  Trading (Dr 50 EUR, Dr 4.60 USD):
    Unchanged. Withdrawals do not affect the trading position.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.10):
    Unchanged. Withdrawal generates no realized gain.

  Unrealized FX Gain (0):
    Still zero. The deposit unwind (−2.76) and omnibus unwind (+2.76)
    cancel. Net EUR exposure unchanged (Deposit 20 + Trading 50 −
    Omnibus 70 = 0), so net unrealized remains zero.


STEP 6 — Revaluation, period 2 (rate → 1.05)

  Delta method: adjustment = (balance × new_rate) − current_USD_balance.
  Each account's USD balance already includes period 1 reval; the delta
  method posts only the incremental change from the previous state.

  EUR Deposit (debit-normal, asset): 20 EUR, current 24, fair 21
  ㉛ Dr  Unrealized FX Gain   3 USD
  ㉜ Cr  EUR Deposit          3 USD

  EUR Omnibus (credit-normal, liability): 70 EUR, current 84, fair 73.50
  Liability decreased by 10.50 (EUR depreciated → bank owes less):
  ㉝ Dr  EUR Omnibus         10.50 USD
  ㉞ Cr  Unrealized FX Gain  10.50 USD

  Trading (debit-normal, asset): 50 EUR, delta from prev closing rate
  50 × (1.05 − 1.20) = −7.50:
  ㉟ Dr  Unrealized FX Gain   7.50 USD
  ㊱ Cr  Trading              7.50 USD

  Net unrealized from step 6: −3 + 10.50 − 7.50 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 21
EUR Omnibus            Credit                70               73.50
Trading                Debit       50                          2.90
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     78.50    78.50  ✓

  Verify: Deposit 20 EUR = 22.16 book − 1.16 reval = 21  ✓
          Omnibus 70 EUR = 77.56 book − 4.06 reval = 73.50  ✓
          Trading 50 EUR: accumulator 55.40, reval −2.90, ledger −2.90  ✓

  EUR Deposit (Dr 20 EUR, Dr 21 USD):
    20 EUR marked to market at new closing rate. Book value 22.16 (at
    1.108), previous fair value 24 (at 1.20), new fair value 21 (at
    1.05). Delta method posts only the incremental change: 21 − 24 =
    −3. The EUR has now depreciated below the original booking rate.

  EUR Omnibus (Cr 70 EUR, Cr 73.50 USD):
    70 EUR liability revalued from 84 to 73.50. EUR depreciated, so
    the bank's obligation decreased by 10.50 USD. This is a gain for
    the bank — the inverse of period 1's loss.

  Trading (Dr 50 EUR, Cr 2.90 USD):
    50 EUR position revalued from fair 60 (at 1.20) to 52.50 (at
    1.05). Delta = −7.50. The credit USD balance means the position's
    fair value (52.50) is below book cost (55.40). The Selinger
    accumulator still reads 55.40; the ledger reflects 0 (post-G/L
    clearing) + 4.60 (period 1) − 7.50 (period 2 delta) = −2.90.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.10):
    Unchanged.

  Unrealized FX Gain (0):
    Still zero. Period 1 gains (+9.20 on assets, −9.20 on liability)
    exactly reversed by period 2 losses (−10.50 on assets, +10.50 on
    liability). The invariant holds: net EUR exposure = 0 → net
    unrealized = 0, regardless of rate direction.


STEP 7 — Withdraw remaining 20 EUR (spot rate 1.02)

  The spot rate has moved to 1.02 since the period 2 close at 1.05.
  As with step 5, withdrawal entries use book value and proportional
  reval unwind — the current spot rate does not affect the accounting.

  Unwind remaining deposit revaluation (reval = −1.16, i.e., 1.16 below book):
  ㊲ Dr  EUR Deposit          1.16 USD
  ㊳ Cr  Unrealized FX Gain   1.16 USD

  Withdrawal at book value (20 × 1.108 = 22.16):
  ㊴ Dr  EUR Omnibus         20 EUR
  ㊵ Dr  EUR Omnibus         22.16 USD
  ㊶ Cr  EUR Deposit         20 EUR
  ㊷ Cr  EUR Deposit         22.16 USD

  Unwind proportional omnibus revaluation (20/70 × (−4.06) = −1.16):
  ㊸ Dr  Unrealized FX Gain   1.16 USD
  ㊹ Cr  EUR Omnibus          1.16 USD

  Net unrealized from step 7: +1.16 − 1.16 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit                50               52.50
Trading                Debit       50                          2.90
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             50       50     57.50    57.50  ✓

  Verify: Omnibus 50 EUR = 55.40 book − 2.90 reval = 52.50  ✓
          (remaining reval: −4.06 + 1.16 unwound = −2.90)
          Trading unchanged: accumulator 55.40, reval −2.90  ✓
          At spot 1.02: Omnibus fair = 51, but balance shows 52.50
          (reflects 1.05 reval). The 1.50 gap is an unrecognized
          intra-period rate change.

  EUR Deposit (0 EUR, 0 USD):
    Fully closed. All EUR withdrawn, all revaluation unwound.

  EUR Omnibus (Cr 50 EUR, Cr 52.50 USD):
    50 EUR remain at the correspondent. These are the EUR from the
    conversion that haven't been physically delivered yet. Book value
    55.40 (50 × 1.108) minus residual revaluation 2.90 (the remaining
    portion of the period 2 adverse adjustment). Fair value at last
    reval rate 1.05 = 52.50 confirms consistency.

  Trading (Dr 50 EUR, Cr 2.90 USD):
    Unchanged. Still holds the unsettled conversion position. The
    Dr 50 EUR mirrors the Omnibus Cr 50 EUR — these are two views of
    the same 50 EUR awaiting delivery.

  USD Cash (Dr 57.50):
    Unchanged.

  Realized FX Gain (Cr 2.10):
    Unchanged.

  Unrealized FX Gain (0):
    Still zero. Net EUR exposure: Trading 50 − Omnibus 50 = 0. The
    Cr 2.90 on Trading is exactly offset by the Cr 2.90 reval
    reduction on Omnibus (52.50 vs book 55.40).


STEP 8 — Settle conversion (deliver 50 EUR to FX counterparty)

  EUR delivery:
  ㊺ Dr  EUR Omnibus         50 EUR
  ㊻ Cr  Trading             50 EUR

  Reverse Trading revaluation (position closed — sale was at 1.15,
  not 1.05, so the mark-to-market unwinds):
  ㊼ Dr  Trading              2.90 USD
  ㊽ Cr  Unrealized FX Gain   2.90 USD

  Unwind remaining omnibus revaluation (50/50 × (−2.90) = −2.90):
  ㊾ Dr  Unrealized FX Gain   2.90 USD
  ㊿ Cr  EUR Omnibus          2.90 USD

  Net unrealized from step 8: +2.90 − 2.90 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit        0                55.40
Trading                Debit        0                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  2.10
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                              0        0     57.50    57.50  ✓

  EUR Deposit (0 EUR, 0 USD):
    Already closed in step 7.

  EUR Omnibus (0 EUR, Cr 55.40 USD):
    All EUR delivered (100 deposited − 30 withdrawn − 20 withdrawn −
    50 settled = 0). The Cr 55.40 USD is the orphaned book value: the
    customer gave up 50 EUR worth 55.40 USD (at blended rate 1.108)
    in the conversion and should have received USD in return. This
    residual is the customer's unmodeled USD entitlement — the scenario
    does not include a Customer USD Deposit account.

  Trading (0 EUR, 0 USD):
    Fully closed. EUR delivered to counterparty, mark-to-market
    reversed. The bank's gain was locked in at the conversion rate
    (1.15), not the revaluation rate. The reval was a temporary
    adjustment that unwound on settlement — whether the rate was
    above book (period 1: 1.20) or below (period 2: 1.05).

  USD Cash (Dr 57.50):
    Unchanged throughout. The 57.50 USD from the FX sale is the only
    real cash the bank holds.

  Realized FX Gain (Cr 2.10):
    Unchanged. Total realized = 2.10 (sold 50 EUR at 1.15, book cost
    at blended rate 1.108). Neither revaluation period affected the
    realized gain — the sale price was already locked in.

  Unrealized FX Gain (0):
    Zero throughout every step. The bank never had net EUR exposure,
    so unrealized gain was always zero.

  USD Cash (Dr 57.50) = Omnibus residual (Cr 55.40) + Realized (Cr 2.10):
    The bank holds 57.50 USD. Of that, 55.40 is the customer's converted
    principal (book value of 50 EUR at blended rate 1.108) and 2.10 is
    the bank's profit (conversion spread: 1.15 − 1.108 = 0.042 per EUR
    × 50 EUR = 2.10).
```

## Design observations

1. **Omnibus must be revalued.** The Omnibus is a credit-normal EUR liability. EUR appreciation increases it (unrealized loss for the bank); EUR depreciation decreases it (unrealized gain). Without Omnibus revaluation, the system incorrectly reports non-zero unrealized gains even when net EUR exposure is zero.

2. **Withdrawal unwinds revaluation, does not realize it.** A withdrawal returns EUR to the customer — it is not a market transaction. The proportional revaluation on both the Deposit (asset) and Omnibus (liability) is reversed. The two unwinds always cancel, keeping net unrealized at zero. This follows from the Selinger model: realization only occurs through the Trading Account (conversions), never through withdrawals.

3. **Net EUR exposure determines net unrealized.** At every step, Deposit Dr + Trading Dr − Omnibus Cr = 0 net EUR. Therefore net unrealized is always zero. This is the fundamental invariant: unrealized FX gain/loss reflects open currency exposure, and this scenario has none (every EUR asset is backed by a EUR liability).

4. **Settlement reverses mark-to-market.** When the Trading position closes via delivery, the revaluation is reversed — not reclassified to realized. The bank sold EUR at 1.15; the subsequent rate movements (1.20 then 1.05) are irrelevant to the bank's gain. The only realized gain is the conversion spread (2.10).

5. **Omnibus USD residual reveals unmodeled account.** After settlement, the Omnibus retains Cr 55.40 USD with no EUR backing. This is the customer's USD entitlement from the conversion — the scenario omits the Customer USD Deposit account. In a complete model, Step 3 would include `Cr Customer USD Deposit 57.50 USD` and the Omnibus residual (55.40) plus Realized Gain (2.10) would exactly fund it (57.50).

6. **Two book value sources.** Regular foreign-currency accounts (EUR Deposit, EUR Omnibus) get their book value from the Group A ledger USD balance. The trading account gets its book value from the position accumulator — its ledger USD balance is 0 after realized G/L clearing, so the ledger balance cannot serve as book value for revaluation. The SPEC's revaluation process (Component 5) documents this exception: the revaluation job reads `current_book_value` from the accumulator for the Trading account instead of from the ledger balance.

7. **Book value leg on conversions.** The conversion template needs a third leg (entries ⑪-⑫) to transfer the proportional USD book value from the source account to the trading account. This requires a `source_book_value` parameter computed by the orchestrator from the source account's ledger USD balance before posting.

8. **Position accumulator survives Group A.** Group A eliminates the need for external book value tracking on all regular accounts, but the trading account still needs the position accumulator because its ledger USD balance gets zeroed by realized G/L clearing.

9. **Delta method across periods.** The second revaluation (Step 6) demonstrates the SPEC's recommended delta approach: each period computes `new_value − current_book_value` where current_book_value includes all prior revaluation adjustments. Only the incremental difference is posted; no reversals are needed. Running revaluation twice at the same rate produces a zero adjustment on the second run (idempotent).

10. **Adverse rate movement inverts asset/liability reval directions.** When EUR depreciates below the original booking rate (1.05 < 1.108), asset revaluations produce losses (Deposit −3, Trading −7.50) and liability revaluations produce gains (Omnibus +10.50) — the inverse of period 1. The net remains zero because net EUR exposure hasn't changed. The Trading account's USD balance goes negative (credit on a debit-normal account), reflecting a position fair value (52.50) below book cost (55.40).

11. **Path independence of final state.** Despite two revaluation periods at different rates (1.20 and 1.05), the final trial balance is identical to what it would be with no revaluation, or with any other intermediate rates. Revaluation entries are temporary mark-to-market adjustments that fully unwind on settlement or withdrawal. The final state depends only on the original booking rates (1.10 and 1.12) and the conversion rate (1.15).

12. **Single vs split Unrealized accounts.** The SPEC specifies separate Unrealized FX Gain (6100) and Unrealized FX Loss (6200) accounts. This walkthrough uses a single account for clarity, since the net is always zero in this scenario. In production, splitting by direction enables separate reporting of unrealized gains and losses as required by IAS 21 financial statement presentation.

13. **Blended book rate from multiple deposits.** When EUR are deposited at different spot rates (1.10 and 1.12), the account carries a weighted-average book rate (1.108). All subsequent operations — conversions, revaluations, withdrawals — use this blended rate as the per-unit book cost. The Group A ledger naturally produces the correct blended USD balance; no external averaging is needed. The realized gain on conversion (2.10) reflects the spread between the sale rate (1.15) and the blended book rate (1.108), not any single deposit rate.

14. **Withdrawal entries are spot-rate-independent.** Steps 5 and 7 show withdrawals occurring when the spot rate (1.22 and 1.02) differs from the last revaluation rate (1.20 and 1.05). The entries are identical regardless of the current spot rate — they use book value (at the blended rate 1.108) and unwind proportional revaluation based on the existing reval amounts, not the current market rate. Post-withdrawal balances reflect the last reval rate, not the current spot. The gap between the account balance and current fair value is an unrecognized intra-period rate change that will be captured by the next period-end revaluation.

## Templates used

| Step | Template | Module |
|---|---|---|
| 1, 2 — Deposit | Deposit template (with Group A dual-currency entries) | Deposit layer |
| 3 — Conversion | `FIAT_FX_CONVERSION_VIA_TRADING` (with book value leg) | Phase 3 |
| 3 — Realized G/L | `REALIZED_FX_GAIN_LOSS` | Phase 3 |
| 4, 6 — Revaluation | Revaluation template (Deposit + Omnibus + Trading, delta method) | Phase 4 |
| 5, 7 — Withdrawal | Withdrawal template (with reval unwind on both Deposit and Omnibus) | Deposit layer |
| 8 — Settlement | Settlement template (EUR delivery + reval reversal) | Phase 3 |

---

## Implementation gap analysis

_Analysis performed 2025-03-25 on branch `refactor/fx-accumulator-model` at commit `15e489bea`._

### What we have (3 templates)

| Template | File | Status |
|---|---|---|
| `FIAT_FX_CONVERSION_VIA_TRADING` | `core/fx/src/ledger/templates/fiat_fx_conversion.rs` | Present |
| `REALIZED_FX_GAIN_LOSS` | `core/fx/src/ledger/templates/realized_fx_gain_loss.rs` | Present |
| `FX_ROUNDING_ADJUSTMENT` | `core/fx/src/ledger/templates/fx_rounding_adjustment.rs` | Present (utility, not in walkthrough) |

### What's missing (3 templates)

1. **Revaluation template** (Steps 4, 6) — The delta-method mark-to-market template that posts `Dr/Cr account` vs `Cr/Dr Unrealized FX Gain` for each foreign-currency account. This is the core of Phase 4. Needs to handle Deposit (asset), Omnibus (liability), and Trading (where book value comes from the accumulator, not ledger balance).

2. **Settlement template** (Step 8) — EUR delivery from Omnibus to Trading (`Dr Omnibus / Cr Trading` in EUR), plus reversal of the Trading account's revaluation and unwind of the Omnibus revaluation. Closes the trading position.

3. **Withdrawal reval-unwind entries** (Steps 5, 7) — Withdrawals need to unwind proportional revaluation on both the Deposit and Omnibus sides before transferring at book value. This likely lives in the Deposit layer's withdrawal template rather than the FX module, but the FX module needs to either provide it or coordinate with the deposit layer to ensure it happens.

### What's wrong with what we have

**`FIAT_FX_CONVERSION_VIA_TRADING` is missing the book-value leg.** The walkthrough's Step 3 has three pairs of entries:

- Entries ⑨-⑩: Source currency movement (`Dr Trading / Cr EUR Deposit` — 50 EUR) — **we have this**
- Entries ⑬-⑭: Target currency movement (`Dr USD Cash / Cr Trading` — 57.50 USD) — **we have this**
- Entries ⑪-⑫: **Book value transfer** (`Dr Trading / Cr EUR Deposit` — 55.40 USD) — **MISSING**

The walkthrough's observation #7 explicitly calls this out: *"The conversion template needs a third leg (entries ⑪-⑫) to transfer the proportional USD book value from the source account to the trading account."* Without this leg, the Trading account's USD balance won't reflect the book cost of the acquired EUR, and the subsequent realized G/L clearing entry won't work correctly (it needs Trading's USD balance to be non-zero so that the G/L entry zeros it out).

The current template only moves `source_amount` in `source_currency` and `target_amount` in `target_currency` — it has no functional-currency (USD) book-value transfer between source and trading accounts. This would need a `source_book_value` parameter computed by the orchestrator from the source account's current USD ledger balance.

### Summary

- **3 templates present**, 1 of which (rounding) is a utility not in the walkthrough
- **2–3 templates missing**: revaluation, settlement, and withdrawal reval-unwind coordination
- **1 template wrong**: the conversion template is missing the critical book-value leg in functional currency, which breaks the Selinger accumulator flow
