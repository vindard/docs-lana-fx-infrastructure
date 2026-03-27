# EUR Deposit → Conversion → Revaluation → Withdrawal → Settlement: Full Walkthrough

End-to-end scenario exercising Group A (dual-currency entries), Phase 3 (trading account conversion + realized G/L), and Phase 4 (period-end revaluation with delta method across multiple periods). A revaluation runs after every non-revaluation step, stress-testing the delta method and revealing how revaluation timing interacts with conversion book value. Functional currency: USD.

Scenario file: `tools/scenario_eur_deposit_with_revals.yaml`

## Scenario

1. Customer deposits 60 EUR (spot rate 1.10 USD/EUR)
2. Revaluation (rate → 1.08)
3. Revaluation (rate → 1.06)
4. Customer deposits 40 EUR (spot rate 1.12 USD/EUR)
5. Revaluation (rate → 1.14)
6. Bank converts 50 EUR → USD (rate 1.15)
7. Revaluation (rate → 1.18)
8. Revaluation (rate → 1.20)
9. Customer withdraws 30 EUR
10. Revaluation (rate → 1.22)
11. Revaluation (rate → 1.05)
12. Customer withdraws remaining 20 EUR
13. Bank partially settles conversion (delivers 20 of 50 EUR)
14. Revaluation (rate → 1.02)
15. Bank settles remaining conversion (delivers 30 EUR to FX counterparty)
16. Revaluation (rate → 0.98)

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

  Out-of-band balances:
    (none)

  EUR Deposit (Dr 60 EUR, Dr 66 USD):
    The bank's record of the customer's claim. 60 EUR deposited,
    booked at spot 1.10 = 66 USD.

  EUR Omnibus (Cr 60 EUR, Cr 66 USD):
    60 EUR received at the correspondent bank. Mirror of the deposit.
    Credit-normal because it is a liability — EUR held on behalf of
    the customer.


STEP 2 — Revaluation (rate → 1.08)

  EUR Deposit (debit-normal, asset): 60 EUR, book 66, fair 64.80
  ⑤ Dr  Unrealized FX Gain   1.20 USD
  ⑥ Cr  EUR Deposit          1.20 USD

  EUR Omnibus (credit-normal, liability): 60 EUR, book 66, fair 64.80
  ⑦ Dr  EUR Omnibus          1.20 USD
  ⑧ Cr  Unrealized FX Gain   1.20 USD

  Net unrealized: −1.20 + 1.20 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       60                 64.80
EUR Omnibus            Credit               60                64.80
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             60       60     64.80    64.80  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = -1.20
    EUR Omnibus     cumulative_reval = -1.20

  EUR Deposit (Dr 60 EUR, Dr 64.80 USD):
    First mark-to-market. EUR depreciated from 1.10 to 1.08, so the
    asset is worth less: 60 × 1.08 = 64.80. The −1.20 adjustment
    reduces the USD balance from 66 to 64.80.

  EUR Omnibus (Cr 60 EUR, Cr 64.80 USD):
    Liability decreased symmetrically. EUR depreciation means the bank
    owes less in USD terms: 66 → 64.80. The −1.20 gain exactly offsets
    the −1.20 loss on the deposit.

  Unrealized FX Gain (0):
    Net zero. Asset loss (−1.20) exactly offset by liability gain
    (+1.20). The bank has no net EUR exposure — Deposit Dr 60 −
    Omnibus Cr 60 = 0 — so net unrealized must be zero.

    Why Omnibus must be revalued: Without the Omnibus entry, the −1.20
    would sit alone in Unrealized FX Gain, reporting a loss that doesn't
    exist. The bank didn't lose anything — the EUR it holds for the
    customer depreciated, but so did the EUR it owes the customer. The
    two adjustments cancel because the bank's position is fully hedged.
    Unrealized FX Gain would only carry a non-zero balance if the bank
    held net EUR exposure — e.g., EUR bought speculatively without a
    matching customer deposit.


STEP 3 — Revaluation (rate → 1.06)

  Consecutive revaluation — delta method posts only the incremental
  change from the previous state (1.08 → 1.06), not from the original
  booking rate.

  ⑨ Dr  Unrealized FX Gain   1.20 USD
  ⑩ Cr  EUR Deposit          1.20 USD
  ⑪ Dr  EUR Omnibus          1.20 USD
  ⑫ Cr  Unrealized FX Gain   1.20 USD

  Net unrealized: −1.20 + 1.20 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       60                 63.60
EUR Omnibus            Credit               60                63.60
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             60       60     63.60    63.60  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = -2.40
    EUR Omnibus     cumulative_reval = -2.40

  Each step posts exactly −1.20 USD (60 × 0.02 = 1.20 per 2-cent rate
  move). The delta method computes the incremental change from the
  previous state regardless of the original booking rate — no reversal
  of the first revaluation is needed.

  Cumulative reval on each account: −2.40 (= −1.20 − 1.20).
  Original book value: 66. Fair value: 63.60. Check: 66 − 2.40 = 63.60 ✓


STEP 4 — Deposit 40 EUR (rate 1.12)
  ⑬ Dr  EUR Deposit        40 EUR
  ⑭ Dr  EUR Deposit        44.80 USD
  ⑮ Cr  EUR Omnibus        40 EUR
  ⑯ Cr  EUR Omnibus        44.80 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit      100                108.40
