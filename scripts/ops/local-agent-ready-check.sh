#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

info() {
  printf '[ready-check] %s\n' "$1"
}

info "checking Python syntax"
python3 -m py_compile tools/*.py tests/*.py

info "running regression tests"
python3 tests/run_regression_tests.py

info "validating stream registry"
python3 tools/validate_stream_registry.py

info "validating architecture consistency"
python3 tools/validate_architecture_consistency.py

info "validating synthesis publication gate"
python3 tools/validate_synthesis_publication_gate.py

info "validating synthesis quality gate"
python3 tools/validate_synthesis_quality_gate.py

info "checking diff whitespace"
git diff --check

info "removing Python bytecode caches"
rm -rf tools/__pycache__ tests/__pycache__

info "ready"
