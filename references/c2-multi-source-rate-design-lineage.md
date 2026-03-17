# Component 2: Multi-Source Rate Design Lineage and Analysis

C2's multi-source rate aggregation design synthesizes patterns from four established oracle and market data architectures. This document traces where each design choice comes from, evaluates robustness, identifies improvement opportunities, and explains what was deliberately excluded given C2's operating context.

## Design Origins

### Multi-reporter median aggregation

**Origin: Chainlink Price Feeds**

Chainlink's core mechanism is straightforward — N independent node operators each report a price, and the on-chain contract takes the median. Typical feeds use 7-31 reporters. The median is chosen over the mean because it is robust to a minority of reporters submitting incorrect values. A single compromised or malfunctioning reporter cannot move the median unless it controls a majority of the reporter set.

C2 applies the same principle with 3+ CEX API sources and median as the default aggregation strategy. The minimum of 3 is the smallest set where a median is meaningful (one outlier cannot dominate). VWAP is offered as an alternative when volume data is available, but median is the default for the same reason Chainlink chose it — outlier resistance without requiring trust in any individual source.

**Where this is robust:** The median works well when sources are independent and failures are uncorrelated. With Bitfinex, Coinbase, and Kraken operating independent matching engines, a price anomaly on one exchange (flash crash, stale order book, API lag) does not propagate through the median.

**Where this could be improved:** With only 3 sources, the median is fragile — if one source fails entirely, you're down to 2, and the "median" of 2 values is just their average. Chainlink typically requires a much higher reporter count for this reason. C2 mitigates this with the circuit breaker (below minimum source threshold), but the transition from "3 healthy sources" to "circuit breaker engaged" is abrupt. A smoother degradation path would help (see tiered fallback below).

### Tolerance band filtering and contributor quality scoring

**Origin: Bloomberg BVAL (Bloomberg Valuation Service)**

Bloomberg's valuation service for fixed income and derivatives aggregates prices from multiple contributor banks and dealers. Each contributor is scored on quality metrics — response frequency, deviation from consensus, quote type (executable vs indicative), and freshness. Contributors that consistently deviate from consensus are down-weighted or excluded from the composite price.

C2 adapts this as tolerance band filtering: each source rate is compared against the cross-source median, and rates exceeding a configurable deviation threshold (2% for BTC/USD, 0.5% for EUR/USD) are flagged and excluded. Sources that consistently deviate trigger degraded-source alerts.

**Where this is robust:** The per-pair threshold configuration is well-chosen. BTC's higher volatility justifies a wider band than fiat pairs. The alert mechanism for consistent deviation catches sources that are systematically biased (e.g., an exchange with thin liquidity quoting persistently wide of the market) rather than just filtering one-off spikes.

**Where this could be improved:** Bloomberg's quality scoring is richer than a simple deviation threshold — it tracks contributor reliability over rolling windows, weights recent behavior more heavily, and distinguishes between "this contributor is occasionally noisy" and "this contributor has degraded permanently." C2's source health monitoring (latency, error rate, deviation) captures the raw signals for this, but the design doesn't specify how these signals feed back into source weighting or exclusion decisions over time. A formalized health score that adjusts source weight dynamically (rather than binary include/exclude at the tolerance band) would be a natural extension.

### Consumer-side staleness enforcement

**Origin: Pyth Network**

Pyth publishes a `publishTime` field with every price update. The protocol does not enforce freshness — it is the consumer's responsibility to check the age of the price before using it and reject stale data. This design pushes staleness policy to the point of use, where the acceptable age depends on context (a DeFi liquidation has different freshness needs than a portfolio display).

C2 adopts the same consumer-side pattern with `RateUseContext` (Transaction vs Reporting) determining the maximum acceptable age. BTC rates used for transactions must be within 60 seconds; the same rate used for end-of-day reporting can be up to 5 minutes old. Fiat pairs allow 5 minutes for transactions and 1 hour for reporting.

**Where this is robust:** Context-dependent staleness is the right approach for a banking system. A single global staleness threshold would be either too tight (rejecting valid rates for reporting) or too loose (accepting stale rates for transactions). The explicit `RateStale` error forces callers to handle the absence rather than silently using outdated data.