EUR Omnibus            Credit              100               108.40
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     108.40   108.40  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = -2.40
    EUR Omnibus     cumulative_reval = -2.40

  EUR Deposit (Dr 100 EUR, Dr 108.40 USD):
    Customer's total claim after both deposits. The USD balance is
    63.60 (first deposit, already revalued) + 44.80 (second deposit,
    at spot 1.12). The blended ledger rate is 108.40 / 100 = 1.084.

    Note: the original historical book value was 60 × 1.10 + 40 × 1.12
    = 110.80 (blended rate 1.108). The ledger rate (1.084) is lower
    because the first deposit was revalued down from 66 to 63.60 before
    the second deposit arrived. The cumulative reval on the account is
    still −2.40 (from steps 2–3), applied only to the first 60 EUR.

  EUR Omnibus (Cr 100 EUR, Cr 108.40 USD):
    100 EUR received at the correspondent bank across two deposits.
    Same blended ledger rate as the deposit.


STEP 5 — Revaluation (rate → 1.14)

  ⑰ Dr  EUR Deposit          5.60 USD
  ⑱ Cr  Unrealized FX Gain   5.60 USD
  ⑲ Dr  Unrealized FX Gain   5.60 USD
  ⑳ Cr  EUR Omnibus          5.60 USD

  Net unrealized: +5.60 − 5.60 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit      100                 114
EUR Omnibus            Credit              100                114
Trading                Debit        0                  0
USD Cash               Debit                           0
Realized FX Gain       Credit                                  0
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100       114      114  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 3.20
    EUR Omnibus     cumulative_reval = 3.20

  EUR Deposit (Dr 100 EUR, Dr 114 USD):
    100 EUR marked to market at 1.14. Delta = 114 − 108.40 = +5.60.
    This is the first revaluation on the combined 100 EUR balance — the
    delta method adjusts from the current ledger state (which includes
    prior revals on the first 60 EUR) to the new fair value.

    Cumulative reval: −2.40 + 5.60 = +3.20. The ledger rate is now
    114 / 100 = 1.14. This is the rate the conversion will use as
    "book value" in the next step — a critical detail.


STEP 6 — Convert 50 EUR → USD (rate 1.15)

  Book value of 50 EUR at blended rate: 50 × 1.14 = 57

  ㉑ Dr  Trading             50 EUR
  ㉒ Cr  EUR Deposit         50 EUR
  ㉓ Dr  Trading             57 USD       ← book value leg
  ㉔ Cr  EUR Deposit         57 USD
  ㉕ Dr  USD Cash            57.50 USD
  ㉖ Cr  Trading             57.50 USD
  ㉗ Dr  Trading              0.50 USD       ← realized G/L clearing
  ㉘ Cr  Realized FX Gain     0.50 USD

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 57
EUR Omnibus            Credit              100                114
Trading                Debit       50                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     114.50   114.50  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 3.20
    EUR Omnibus     cumulative_reval = 3.20
    Trading         accumulator = 57

  EUR Deposit (Dr 50 EUR, Dr 57 USD):
    Customer's remaining balance after conversion. 50 EUR at the current
    ledger rate 1.14 = 57 USD.

  EUR Omnibus (Cr 100 EUR, Cr 114 USD):
    Unchanged. The EUR haven't physically left the correspondent bank
    yet — settlement is pending.

  Trading (Dr 50 EUR, Dr 0 USD):
    Holds the 50 EUR acquired from the customer's deposit. USD is zero
    because book value in (57), sale proceeds out (57.50), and G/L
    clearing (0.50) net out: 57 − 57.50 + 0.50 = 0. The Selinger
    accumulator tracks the book cost (57 USD) separately.

  USD Cash (Dr 57.50):
    Proceeds from selling 50 EUR at 1.15 on the FX market.

  Realized FX Gain (Cr 0.50):
    Locked-in profit from the conversion spread. Book cost 57 USD
    (50 EUR × 1.14), sold for 57.50 USD (50 EUR × 1.15).
    Difference = 0.50.

    KEY INSIGHT: Without the prior revaluations, the book rate would be
    1.108 (the historical weighted-average), giving a realized gain of
    57.50 − 55.40 = 2.10. The revaluation at step 5 inflated the
    ledger USD balance to 114 (rate 1.14), so the conversion sees a
    higher "book cost" and reports a smaller realized gain. The total
    economic gain is unchanged (0.50 realized + 1.60 shifted into the
    Omnibus residual = 2.10), but the classification is path-dependent
    on revaluation timing.


STEP 7 — Revaluation (rate → 1.18)

  First three-account revaluation — Deposit, Omnibus, and Trading all
  carry EUR positions.

  ㉙ Dr  EUR Deposit          2 USD
  ㉚ Cr  Unrealized FX Gain   2 USD
  ㉛ Dr  Unrealized FX Gain   4 USD
  ㉜ Cr  EUR Omnibus          4 USD
  ㉝ Dr  Trading              2 USD
  ㉞ Cr  Unrealized FX Gain   2 USD

  Net unrealized: +2 − 4 + 2 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 59
