"""Explicit, configurable cost model. Net results are always reported after costs.

Costs are applied on both legs: adverse slippage on entry and exit prices, plus
brokerage + statutory/exchange charges on each notional. Numbers are illustrative
defaults to be finalized in Phase 0 (docs/outcome-definitions.md), not real
broker figures.
"""

from __future__ import annotations

from pydantic import BaseModel


class CostModel(BaseModel):
    slippage_bps: float = 5.0        # adverse price move per leg (basis points)
    brokerage_bps: float = 3.0       # per leg
    statutory_bps: float = 10.0      # STT/exchange/GST/stamp bundled, per leg (placeholder)

    def net_return(self, entry: float, exit: float) -> float:
        """Net fractional return of a long round-trip after slippage + charges."""
        slip = self.slippage_bps / 1e4
        entry_eff = entry * (1 + slip)      # pay up on entry
        exit_eff = exit * (1 - slip)        # give up on exit
        gross = (exit_eff - entry_eff) / entry_eff
        charges = 2 * (self.brokerage_bps + self.statutory_bps) / 1e4
        return gross - charges

    @staticmethod
    def gross_return(entry: float, exit: float) -> float:
        return (exit - entry) / entry
