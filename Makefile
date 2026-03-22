.PHONY: test test-verbose test-auth test-app test-integration fixtures

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Run with full output
test-verbose:
	python -m pytest tests/ -v --tb=long -s

# Run individual test files
test-auth:
	python -m pytest tests/test_auth.py -v

test-app:
	python -m pytest tests/test_app.py -v

test-integration:
	python -m pytest tests/test_integration.py -v

# Regenerate test fixtures
fixtures:
	python tests/test_data/generate_test_data.py
