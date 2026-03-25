#!/usr/bin/env python3
"""FX Scenario Calculator — multi-currency accounting engine."""

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:
    print("Error: pyyaml required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

D = Decimal
ZERO = D("0")
TWO_PLACES = D("0.01")


def d(val) -> Decimal:
    return D(str(val))


def q(val: Decimal) -> Decimal:
    return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def fmt(v: Decimal) -> str:
    v = q(v)
    if v == v.to_integral_value():
        return str(int(v))
    return str(v)


def circled(n: int) -> str:
    if 1 <= n <= 20:
        return chr(0x2460 + n - 1)
    elif 21 <= n <= 35:
        return chr(0x3251 + n - 21)
    elif 36 <= n <= 50:
        return chr(0x32B1 + n - 36)
    return f"({n})"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Account:
    name: str
    normal_side: str  # "debit" or "credit"
    eur_balance: Decimal = field(default_factory=lambda: ZERO)
    usd_balance: Decimal = field(default_factory=lambda: ZERO)
    cumulative_reval: Decimal = field(default_factory=lambda: ZERO)
    accumulator: Decimal = field(default_factory=lambda: ZERO)
    revalued: bool = True

    def snapshot(self):
        return {
            "name": self.name,
            "normal_side": self.normal_side,
            "eur_balance": str(self.eur_balance),
            "usd_balance": str(self.usd_balance),
            "cumulative_reval": str(self.cumulative_reval),
            "accumulator": str(self.accumulator),
        }


@dataclass
class JournalEntry:
    number: int
    account: str
    direction: str  # "Dr" or "Cr"
    amount: Decimal
    currency: str
    memo: str = ""

    def display(self) -> str:
        glyph = circled(self.number)
        s = f"  {glyph} {self.direction}  {self.account:<22s} {fmt(self.amount)} {self.currency}"
        if self.memo:
            s += f"       \u2190 {self.memo}"
        return s

    def to_dict(self):
        return {
            "number": self.number,
            "account": self.account,
            "direction": self.direction,
            "amount": str(q(self.amount)),
            "currency": self.currency,
            "memo": self.memo,
        }


@dataclass
class StepResult:
    step_number: int
    description: str
    journal_entries: List[JournalEntry]
    trial_balance: dict
    verification_lines: List[str]
    net_unrealized: Decimal

    def to_dict(self):
        return {
            "step_number": self.step_number,
            "description": self.description,
            "journal_entries": [e.to_dict() for e in self.journal_entries],
            "trial_balance": self.trial_balance,
            "verification_lines": self.verification_lines,
            "net_unrealized": str(self.net_unrealized),
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

ACCOUNT_ORDER = [
    "EUR Deposit", "EUR Omnibus", "Trading",
    "USD Cash", "Realized FX Gain", "Unrealized FX Gain",
]


class FXEngine:
    def __init__(self, functional_currency="USD", foreign_currency="EUR"):
        self.fc = functional_currency
        self.fgn = foreign_currency
        self.entry_counter = 0
        self.accounts = {
            "EUR Deposit": Account("EUR Deposit", "debit", revalued=True),
            "EUR Omnibus": Account("EUR Omnibus", "credit", revalued=True),
            "Trading": Account("Trading", "debit", revalued=True),
            "USD Cash": Account("USD Cash", "debit", revalued=False),
            "Realized FX Gain": Account("Realized FX Gain", "credit", revalued=False),
            "Unrealized FX Gain": Account("Unrealized FX Gain", "credit", revalued=False),
        }
        self.account_order = ACCOUNT_ORDER

    def _entry(self, account, direction, amount, currency, memo=""):
        self.entry_counter += 1
        return JournalEntry(self.entry_counter, account, direction, amount, currency, memo)

    def _apply(self, entry):
        acct = self.accounts[entry.account]
        sign = D("1") if entry.direction == "Dr" else D("-1")
        if acct.normal_side == "credit":
            sign = -sign
        if entry.currency == self.fgn:
            acct.eur_balance += sign * entry.amount
        else:
            acct.usd_balance += sign * entry.amount

    def _apply_entries(self, entries):
        for e in entries:
            self._apply(e)

    def _trial_balance(self):
        return {name: self.accounts[name].snapshot() for name in self.account_order}

    def _check_trial_balance(self):
        eur_dr = eur_cr = usd_dr = usd_cr = ZERO
        for acct in self.accounts.values():
            if acct.normal_side == "debit":
                if acct.eur_balance >= ZERO:
                    eur_dr += acct.eur_balance
                else:
                    eur_cr += abs(acct.eur_balance)
                if acct.usd_balance >= ZERO:
                    usd_dr += acct.usd_balance
                else:
                    usd_cr += abs(acct.usd_balance)
            else:
                if acct.eur_balance >= ZERO:
                    eur_cr += acct.eur_balance
                else:
                    eur_dr += abs(acct.eur_balance)
                if acct.usd_balance >= ZERO:
                    usd_cr += acct.usd_balance
                else:
                    usd_dr += abs(acct.usd_balance)
        if q(eur_dr) != q(eur_cr) or q(usd_dr) != q(usd_cr):
            raise ValueError(
                f"Trial balance failed! EUR: {q(eur_dr)} Dr vs {q(eur_cr)} Cr, "
                f"USD: {q(usd_dr)} Dr vs {q(usd_cr)} Cr"
            )

    # -- Step processors ---------------------------------------------------

    def process_deposit(self, step_num, amount, rate):
        usd_amount = q(amount * rate)
        entries = [
            self._entry("EUR Deposit", "Dr", amount, self.fgn),
            self._entry("EUR Deposit", "Dr", usd_amount, self.fc),
            self._entry("EUR Omnibus", "Cr", amount, self.fgn),
            self._entry("EUR Omnibus", "Cr", usd_amount, self.fc),
        ]
        self._apply_entries(entries)
        self._check_trial_balance()
        return StepResult(step_num, f"Deposit {fmt(amount)} {self.fgn} (rate {rate})",
                          entries, self._trial_balance(), [], ZERO)

    def process_conversion(self, step_num, amount, rate):
        deposit = self.accounts["EUR Deposit"]
        if amount > deposit.eur_balance:
            raise ValueError(f"Cannot convert {amount} EUR: Deposit only has {deposit.eur_balance}")

        book_rate = deposit.usd_balance / deposit.eur_balance
        source_book_value = q(amount * book_rate)
        proceeds = q(amount * rate)
        realized_gl = proceeds - source_book_value

        entries = [
            self._entry("Trading", "Dr", amount, self.fgn),
            self._entry("EUR Deposit", "Cr", amount, self.fgn),
            self._entry("Trading", "Dr", source_book_value, self.fc, "book value leg"),
            self._entry("EUR Deposit", "Cr", source_book_value, self.fc),
            self._entry("USD Cash", "Dr", proceeds, self.fc),
            self._entry("Trading", "Cr", proceeds, self.fc),
        ]

        abs_gl = abs(realized_gl)
        if realized_gl >= ZERO:
            entries.append(self._entry("Trading", "Dr", abs_gl, self.fc, "realized G/L clearing"))
            entries.append(self._entry("Realized FX Gain", "Cr", abs_gl, self.fc))
        else:
            entries.append(self._entry("Realized FX Gain", "Dr", abs_gl, self.fc, "realized G/L clearing"))
            entries.append(self._entry("Trading", "Cr", abs_gl, self.fc))

        self._apply_entries(entries)
        self.accounts["Trading"].accumulator += source_book_value
        self._check_trial_balance()

        verification = [
            f"Book value of {fmt(amount)} {self.fgn} at blended rate: "
            f"{fmt(amount)} \u00d7 {book_rate} = {fmt(source_book_value)}"
        ]
        return StepResult(step_num, f"Convert {fmt(amount)} {self.fgn} \u2192 {self.fc} (rate {rate})",
                          entries, self._trial_balance(), verification, ZERO)

    def process_revaluation(self, step_num, rate):
        entries = []
        net_unrealized = ZERO
        verification = []

        for name in ["EUR Deposit", "EUR Omnibus", "Trading"]:
            acct = self.accounts[name]
            if acct.eur_balance == ZERO:
                continue

            fair_value = q(acct.eur_balance * rate)
            if name == "Trading":
                adjustment = q(fair_value - (acct.accumulator + acct.cumulative_reval))
            else:
                adjustment = q(fair_value - acct.usd_balance)

            if adjustment == ZERO:
                continue

            abs_adj = abs(adjustment)
            pair = self._make_reval_entries(acct, adjustment, abs_adj)
            entries.extend(pair)
            self._apply_entries(pair)
            acct.cumulative_reval += adjustment

            if acct.normal_side == "debit":
                net_unrealized += adjustment
            else:
                net_unrealized -= adjustment

            verification.append(
                f"{name} ({acct.normal_side}): {fmt(acct.eur_balance)} {self.fgn}, "
                f"adjustment {fmt(adjustment)}"
            )

        self._check_trial_balance()
        verification.append(f"Net unrealized: {fmt(net_unrealized)}")
        return StepResult(step_num, f"Revaluation (rate \u2192 {rate})",
                          entries, self._trial_balance(), verification, q(net_unrealized))

    def _make_reval_entries(self, acct, adjustment, abs_adj):
        if acct.normal_side == "debit":
            if adjustment > ZERO:
                return [
                    self._entry(acct.name, "Dr", abs_adj, self.fc),
                    self._entry("Unrealized FX Gain", "Cr", abs_adj, self.fc),
                ]
            else:
                return [
                    self._entry("Unrealized FX Gain", "Dr", abs_adj, self.fc),
                    self._entry(acct.name, "Cr", abs_adj, self.fc),
                ]
        else:
            if adjustment > ZERO:
                return [
                    self._entry("Unrealized FX Gain", "Dr", abs_adj, self.fc),
                    self._entry(acct.name, "Cr", abs_adj, self.fc),
                ]
            else:
                return [
                    self._entry(acct.name, "Dr", abs_adj, self.fc),
                    self._entry("Unrealized FX Gain", "Cr", abs_adj, self.fc),
                ]

    def _unwind_reval(self, acct, portion, entries):
        if portion == ZERO:
            return ZERO
        abs_portion = abs(portion)
        net = ZERO

        if acct.normal_side == "debit":
            if portion > ZERO:
                pair = [
                    self._entry("Unrealized FX Gain", "Dr", abs_portion, self.fc),
                    self._entry(acct.name, "Cr", abs_portion, self.fc),
                ]
                net -= abs_portion
            else:
                pair = [
                    self._entry(acct.name, "Dr", abs_portion, self.fc),
                    self._entry("Unrealized FX Gain", "Cr", abs_portion, self.fc),
                ]
                net += abs_portion
        else:
            if portion > ZERO:
                pair = [
                    self._entry(acct.name, "Dr", abs_portion, self.fc),
                    self._entry("Unrealized FX Gain", "Cr", abs_portion, self.fc),
                ]
                net += abs_portion
            else:
                pair = [
                    self._entry("Unrealized FX Gain", "Dr", abs_portion, self.fc),
                    self._entry(acct.name, "Cr", abs_portion, self.fc),
                ]
                net -= abs_portion

        entries.extend(pair)
        self._apply_entries(pair)
        acct.cumulative_reval -= portion
        return net

    def process_withdrawal(self, step_num, amount):
        deposit = self.accounts["EUR Deposit"]
        omnibus = self.accounts["EUR Omnibus"]
        if amount > deposit.eur_balance:
            raise ValueError(f"Cannot withdraw {amount} EUR: Deposit only has {deposit.eur_balance}")

        entries = []
        net_unrealized = ZERO
        verification = []

        # Phase 1: Unwind proportional deposit reval
        dep_portion = q(amount / deposit.eur_balance * deposit.cumulative_reval)
        if dep_portion != ZERO:
            net_unrealized += self._unwind_reval(deposit, dep_portion, entries)
            verification.append(f"Unwind deposit reval: {fmt(dep_portion)}")

        # Phase 2: Transfer at book rate
        book_rate = (deposit.usd_balance - deposit.cumulative_reval) / deposit.eur_balance
        book_value = q(amount * book_rate)
        transfer = [
            self._entry("EUR Omnibus", "Dr", amount, self.fgn),
            self._entry("EUR Omnibus", "Dr", book_value, self.fc),
            self._entry("EUR Deposit", "Cr", amount, self.fgn),
            self._entry("EUR Deposit", "Cr", book_value, self.fc),
        ]
        entries.extend(transfer)
        self._apply_entries(transfer)

        # Phase 3: Unwind proportional omnibus reval
        # Use pre-transfer omnibus EUR (current + amount, since Dr reduced it)
        omnibus_eur_before = omnibus.eur_balance + amount
        omni_portion = q(amount / omnibus_eur_before * omnibus.cumulative_reval)
        if omni_portion != ZERO:
            net_unrealized += self._unwind_reval(omnibus, omni_portion, entries)
            verification.append(f"Unwind omnibus reval: {fmt(omni_portion)}")

        verification.append(f"Net unrealized from withdrawal: {fmt(net_unrealized)}")
        self._check_trial_balance()
        return StepResult(step_num, f"Withdraw {fmt(amount)} {self.fgn}",
                          entries, self._trial_balance(), verification, q(net_unrealized))

    def process_settlement(self, step_num, amount):
        trading = self.accounts["Trading"]
        omnibus = self.accounts["EUR Omnibus"]
        if amount > trading.eur_balance:
            raise ValueError(f"Cannot settle {amount} EUR: Trading only has {trading.eur_balance}")

        entries = []
        net_unrealized = ZERO
        verification = []

        # Capture pre-settlement balances
        omnibus_eur_before = omnibus.eur_balance
        trading_eur_before = trading.eur_balance

        # Phase 1: EUR delivery
        eur_delivery = [
            self._entry("EUR Omnibus", "Dr", amount, self.fgn),
            self._entry("Trading", "Cr", amount, self.fgn),
        ]
        entries.extend(eur_delivery)
        self._apply_entries(eur_delivery)

        # Phase 2: Reverse Trading revaluation (proportional)
        proportion = amount / trading_eur_before if trading_eur_before > ZERO else D("1")
        trading_reval_portion = q(proportion * trading.cumulative_reval)
        if trading_reval_portion != ZERO:
            abs_portion = abs(trading_reval_portion)
            if trading_reval_portion < ZERO:
                pair = [
                    self._entry("Trading", "Dr", abs_portion, self.fc),
                    self._entry("Unrealized FX Gain", "Cr", abs_portion, self.fc),
                ]
                net_unrealized += abs_portion
            else:
                pair = [
                    self._entry("Unrealized FX Gain", "Dr", abs_portion, self.fc),
                    self._entry("Trading", "Cr", abs_portion, self.fc),
                ]
                net_unrealized -= abs_portion
            entries.extend(pair)
            self._apply_entries(pair)
            trading.cumulative_reval -= trading_reval_portion
            verification.append(f"Reverse Trading reval: {fmt(trading_reval_portion)}")

        # Phase 3: Unwind proportional Omnibus reval
        omni_portion = q(amount / omnibus_eur_before * omnibus.cumulative_reval)
        if omni_portion != ZERO:
            net_unrealized += self._unwind_reval(omnibus, omni_portion, entries)
            verification.append(f"Unwind omnibus reval: {fmt(omni_portion)}")

        # Phase 4: Zero out proportional accumulator
        acc_portion = q(proportion * trading.accumulator)
        trading.accumulator -= acc_portion

        verification.append(f"Net unrealized from settlement: {fmt(net_unrealized)}")
        self._check_trial_balance()
        return StepResult(step_num, f"Settle {fmt(amount)} {self.fgn}",
                          entries, self._trial_balance(), verification, q(net_unrealized))

    def process_step(self, step_num, step):
        t = step["type"]
        if t == "deposit":
            return self.process_deposit(step_num, d(step["amount"]), d(step["rate"]))
        elif t == "conversion":
            return self.process_conversion(step_num, d(step["amount"]), d(step["rate"]))
        elif t == "revaluation":
            return self.process_revaluation(step_num, d(step["rate"]))
        elif t == "withdrawal":
            return self.process_withdrawal(step_num, d(step["amount"]))
        elif t == "settlement":
            return self.process_settlement(step_num, d(step["amount"]))
        else:
            raise ValueError(f"Unknown step type: {t}")


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_trial_balance(tb, fc, fgn):
    lines = []
    lines.append("")
    hdr1 = f"{'':37s}{fgn:>16s}{'':4s}{fc:>16s}"
    hdr2 = f"{'Account':<23s}{'Normal':<8s}{'Dr':>8s}{'Cr':>8s}{'Dr':>10s}{'Cr':>10s}"
    sep = "\u2500" * 23 + "  " + "\u2500" * 6 + "    " + "\u2500" * 4 + "     " + "\u2500" * 4 + "     " + "\u2500" * 5 + "    " + "\u2500" * 5
    lines.append(hdr1)
    lines.append(hdr2)
    lines.append(sep)

    eur_dr_total = eur_cr_total = usd_dr_total = usd_cr_total = ZERO

    for name in ACCOUNT_ORDER:
        snap = tb[name]
        normal = snap["normal_side"].capitalize()
        eur_bal = D(snap["eur_balance"])
        usd_bal = D(snap["usd_balance"])

        if snap["normal_side"] == "debit":
            if eur_bal >= ZERO:
                eur_dr_s, eur_cr_s = fmt(eur_bal), ""
                eur_dr_total += q(eur_bal)
            else:
                eur_dr_s, eur_cr_s = "", fmt(abs(eur_bal))
                eur_cr_total += q(abs(eur_bal))
            if usd_bal >= ZERO:
                usd_dr_s, usd_cr_s = fmt(usd_bal), ""
                usd_dr_total += q(usd_bal)
            else:
                usd_dr_s, usd_cr_s = "", fmt(abs(usd_bal))
                usd_cr_total += q(abs(usd_bal))
        else:
            if eur_bal >= ZERO:
                eur_dr_s, eur_cr_s = "", fmt(eur_bal)
                eur_cr_total += q(eur_bal)
            else:
                eur_dr_s, eur_cr_s = fmt(abs(eur_bal)), ""
                eur_dr_total += q(abs(eur_bal))
            if usd_bal >= ZERO:
                usd_dr_s, usd_cr_s = "", fmt(usd_bal)
                usd_cr_total += q(usd_bal)
            else:
                usd_dr_s, usd_cr_s = fmt(abs(usd_bal)), ""
                usd_dr_total += q(abs(usd_bal))

        lines.append(
            f"{name:<23s}{normal:<8s}{eur_dr_s:>8s}{eur_cr_s:>8s}{usd_dr_s:>10s}{usd_cr_s:>10s}"
        )

    lines.append(sep)
    balanced = q(eur_dr_total) == q(eur_cr_total) and q(usd_dr_total) == q(usd_cr_total)
    check = "\u2713" if balanced else "\u2717"
    lines.append(
        f"{'Totals':<31s}{fmt(eur_dr_total):>8s}{fmt(eur_cr_total):>8s}"
        f"{fmt(usd_dr_total):>10s}{fmt(usd_cr_total):>10s}  {check}"
    )
    lines.append("")
    return "\n".join(lines)


def format_step(result, fc, fgn):
    lines = []
    lines.append(f"\nSTEP {result.step_number} \u2014 {result.description}")
    if result.verification_lines and result.verification_lines[0].startswith("Book value"):
        lines.append(f"\n  {result.verification_lines[0]}\n")
    lines.append("")
    for entry in result.journal_entries:
        lines.append(entry.display())
    lines.append(format_trial_balance(result.trial_balance, fc, fgn))
    for v in result.verification_lines:
        if not v.startswith("Book value"):
            lines.append(f"  {v}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

DEFAULT_SCENARIO = {
    "functional_currency": "USD",
    "foreign_currency": "EUR",
    "steps": [
        {"type": "deposit", "amount": 60, "rate": 1.10},
        {"type": "deposit", "amount": 40, "rate": 1.12},
        {"type": "conversion", "amount": 50, "rate": 1.15},
        {"type": "revaluation", "rate": 1.20},
        {"type": "withdrawal", "amount": 30},
        {"type": "revaluation", "rate": 1.05},
        {"type": "withdrawal", "amount": 20},
        {"type": "settlement", "amount": 50},
    ],
}


def run_scenario(config, max_step=None):
    engine = FXEngine(
        config.get("functional_currency", "USD"),
        config.get("foreign_currency", "EUR"),
    )
    results = []
    for i, step in enumerate(config["steps"], 1):
        if max_step is not None and i > max_step:
            break
        result = engine.process_step(i, step)
        results.append(result)
    return results, engine


# ---------------------------------------------------------------------------
# Test — verify against walkthrough numbers
# ---------------------------------------------------------------------------

def run_tests():
    results, _ = run_scenario(DEFAULT_SCENARIO)

    def bal(step_idx, name):
        snap = results[step_idx].trial_balance[name]
        return D(snap["eur_balance"]), D(snap["usd_balance"])

    checks = 0
    failures = 0

    def check(desc, actual, expected):
        nonlocal checks, failures
        checks += 1
        if q(actual) != q(expected):
            print(f"  FAIL: {desc}: expected {q(expected)}, got {q(actual)}")
            failures += 1
        else:
            print(f"  OK: {desc}")

    print("Running walkthrough verification...\n")

    # Step 1: Deposit 60 EUR @ 1.10
    eur, usd = bal(0, "EUR Deposit")
    check("Step 1 Deposit EUR", eur, d(60))
    check("Step 1 Deposit USD", usd, d(66))

    # Step 2: Deposit 40 EUR @ 1.12
    eur, usd = bal(1, "EUR Deposit")
    check("Step 2 Deposit EUR", eur, d(100))
    check("Step 2 Deposit USD", usd, d("110.80"))

    # Step 3: Convert 50 EUR @ 1.15
    eur, usd = bal(2, "EUR Deposit")
    check("Step 3 Deposit EUR", eur, d(50))
    check("Step 3 Deposit USD", usd, d("55.40"))
    eur, usd = bal(2, "Trading")
    check("Step 3 Trading EUR", eur, d(50))
    check("Step 3 Trading USD", usd, d(0))
    _, usd = bal(2, "USD Cash")
    check("Step 3 USD Cash", usd, d("57.50"))
    _, usd = bal(2, "Realized FX Gain")
    check("Step 3 Realized", usd, d("2.10"))

    # Step 4: Reval @ 1.20
    eur, usd = bal(3, "EUR Deposit")
    check("Step 4 Deposit EUR", eur, d(50))
    check("Step 4 Deposit USD", usd, d(60))
    _, usd = bal(3, "EUR Omnibus")
    check("Step 4 Omnibus USD", usd, d(120))
    _, usd = bal(3, "Trading")
    check("Step 4 Trading USD", usd, d("4.60"))
    _, usd = bal(3, "Unrealized FX Gain")
    check("Step 4 Unrealized", usd, d(0))

    # Step 5: Withdraw 30 EUR
    eur, usd = bal(4, "EUR Deposit")
    check("Step 5 Deposit EUR", eur, d(20))
    check("Step 5 Deposit USD", usd, d(24))
    eur, usd = bal(4, "EUR Omnibus")
    check("Step 5 Omnibus EUR", eur, d(70))
    check("Step 5 Omnibus USD", usd, d(84))
    _, usd = bal(4, "Unrealized FX Gain")
    check("Step 5 Unrealized", usd, d(0))

    # Step 6: Reval @ 1.05
    _, usd = bal(5, "EUR Deposit")
    check("Step 6 Deposit USD", usd, d(21))
    _, usd = bal(5, "EUR Omnibus")
    check("Step 6 Omnibus USD", usd, d("73.50"))
    _, usd = bal(5, "Trading")
    check("Step 6 Trading USD", usd, d("-2.90"))
    _, usd = bal(5, "Unrealized FX Gain")
    check("Step 6 Unrealized", usd, d(0))

    # Step 7: Withdraw 20 EUR
    eur, usd = bal(6, "EUR Deposit")
    check("Step 7 Deposit EUR", eur, d(0))
    check("Step 7 Deposit USD", usd, d(0))
    eur, usd = bal(6, "EUR Omnibus")
    check("Step 7 Omnibus EUR", eur, d(50))
    check("Step 7 Omnibus USD", usd, d("52.50"))
    _, usd = bal(6, "Unrealized FX Gain")
    check("Step 7 Unrealized", usd, d(0))

    # Step 8: Settlement
    eur, usd = bal(7, "EUR Omnibus")
    check("Step 8 Omnibus EUR", eur, d(0))
    check("Step 8 Omnibus USD", usd, d("55.40"))
    eur, usd = bal(7, "Trading")
    check("Step 8 Trading EUR", eur, d(0))
    check("Step 8 Trading USD", usd, d(0))
    _, usd = bal(7, "USD Cash")
    check("Step 8 USD Cash", usd, d("57.50"))
    _, usd = bal(7, "Unrealized FX Gain")
    check("Step 8 Unrealized", usd, d(0))

    print(f"\n{checks} checks, {failures} failures")
    return failures == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="FX Scenario Calculator")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a scenario")
    run_p.add_argument("file", help="YAML scenario file")
    run_p.add_argument("--step", type=int, help="Run up to step N")
    run_p.add_argument("--json", dest="json_output", action="store_true", help="JSON output")

    init_p = sub.add_parser("init", help="Write default scenario")
    init_p.add_argument("file", help="Output YAML file")

    sub.add_parser("test", help="Verify against walkthrough numbers")

    args = parser.parse_args()

    if args.command == "run":
        with open(args.file) as f:
            config = yaml.safe_load(f)
        results, engine = run_scenario(config, args.step)
        if args.json_output:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            for r in results:
                print(format_step(r, engine.fc, engine.fgn))

    elif args.command == "init":
        with open(args.file, "w") as f:
            yaml.dump(DEFAULT_SCENARIO, f, default_flow_style=False, sort_keys=False)
        print(f"Wrote default scenario to {args.file}")

    elif args.command == "test":
        success = run_tests()
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