EUR Omnibus            Credit              100                118
Trading                Debit       50                  2
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     118.50   118.50  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 5.20
    EUR Omnibus     cumulative_reval = 7.20
    Trading         cumulative_reval = 2, accumulator = 57

  EUR Deposit (Dr 50 EUR, Dr 59 USD):
    50 EUR marked to market at 1.18. Delta = 59 − 57 = +2.

  EUR Omnibus (Cr 100 EUR, Cr 118 USD):
    100 EUR liability revalued from 114 to 118. Delta = +4.

  Trading (Dr 50 EUR, Dr 2 USD):
    50 EUR position revalued. Delta = (50 × 1.18) − (accumulator 57 +
    cumulative_reval 0) = 59 − 57 = +2. The Trading account uses the
    accumulator as its book value base, not the ledger balance (which
    was zeroed by realized G/L clearing).

  Unrealized FX Gain (0):
    Net zero. Asset-side gains (Deposit +2, Trading +2 = +4) exactly
    offset liability growth (Omnibus +4). Net EUR exposure:
    Deposit 50 + Trading 50 − Omnibus 100 = 0.


STEP 8 — Revaluation (rate → 1.20)

  Consecutive revaluation — delta from 1.18 to 1.20.

  ㉟ Dr  EUR Deposit          1 USD
  ㊱ Cr  Unrealized FX Gain   1 USD
  ㊲ Dr  Unrealized FX Gain   2 USD
  ㊳ Cr  EUR Omnibus          2 USD
  ㊴ Dr  Trading              1 USD
  ㊵ Cr  Unrealized FX Gain   1 USD

  Net unrealized: +1 − 2 + 1 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       50                 60
EUR Omnibus            Credit              100                120
Trading                Debit       50                  3
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                            100      100     120.50   120.50  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 6.20
    EUR Omnibus     cumulative_reval = 9.20
    Trading         cumulative_reval = 3, accumulator = 57

  Verify cumulative revals at this point:
    Deposit: +3.20 (steps 2–5) + 2 (step 7) + 1 (step 8) = +6.20
    Omnibus: +3.20 (steps 2–5) + 4 (step 7) + 2 (step 8) = +9.20
    Trading: 0 + 2 (step 7) + 1 (step 8) = +3
    Deposit book value (reval-stripped): 60 − 6.20 = 53.80 → rate 53.80/50 = 1.076
    Omnibus book value (reval-stripped): 120 − 9.20 = 110.80 → rate 110.80/100 = 1.108 ✓


STEP 9 — Withdraw 30 EUR

  Unwind proportional deposit revaluation (30/50 × 6.20 = 3.72):
  ㊶ Dr  Unrealized FX Gain   3.72 USD
  ㊷ Cr  EUR Deposit          3.72 USD

  Withdrawal at book value (30 × 1.076 = 32.28):
  ㊸ Dr  EUR Omnibus         30 EUR
  ㊹ Dr  EUR Omnibus         32.28 USD
  ㊺ Cr  EUR Deposit         30 EUR
  ㊻ Cr  EUR Deposit         32.28 USD

  Unwind proportional omnibus revaluation (30/100 × 9.20 = 2.76):
  ㊼ Dr  EUR Omnibus          2.76 USD
  ㊽ Cr  Unrealized FX Gain   2.76 USD

  Net unrealized from step 9: −3.72 + 2.76 = −0.96

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 24
EUR Omnibus            Credit                70               84.96
Trading                Debit       50                  3
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit       0.96                       0
                                 ────     ────     ─────    ─────
Totals                             70       70     85.46    85.46  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 2.48
    EUR Omnibus     cumulative_reval = 6.44
    Trading         cumulative_reval = 3, accumulator = 57

  Unrealized FX Gain (Dr 0.96):
    Non-zero for the first time. The deposit unwind (−3.72) and omnibus
    unwind (+2.76) do NOT cancel because the proportions differ:
    deposit had 50 EUR (30/50 = 60%), omnibus had 100 EUR (30/100 = 30%).
    In a scenario without intermediate revaluations, deposit and omnibus
    cumulative revals would be symmetric and the unwinds would cancel.
    Here, multiple revaluations at different EUR balances (60 EUR vs
    100 EUR) broke the symmetry.

    This is expected — the invariant (net unrealized = 0) holds after
    revaluation, not necessarily between operations. The next revaluation
    will restore it.

  EUR Deposit (Dr 20 EUR, Dr 24 USD):
    20 EUR remaining. The book rate used for withdrawal is 1.076 — the
    reval-stripped rate (deposit USD minus cumulative reval, divided by
    EUR balance). This is lower than the original historical rate (1.108)
    because the conversion at step 6 consumed USD at the revalued rate
    (1.14), removing more USD per EUR than historical cost.

  EUR Omnibus (Cr 70 EUR, Cr 84.96 USD):
    70 EUR remaining. Book value transfer (32.28) plus partial omnibus
    reval unwind (2.76) reduces the balance from 120.

  Trading (Dr 50 EUR, Dr 3 USD):
    Unchanged. Withdrawals do not affect the trading position.

  Value sources for withdrawal calculations:

    Phase 1 — Unwind deposit reval (30/50 × 6.20 = 3.72):
      30          input parameter (withdrawal amount)
      50          ledger read (EUR Deposit EUR balance)
      6.20        OUT-OF-BAND (deposit cumulative reval)

    Phase 2 — Transfer at book value (30 × 1.076 = 32.28):
      1.076       derived: (deposit_USD − cumulative_reval) / deposit_EUR
                  = (56.28 − 2.48) / 50, where 56.28 and 2.48 are the
                  post-phase-1 values (ledger read + out-of-band)

    Phase 3 — Unwind omnibus reval (30/100 × 9.20 = 2.76):
      100         ledger-derive (omnibus EUR before transfer: 70 + 30)
      9.20        OUT-OF-BAND (omnibus cumulative reval)

    The critical out-of-band value is cumulative_reval. Group A's
    ledger USD balance blends original book value with revaluation
    adjustments — they are inseparable from the ledger alone. The
    ledger shows EUR Deposit = 60 USD, but cannot answer "how much
    is reval?" without a separately tracked cumulative_reval field.
    This is analogous to the Trading account's position accumulator:
    both are out-of-band values that Group A's ledger cannot provide.

    cumulative_reval is updated by three operations:
      revaluation:  += adjustment
      withdrawal:   -= proportional unwind
      settlement:   -= proportional reverse


