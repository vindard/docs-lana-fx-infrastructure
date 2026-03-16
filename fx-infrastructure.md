# Workstream 2: FX Infrastructure

## Problem Statement

Lana-bank has no FX infrastructure beyond `PriceOfOneBTC` — a single struct that converts between BTC and USD using a spot rate. There is no rate storage, no trading accounts, no gain/loss tracking, no revaluation process, and no support for historical rates. Any multicurrency expansion requires building this infrastructure from scratch.

## Current State

### Price Module (`core/price/`)

```rust
// The only conversion primitive in the system
struct PriceOfOneBTC(UsdCents);

impl PriceOfOneBTC {
    // USD → BTC: rounds UP (less favorable)
    fn cents_to_sats_round_up(&self, cents: UsdCents) -> Satoshis {
        let btc = cents.to_usd() / self.to_usd();
        Satoshis::try_from_btc(btc.round_dp(8, RoundingStrategy::AwayFromZero))
    }

    // BTC → USD: rounds DOWN (less favorable)
    fn sats_to_cents_round_down(&self, sats: Satoshis) -> UsdCents {
        let usd = sats.to_btc() * self.to_usd();
        UsdCents::try_from_usd(usd.round_dp(2, RoundingStrategy::ToZero))
    }
}
```

**Limitations:**
- Only BTC↔USD pair
- No rate history — uses current spot rate only
- No record of which rate was used for a given transaction
- Rate source: Bitfinex (single provider, no fallback)
- Rounding direction is hardcoded (conservative), not configurable per use case

### What's Missing

