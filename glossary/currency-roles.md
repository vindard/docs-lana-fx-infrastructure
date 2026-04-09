# Currency Terminology

Three distinct roles a currency can play in a multi-currency system. Every amount in the ledger exists in the context of one of these roles, and confusing them produces incorrect accounting entries.

---

## Term: `transaction currency`

> The currency in which a specific transaction is denominated. This is the currency the customer or counterparty actually deals in for that operation.

**Example:** A customer deposits 60 EUR. The transaction currency is EUR regardless of what currency the bank reports in.

**Why it matters:** The transaction currency determines which account sets and omnibus accounts are involved, and it's the currency of the "native" leg in dual-currency entries. It's a property of individual transactions, not of the entity — the same customer might deposit in EUR today and GBP tomorrow.

### Distinct from

- **Functional currency** — Transaction currency varies per transaction; functional currency is fixed for the entity. A EUR deposit and a GBP deposit both get translated to the same functional currency.

- **Source/target currency** — These are conversion terms (one currency exchanged for another). Transaction currency doesn't imply a conversion — a USD deposit into a USD-functional entity has a transaction currency but no conversion occurs.

---

## Term: `functional currency`

> The currency of the primary economic environment in which the entity operates. All foreign-currency amounts are ultimately [translated](currency-translation.md#term-currency-translation) into the functional currency for ledger recording and reporting. Configured per Lana instance.

**Example:** If functional currency is USD, then a 60 EUR deposit is translated to 66 USD at spot. The 66 USD is the functional-currency book value. Revaluation adjustments are computed against this functional-currency balance.

**Why it matters:** The functional currency is the anchor for the entire dual-currency entry design. Every foreign-currency entry carries a parallel functional-currency entry. The delta revaluation method computes adjustments as `(foreign_balance × closing_rate) - functional_currency_balance`. Getting the functional currency wrong means every revaluation, every book value, and every gain/loss calculation is wrong.

### Distinct from

- **Transaction currency** — Functional currency is an entity-level constant; transaction currency varies per operation. When they're the same (e.g. a USD deposit in a USD-functional entity), no translation is needed.

- **Presentation currency** — Functional currency is for internal accounting; presentation currency is for external reporting. They're often the same but don't have to be.

- **Base currency** — In exchange rate notation, "base" is a pair-relative concept (the denominator in a rate pair). Functional currency happens to be the base in most [currency translations](currency-translation.md#term-currency-translation), but "base" has no institutional meaning — it's just which side of the rate you're on.

---

## Term: `presentation currency`

> The currency in which financial statements are presented to external stakeholders. This can differ from the functional currency when the entity reports to a parent company or regulator in a different jurisdiction.

**Example:** A Lana instance operating in Europe might have EUR as its functional currency but present consolidated statements in USD for a US-based parent company. All EUR functional-currency balances would be translated to USD at the reporting date for presentation.

**Why it matters:** Presentation currency translation is an additional layer that sits on top of functional-currency financial statements rather than being embedded in day-to-day transaction recording. Included here to complete the IAS 21 framework and prevent confusion with functional currency.

### Distinct from

- **Functional currency** — Functional currency drives daily accounting (translations, revaluations, gain/loss). Presentation currency is a reporting-time transformation applied to already-completed functional-currency statements. You can change presentation currency without re-recording any transactions.

**IAS 21 relationship:** IAS 21 defines all three roles explicitly. Transaction → functional translation happens at transaction date using spot rates. Functional → presentation translation happens at reporting date using closing rates, with differences going to other comprehensive income (OCI) rather than P&L.

---

## Summary

| Role | Varies per | Determines |
|------|-----------|------------|
| Transaction | transaction | which omnibus, which account sets, native leg of dual-currency entries |
| Functional | entity/instance | book values, revaluation baselines, functional leg of dual-currency entries |
| Presentation | reporting context | how financial statements are denominated for external consumers |

---

## Informal terms to avoid as role labels

The following terms appear frequently in banking and accounting literature but map ambiguously to the three IAS 21 roles. They should not be used in code or specs when referring to a specific currency's role. Listed here so that when encountered externally, the intended meaning can be resolved to the correct IAS 21 term.

| Term | What it usually means | Why it's ambiguous as a role label |
|------|----------------------|-------------------|
| **Foreign currency** | Any currency that isn't the functional currency | Relative — EUR is "foreign" to a USD-functional entity but not to a EUR-functional one. Says nothing about which role the currency plays. |
| **Local currency** | Currency of the jurisdiction the entity operates in | Usually equals functional currency, but not necessarily. A US-owned subsidiary in Germany has EUR as local but might have USD as functional if its economic activity is USD-denominated. IAS 21 says functional *usually* equals local, but it's a determination not an assumption. |
| **Jurisdiction currency** | Same as local currency, with regulatory emphasis | Adds no precision over "local currency." Could refer to functional or presentation depending on whether the regulator requires operational or reporting compliance. |
| **Home currency** | Functional currency | Pure synonym, but informal and not used in any standard. |
| **Reporting currency** | Sometimes functional, sometimes presentation | The most dangerous one. Treasury desks often mean functional; consolidation teams often mean presentation. IAS 21 introduced the three-term framework specifically because "reporting currency" was causing confusion. |
| **Settlement currency** | Currency actually delivered when a transaction completes | Usually equals transaction currency, but can differ in FX workflows (e.g. CLS settlement). |