STEP 10 — Revaluation (rate → 1.22)

  ㊾ Dr  EUR Deposit            0.40 USD
  ㊿ Cr  Unrealized FX Gain     0.40 USD
  (51) Dr  Unrealized FX Gain     0.44 USD
  (52) Cr  EUR Omnibus            0.44 USD
  (53) Dr  Trading                1 USD
  (54) Cr  Unrealized FX Gain     1 USD

  Net unrealized from step 10: +0.40 − 0.44 + 1 = +0.96
  Cumulative unrealized: −0.96 + 0.96 = 0  ✓ (restored)

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 24.40
EUR Omnibus            Credit                70               85.40
Trading                Debit       50                  4
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     85.90    85.90  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = 2.88
    EUR Omnibus     cumulative_reval = 6.88
    Trading         cumulative_reval = 4, accumulator = 57

  Unrealized FX Gain (0):
    Restored to zero. The +0.96 from this revaluation exactly offsets
    the −0.96 gap left by the withdrawal. After every revaluation, the
    invariant holds: net EUR exposure = 0 → net unrealized = 0.

  Note the asymmetric adjustments: Deposit +0.40, Omnibus +0.44,
  Trading +1.00. The Deposit and Omnibus deltas differ (0.40 vs 0.44)
  because their EUR balances differ (20 vs 70) and their previous
  USD states reflected different cumulative reval histories.


STEP 11 — Revaluation (rate → 1.05)

  Large adverse rate swing: 1.22 → 1.05. EUR depreciates sharply.

  (55) Dr  Unrealized FX Gain     3.40 USD
  (56) Cr  EUR Deposit            3.40 USD
  (57) Dr  EUR Omnibus           11.90 USD
  (58) Cr  Unrealized FX Gain    11.90 USD
  (59) Dr  Unrealized FX Gain     8.50 USD
  (60) Cr  Trading                8.50 USD

  Net unrealized: −3.40 + 11.90 − 8.50 = 0  ✓

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit       20                 21
EUR Omnibus            Credit                70               73.50
Trading                Debit       50                          4.50
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                             70       70     78.50    78.50  ✓

  Out-of-band balances:
    EUR Deposit     cumulative_reval = -0.52
    EUR Omnibus     cumulative_reval = -5.02
    Trading         cumulative_reval = -4.50, accumulator = 57

  Trading (Dr 50 EUR, Cr 4.50 USD):
    Credit USD balance on a debit-normal account — the position's fair
    value (52.50 at 1.05) is below the accumulator book cost (57).
    Ledger: 0 (post-G/L clearing) + 3 (prior revals) − 8.50 (this
    step) = −4.50 (shown as Cr, but the cumulative reval accounts for
    it: accumulator 57 + cumulative_reval −4.50 matches the non-ledger
    tracking).

  EUR Omnibus (Cr 70 EUR, Cr 73.50 USD):
    Liability decreased by 11.90. EUR depreciation → bank owes less.
    This gain offsets the combined asset losses (Deposit −3.40 +
    Trading −8.50 = −11.90).


STEP 12 — Withdraw remaining 20 EUR

  Unwind remaining deposit revaluation (cumulative reval = −0.52):
  (61) Dr  EUR Deposit          0.52 USD
  (62) Cr  Unrealized FX Gain   0.52 USD

  Withdrawal at book value (20 × 1.076 = 21.52):
  (63) Dr  EUR Omnibus         20 EUR
  (64) Dr  EUR Omnibus         21.52 USD
  (65) Cr  EUR Deposit         20 EUR
  (66) Cr  EUR Deposit         21.52 USD

  Unwind proportional omnibus revaluation (20/70 × (−5.02) = −1.43):
  (67) Dr  Unrealized FX Gain   1.43 USD
  (68) Cr  EUR Omnibus          1.43 USD

  Net unrealized from step 12: +0.52 − 1.43 = −0.91

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit                50               53.41
Trading                Debit       50                          4.50
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit       0.91                       0
                                 ────     ────     ─────    ─────
