#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# scripts/run_tests.sh — Run the full Plan B test suite locally
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=============================="
echo "  Plan B — Test Suite Runner"
echo "=============================="

# 1. Ensure dependencies are installed
echo ""
echo "→ Checking dependencies..."
pip install --quiet pytest flask pandas 2>/dev/null || pip install --quiet --break-system-packages pytest flask pandas

# 2. Generate test fixtures (idempotent)
echo "→ Generating test data fixtures..."
python3 "$PROJECT_ROOT/tests/test_data/generate_test_data.py"

# 3. Run pytest
echo ""
echo "→ Running tests..."
cd "$PROJECT_ROOT"
python3 -m pytest tests/ -v --tb=short "$@"

echo ""
echo "=============================="
echo "  All tests complete."
echo "=============================="
