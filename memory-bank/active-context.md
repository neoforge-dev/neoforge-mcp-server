# Active Context - MCP Refactor

## Current Focus
- Phase 2: BaseServer Migration & Test Coverage (>90% target)
- Fixing 3 failing tests:
  1. test_list_sessions (status missing in list_processes)
  2. test_async_await_support
  3. test_export_variants

## Recent Changes
- All servers migrated to BaseServer
- Basic health tests passing
- Fixed NeoDO test mocking/validation
- Enhanced JS parser (exports, variables)

## Next Steps
1. Fix test_list_sessions (add status)
2. Address JS parser test failures
3. Increase test coverage (>90%)

## Active Decisions
- Using Pydantic for NeoDO validation
- Centralized NeoDO mocking
- JS parser fixes implemented

## Status
- BaseServer: Done
- Server Migration: 4/7 Complete
- Test Coverage: ~9% (Target: >90%)

# --- Active Context ---
# Status: All servers migrated. Basic tests passing for all servers.
# Next: Address the 3 known failing tests, starting with test_list_sessions.
# Blockers: Low overall test coverage (~9%) remains a priority.
# Decisions: Used Pydantic models for NeoDO request validation. Centralized DO mocking in fixture.

# --- Progress ---
# BaseServer: Done & Tests Passing.
# Server Migration: 4/7 Done (Core, LLM, NeoDev, NeoOps).
# Testing: BaseServer, LLMServer, NeoDevServer tests passing. Initial NeoOpsServer tests passing. Overall coverage low (~9%). 