Totals                             50       50     58.41    58.41  ✓

  Out-of-band balances:
    EUR Omnibus     cumulative_reval = -3.59
    Trading         cumulative_reval = -4.50, accumulator = 57

  EUR Deposit (0 EUR, 0 USD):
    Fully closed. All EUR withdrawn, all revaluation unwound.

  Unrealized FX Gain (Dr 0.91):
    Again non-zero after a withdrawal, same mechanism as step 9. The
    subsequent revaluation will restore it.

  Book rate consistency: both withdrawals (steps 9 and 12) use book
  rate 1.076 — the reval-stripped rate. This is lower than the original
  historical rate (1.108) because the conversion at step 6 consumed
  EUR at the revalued rate (1.14), removing 57 USD for 50 EUR instead
  of the historical 55.40.


STEP 13 — Partial settlement (deliver 20 of 50 EUR to FX counterparty)

  EUR delivery (20 of 50):
  (69) Dr  EUR Omnibus         20 EUR
  (70) Cr  Trading             20 EUR

  Reverse proportional Trading revaluation (20/50 × (−4.50) = −1.80):
  (71) Dr  Trading              1.80 USD
  (72) Cr  Unrealized FX Gain   1.80 USD

  Unwind proportional omnibus revaluation (20/50 × (−3.59) = −1.44):
  (73) Dr  Unrealized FX Gain   1.44 USD
  (74) Cr  EUR Omnibus          1.44 USD

  Net unrealized from step 13: +1.80 − 1.44 = +0.36
  Cumulative unrealized: −0.91 + 0.36 = −0.55

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit                30               54.85
Trading                Debit       30                          2.70
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit       0.55                       0
                                 ────     ────     ─────    ─────
Totals                             30       30     58.05    58.05  ✓

  Out-of-band balances:
    EUR Omnibus     cumulative_reval = -2.15
    Trading         cumulative_reval = -2.70, accumulator = 34.20

  EUR Omnibus (Cr 30 EUR, Cr 54.85 USD):
    Only 30 EUR remain at the correspondent (50 − 20 delivered). But
    the USD balance is 54.85 — far above fair value at any recent rate
    (30 × 1.05 = 31.50). This is because settlement delivers EUR but
    does not transfer USD book value out of Omnibus. The 54.85 includes
    orphaned USD from the 20 EUR already delivered, plus the book value
    of the remaining 30 EUR.

  Trading (Dr 30 EUR, Cr 2.70 USD):
    30 EUR remain in the trading position. The accumulator was
    proportionally reduced: 57 × (30/50) = 34.20. Cumulative reval:
    −4.50 + 1.80 reversed = −2.70.

  Unrealized FX Gain (Dr 0.55):
    Still non-zero — the partial settlement's reval unwinds (Trading
    +1.80 vs Omnibus −1.44) didn't fully cancel, adding +0.36 to the
    existing −0.91 gap from the withdrawal.

  MODEL ARTIFACT: Partial settlement does not transfer USD book value
  out of Omnibus — it only moves EUR. Compare with withdrawal (steps 9,
  12), which includes a USD book value transfer leg. This causes the
  Omnibus USD balance (54.85) to become disconnected from its EUR
  balance (30), inflating the USD side with orphaned book value from
  the 20 EUR already delivered. In a complete model with a Customer USD
  Deposit account, the conversion at step 6 would have credited that
  account with the customer's USD entitlement, and the Omnibus would
  only carry USD proportional to its EUR balance. The settlement
  template should either transfer proportional USD book value to the
  customer's account, or the model should separate orphaned residual
  from EUR-backed book value before revaluation runs.


STEP 14 — Revaluation (rate → 1.02)

  Only Omnibus and Trading have EUR positions; Deposit is closed.

  (75) Dr  EUR Omnibus         24.25 USD
  (76) Cr  Unrealized FX Gain  24.25 USD
  (77) Dr  Unrealized FX Gain   0.90 USD
  (78) Cr  Trading              0.90 USD

  Net unrealized from step 14: +24.25 − 0.90 = +23.35
  Cumulative unrealized: −0.55 + 23.35 = +22.80

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit                30               30.60
Trading                Debit       30                          3.60
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                 22.80
                                 ────     ────     ─────    ─────
Totals                             30       30     57.50    57.50  ✓

  Out-of-band balances:
    EUR Omnibus     cumulative_reval = -26.40
    Trading         cumulative_reval = -3.60, accumulator = 34.20

  Unrealized FX Gain (Cr 22.80) — MODEL ARTIFACT:
    This massive balance is NOT a real unrealized FX gain. The bank has
    zero net EUR exposure (Trading 30 − Omnibus 30 = 0), so the true
    economic unrealized should be near zero.

    The 22.80 arises because the revaluation delta method adjusts
    Omnibus from its inflated USD balance (54.85) to fair value (30.60),
    posting −24.25, while Trading only adjusts by −0.90. The asymmetry
    exists because Omnibus carries orphaned USD book value from the
    partial settlement (see step 13 note), while Trading does not.

    In a complete model with a Customer USD Deposit account, the
    Omnibus USD would only reflect the book value of its remaining
    30 EUR (~32 USD), and the revaluation adjustment would be small
    (~1.40), producing a near-zero net unrealized consistent with the
    bank's zero EUR exposure.

    The 22.80 is self-correcting — it fully unwinds on final settlement
    (step 15) — but it would produce misleading intermediate financial
    statements if reported as-is.

  EUR Omnibus (Cr 30 EUR, Cr 30.60 USD):
    Now at fair value (30 × 1.02 = 30.60). The delta method adjustment
    of −24.25 brought it from the bloated 54.85 down to fair value.

  Trading (Dr 30 EUR, Cr 3.60 USD):
    30 EUR at fair value 30.60 (30 × 1.02). Accumulator 34.20,
    cumulative reval −2.70 − 0.90 = −3.60. Ledger balance −3.60 ✓


