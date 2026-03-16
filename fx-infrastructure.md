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
| Multi-source rate aggregation | Not implemented |
| Rate staleness / circuit breakers | Not implemented |
| Collateral mark-to-market (accounting entries) | Not implemented (LTV calc exists but doesn't post entries) |
| Cost basis / lot tracking for BTC | Not implemented |
| Segregation controls for custodied BTC | Not implemented |

## Accounting Framework

BTC and fiat currencies fall under fundamentally different accounting standards. This distinction governs every design decision in the FX infrastructure.

### Fiat FX: IAS 21 / ASC 830

IAS 21 (IFRS) and ASC 830 (US GAAP) govern the translation and reporting of foreign currency transactions and balances. These standards apply to **fiat-to-fiat** pairs (USD/EUR, USD/GBP, etc.).

| Concept | Definition | Lana Context |
|---------|-----------|--------------|
| **Transaction currency** | Currency in which a transaction occurs | EUR for a Euro-denominated loan |
| **Functional currency** | Currency of the entity's primary economic environment | USD (the platform operates in USD) |
| **Presentation currency** | Currency financial statements are presented in | USD |

Under IAS 21:
- Transactions recorded at **spot rate** on transaction date
- Monetary items revalued at **closing rate** at each reporting date
- Differences go to **profit or loss** (for monetary items)
- Non-monetary items remain at **historical rate**

This framework drives the auto-reversal pattern for period-end revaluation: unrealized gains/losses are booked and then reversed so that when a position settles, the realized gain/loss captures the full movement from the original transaction date.

### BTC: FASB ASU 2023-08 (Fair Value Through Net Income)

Bitcoin is **not** a foreign currency. Under FASB ASU 2023-08 (effective for fiscal years beginning after December 15, 2024), bitcoin and other qualifying crypto assets are classified as **intangible assets measured at fair value**, with fair value changes recognized through **net income** (P&L).

Key implications for Lana's FX infrastructure:

| Aspect | IAS 21 (Fiat FX) | ASU 2023-08 (BTC) |
|--------|-------------------|---------------------|
| Classification | Foreign currency | Intangible asset at fair value |
| Measurement | Spot/closing rate translation | Fair value through net income |
| Gain/loss recognition | Unrealized → OCI or P&L; realized on settlement | All fair value changes → P&L (no unrealized/realized distinction) |
| Period-end treatment | Revalue + auto-reverse | Cumulative fair value adjustment (no reversal) |
| Closest analogy | — | Trading securities under ASC 320 |

**The agent/custody exception:** When the platform holds BTC as agent (collateral on behalf of borrowers), both the asset (collateral held) and liability (obligation to return) move together with fair value changes. There is no P&L impact because the platform does not own the BTC. ASU 2023-08's P&L recognition applies only to BTC the platform **owns** (e.g., BTC received as fee income, BTC held in treasury).

## Component 1: Exchange Rate Storage

### Schema

```sql
CREATE TABLE exchange_rates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency   VARCHAR(5) NOT NULL,       -- 'BTC', 'USD', 'EUR'
    to_currency     VARCHAR(5) NOT NULL,
    rate            DECIMAL(18,10) NOT NULL,    -- high precision for rate itself
    rate_timestamp  TIMESTAMP WITH TIME ZONE NOT NULL,
    rate_type       VARCHAR(20) NOT NULL,       -- 'SPOT', 'CLOSING'
    source          VARCHAR(50) NOT NULL,       -- 'BITFINEX', 'COINBASE', 'ECB', 'MANUAL', 'AGGREGATED'
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

> **Note on AVERAGE rate type:** An `AVERAGE` rate type (monthly weighted average) is used in multi-entity consolidation scenarios where subsidiaries have different functional currencies (IAS 21.40). For a single-entity USD platform, this is not needed. It should be introduced if/when Lana requires consolidated financial statements across entities with different functional currencies.

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
- Multiple sources for resilience (see Component 2: Multi-Source Rate Aggregation)
- The existing `PriceOfOneBTC` price feed becomes one source among several

### Rate Staleness Enforcement

Every rate lookup must validate freshness before use. Stale rates are rejected with an explicit error, forcing the caller to handle the absence rather than silently using outdated data.

| Currency Type | Transaction Use Max Age | Reporting Use Max Age |
|---------------|------------------------|----------------------|
| BTC | 60 seconds | 5 minutes |
| Fiat | 5 minutes | 1 hour |

Configuration can be stored per currency pair, either as a `max_age_seconds` column on a configuration table or as application-level configuration:

```rust
struct RateFreshnessConfig {
    /// Maximum acceptable age for rates used in transactions
    transaction_max_age: Duration,
    /// Maximum acceptable age for rates used in reporting
    reporting_max_age: Duration,
}

impl ExchangeRateService {
    async fn get_rate_checked(
        &self,
        from: CurrencyCode,
        to: CurrencyCode,
        at: DateTime<Utc>,
        rate_type: RateType,
        use_context: RateUseContext,  // Transaction | Reporting
    ) -> Result<ExchangeRate, PriceError> {
        let rate = self.get_rate(from, to, at, rate_type).await?;
        let max_age = self.freshness_config(from, to).max_age_for(use_context);
        let age = Utc::now() - rate.rate_timestamp;

        if age > max_age {
            return Err(PriceError::RateStale {
                from, to, rate_age: age, max_age,
            });
        }
        Ok(rate)
    }
}
```

### Rate Tolerance Bands

To guard against erroneous rates from a single source, each captured rate is compared against the median across providers:

- Configurable deviation threshold per currency pair (e.g., 2% for BTC/USD, 0.5% for EUR/USD)
- Rates exceeding the threshold are flagged and excluded from the aggregated rate
- Alert generated when a source consistently deviates (degraded source detection)

### Circuit Breaker Logic

FX-dependent operations must halt gracefully when reliable rates are unavailable:

| Condition | Action |
|-----------|--------|
| No valid rate available for a required pair | Reject transaction with explicit `NoRateAvailable` error |
| Rate used in pending operation differs from current rate by > threshold | Reject with `RateDrift` error; client must re-quote |
| Sudden large move (configurable % change within time window) | Alert; optionally pause automated FX operations pending manual review |
| All sources failing for a pair | Circuit breaker OPEN; reject all FX operations for that pair |

## Component 2: Multi-Source Rate Aggregation

The current system depends on a single Bitfinex feed. A single-source failure means complete loss of pricing capability. Multi-source aggregation provides resilience, accuracy, and auditability.

### Design

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Bitfinex  │  │  Coinbase   │  │   Kraken   │
│  (source)  │  │  (source)   │  │  (source)  │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┼───────────────┘
                      │
              ┌───────▼──────┐
              │  Aggregator  │
              │  (median /   │
              │   VWAP)      │
              └───────┬──────┘
                      │
              ┌───────▼──────┐
              │ exchange_rates│
              │   table      │
              └──────────────┘
```

### Requirements

- **Minimum 3 independent BTC sources** (Bitfinex, Coinbase, Kraken) to enable meaningful median calculation
- **Aggregation strategy:** Median (default) — robust against single-source outliers. VWAP (volume-weighted average price) available as an option for higher fidelity when volume data is accessible.
- **Automatic fallback:** If a source fails, the aggregator continues with remaining sources. Below minimum source threshold (configurable, default 2), the circuit breaker engages.
- **Source health monitoring:** Track per source:
  - Last successful fetch timestamp
  - Error rate (rolling window)
  - Response latency (p50, p99)
  - Deviation from aggregated rate (rolling window)
- **Source weighting:** Equal weight by default, configurable per source. Degraded sources can be down-weighted before removal.

### Integration with Existing Price Feed

The existing `PriceOfOneBTC` / Bitfinex fetcher becomes one source adapter among several. Each source adapter implements a common trait:

```rust
#[async_trait]
trait RateSourceAdapter: Send + Sync {
    fn source_name(&self) -> &str;
    async fn fetch_rate(&self, pair: CurrencyPair) -> Result<RateQuote, SourceError>;
}

struct RateQuote {
    pair: CurrencyPair,
    rate: Decimal,
    timestamp: DateTime<Utc>,
    source: String,
    volume_24h: Option<Decimal>,  // For VWAP if available
}
```

The aggregator collects quotes from all healthy sources, applies tolerance band filtering, computes the aggregated rate, and writes both the aggregated rate and individual source rates to the `exchange_rates` table.

## Component 3: Rate-Per-Transaction Recording

Every cross-currency journal entry must record the rate used. Additionally, **single-currency foreign transactions** (no exchange involved) should also capture the spot rate at transaction time, even though the rate is not an input to the entry amounts.

The reason: IAS 21 requires initial recognition of foreign-currency items at the transaction-date spot rate. This rate becomes the **historical rate** — the baseline for computing all future revaluation deltas. Without it, the first revaluation has no reference point. While the rate could theoretically be reverse-looked-up from the `exchange_rates` table by timestamp, storing it on the transaction is more reliable (eliminates ambiguity about which rate/source applied) and gives auditors a self-contained record of the USD-equivalent value at origination.

| Transaction Type | Rate Role | Why Record |
|-----------------|-----------|------------|
| Cross-currency (exchange) | **Input** — determines amounts on both legs | Required: the rate produced the entry amounts |
| Single-currency foreign | **Metadata** — records functional-currency equivalent | Required: establishes historical rate for revaluation baseline and audit trail |

Two approaches for recording:

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

## Component 4: Trading Accounts (Selinger Model)

### Concept

A **trading account** is an intermediary account that all currency conversions flow through. It absorbs exchange rate differences and its running balance represents the cumulative unrealized FX gain/loss.

### Chart of Accounts Additions

```
EQUITY / FX
  3200  FX Trading Account           -- intermediary for all conversions
  3210  FX Rounding Differences       -- suspense account for rounding variances
                                      -- from cross-rate triangulation and
                                      -- conversion rounding

REVENUE
  4200  Realized FX Gain             -- closed FX positions (permanent)

EXPENSES
  5100  Realized FX Loss             -- closed FX positions (permanent)

OTHER INCOME / EXPENSE
  6100  Unrealized FX Gain           -- period-end revaluation (auto-reversing)
  6200  Unrealized FX Loss           -- period-end revaluation (auto-reversing)
```

The **FX Rounding Differences (3210)** account accumulates small variances that arise from:
- Cross-rate triangulation (e.g., EUR→USD→BTC introduces rounding at each step)
- Conversion rounding where debits and credits differ by fractions of a cent
- Inverse rate calculations (`1/rate` is not perfectly reversible at finite precision)

This account should be monitored and periodically cleared to P&L when balances exceed a materiality threshold.

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

### Scoping Note

Trading accounts deliver maximum value when the system handles **3 or more currencies**. With only BTC/USD, the direct gain/loss approach is simpler and sufficient because there is only one conversion path and no cross-rate complexity.

**Recommendation:** Implement direct gain/loss booking as the interim solution for BTC/USD-only operations. Introduce the full trading account machinery when a second fiat currency (e.g., EUR) is added, at which point cross-rate triangulation and multi-leg conversions make the intermediary account essential.

### Rate Locking and Spread Considerations

The trading account (or the direct gain/loss approach) must accommodate operational pricing concerns:

- **Rate locks:** Customer-facing rates held for a configurable time window (e.g., 30 seconds for a quote, 24 hours for a facility drawdown). The locked rate is the rate recorded on the transaction, even if the market moves during the lock period.
- **Rate markup / spread:** Configurable per currency pair, applied on top of the mid-market rate. The spread is revenue for the platform. The trading account records the mid-market rate; the spread is booked separately to a revenue account.
- **Rate agreements:** Contractual rates for specific customers or facility types (e.g., a corporate borrower with a negotiated BTC conversion rate). These override the standard markup.

## Component 5: Period-End Revaluation

Period-end revaluation follows two distinct regimes reflecting the accounting framework.

### Fiat FX Revaluation (IAS 21)

#### The Revaluation Process

```
DAILY or MONTHLY (configurable per account type):

1. IDENTIFY candidates
   - All accounts with non-functional-currency balances
   - All open foreign-currency receivables/payables
   - All foreign-currency cash/bank accounts

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
   (Method depends on chosen approach — see below)

5. LOG results
   Store revaluation report: account, currency, old value, new value, adjustment, rate used
```

#### Revaluation Methods

Two established methods exist for posting revaluation entries:

**Full Reversal Method:**
Post the revaluation entry, then schedule an auto-reversal on the first day of the next period. This ensures that when a position settles, the realized gain/loss captures the full movement from the original transaction date.

```
Feb 28 (revaluation):
  Dr  EUR Receivable             $5,000 USD  (revaluation adjustment)
    Cr  Unrealized FX Gain               $5,000 USD

Mar 1 (auto-reversal):
  Dr  Unrealized FX Gain        $5,000 USD
    Cr  EUR Receivable                   $5,000 USD
```

- Straightforward mental model
- Higher journal volume (two entries per revaluation)
- Mid-period settlements require care to avoid double-counting

**Delta Method:**
Compare the current closing rate with the rate from the most recent revaluation (or original transaction if first revaluation). Post only the incremental difference. No reversals needed.

```
Jan 31 (first revaluation, original rate 1.10, closing rate 1.12):
  adjustment = balance × (1.12 - 1.10) = $2,000
  Dr  EUR Receivable             $2,000 USD
    Cr  Unrealized FX Gain               $2,000 USD

Feb 28 (second revaluation, closing rate 1.15):
  adjustment = balance × (1.15 - 1.12) = $3,000
  Dr  EUR Receivable             $3,000 USD
    Cr  Unrealized FX Gain               $3,000 USD
```

- Fewer journal entries (no reversals)
- Can run multiple times per day without side effects (idempotent within a period)
- Handles mid-period settlements cleanly (settled portion is simply excluded from next delta)
- Used by SAP S/4HANA and similar ERP systems

**Recommendation: Delta method** for new implementations. The delta approach produces fewer entries, is naturally idempotent, and handles mid-period settlements without special logic. Full reversal is acceptable if auto-reversal is already built into the job framework.

#### Reconciliation Job

A periodic reconciliation job verifies that:
- Trading account balances (if in use) net to expected values given current rates
- The sum of all unrealized gain/loss entries matches the expected revaluation position
- No orphaned reversal entries exist (full reversal method)

### BTC Fair Value Revaluation (ASU 2023-08)

BTC revaluation operates under a fundamentally different model than fiat FX:

- **Continuous fair value tracking**, not period-end-only. Fair value adjustments can be posted at any frequency (daily, hourly, or on every price update).
- **All fair value changes flow to net income.** There is no "unrealized" vs "realized" distinction in the IAS 21 sense. Every adjustment is recognized in P&L.
- **No auto-reversal.** Adjustments are cumulative. Each revaluation posts the delta between the current fair value and the last recorded fair value.

**For platform-owned BTC** (treasury holdings, fee income received in BTC):

```
BTC purchased at $50,000. Current fair value: $55,000.

  Dr  BTC Holdings              $5,000 USD
    Cr  BTC Fair Value Gain (P&L)        $5,000 USD

If fair value later drops to $52,000:
  Dr  BTC Fair Value Loss (P&L)  $3,000 USD
    Cr  BTC Holdings                     $3,000 USD
```

**For custodied BTC** (collateral held as agent):
Both the asset and liability sides move together — no P&L impact. This is handled by Component 6 (BTC Collateral Accounting) and is economically distinct from ASU 2023-08 revaluation.

### Implementation

Both fiat FX and BTC revaluation follow the established job pattern: `EndOfDay event → Handler → Collector → Worker`.

**Event Handler** — registered in module `init()`, listens for `CoreTimeEvent::EndOfDay`:

```rust
// core/fx/src/jobs/end_of_day.rs (or core/credit/src/.../jobs/)
const JOB_TYPE: JobType = JobType::new("task.collect-accounts-for-fx-revaluation");

pub struct FxRevaluationEndOfDayHandler {
    spawner: JobSpawner<CollectAccountsForRevaluationConfig>,
}

impl<E> OutboxEventHandler<E> for FxRevaluationEndOfDayHandler
where
    E: OutboxEventMarker<CoreTimeEvent>,
{
    async fn handle_persistent(
        &self,
        op: &mut DbOp<'_>,
        event: &PersistentOutboxEvent<E>,
    ) -> Result<(), Box<dyn Error + Send + Sync>> {
        if let Some(CoreTimeEvent::EndOfDay { day, .. }) = event.as_event() {
            event.inject_trace_parent();
            let config = CollectAccountsForRevaluationConfig { day: *day };
            self.spawner
                .spawn_in_op(op, JobId::new(), config)
                .await?;
        }
        Ok(())
    }
}
```

**Collector Job** — cursor-based pagination over accounts with foreign-currency balances:

```rust
// core/fx/src/jobs/collect_accounts_for_revaluation.rs
const PAGE_SIZE: i64 = 100;

#[derive(Serialize, Deserialize)]
struct CollectorState {
    last_cursor: Option<(DateTime<Utc>, AccountId)>,
}

impl JobRunner for CollectAccountsForRevaluationJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        let config = current_job.config::<CollectAccountsForRevaluationConfig>()?;
        let mut state = current_job
            .execution_state::<CollectorState>()?
            .unwrap_or_default();

        let closing_rates = self.rate_service
            .get_closing_rates(config.day)
            .await?;

        let mut op = self.pool.begin().await?;
        let accounts = self.repo
            .list_foreign_currency_accounts_in_op(
                &mut op,
                state.last_cursor,
                PAGE_SIZE,
            )
            .await?;

        if accounts.is_empty() {
            return Ok(JobCompletion::Complete);
        }

        let specs: Vec<_> = accounts.iter().map(|(id, currency, ts)| {
            let config = ProcessRevaluationConfig {
                account_id: *id,
                currency: *currency,
                day: config.day,
                closing_rate: closing_rates.get(*currency),
            };
            JobSpec::new(JobId::new(), config)
                .queue_id(id.to_string())
        }).collect();

        self.worker_spawner.spawn_all_in_op(&mut op, specs).await?;

        state.last_cursor = accounts.last().map(|(id, _, ts)| (*ts, *id));
        current_job.update_execution_state(&state).await?;
        op.commit().await?;

        Ok(JobCompletion::RescheduleAt(Utc::now()))  // Continue pagination
    }
}
```

**Worker Job** — per-account revaluation entry posting:

```rust
// core/fx/src/jobs/process_revaluation.rs
impl JobRunner for ProcessRevaluationJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        let config = current_job.config::<ProcessRevaluationConfig>()?;

        let foreign_balance = self.accounting
            .get_balance(config.account_id, config.currency)
            .await?;
        let current_book_value = self.accounting
            .get_functional_currency_balance(config.account_id)
            .await?;
        let new_value = foreign_balance * config.closing_rate;
        let adjustment = new_value - current_book_value;

        if !adjustment.is_zero() {
            self.accounting.post_revaluation_entry(
                config.account_id,
                adjustment,
                config.closing_rate,
                config.day,
            ).await?;
        }

        Ok(JobCompletion::Complete)
    }
}
```

## Component 6: BTC Collateral Accounting

### The Agent Relationship

The platform holds BTC as **agent**, not as owner. This means:
- Price movements affect both the asset (collateral held) and liability (obligation to return) equally
- **No P&L impact** for the platform from BTC price changes on custodied collateral
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
| Auto-reversal | Yes (fiat FX) / No (BTC owned) | Not needed (cumulative) |
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

### Cost Basis and Lot Tracking

When BTC collateral is liquidated, cost basis is needed for tax reporting regardless of the agent relationship. The lending model provides a natural lot identification strategy:

- **Per-facility cost basis:** Each facility's collateral has a known deposit price (the BTC/USD rate at the time of collateral receipt). This is the most natural approach since collateral is segregated per facility.
- **Specific identification:** Since each collateral deposit is tracked individually (facility ID + deposit timestamp + amount), specific identification is straightforward — no need for FIFO/LIFO assumptions.
- **Multiple deposits per facility:** If a borrower tops up collateral across multiple deposits at different prices, each deposit is a separate lot within the facility. Liquidation should specify which lots are being sold (typically oldest first, matching FIFO, but configurable).

```rust
struct CollateralLot {
    facility_id: FacilityId,
    deposit_timestamp: DateTime<Utc>,
    btc_amount: Satoshis,
    cost_basis_usd: UsdCents,  // BTC/USD rate at deposit time × amount
    rate_at_deposit: Decimal,
}
```

### Segregation Controls

Proper segregation of custodied BTC is a regulatory and fiduciary requirement. The Celsius bankruptcy demonstrated what happens when customer assets and platform assets are commingled.

**Ledger-level enforcement:**
- CALA account permissions and template restrictions must ensure that **only authorized templates** can debit collateral accounts
- No general-purpose transfer template should be able to move collateral BTC
- Collateral accounts should be in a dedicated account set with restricted access

**Reconciliation between on-chain and ledger:**
- Periodic job comparing the sum of custody wallet balances (on-chain) against the sum of all collateral ledger accounts
- Discrepancies generate alerts for immediate investigation
- The reconciliation job should log both the on-chain balance and ledger balance for audit trail

**Proof-of-reserves entries:**
- Periodic attestation entries recording the reconciliation result
- These serve as accounting evidence that the platform's BTC obligations are fully backed
- Frequency: at minimum monthly, ideally daily

```
// Proof-of-reserves attestation (informational entry, nets to zero)
Dr  Reserves Attestation Suspense     X BTC
  Cr  Reserves Attestation Suspense          X BTC

// Metadata: on-chain balance, ledger balance, discrepancy (if any), attestation timestamp
```

### On-Chain / Ledger Reconciliation Job

```rust
const JOB_TYPE: JobType = JobType::new("task.btc-onchain-ledger-reconciliation");

impl JobRunner for OnChainLedgerReconciliationJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        // Sum all collateral ledger accounts
        let ledger_total = self.accounting
            .sum_collateral_btc_balances()
            .await?;

        // Query on-chain custody wallet balances
        let onchain_total = self.custody_service
            .get_total_btc_balance()
            .await?;

        let discrepancy = onchain_total - ledger_total;

        self.reconciliation_repo.record_result(ReconciliationResult {
            timestamp: Utc::now(),
            ledger_balance: ledger_total,
            onchain_balance: onchain_total,
            discrepancy,
            status: if discrepancy.abs() <= self.tolerance {
                ReconciliationStatus::Matched
            } else {
                ReconciliationStatus::Discrepancy
            },
        }).await?;

        if discrepancy.abs() > self.tolerance {
            self.alerts.fire_reconciliation_discrepancy(
                ledger_total, onchain_total, discrepancy,
            ).await?;
        }

        Ok(JobCompletion::Complete)
    }
}
```

## Component 7: Job Orchestration

All FX operations use the established Rust job framework (`obix` crate), not Dagster. Dagster is reserved for reporting/data warehouse pipelines.

### Daily Revaluation Flow

Triggered by the existing `CoreTimeEvent::EndOfDay` event, following the same handler → collector → worker pattern used by interest accrual and obligation processing:

```
CoreTimeEvent::EndOfDay { day }
  ├── FxRevaluationEndOfDayHandler
  │     └── CollectAccountsForRevaluationJob (cursor-paginated)
  │           └── ProcessRevaluationJob (per account, posts entries)
  │
  └── CollateralRevaluationEndOfDayHandler
        └── CollectFacilitiesForCollateralRevaluationJob (cursor-paginated)
              └── ProcessCollateralRevaluationJob (per facility, both-sides entry)
```

**Registration** — in the FX module's `init()`, called from `LanaApp::init()`:

```rust
// Registration follows the same pattern as credit facility jobs
outbox.register_event_handler(
    jobs,
    OutboxEventJobConfig::new(JOB_TYPE_COLLECT_FX_REVALUATION),
    FxRevaluationEndOfDayHandler::new(collector_spawner),
).await?;

outbox.register_event_handler(
    jobs,
    OutboxEventJobConfig::new(JOB_TYPE_COLLECT_COLLATERAL_REVALUATION),
    CollateralRevaluationEndOfDayHandler::new(collector_spawner),
).await?;
```

**Collateral revaluation collector** — same cursor-based pattern:

```rust
// core/credit/collateral/src/jobs/collect_facilities_for_revaluation.rs
impl JobRunner for CollectFacilitiesForCollateralRevaluationJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        let config = current_job.config::<CollateralRevalConfig>()?;
        let mut state = current_job
            .execution_state::<CollectorState>()?
            .unwrap_or_default();

        let mut op = self.pool.begin().await?;
        let facilities = self.repo
            .list_active_facilities_with_collateral_in_op(
                &mut op,
                state.last_cursor,
                PAGE_SIZE,
            )
            .await?;

        if facilities.is_empty() {
            return Ok(JobCompletion::Complete);
        }

        let btc_usd_rate = self.rate_service
            .get_closing_rate(CurrencyCode::BTC, CurrencyCode::USD, config.day)
            .await?;

        let specs: Vec<_> = facilities.iter().map(|(id, ts)| {
            let config = ProcessCollateralRevalConfig {
                facility_id: *id,
                day: config.day,
                btc_usd_rate,
            };
            JobSpec::new(JobId::new(), config)
                .queue_id(id.to_string())
        }).collect();

        self.worker_spawner.spawn_all_in_op(&mut op, specs).await?;

        state.last_cursor = facilities.last().map(|(id, ts)| (*ts, *id));
        current_job.update_execution_state(&state).await?;
        op.commit().await?;

        Ok(JobCompletion::RescheduleAt(Utc::now()))
    }
}
```

### LTV Monitoring (Higher Frequency)

Separate from the daily accounting revaluation, LTV monitoring should run at higher frequency. Two options based on existing patterns:

**Option A: Triggered by price updates** — react to `CorePriceEvent::PriceUpdated` (published every 60s by the Bitfinex price fetcher):

```rust
// Reacts to every price update, checks LTV thresholds
pub struct LtvMonitorPriceHandler {
    spawner: JobSpawner<LtvCheckConfig>,
}

impl<E> OutboxEventHandler<E> for LtvMonitorPriceHandler
where
    E: OutboxEventMarker<CorePriceEvent>,
{
    async fn handle_persistent(
        &self,
        op: &mut DbOp<'_>,
        event: &PersistentOutboxEvent<E>,
    ) -> Result<(), Box<dyn Error + Send + Sync>> {
        if let Some(CorePriceEvent::PriceUpdated { price, .. }) = event.as_event() {
            event.inject_trace_parent();
            let config = LtvCheckConfig { btc_price: *price };
            self.spawner
                .spawn_in_op(op, JobId::new(), config)
                .await?;
        }
        Ok(())
    }
}
```

This follows the collector → worker pattern: the collector paginates over active facilities, the worker checks each facility's LTV and triggers margin calls if thresholds are breached.

**Option B: Continuous loop job** — like the Bitfinex price fetcher, runs indefinitely with an internal sleep interval:

```rust
// Runs continuously, polls every N seconds
const LTV_CHECK_INTERVAL: Duration = Duration::from_secs(900); // 15 minutes

impl JobRunner for LtvMonitorJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        loop {
            let current_price = self.price_service.get_current_btc_price().await?;

            let at_risk = self.credit_facilities
                .list_facilities_above_ltv_threshold(
                    current_price,
                    self.warning_threshold,
                )
                .await?;

            for facility in at_risk {
                if facility.ltv >= self.margin_call_threshold {
                    self.credit_facilities
                        .trigger_margin_call(facility.id)
                        .await?;
                } else {
                    self.notifications
                        .send_ltv_warning(facility.id, facility.ltv)
                        .await?;
                }
            }

            tokio::select! {
                _ = tokio::time::sleep(LTV_CHECK_INTERVAL) => {},
                _ = current_job.signal_shutdown() => break,
            }
        }
        Ok(JobCompletion::Complete)
    }
}
```

**Option A is preferred** because it naturally throttles to the rate of price updates and follows the event-driven pattern used throughout the system. Option B is appropriate if LTV checks need to be decoupled from the price feed cadence.

### Rate Health Monitoring Job

A continuous job monitors the health of the rate infrastructure:

```rust
const JOB_TYPE: JobType = JobType::new("task.rate-health-monitor");

impl JobRunner for RateHealthMonitorJobRunner {
    async fn run(&self, current_job: CurrentJob) -> Result<JobCompletion, Error> {
        loop {
            for pair in self.monitored_pairs.iter() {
                let health = self.rate_service.check_source_health(pair).await?;

                if health.active_sources < self.min_sources {
                    self.alerts.fire_insufficient_sources(pair, &health).await?;
                }
                if health.staleness > self.staleness_threshold {
                    self.alerts.fire_rate_stale(pair, health.staleness).await?;
                }
                if health.max_deviation > self.deviation_threshold {
                    self.alerts.fire_rate_deviation(pair, &health).await?;
                }
            }

            tokio::select! {
                _ = tokio::time::sleep(Duration::from_secs(30)) => {},
                _ = current_job.signal_shutdown() => break,
            }
        }
        Ok(JobCompletion::Complete)
    }
}
```

## Component 8: Regulatory and Reporting Considerations

### Audit Trail

The FX infrastructure provides a complete audit trail by design:

- **Rate-per-transaction recording** (Component 3) ensures every cross-currency entry can be traced to a specific rate, source, and timestamp
- **Exchange rate storage** (Component 1) enables reconstruction of the rate at any historical point
- **Rate source metadata** documents which providers contributed to each aggregated rate, the aggregation method used, and any outliers that were excluded

### Rate Methodology Documentation

Regulatory examiners expect documented policies for:
- Rate sources and selection criteria
- Aggregation methodology (median, VWAP)
- Fallback procedures when primary sources fail
- Tolerance thresholds and the rationale for their values
- Manual override procedures and required approvals

### Cash Flow Statement (ASC 830)

ASC 830-230-55-1 requires that cash flows be translated at the exchange rates in effect at the time of the cash flows. Cash flow amounts cannot be derived from differences in translated balance sheet amounts because balance sheet translation uses closing rates while income statement translation uses transaction-date rates.

This means the system must be able to:
- Retrieve the rate that was in effect when each cash flow occurred (enabled by Component 3)
- Produce cash flow statement line items translated at historical rates, not closing rates

### Hyperinflation (IAS 29)

If the platform operates in or has exposure to hyperinflationary jurisdictions, IAS 29 requires financial statements to be restated for the effects of inflation **before** translation under IAS 21. This is noted as a future consideration — not currently applicable for a USD-functional-currency platform, but relevant if expanding to certain emerging markets.

### Segregation and Proof of Reserves

Regulatory frameworks increasingly require provable controls over custodied crypto assets, not just policy documentation. The segregation controls and on-chain/ledger reconciliation in Component 6 provide the accounting evidence for:
- Customer asset segregation (CALA template restrictions)
- Continuous proof of reserves (reconciliation job)
- Audit-ready reconciliation history (stored results with timestamps)

## Implementation Order

### Phase 1: Rate Storage + Multi-Source Aggregation (Foundation)
- Create `exchange_rates` table and migration
- Build `ExchangeRateService` with rate lookup (direct, inverse, cross-rate)
- Implement rate source adapter trait and Bitfinex adapter (wrapping existing feed)
- Add Coinbase and Kraken adapters
- Build aggregator (median) with tolerance band filtering
- Store rate used on each cross-currency transaction (metadata)

### Phase 2: Rate Robustness
- Implement rate staleness enforcement
- Add tolerance band configuration per currency pair
- Build circuit breaker logic
- Deploy rate health monitoring job

### Phase 3: Collateral Revaluation
- Build collateral revaluation template (both-sides, no P&L)
- Create `CollateralRevaluationEndOfDayHandler` + collector + worker jobs triggered by `CoreTimeEvent::EndOfDay`
- Post USD-denominated adjustment entries
- Delivers immediate value for LTV monitoring accuracy

### Phase 4: Segregation Controls + On-Chain Reconciliation
- Implement CALA template restrictions on collateral accounts
- Build on-chain/ledger reconciliation job
- Add proof-of-reserves attestation entries
- Cost basis / lot tracking for collateral liquidation

### Phase 5: Chart of Accounts + General FX Revaluation
- Add FX-specific accounts (realized gain/loss, unrealized gain/loss, rounding differences)
- Build general revaluation (delta method) for fiat foreign-currency balances
- Implement BTC fair value revaluation for platform-owned BTC
- Build reconciliation job for revaluation verification
- This phase is needed when a second fiat currency is introduced

### Phase 6: Trading Accounts
- Create trading account template for currency conversions
- Route all FX conversions through trading account
- Realized gain/loss posting on position closure
- Needed when 3+ currencies create cross-rate complexity

## Dependencies

- **Workstream 1 (Generic Money Type)**: Not a hard dependency — FX infrastructure can work with the current `UsdCents`/`Satoshis` types for BTC/USD. But supporting additional currency pairs requires the generic type.
- **CALA**: Transaction metadata support for storing rates. Template parameterization for currency (already supported but not used). Account permissions for segregation controls.
- **Jobs framework** (`obix`): Already in place. FX jobs follow the established handler → collector → worker pattern used by interest accrual and obligation processing.
- **Time events**: `CoreTimeEvent::EndOfDay` already exists and triggers daily operations. FX revaluation hooks into the same event.
- **Price feeds**: Current Bitfinex integration needs to be extended to write closing rates to the rate table. `CorePriceEvent::PriceUpdated` can trigger high-frequency LTV monitoring. Additional source adapters (Coinbase, Kraken) need to be implemented.
- **ASU 2023-08 compliance review**: Legal/accounting team should confirm the fair value treatment approach before implementation of BTC revaluation entries.
- **Custody integration**: On-chain balance queries needed for the reconciliation job in Phase 4. Requires API access to the custody solution.