**Where this could be improved:** The staleness thresholds are static configuration. In practice, acceptable staleness correlates with market conditions — during high volatility, even a 30-second-old BTC rate may be dangerously stale for a collateral valuation, while during a weekend with minimal trading a 2-minute-old rate is perfectly fine. An adaptive staleness threshold that tightens during high-volatility periods (detectable from the rate of change in recent updates) would be more sophisticated.

### Circuit breaker pattern

**Origin: Traditional exchange infrastructure + consumer-side oracle patterns**

Stock exchanges have used circuit breakers since the 1987 crash — trading halts when prices move beyond defined thresholds within a time window. In oracle infrastructure, circuit breakers are typically implemented consumer-side: Chainlink consumers check `answeredInRound` and revert if the feed is stale; Pyth consumers reject prices older than their threshold.

C2 formalizes this into four conditions: no valid rate available, rate drift on pending operations, sudden large moves, and all sources failing. Each condition maps to a specific action (reject, re-quote, alert, or full halt).

**Where this is robust:** The four-condition model covers the realistic failure modes well. The `RateDrift` error (rate used in a pending operation differs from current rate by more than threshold) is particularly well-designed — it catches the scenario where a customer locks a rate, the market moves significantly during the lock period, and the transaction would execute at a rate that no longer reflects market conditions. This is a banking-specific concern that generic oracle designs don't address.

**Where this could be improved:** The transition from "degraded but operational" to "circuit breaker OPEN" is binary. A graduated response — warning state → reduced functionality (e.g., block new transactions but allow reporting) → full halt — would give operators time to intervene before complete shutdown. The "sudden large move" condition specifies "optionally pause automated FX operations pending manual review," which is the right instinct but could be formalized into explicit severity levels.

## Patterns Not Yet Adopted

### Confidence intervals

**Origin: Pyth Network**

Pyth publishes every price with a `confidence` field representing the uncertainty band (e.g., BTC/USD = $67,000 +/- $50). This lets consumers make risk-adjusted decisions — a tight confidence interval means sources agree; a wide one means they disagree significantly.

C2 produces a single aggregated rate with no signal about source agreement. When the tolerance band filter excludes an outlier, the resulting median is published without any indication that a source was excluded or that the remaining sources disagreed. Downstream consumers (circuit breaker, rate locking, LTV monitoring) have no way to distinguish a high-confidence rate from a low-confidence one.

**Recommendation:** Add a `spread_pct` (or equivalent) to the aggregated rate output — computed as `(max_source - min_source) / median` across the sources that passed tolerance filtering. This is cheap to compute (the data is already available during aggregation) and gives downstream consumers a concrete signal. For example, the circuit breaker could apply tighter thresholds when confidence is low, and the rate locking logic could shorten lock windows during periods of high source disagreement.

### Heartbeat + deviation dual trigger

**Origin: Chainlink Price Feeds**

Chainlink feeds update on either a time heartbeat (e.g., every 3600s for stable pairs, every 27s for ETH/USD) or a deviation threshold (e.g., price moves > 0.5%), whichever comes first. This is bandwidth-efficient: during calm markets the feed updates infrequently, but during volatile markets it updates on every significant move.

C2 specifies fixed polling intervals only (60s for BTC, 5 minutes for fiat). This means during calm weekend markets the system fetches and stores redundant identical rates every 60 seconds, and during a volatile crash the 60-second window could miss a move that matters for LTV monitoring. A 5% BTC drop that happens at second 15 won't be captured until second 60 — 45 seconds of stale data during the exact moment freshness matters most.

**Recommendation:** Add a deviation-triggered update mode alongside the fixed interval. When any single source reports a rate that deviates from the last published aggregated rate by more than a configurable threshold (e.g., 1% for BTC), immediately poll all sources and publish a new aggregated rate. This is particularly important for the collateral revaluation and LTV monitoring path, where a delayed price update during a crash could mean the difference between a timely margin call and an under-collateralized position.

### Smoothed / averaged rate

**Origin: Pyth Network (EMA price), Uniswap (TWAP)**