| Component | Status |
|-----------|--------|
| Exchange rate storage (historical) | Not implemented |
| Rate stored per transaction | Not implemented |
| Trading accounts (Selinger model) | Not implemented |
| Unrealized FX gain/loss accounts | Not implemented |
| Realized FX gain/loss accounts | Not implemented |
| Period-end revaluation batch | Not implemented |
| Auto-reversal of revaluation entries | Not implemented |
| Multi-pair rate service | Not implemented |
| Collateral mark-to-market (accounting entries) | Not implemented (LTV calc exists but doesn't post entries) |

## Reference: The Three Accounting Concepts

### IAS 21 / ASC 830 Framework

| Concept | Definition | Lana Context |
|---------|-----------|--------------|
| **Transaction currency** | Currency in which a transaction occurs | USD for loans, BTC for collateral |
| **Functional currency** | Currency of the entity's primary economic environment | USD (the platform operates in USD) |
| **Presentation currency** | Currency financial statements are presented in | USD |

Under IAS 21:
- Transactions recorded at **spot rate** on transaction date
- Monetary items revalued at **closing rate** at each reporting date
- Differences go to **profit or loss** (for monetary items)
- Non-monetary items remain at **historical rate**

## Component 1: Exchange Rate Storage

### Schema

```sql
CREATE TABLE exchange_rates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency   VARCHAR(5) NOT NULL,       -- 'BTC', 'USD', 'EUR'
    to_currency     VARCHAR(5) NOT NULL,
    rate            DECIMAL(18,10) NOT NULL,    -- high precision for rate itself
    rate_timestamp  TIMESTAMP WITH TIME ZONE NOT NULL,
    rate_type       VARCHAR(20) NOT NULL,       -- 'SPOT', 'CLOSING', 'AVERAGE'
    source          VARCHAR(50) NOT NULL,       -- 'BITFINEX', 'ECB', 'MANUAL'
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    UNIQUE(from_currency, to_currency, rate_timestamp, rate_type)
);

CREATE INDEX idx_exchange_rates_lookup
    ON exchange_rates(from_currency, to_currency, rate_type, rate_timestamp DESC);
```

### Rate Types

| Type | Purpose | Frequency |
|------|---------|-----------|
| `SPOT` | Transaction recording | Real-time / on-demand |
| `CLOSING` | Period-end revaluation of monetary items | Daily (end of business) |
| `AVERAGE` | Income statement translation (consolidation) | Monthly |

### Rate Lookup Strategy

```rust
// Fetch the most recent rate at or before a given timestamp
async fn get_rate(
    &self,
    from: CurrencyCode,
    to: CurrencyCode,
    at: DateTime<Utc>,
    rate_type: RateType,
) -> Result<ExchangeRate, PriceError> {
    // Try direct pair
    if let Some(rate) = self.repo.find_rate(from, to, at, rate_type).await? {
        return Ok(rate);
    }
    // Try inverse
    if let Some(rate) = self.repo.find_rate(to, from, at, rate_type).await? {
        return Ok(rate.invert());
    }
    // Try cross-rate via USD (triangulation)
    if from != USD && to != USD {
        let from_usd = self.repo.find_rate(from, USD, at, rate_type).await?;
        let to_usd = self.repo.find_rate(to, USD, at, rate_type).await?;
        if let (Some(a), Some(b)) = (from_usd, to_usd) {
            return Ok(a.cross(b));
        }
    }
    Err(PriceError::RateNotFound { from, to, at })
}
```

### BTC-Specific Considerations

- BTC rates need **intraday granularity** (hourly or 15-minute for LTV monitoring)
- Store BTC rates with higher precision: `DECIMAL(18,10)` minimum
- Multiple sources for resilience (Bitfinex, Coinbase, Kraken) with median/VWAP aggregation
- The existing `PriceOfOneBTC` price feed becomes a rate source that writes to this table

## Component 2: Rate-Per-Transaction Recording

Every cross-currency journal entry must record the rate used. Two approaches:

### Approach A: Rate as Template Parameter

Store the rate in the CALA transaction metadata:

```rust
struct CrossCurrencyEntryParams {
    pub source_amount: Decimal,
    pub source_currency: CurrencyCode,
    pub target_amount: Decimal,
    pub target_currency: CurrencyCode,
    pub exchange_rate: Decimal,         // rate used for conversion
    pub rate_timestamp: DateTime<Utc>,  // when the rate was observed
}
```

The template creates entries in both currencies, and the rate is stored as transaction metadata for audit trail.

### Approach B: Rate as Entry Metadata

CALA entries support metadata. Store the rate on each entry:

```json
{
  "exchange_rate": "50000.00",
  "rate_source": "BITFINEX",
  "rate_timestamp": "2025-01-15T14:30:00Z"
}
```

**Recommended: Approach A** — the rate is a property of the transaction, not individual entries.

## Component 3: Trading Accounts (Selinger Model)

### Concept

A **trading account** is an intermediary account that all currency conversions flow through. It absorbs exchange rate differences and its running balance represents the cumulative unrealized FX gain/loss.

### Chart of Accounts Additions

```
EQUITY / FX
  3200  FX Trading Account           -- intermediary for all conversions

REVENUE
  4200  Realized FX Gain             -- closed FX positions (permanent)

EXPENSES
  5100  Realized FX Loss             -- closed FX positions (permanent)

OTHER INCOME / EXPENSE
  6100  Unrealized FX Gain           -- period-end revaluation (auto-reversing)
  6200  Unrealized FX Loss           -- period-end revaluation (auto-reversing)
```

### How Conversions Flow Through the Trading Account

**Example: Converting USD 50,000 to BTC at rate $50,000/BTC = 1 BTC**

```
Entry 1 (USD side):
  Dr  FX Trading Account       50,000 USD
    Cr  USD Cash                         50,000 USD

Entry 2 (BTC side):
  Dr  BTC Holdings              1.00000000 BTC
    Cr  FX Trading Account               1.00000000 BTC
```

Trading account now holds: `+50,000 USD` and `-1 BTC`. At current rate ($50,000), net value = 0.

**If BTC rises to $55,000:**
Trading account: `+50,000 USD` and `-1 BTC` (= -$55,000 equivalent).
Net value = 50,000 - 55,000 = **-$5,000** = unrealized gain of $5,000 (credit balance in an equity account = gain).

**If BTC drops to $45,000:**
Net value = 50,000 - 45,000 = **+$5,000** = unrealized loss of $5,000.

### CALA Template: FX Conversion via Trading Account

```rust
// Template: fx_buy_via_trading
entries: [
    // Leg 1: Source currency out
    Entry {
        account: "params.trading_account_id",
        units: "params.source_amount",
        currency: "params.source_currency",
        direction: DEBIT,
        layer: SETTLED,
    },
    Entry {
        account: "params.source_account_id",
        units: "params.source_amount",
        currency: "params.source_currency",
        direction: CREDIT,
        layer: SETTLED,
    },
    // Leg 2: Target currency in
    Entry {
        account: "params.target_account_id",
        units: "params.target_amount",
        currency: "params.target_currency",
        direction: DEBIT,
        layer: SETTLED,
    },
    Entry {
        account: "params.trading_account_id",
        units: "params.target_amount",
        currency: "params.target_currency",
        direction: CREDIT,
        layer: SETTLED,
    },
]
```

### Alternative: Direct Gain/Loss Booking (No Trading Account)

Some systems skip trading accounts and post gain/loss directly:

```
Dr  BTC Holdings              1 BTC    [= $50,000]
  Cr  USD Cash                          $50,000

// On sale at $55,000:
Dr  USD Cash                   $55,000
  Cr  BTC Holdings                      1 BTC    [= $50,000 cost basis]
  Cr  Realized FX Gain                  $5,000
```

This is simpler but requires tracking cost basis per lot (FIFO/LIFO/specific identification). Trading accounts avoid this complexity by letting the balance do the tracking.

## Component 4: Period-End Revaluation

### The Revaluation Process

```
DAILY or MONTHLY (configurable per account type):

1. IDENTIFY candidates
   - All accounts with non-functional-currency balances
   - All open foreign-currency receivables/payables
   - All foreign-currency cash/bank accounts
   - BTC collateral accounts

2. FETCH closing rates
   - Get CLOSING rate for each currency pair from exchange_rates table
   - If no closing rate, fall back to most recent SPOT rate

3. CALCULATE adjustments
   For each (account, currency):
     foreign_balance = sum of entries in foreign currency
     current_book_value = current balance in functional currency (USD)
     new_value = foreign_balance × closing_rate
     adjustment = new_value - current_book_value

4. POST revaluation entries
   If adjustment > 0 (gain):
     Dr  Foreign Currency Account     adjustment USD
       Cr  Unrealized FX Gain                    adjustment USD

   If adjustment < 0 (loss):
     Dr  Unrealized FX Loss           |adjustment| USD
       Cr  Foreign Currency Account              |adjustment| USD

5. SCHEDULE auto-reversal
   Create reversing entries dated first day of next period

6. LOG results
   Store revaluation report: account, currency, old value, new value, adjustment, rate used
```

### Auto-Reversal Pattern

**Why reverse?** So that when a position is eventually settled (realized), the realized gain/loss captures the **full movement from original transaction date**, not just from the last revaluation.

```
Feb 28 (revaluation):
  Dr  BTC Holdings              $5,000 USD  (revaluation adjustment)
    Cr  Unrealized FX Gain               $5,000 USD

Mar 1 (auto-reversal):
  Dr  Unrealized FX Gain        $5,000 USD
    Cr  BTC Holdings                     $5,000 USD

Mar 15 (actual sale — realized gain calculated from original cost):
  Dr  USD Cash                  $55,000
    Cr  BTC Holdings                     1 BTC [= $50,000 original cost]
    Cr  Realized FX Gain                 $5,000
```

Without reversal, the Mar 15 entry would only show the gain since Feb 28, missing the Feb portion.

### Implementation in Lana

This would be a **Dagster job** (`core/price/` or a new `core/fx/` module):

```rust
// Pseudocode for the revaluation job
async fn run_fx_revaluation(
    &self,
    revaluation_date: NaiveDate,
    rate_service: &ExchangeRateService,
    accounting: &AccountingService,
) -> Result<RevaluationReport, FxError> {
    let closing_rates = rate_service
        .get_closing_rates(revaluation_date)
        .await?;

    let foreign_accounts = accounting
        .find_accounts_with_foreign_currency_balances()
        .await?;

    let mut entries = Vec::new();

    for (account, currency, foreign_balance) in foreign_accounts {
        let rate = closing_rates.get(currency, self.functional_currency)?;
        let new_value = foreign_balance * rate;
        let current_book_value = accounting
            .get_functional_currency_balance(account)
            .await?;
        let adjustment = new_value - current_book_value;

        if !adjustment.is_zero() {
            entries.push(RevaluationEntry {
                account,
                currency,
                adjustment,
                rate_used: rate,
                auto_reverse_date: first_day_of_next_period(revaluation_date),
            });
        }
    }

    let report = self.post_revaluation_entries(entries).await?;
    Ok(report)
}
```

## Component 5: BTC Collateral Accounting

### The Agent Relationship

The platform holds BTC as **agent**, not as owner. This means:
- Price movements affect both the asset (collateral held) and liability (obligation to return) equally
- **No P&L impact** for the platform from BTC price changes
- The platform's revenue is interest income, not crypto appreciation
- Revaluation is still needed for LTV monitoring and regulatory reporting

### Collateral Entry Flow

**A. Receiving BTC Collateral**

*Borrower deposits 2 BTC for $80,000 loan. BTC @ $50,000.*

```
Dr  BTC Collateral Held         2.00000000 BTC   [= $100,000]
  Cr  Collateral Obligation              2.00000000 BTC   [= $100,000]

Dr  Loans Outstanding           $80,000
  Cr  USD Cash                           $80,000
```

Initial LTV = 80,000 / 100,000 = 80%.

**B. Daily Mark-to-Market**

*BTC drops to $42,000. New collateral value = $84,000.*

```
Dr  Collateral Obligation       $16,000   (decrease in liability)
  Cr  BTC Collateral Held               $16,000   (decrease in asset)
```

Both sides move together — no P&L entry. New LTV = 80,000 / 84,000 = 95.2%.

Note: The BTC quantity stays at 2.00000000 BTC. Only the USD valuation changes. This is a USD-denominated revaluation entry, not a BTC entry.

**C. Liquidation (LTV Breach)**

*BTC @ $38,000. LTV = 105%. Liquidate 1.5 BTC.*

```
// Remove BTC from collateral
Dr  Collateral Obligation       1.50000000 BTC   [= $57,000]
  Cr  BTC Collateral Held               1.50000000 BTC   [= $57,000]

// Record sale proceeds
Dr  USD Cash                    $57,000
  Cr  Liquidation Proceeds              $57,000

// Apply to loan
Dr  Liquidation Proceeds        $57,000
  Cr  Loans Outstanding                 $57,000
```

Remaining: 0.5 BTC collateral, $23,000 loan.

**D. Returning Collateral on Repayment**

*Loan fully repaid. Return 2 BTC. BTC @ $60,000.*

```
// Receive loan repayment
Dr  USD Cash                    $80,000
  Cr  Loans Outstanding                 $80,000

// Return collateral
Dr  Collateral Obligation       2.00000000 BTC   [= $120,000]
  Cr  BTC Collateral Held               2.00000000 BTC   [= $120,000]
```

Both accounts zero out. No gain/loss for the platform.

### Collateral Revaluation vs General FX Revaluation

| Aspect | General FX Revaluation | Collateral Revaluation |
|--------|----------------------|----------------------|
| P&L impact | Yes — unrealized gain/loss | No — both sides of balance sheet move |
| Frequency | Daily or monthly | Per-event (price trigger) or daily |
| Auto-reversal | Yes | Not needed (cumulative) |
| Purpose | Financial reporting | LTV monitoring + reporting |
| Accounts affected | Asset OR liability | Asset AND liability equally |

### Collateral Revaluation Template

```rust
// Template: collateral_revalue
// Posts a USD-only entry adjusting both sides
params: [
    { name: "collateral_account_id", type: UUID },
    { name: "obligation_account_id", type: UUID },
    { name: "adjustment_amount", type: DECIMAL },  // positive = value increase
]

entries: [
    // If positive (value increase): DR collateral, CR obligation
    // If negative (value decrease): DR obligation, CR collateral
    Entry {
        account: "params.collateral_account_id",
        units: "params.adjustment_amount",
        currency: "'USD'",
        direction: if adjustment > 0 { DEBIT } else { CREDIT },
        layer: SETTLED,
    },
    Entry {
        account: "params.obligation_account_id",
        units: "decimal.Abs(params.adjustment_amount)",
        currency: "'USD'",
        direction: if adjustment > 0 { CREDIT } else { DEBIT },
        layer: SETTLED,
    },
]
```

## Component 6: Revaluation Batch Job (Dagster)

### Job Design

```python
# dagster/lana/assets/fx_revaluation.py

@asset(
    partitions_def=DailyPartitionsDefinition(start_date="2025-01-01"),
    automation_condition=AutomationCondition.on_cron("0 0 * * *"),  # midnight daily
)
def fx_revaluation(context, lana_client: LanaClient):
    """
    Daily FX revaluation:
    1. Fetch closing rates for all active currency pairs
    2. Revalue all foreign-currency monetary balances
    3. Post adjustment entries (auto-reversing)
    4. Revalue BTC collateral (non-reversing, both sides)
    5. Check LTV thresholds and trigger margin calls
    """
    reval_date = context.partition_key

    # Step 1: Closing rates
    closing_rates = lana_client.get_closing_rates(reval_date)

    # Step 2: General FX revaluation (with auto-reversal)
    general_report = lana_client.revalue_foreign_currency_accounts(
        date=reval_date,
        rates=closing_rates,
        auto_reverse=True,
    )

    # Step 3: Collateral revaluation (no reversal, both sides move)
    collateral_report = lana_client.revalue_btc_collateral(
        date=reval_date,
        btc_usd_rate=closing_rates["BTC/USD"],
    )

    # Step 4: LTV check
    margin_calls = lana_client.check_ltv_thresholds(
        date=reval_date,
    )

    context.log.info(
        f"Revaluation complete: {general_report.adjustments_count} FX adjustments, "
        f"{collateral_report.facilities_revalued} collateral updates, "
        f"{len(margin_calls)} margin calls triggered"
    )

    return {
        "general_adjustments": general_report.total_adjustment,
        "collateral_revaluations": collateral_report.facilities_revalued,
        "margin_calls_triggered": len(margin_calls),
    }
```

### LTV Monitoring (Higher Frequency)

Separate from the daily accounting revaluation, LTV monitoring should run more frequently:

```python
@sensor(minimum_interval_seconds=900)  # every 15 minutes
def ltv_monitor(context, lana_client: LanaClient, price_feed: PriceFeed):
    """
    High-frequency LTV monitoring.
    Does NOT post accounting entries — only triggers alerts/margin calls.
    """
    current_btc_price = price_feed.get_spot("BTC", "USD")

    at_risk_facilities = lana_client.get_facilities_above_ltv_threshold(
        btc_price=current_btc_price,
        warning_threshold=0.85,
        margin_call_threshold=0.95,
    )

    for facility in at_risk_facilities:
        if facility.ltv >= 0.95:
            lana_client.trigger_margin_call(facility.id)
        elif facility.ltv >= 0.85:
            lana_client.send_ltv_warning(facility.id)
```

## Implementation Order

### Phase 1: Rate Storage (Foundation)
- Create `exchange_rates` table and migration
- Build `ExchangeRateService` with rate lookup (direct, inverse, cross-rate)
- Modify `PriceOfOneBTC` to write to the rate table as a source
- Store rate used on each cross-currency transaction (metadata)

### Phase 2: Chart of Accounts
- Add FX-specific accounts (trading, realized gain/loss, unrealized gain/loss)
- Create CALA account sets for FX reporting
- Add account-level currency designation

### Phase 3: Revaluation (Collateral First)
- Build collateral revaluation template (both-sides, no reversal)
- Create daily Dagster job for collateral mark-to-market
- Post USD-denominated adjustment entries
- This delivers immediate value for LTV monitoring accuracy

### Phase 4: General FX Revaluation
- Build general revaluation template (single-side, with auto-reversal)
- Extend Dagster job for all foreign-currency balances
- Implement auto-reversal mechanism
- Build revaluation report

### Phase 5: Trading Accounts
- Create trading account template for currency conversions
- Route all FX conversions through trading account
- Realized gain/loss posting on position closure

## Dependencies

- **Workstream 1 (Generic Money Type)**: Not a hard dependency — FX infrastructure can work with the current `UsdCents`/`Satoshis` types for BTC/USD. But supporting additional currency pairs requires the generic type.
- **CALA**: Transaction metadata support for storing rates. Template parameterization for currency (already supported but not used).
- **Dagster**: Job scheduling infrastructure already exists. New jobs follow existing patterns.
- **Price feeds**: Current Bitfinex integration needs to be extended to write closing rates to the rate table.
