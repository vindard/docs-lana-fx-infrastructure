# FX Operations

---

## Term: `currency translation`

> The result of applying an exchange rate to a specific amount to express it in the functional currency. A currency translation bundles three things: the exchange rate used, the original (foreign) amount, and the computed functional-currency equivalent.

**Example:** 60 EUR translated at 1.10 USD/EUR = 66 USD. The currency translation is the whole triple: (rate: 1.10, foreign amount: 60 EUR, functional equivalent: 66 USD).

**Why this term:** The codebase previously used `ReferenceRate` for this concept, which caused semantic collision with `ExchangeRate` — both had "rate" in the name but represented fundamentally different things. An exchange rate is a dimensionless ratio between two currencies. A currency translation is the recorded outcome of using that ratio on a concrete amount. Calling both "rates" obscured this distinction and made the API confusing to read (e.g. `find_spot_rate` vs `find_spot_exchange_rate` looked like duplicates until you checked the return types).

**Origin:** IAS 21 uses "foreign currency translation" as its formal term for this operation — converting foreign-currency amounts into the functional currency at a given rate for ledger recording purposes. This maps exactly to what the struct represents.

### Distinct from

- **Exchange Rate** — A ratio between two currencies at a point in time (e.g. 1.10 USD/EUR). Has no amount attached. An exchange rate is an input to a currency translation, not the currency translation itself.

- **Quote** — Conceptually close but carries a dimension of time and tentativeness. A quote is a rate offered *before* a transaction — forward-looking and potentially rejected. A currency translation is the recorded result *after* applying a rate — backward-looking and final. In FX desks, "we quoted 1.10" vs "we translated at 1.10" are different moments in a transaction's lifecycle.

- **Valuation** — Broader term for assessing worth. A revaluation adjusts a previously-translated amount to a new rate. The initial currency translation establishes the book value; subsequent valuations measure deviation from it. "Valuation" is correct but too general — it doesn't convey the currency-conversion specificity that "currency translation" does.

- **Conversion** — The actual exchange of one currency for another (e.g. selling EUR for USD through a trading account). A conversion changes what currency you hold. A currency translation only changes how you *express* what you hold — the underlying foreign-currency position is unchanged. In the SPEC, conversions flow through the Selinger trading account; currency translations are ledger entries on the same account in a second currency.

### Code mapping

| Before | After |
|--------|-------|
| `ReferenceRate` | `CurrencyTranslation` |
| `find_spot_rate(amount)` | `translate_at_spot(amount)` |
| `find_nearest_historical_rate(at, amount)` | `translate_at_nearest_historical(at, amount)` |
| `find_spot_exchange_rate()` | *(unchanged — this actually is a rate)* |
| `find_nearest_historical_exchange_rate(at)` | *(unchanged)* |