Pyth publishes both a spot price and an exponential moving average (EMA). Uniswap v3 provides a time-weighted average price (TWAP) oracle that is resistant to single-block manipulation because it averages over a configurable window.

C2 defines only SPOT and CLOSING rate types. There is no smoothed or averaged rate. The design doc acknowledges an AVERAGE rate type as "not yet needed" (for multi-entity consolidation under IAS 21.40), but does not consider a smoothed rate for operational use.

**Where this matters for Lana:** LTV monitoring is the primary use case. Using raw spot rates means a single-second exchange wick (a momentary anomalous price that immediately reverts) could trigger a margin call or liquidation. A 5-minute TWAP or EMA would filter these wicks while still responding to genuine sustained moves. This does not replace spot rates for transaction execution — the rate recorded on a transaction should always be the actual spot rate at execution time — but for risk monitoring, a smoothed rate produces fewer false alarms.

### Tiered source priority (waterfall)

**Origin: Bloomberg BVAL**

Bloomberg BVAL applies a strict hierarchy when computing composite prices: (1) executable quotes from lit venues, (2) indicative quotes from dealers, (3) model-derived prices from comparable instruments. Each tier is only used when the tier above it is unavailable or insufficient. This provides graceful degradation rather than a binary on/off.

C2 treats all sources equally (modulo configurable weighting). When sources drop below the minimum threshold, the circuit breaker engages immediately. There is no intermediate tier.

**Recommendation:** For fiat FX rates, consider a tiered approach: (1) primary tier — direct exchange/provider APIs with real-time feeds, (2) secondary tier — aggregator APIs or central bank reference rates (e.g., ECB daily fixing for EUR), (3) tertiary tier — cross-rate triangulation from available pairs. For BTC, a similar hierarchy: (1) major exchange APIs, (2) aggregator services, (3) last-known closing rate (acceptable for reporting, not for transactions). The circuit breaker would engage only when all tiers are exhausted, rather than when primary sources alone drop below the minimum.

## What Was Deliberately Excluded

### Decentralized consensus

Oracle networks like Chainlink use BFT-style commit-reveal protocols among reporters to prevent front-running and ensure that no single reporter can see others' answers before submitting their own. This is essential in adversarial environments where reporters have financial incentives to manipulate prices.

C2 excludes this entirely because the threat model is different. Lana controls its own infrastructure and selects its own rate sources. The risk is source failure or error, not deliberate manipulation by the sources. The bank is legally accountable for rate accuracy — regulatory oversight and audit trails substitute for cryptoeconomic incentives. Adding consensus overhead would increase latency and complexity without addressing any real threat in this context.

### On-chain storage and verification

Oracle feeds store prices on-chain for transparency and verifiability — any consumer can independently verify that the price was reported by the claimed set of reporters. This is necessary when the consumer is a smart contract that cannot trust off-chain data.

C2 stores rates in PostgreSQL because the consumers are internal services within the same trust boundary. The `exchange_rates` table provides the same queryability (historical lookups, cross-rate triangulation, indexed searches) at orders of magnitude lower cost and latency. The audit trail requirement is met by the database's own transaction log and the rate source metadata stored alongside each rate, not by on-chain immutability.

### Cryptoeconomic incentives for source quality

Chainlink node operators stake LINK tokens and risk slashing for persistent inaccuracy. Pyth publishers' reputations affect their inclusion in the publisher set. These mechanisms are necessary when sources are untrusted third parties.

C2 replaces this with operational monitoring and configuration. Source adapters are written and maintained by the engineering team. A source that degrades is down-weighted or removed via configuration change, not via an automated economic penalty. This is appropriate because the source set is small and curated (3-5 exchanges), not a permissionless network of anonymous reporters.

### Gas optimization and update batching

On-chain oracles spend significant engineering effort on gas optimization — batching updates, using compact storage formats, and minimizing on-chain writes. Chainlink's OCR (Off-Chain Reporting) protocol was designed specifically to reduce the gas cost of multi-reporter aggregation.

None of this is relevant to C2. Writing a row to PostgreSQL costs microseconds and fractions of a cent. The design can afford to store every individual source quote alongside the aggregated rate, providing a richer audit trail than any gas-constrained on-chain oracle.