STEP 15 — Settle remaining conversion (deliver 30 EUR to FX counterparty)

  EUR delivery:
  (79) Dr  EUR Omnibus         30 EUR
  (80) Cr  Trading             30 EUR

  Reverse Trading revaluation (position closed — cumulative reval −3.60):
  (81) Dr  Trading              3.60 USD
  (82) Cr  Unrealized FX Gain   3.60 USD

  Unwind remaining omnibus revaluation (30/30 × (−26.40) = −26.40):
  (83) Dr  Unrealized FX Gain  26.40 USD
  (84) Cr  EUR Omnibus         26.40 USD

  Net unrealized from step 15: +3.60 − 26.40 = −22.80
  Cumulative unrealized: +22.80 − 22.80 = 0  ✓ (restored)

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit        0                57
Trading                Debit        0                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                              0        0     57.50    57.50  ✓

  Out-of-band balances:
    (none)

  EUR Omnibus (0 EUR, Cr 57 USD):
    All EUR delivered (100 deposited − 30 withdrawn − 20 withdrawn −
    20 settled − 30 settled = 0). The Cr 57 USD is the orphaned book
    value: the customer gave up 50 EUR worth 57 USD (at the revalued
    ledger rate 1.14) in the conversion and should have received USD
    in return. This residual is the customer's unmodeled USD
    entitlement — the scenario does not include a Customer USD Deposit
    account.

    Compare to the no-intermediate-reval case: the residual would be
    55.40 (50 × 1.108 historical rate). The extra 1.60 is exactly
    the realized G/L reduction (2.10 − 0.50 = 1.60).

  Trading (0 EUR, 0 USD):
    Fully closed. EUR delivered to counterparty, mark-to-market
    reversed. The bank's gain was locked in at the conversion rate
    (1.15), not any revaluation rate.

  USD Cash (Dr 57.50):
    Unchanged throughout. The 57.50 USD from the FX sale is the only
    real cash the bank holds.

  Realized FX Gain (Cr 0.50):
    Unchanged. Total realized = 0.50 (sold 50 EUR at 1.15, book cost
    at revalued ledger rate 1.14). The realized gain is smaller than
    the historical spread (2.10) because revaluation before the
    conversion inflated the "book cost" from 55.40 to 57.

  Unrealized FX Gain (0):
    The artifact 22.80 from step 14 fully unwound. The Omnibus reval
    unwind (−26.40) absorbed both the orphaned book value and the
    reval adjustments. The Trading reval unwind (+3.60) was small by
    comparison. Net effect: −22.80, exactly cancelling the prior
    balance. The self-correcting nature confirms this is a temporary
    model artifact, not a permanent accounting error.

  USD Cash (Dr 57.50) = Omnibus residual (Cr 57) + Realized (Cr 0.50):
    The bank holds 57.50 USD. Of that, 57 is the customer's converted
    principal (book value of 50 EUR at revalued rate 1.14) and 0.50 is
    the bank's profit (conversion spread: 1.15 − 1.14 = 0.01 per EUR
    × 50 EUR = 0.50). Total = 57.50. Identical economic outcome to
    the no-reval case (55.40 + 2.10 = 57.50).


STEP 16 — Revaluation (rate → 0.98)

  No entries — all EUR balances are zero.

                                       EUR                USD
Account                Normal     Dr       Cr        Dr       Cr
─────────────────────  ──────    ────     ────     ─────    ─────
EUR Deposit            Debit        0                  0
EUR Omnibus            Credit        0                57
Trading                Debit        0                  0
USD Cash               Debit                         57.50
Realized FX Gain       Credit                                  0.50
Unrealized FX Gain     Credit                                  0
                                 ────     ────     ─────    ─────
Totals                              0        0     57.50    57.50  ✓

  Out-of-band balances:
    (none)

  Revaluation is purely a function of open EUR positions. Once
  everything is settled and withdrawn, there is nothing to mark to
  market — the revaluation is a no-op regardless of the rate.
