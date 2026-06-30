# Task: Fix Semantic Routing

Use this template for narrow semantic routing fixes.

## Scope

- Keep the patch focused on routing behavior and its tests.
- Prefer tests first, or add tests with the patch when the existing test surface
  is insufficient.
- Do not touch `dispatches/`.
- Do not change `.github/workflows/daily-radar.yml` unless explicitly requested.
- Do not change `automation/daily-radar` unless explicitly requested.

## Expected Workflow

1. Identify the failing or missing routing behavior.
2. Add or update the narrowest relevant test.
3. Patch the routing implementation.
4. Run the targeted routing test.
5. Run relevant regression tests or validators before reporting ready.

## Handoff

Return changed files, tests, risks and ready/not ready status.
