# Runbook: Model rollback

**When:** drift detected (PSI > threshold in `services/monitoring/drift`), a
calibration regression, or a champion underperforming its baseline out-of-sample.

**Steps:**
1. Confirm the regression: compare the current champion's OOS metrics against the
   predefined baseline and the prior champion's model card.
2. Roll back: `ModelRegistry.rollback()` promotes the previous champion and demotes
   the current one. **Code/config only — no data migration.**
3. Verify: `registry.champion()` returns the expected model; reproducibility test
   passes (same snapshot + feature/label versions → same metrics).
4. Open a review ticket for the demoted model; keep its card and metrics visible in
   the audit record (never delete a failed model's history).

**Champion/challenger:** promote a challenger only after it beats the baseline on an
untouched period after costs (`beats_baseline`). Never tune on the final test set.
