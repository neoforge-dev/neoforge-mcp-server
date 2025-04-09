# Active Context - Neo MCP Server Refactor

**Current Focus**: Migrate the final server (`NeoDOServer`) to the `BaseServer` architecture.

**Current Task**: Start the migration of `NeoDOServer` to use `BaseServer`.

**Recent Changes / Decisions**:
*   `NeoLLMServer` migration verified (already used `BaseServer`), security dependencies integrated, and tests updated/passing.
*   `NeoLocalServer` successfully migrated to `BaseServer`, tests passing.
*   Resolved issues with API key loading (`ConfigManager`) and validation/permission checks (`SecurityManager`) for config-defined keys.
*   Overall test coverage remains low (~9%) and below the 9% threshold.
*   Decided to defer addressing low coverage and warnings until all servers are migrated to `BaseServer`.

**Next Steps**:
1.  **Refactor `NeoDOServer`**: Update `server/neodo/server.py` to inherit from `BaseServer`, remove redundant setup, adjust `main` function/factory, integrate security dependencies.
2.  **Add `NeoDOServer` Basic Tests**: Create `tests/neodo/test_neodo_server.py` with tests for basic initialization and the `/health` endpoint using the factory pattern.
3.  **Add `NeoDOServer` Placeholder Endpoint Tests**: Add tests for key DO endpoints (e.g., `/droplets`, `/databases`) using valid API keys from config.
4.  Plan next steps (likely increasing test coverage).

**Active Considerations / Questions**:
*   Need to ensure DigitalOcean specific clients/managers in `NeoDOServer` correctly receive the `ServerConfig` object from `BaseServer` during initialization.
*   Remember to address the `PytestDeprecationWarning` and `Coverage Warning` after migrations.

# --- Active Context ---
# Status: Completed NeoOpsServer migration to BaseServer & initial tests passing.
# Next: Add tests for NeoOpsServer endpoints (placeholder /processes, /resources).
# Blockers: Low overall test coverage remains a priority.
# Decisions: Placeholder logic used for LLM/NeoDev/NeoOps tests. Security integration deferred.

# --- Progress ---
# BaseServer: Done & Tests Passing.
# Server Migration: 4/7 Done (Core, LLM, NeoDev, NeoOps).
# Testing: BaseServer, LLMServer, NeoDevServer tests passing. Initial NeoOpsServer tests passing. Overall coverage low (~9%). 