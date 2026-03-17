# Analysis: Trading Accounts (Selinger Model Analogy)

## 1. Definition: Selinger Model

The **Selinger model** (from IBM System R, 1979) is a **cost-based query optimization framework** that:

> Enumerates possible execution plans for a query, estimates the cost of each plan using data statistics, and selects the lowest-cost plan using dynamic programming.

### Core Characteristics

- **Cost-based**: Uses a numeric cost model (I/O, CPU, cardinality)
- **Plan enumeration**: Considers multiple execution strategies (e.g., join orders)
- **Dynamic programming**: Builds optimal plans from optimal subplans
- **Incremental accumulation**: Total cost is computed as the sum of stepwise costs
- **State pruning**: Retains only the cheapest plan per subproblem

---

## 2. Summary of Proposed Model

The proposed **Trading Account model**—where all FX conversions flow through an intermediary account that accumulates valuation differences—is:

> ✅ Strongly aligned with Selinger-style *incremental accumulation*  
> ⚠️ Not a direct analogue, but structurally similar at a systems level  
> 🚀 Particularly well-suited for event-sourced, multi-currency ledger systems  

---

## 3. Restating the Model

**Concept:**
- Every FX conversion is routed through a **Trading Account**
- The Trading Account absorbs:
  - Differences between execution rate and reference (mark-to-market) rate
- Its balance represents:
  - **Cumulative unrealized FX gain/loss**

---

## 4. Mapping to Selinger Model

| Selinger Concept                  | Trading Account Equivalent                          |
|----------------------------------|----------------------------------------------------|
| Query plan                       | Sequence of FX conversions                         |
| Cost function                    | FX valuation difference (PnL delta)                |
| Incremental cost accumulation    | Accumulation in Trading Account                    |
| Intermediate results matter      | Intermediate FX states affect valuation            |
| Final cost = sum of steps        | Total unrealized PnL = accumulated deltas          |
| Plan pruning                     | (Not applicable / constrained by accounting rules) |

### Key Insight

> The Trading Account behaves like a **running cost accumulator over a transformation path**, analogous to how Selinger accumulates cost across a query plan.

---

## 5. Structural Fit

### 5.1 Strong Parallels

#### a. Incremental Accumulation

- Selinger:
  - Cost is accumulated step-by-step during plan construction  
- Trading Account:
  - FX deltas are accumulated per transaction  

👉 Both avoid recomputation from scratch.

---

#### b. Path Awareness

- Selinger:
  - Intermediate join results affect total cost  
- Trading Account:
  - Sequence of FX conversions affects cumulative valuation  

👉 Both are **path-dependent systems**.

---

#### c. State Compression

- Selinger:
  - Retains only optimal subplans  
- Trading Account:
  - Collapses all historical FX effects into a single running balance  

👉 Both reduce complexity via **state summarization**.

---

## 6. Key Differences

### 6.1 Optimization vs Determinism

- Selinger:
  - Chooses *best* plan based on cost  
- Trading Account:
  - Must follow **deterministic accounting rules**

❗ No “optimization” freedom:
- You cannot choose a path that improves PnL artificially

---

### 6.2 Probabilistic vs Realized Data

- Selinger:
  - Uses estimated statistics  
- Trading Account:
  - Uses **actual executed rates + current market rates**

👉 No estimation—only measurement.

---

### 6.3 Search Space

- Selinger:
  - Explores multiple candidate plans  
- Trading Account:
  - Processes a **single realized transaction stream**

👉 No branching or plan enumeration.

---

## 7. Advantages of the Trading Account Model

### 7.1 Eliminates Lot Matching Complexity

Traditional FX accounting:
- Requires FIFO / LIFO / specific identification  
- Complex reconciliation logic  

Trading Account:
- No need to match inflows/outflows  
- All differences flow into a single accumulator  

---

### 7.2 Path-Independent Valuation

Even though trades are path-dependent:

> The resulting unrealized PnL is captured **without needing explicit pairing logic**

---

### 7.3 Clean Ledger Semantics

- All FX effects are:
  - Explicit  
  - Traceable  
  - Isolated  

👉 Improves auditability and reasoning.

---

### 7.4 Natural Fit for Event-Sourced Systems

- Each FX event:
  - Emits a delta  
  - Updates Trading Account  

👉 Aligns with:
- append-only logs  
- deterministic replay  

---

### 7.5 Separation of Concerns

Decouples:
- **Execution layer** (trades, transfers)  
- **Valuation layer** (PnL accumulation)

---

## 8. Conceptual Interpretation

The Trading Account can be viewed as:

> A **residual balancing account** that preserves value consistency across currency transformations.

Or more formally:

> A **stateful accumulator of valuation discrepancies across a multi-currency graph of transactions.**

---

## 9. System Design Implications

### 9.1 Ledger Structure

Each FX conversion becomes:

- Debit: Target currency account  
- Credit: Source currency account  
- Offset: Trading Account captures valuation delta  

---

### 9.2 Revaluation Process

At any point:

- Compute current value of positions  
- Compare against historical implied value  
- Post delta to Trading Account  

---

### 9.3 Period Close

- Trading Account balance → realized P&L  
- Reset or carry forward depending on accounting policy  

---

## 10. Limitations / Considerations

### 10.1 Accounting Standards Alignment

- IFRS / GAAP may require:
  - Realized vs unrealized distinction  
  - Specific treatment of monetary vs non-monetary items  

👉 Model must map cleanly to reporting requirements.

---

### 10.2 Multi-Entity / Multi-Book Complexity

- Per-entity Trading Accounts required  
- Potential need for:
  - per-currency-pair accounts  
  - per-instrument segmentation  

---

### 10.3 Realization Events

- When positions are closed:
  - Need to move portion of Trading Account → realized PnL  

👉 Requires clear policy.

---

### 10.4 Reference Rate Definition

- What is “current value”?
  - Mid-market?
  - Bid/ask?
  - Internal pricing?

👉 Impacts PnL materially.

---

## 11. Final Assessment

### Fit with Selinger

| Dimension              | Fit Level |
|-----------------------|----------|
| Structural analogy    | High     |
| Mathematical analogy  | Moderate |
| Operational behavior  | Low      |

---

### Overall Verdict

> The Trading Account model is **not an implementation of Selinger**, but it *embodies the same core idea*:
>
> **Accumulate the effect of incremental transformations into a single scalar that represents total system “cost” (PnL).**

---

## 12. Key Takeaway

> You are effectively transforming FX accounting from:
>
> - a **matching problem** (lots, FIFO, pairing)
>
> into:
>
> - a **flow + accumulation problem** (deltas into a residual account)
>
> This is a **meaningful architectural simplification** with strong theoretical grounding.
