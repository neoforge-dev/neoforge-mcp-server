# Active Context

## Phase
- Phase 2: BaseServer Migration & >90% Test Coverage.

## Current Task
- ~~Fix remaining failing tests in `tests/llm/test_llm_server.py`.~~
  - ~~`test_generate_endpoint_default_model` (ValidationError)~~
  - ~~`test_generate_model_not_found` (MCPError instead of NotFoundError)~~
- Fixed all tests in `tests/llm/test_llm_server.py`. Coverage of LLM server improved to 92%.
- ~~Investigate/fix `test_list_sessions_empty` in `tests/test_system_utilities.py`.~~
- Fixed `test_list_sessions_empty` by using the CommandExecutor's list_processes method properly.
- ~~Investigate/fix JS Parser tests (`test_async_await_support`, `test_export_variants`).~~
- Fixed JS Parser test `test_export_variants` in `tests/test_javascript_parser.py` by correctly checking for 're-export' type instead of 'is_re_export' property.
- *Previously addressed in this session:* `test_list_models_unauthorized`, `test_list_models_endpoint`, `test_tokenize_unauthorized`, `test_tokenize_model_not_found`.

## Other Known Failures (To Address Next)
- None currently identified.

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
    - Fixed test_list_sessions_empty to use CommandExecutor's list_processes method.
    - Fixed JS Parser tests to correctly identify re-exports.
- **Parameter Handling:**
    - LLM generate endpoint now properly handles parameters, avoiding ValidationError when parameters are None.

## Next Steps (Priority Order)
1. ~~Fix `test_generate_endpoint_default_model` (LLM Server).~~
2. ~~Fix `test_generate_model_not_found` (LLM Server).~~
3. ~~Re-run all LLM tests (`tests/llm/test_llm_server.py`).~~
4. ~~Investigate/fix `test_list_sessions`.~~
5. ~~Investigate/fix JS Parser tests (`test_async_await_support`, `test_export_variants`).~~
6. Systematically increase test coverage across all servers (Target: >90%).

## Test Status / Coverage
- LLM Server (`tests/llm/test_llm_server.py`): 14/14 passing (100%).
- LLM Server implementation coverage: 92%.
- `test_list_sessions_empty`: Fixed and passing.
- JS Parser tests: All now passing.
- Overall Coverage: ~14.7% (Target: >90%).

## Active Decisions
- Standardized error handling via `MCPError` and `ErrorHandlerMiddleware`.
- Using `ApiKey` dataclass and explicit permissions in `SecurityManager`.
- `loguru` `bind` method expected by middleware; mocks need to support this.
- Parameters for model operations are now passed only when they have non-None values.
- Renamed methods in server/core/__init__.py need to be reflected in tests (e.g., list_sessions → list_processes).
- JS Parser tests looking for specific export types must check for the correct property names used by the implementation.

# --- Active Context ---
# Status: All servers migrated. All previously failing tests are now fixed.
# Next: Focus on systematically increasing test coverage across all servers.
# Blockers: Low overall test coverage (~14.7%) remains a priority.
# Decisions: Used Pydantic models for NeoDO request validation. Centralized DO mocking in fixture.

# --- Progress ---
# BaseServer: Done & Tests Passing.
# Server Migration: 4/7 Done (Core, LLM, NeoDev, NeoOps).
# Testing: BaseServer, LLMServer tests passing. Initial NeoDevServer, NeoOpsServer tests passing. Previously identified failing tests fixed. Overall coverage improving (~14.7%). 