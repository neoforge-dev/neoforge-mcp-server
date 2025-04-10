# Active Context

## Phase
- Phase 2: BaseServer Migration & >90% Test Coverage.

## Current Task
- Systematically increase test coverage across all servers (Target: >90%).
- **Currently working on:** Implementing tests for `CoreServer` (`server/core/server.py`) located in `tests/core/test_core_server.py`.
  - Added basic fixtures (TestClient, mocked SecurityManager/CommandExecutor).
  - Added tests for `/health`.
  - Added tests for `/api/v1/execute`.
  - Added tests for `/api/v1/terminate/{pid}`.
  - Added tests for `/api/v1/output/{pid}`.
  - Added tests for `/api/v1/processes`.
  - Added tests for `/api/v1/block` and `/api/v1/unblock`.
  - **Next for CoreServer:** Add tests for `/sse`.

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
1.  **Complete `CoreServer` Tests:** Finish writing tests for `CoreServer` (`/sse` endpoint).
2.  **Run CoreServer Coverage:** Execute `pytest --cov=server/core tests/core/` to assess coverage.
3.  **Address Utility Modules (`server/utils`):** Write unit tests for core utilities:
    - `error_handling.py`
    - `config.py`
    - `logging.py`
    - `security.py`
    - `command_executor.py` (if not sufficiently covered by CoreServer tests)
    - `file_operations.py`, `monitoring.py`, `validation.py`
4.  **Address `LLMServer` (`server/llm`):** Write/improve tests for:
    - `manager.py` (unit tests, mock external calls)
    - `models.py` (unit tests, mock external calls/local loading)
    - `server.py` (integration tests for API endpoints)
5.  **Address `Code Understanding` (`server/code_understanding`):** Prioritize key modules:
    - `parser.py`, `analyzer.py`, `extractor.py`, `language_adapters.py`
6.  **Address Remaining Neo* Servers:** Write integration tests for specific functionalities:
    - `NeoDO`, `NeoDev`, `NeoOps`, `NeoLocal`

## Test Status / Coverage
- LLM Server (`tests/llm/test_llm_server.py`): 14/14 passing (100%).
- LLM Server implementation coverage: 92%.
- `test_list_sessions_empty`: Fixed and passing.
- JS Parser tests: All now passing.
- **CoreServer Tests (`tests/core/test_core_server.py`):** In progress. Basic structure and tests for execute, terminate, output, processes, block/unblock endpoints implemented. `/sse` tests pending.
- Overall Coverage: ~14.7% (Target: >90%). *Note: Detailed analysis indicated widespread 0% coverage in many modules, requiring systematic effort.*

## Active Decisions
- Standardized error handling via `MCPError` and `ErrorHandlerMiddleware`.
- Using `ApiKey` dataclass and explicit permissions in `SecurityManager`.
- `loguru` `bind` method expected by middleware; mocks need to support this.
- Parameters for model operations are now passed only when they have non-None values.
- Renamed methods in server/core/__init__.py need to be reflected in tests (e.g., list_sessions → list_processes).
- JS Parser tests looking for specific export types must check for the correct property names used by the implementation.
- **Testing Strategy:** Adopted a prioritized approach focusing on Utilities -> Core -> LLM -> Neo* servers.
- **CoreServer Test Fixtures:** Standardized fixtures for `TestClient`, mocked `SecurityManager`, `CommandExecutor`, and `ApiKey`. Using `patch.object` within fixtures to inject mocks.

# --- Active Context ---
# Status: All servers migrated. All previously failing tests fixed. Test implementation for `CoreServer` is in progress.
# Next: Complete `CoreServer` tests (SSE endpoint), then move to testing `server/utils`.
# Blockers: Low overall test coverage (~14.7%) remains the primary focus. Widespread 0% coverage identified in core utilities and servers.
# Decisions: Prioritized testing plan established. Standard fixtures for CoreServer tests created.

# --- Progress ---
# BaseServer: Done & Tests Passing.
# Server Migration: All servers migrated.
# Testing: LLMServer (92% cov), BaseServer tests passing. System utils/JS parser tests fixed. **CoreServer tests in progress.** Overall coverage low (~14.7%). 