```

## Design observations

1. **Revaluation before conversion contaminates the book rate.** The conversion at step 6 uses the ledger rate (1.14) rather than the historical blended rate (1.108) because Group A uses the ledger USD balance as the book value source. The revaluation at step 5 inflated the ledger USD balance from 108.40 to 114, so the conversion sees a higher "book cost" and reports a smaller realized gain (0.50 vs 2.10). The total economic gain is unchanged (0.50 realized + 1.60 in Omnibus residual = 2.10), but the classification between realized and unrealized/residual is path-dependent on revaluation timing. **If realized G/L must always reflect the spread between the conversion rate and the original historical cost, the conversion template must use the accumulator (or an explicit original-book-value parameter) rather than the current ledger balance.**

2. **Omnibus must be revalued.** The Omnibus is a credit-normal EUR liability. EUR appreciation increases it (unrealized loss for the bank); EUR depreciation decreases it (unrealized gain). Without Omnibus revaluation, the system incorrectly reports non-zero unrealized gains even when net EUR exposure is zero.

3. **Withdrawal unwinds revaluation, does not realize it.** A withdrawal returns EUR to the customer — it is not a market transaction. The proportional revaluation on both the Deposit (asset) and Omnibus (liability) is reversed. In the simple case (no intermediate revaluations), the two unwinds cancel. With intermediate revaluations at different EUR balance levels (steps 9 and 12), the unwinds produce a temporary non-zero net unrealized (−0.96 and −0.91) because the deposit and omnibus have different proportional reval amounts. The subsequent revaluation restores net unrealized to zero.

4. **Net EUR exposure determines net unrealized — with a caveat.** At every revaluation step, Deposit Dr + Trading Dr − Omnibus Cr = 0 net EUR. In a complete model, net unrealized would therefore be zero after revaluation. However, the current model breaks this invariant after partial settlement (step 14: Cr 22.80 despite zero net EUR exposure) because the Omnibus USD balance becomes disconnected from its EUR balance (see observation #6). The invariant holds correctly for all revaluation steps that are not preceded by a partial settlement without intervening revaluation.

5. **Settlement reverses mark-to-market.** When the Trading position closes via delivery, the revaluation is reversed — not reclassified to realized. The bank sold EUR at 1.15; the 9 subsequent rate movements are irrelevant to the bank's gain. The only realized gain is the conversion spread (0.50 in this scenario, or 2.10 without prior revaluation).

6. **Partial settlement produces a spurious large unrealized balance (model artifact).** Settlement delivers EUR from Omnibus but does not transfer USD book value out — unlike withdrawal, which includes a USD book value transfer leg. After the partial settlement at step 13 (20 of 50 EUR), Omnibus retains 54.85 USD for only 30 EUR (effective rate 1.83, far above any market rate). The subsequent revaluation at step 14 adjusts Omnibus from 54.85 to fair value 30.60, producing an Unrealized FX Gain of Cr 22.80 — despite the bank having zero net EUR exposure. This is a **model artifact**, not a real FX gain. The revaluation correctly applies the delta method, but the Omnibus USD is inflated by orphaned book value from the settled EUR. In a complete model with a Customer USD Deposit account, the Omnibus would only carry USD proportional to its EUR balance, and the unrealized would remain near zero. The artifact is self-correcting (unwinds on final settlement at step 15), but would produce misleading intermediate financial statements. **The settlement template needs a USD book value transfer leg (analogous to withdrawal) or the model needs to separate orphaned residual from EUR-backed book value before revaluation.**

7. **Omnibus USD residual reveals unmodeled account and absorbs reval-shifted book value.** After settlement, the Omnibus retains Cr 57 USD with no EUR backing. This is the customer's USD entitlement from the conversion. In a no-reval scenario, this would be 55.40 (50 × 1.108 historical rate). The extra 1.60 is exactly the realized G/L reduction (2.10 − 0.50). The residual represents whatever "book value" the conversion consumed from the deposit — if that book value was inflated by revaluation, the residual is correspondingly larger.

8. **Two book value sources.** Regular foreign-currency accounts (EUR Deposit, EUR Omnibus) get their book value from the Group A ledger USD balance. The trading account gets its book value from the position accumulator — its ledger USD balance is 0 after realized G/L clearing, so the ledger balance cannot serve as book value for revaluation. The SPEC's revaluation process (Component 5) documents this exception: the revaluation job reads `current_book_value` from the accumulator for the Trading account instead of from the ledger balance.

9. **Book value leg on conversions.** The conversion template needs a third leg (entries ㉓-㉔) to transfer the proportional USD book value from the source account to the trading account. This requires a `source_book_value` parameter computed by the orchestrator from the source account's ledger USD balance before posting.

10. **Position accumulator survives Group A.** Group A eliminates the need for external book value tracking on all regular accounts, but the trading account still needs the position accumulator because its ledger USD balance gets zeroed by realized G/L clearing.

11. **Consecutive revaluations demonstrate delta method correctness.** Steps 2→3 (1.08 → 1.06), 7→8 (1.18 → 1.20), and 10→11 (1.22 → 1.05) show back-to-back revaluations. Each posts only the incremental delta from the previous state. Steps 2→3 are particularly illustrative: two consecutive revaluations on a single 60 EUR deposit each post exactly −1.20 USD adjustment (60 × 0.02 = 1.20), confirming that the delta method computes incremental changes from the current state regardless of the original booking rate. Running revaluation twice at the same rate produces a zero adjustment on the second run (idempotent).

12. **Adverse rate movement inverts asset/liability reval directions.** When EUR depreciates sharply (step 11: 1.22 → 1.05), asset revaluations produce losses (Deposit −3.40, Trading −8.50) and liability revaluations produce gains (Omnibus +11.90) — the inverse of the appreciation steps. The net remains zero because net EUR exposure hasn't changed. The Trading account's USD balance goes negative (credit on a debit-normal account), reflecting a position fair value (52.50) below book cost (57).

13. **Path independence of total economic outcome.** Despite 9 revaluations at 8 different rates, the final trial balance's total economic outcome (57.50 USD) is identical to what it would be with no revaluation, or with any other intermediate rates. However, the split between realized gain and Omnibus residual IS path-dependent — revaluation before conversion shifts gain from realized (0.50) to residual (57 vs 55.40). The final state depends on the original booking rates (1.10, 1.12), the conversion rate (1.15), and whether revaluation occurred before conversion.

14. **Single vs split Unrealized accounts.** The SPEC specifies separate Unrealized FX Gain (6100) and Unrealized FX Loss (6200) accounts. This walkthrough uses a single account for clarity, since the net is always zero after revaluation in this scenario. In production, splitting by direction enables separate reporting of unrealized gains and losses as required by IAS 21 financial statement presentation.

15. **Blended book rate shifts with revaluation vintage.** The original historical blended rate is 1.108 (60 EUR at 1.10 + 40 EUR at 1.12). After revaluations at 1.08 and 1.06 before the second deposit, the ledger blended rate drops to 1.084 (108.40/100). After revaluation at 1.14, it rises to 1.14 (114/100). The conversion uses whichever rate the ledger shows at the time. After conversion, the reval-stripped book rate for the remaining 50 EUR is 1.076 — lower than the historical 1.108 because the conversion consumed USD at the revalued rate (1.14), removing 57 USD for 50 EUR instead of the historical 55.40. Both withdrawals (steps 9 and 12) use this distorted rate.

16. **Post-settlement revaluation is a no-op.** Step 16 produces zero entries because all EUR balances are zero. Revaluation is purely a function of open EUR positions — once everything is settled and withdrawn, there is nothing to mark to market.

17. **Withdrawal entries are spot-rate-independent.** Steps 9 and 12 show withdrawals using book value and proportional reval unwind. Post-withdrawal balances reflect the last reval rate, not the current spot. The gap between the account balance and current fair value is an unrecognized intra-period rate change captured by the next revaluation run.

## Templates used

| Step | Template | Module |
|---|---|---|
| 1, 4 — Deposit | Deposit template (with Group A dual-currency entries) | Deposit layer |
| 6 — Conversion | `FIAT_FX_CONVERSION_VIA_TRADING` (with book value leg) | Phase 3 |
| 6 — Realized G/L | `REALIZED_FX_GAIN_LOSS` | Phase 3 |
| 2, 3, 5, 7, 8, 10, 11, 14, 16 — Revaluation | Revaluation template (Deposit + Omnibus + Trading, delta method) | Phase 4 |
| 9, 12 — Withdrawal | Withdrawal template (with reval unwind on both Deposit and Omnibus) | Deposit layer |
| 13, 15 — Settlement | Settlement template (EUR delivery + reval reversal) | Phase 3 |

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

1. **Revaluation template** (Steps 2, 3, 5, 7, 8, 10, 11, 14, 16) — The delta-method mark-to-market template that posts `Dr/Cr account` vs `Cr/Dr Unrealized FX Gain` for each foreign-currency account. This is the core of Phase 4. Needs to handle Deposit (asset), Omnibus (liability), and Trading (where book value comes from the accumulator, not ledger balance).

2. **Settlement template** (Steps 13, 15) — EUR delivery from Omnibus to Trading (`Dr Omnibus / Cr Trading` in EUR), plus reversal of the Trading account's revaluation and unwind of the Omnibus revaluation. Closes the trading position.

3. **Withdrawal reval-unwind entries** (Steps 9, 12) — Withdrawals need to unwind proportional revaluation on both the Deposit and Omnibus sides before transferring at book value. This likely lives in the Deposit layer's withdrawal template rather than the FX module, but the FX module needs to either provide it or coordinate with the deposit layer to ensure it happens.

### What's wrong with what we have

**`FIAT_FX_CONVERSION_VIA_TRADING` is missing the book-value leg.** The walkthrough's Step 6 has three pairs of entries:

- Entries ㉑-㉒: Source currency movement (`Dr Trading / Cr EUR Deposit` — 50 EUR) — **we have this**
- Entries ㉕-㉖: Target currency movement (`Dr USD Cash / Cr Trading` — 57.50 USD) — **we have this**
- Entries ㉓-㉔: **Book value transfer** (`Dr Trading / Cr EUR Deposit` — 57 USD) — **MISSING**

The walkthrough's observation #9 explicitly calls this out: *"The conversion template needs a third leg (entries ㉓-㉔) to transfer the proportional USD book value from the source account to the trading account."* Without this leg, the Trading account's USD balance won't reflect the book cost of the acquired EUR, and the subsequent realized G/L clearing entry won't work correctly (it needs Trading's USD balance to be non-zero so that the G/L entry zeros it out).

The current template only moves `source_amount` in `source_currency` and `target_amount` in `target_currency` — it has no functional-currency (USD) book-value transfer between source and trading accounts. This would need a `source_book_value` parameter computed by the orchestrator from the source account's current USD ledger balance.

### Summary

- **3 templates present**, 1 of which (rounding) is a utility not in the walkthrough
- **2–3 templates missing**: revaluation, settlement, and withdrawal reval-unwind coordination
- **1 template wrong**: the conversion template is missing the critical book-value leg in functional currency, which breaks the Selinger accumulator flow

