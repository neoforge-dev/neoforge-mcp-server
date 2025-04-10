# Active Context

## Phase
- Phase 2: BaseServer Migration & >90% Test Coverage.

## Current Task
- Fix remaining failing tests in `tests/llm/test_llm_server.py`.
  - `test_generate_endpoint_default_model` (ValidationError)
  - `test_generate_model_not_found` (MCPError instead of NotFoundError)
- *Previously addressed in this session:* `test_list_models_unauthorized`, `test_list_models_endpoint`, `test_tokenize_unauthorized`, `test_tokenize_model_not_found`.

## Other Known Failures (To Address Next)
- `test_list_sessions` (Location TBD - likely NeoOps or Core)
- JS Parser: `test_async_await_support`, `test_export_variants` (Location TBD)

## Recent System Changes (Impact Summary)
- **Routing:** Placeholder `/api/v1/models` removed from `BaseServer` to fix conflict.
- **Error Handling:**
    - `BaseServer` uses `ErrorHandlerMiddleware`.
    - Endpoints use `@handle_exceptions` & specific `MCPError` subclasses (`AuthorizationError`, `NotFoundError`).
    - LLM `tokenize` & `generate` updated to raise `NotFoundError` for missing models.
- **Security:** `SecurityManager` logic updated (`check_permission` includes role check).
- **Testing:**
    - LLM tests updated for new error/response structures.
    - `TestClient` usage standardized in LLM tests (`raise_server_exceptions=False` for checking HTTP responses).

## Next Steps (Priority Order)
1. Fix `test_generate_endpoint_default_model` (LLM Server).
2. Fix `test_generate_model_not_found` (LLM Server).
3. Re-run all LLM tests (`tests/llm/test_llm_server.py`).
4. Investigate/fix `test_list_sessions`.
5. Investigate/fix JS Parser tests (`test_async_await_support`, `test_export_variants`).
6. Systematically increase test coverage across all servers (Target: >90%).

## Test Status / Coverage
- LLM Server (`tests/llm/test_llm_server.py`): 11/14 passing.
- Overall Coverage: ~9% (Target: >90%).

## Active Decisions
- Standardized error handling via `MCPError` and `ErrorHandlerMiddleware`.
- Using `ApiKey` dataclass and explicit permissions in `SecurityManager`.
- `loguru` `bind` method expected by middleware; mocks need to support this.

# --- Active Context ---
# Status: All servers migrated. Basic tests passing for all servers.
# Next: Address the 3 known failing tests, starting with test_list_sessions.
# Blockers: Low overall test coverage (~9%) remains a priority.
# Decisions: Used Pydantic models for NeoDO request validation. Centralized DO mocking in fixture.

# --- Progress ---
# BaseServer: Done & Tests Passing.
# Server Migration: 4/7 Done (Core, LLM, NeoDev, NeoOps).
# Testing: BaseServer, LLMServer, NeoDevServer tests passing. Initial NeoOpsServer tests passing. Overall coverage low (~9%). 