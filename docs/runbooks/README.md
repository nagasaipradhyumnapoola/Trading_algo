# Runbooks

Operational procedures for Indian Alpha. Every runbook ends with the system in a
**safe** state: deterministic results preserved, nothing fabricated, no broker action.

- [Feed outage / stale data](feed-outage.md)
- [LLM provider outage](provider-outage.md)
- [Model rollback](model-rollback.md)
- [Backup & restore drill](restore-drill.md)

Core principle: **degrade, don't fabricate.** When inputs are missing, label the
degradation in the UI and suppress the affected recommendations — never invent data,
probabilities, or analysis to fill the gap.
