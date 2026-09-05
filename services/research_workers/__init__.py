"""research_workers — discovery, document pipeline, and LLM agent jobs.

Home of the nine-agent research floor (`agents/`) and the mandatory
`llm_gateway/`. Per docs/LLM_GATEWAY.md, agents NEVER call a provider directly;
they call `LLMGateway.request(...)`. Built out in Phase 3.
"""
