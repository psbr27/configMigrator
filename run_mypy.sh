#!/bin/bash
# Script to run mypy type checking on the project

echo "Running mypy type checking on source files..."
source venv/bin/activate
mypy src/ --ignore-missing-imports --show-error-codes --pretty

echo ""
echo "To fix mypy issues, you can:"
echo "1. Add type annotations to functions"
echo "2. Fix import ordering issues"
echo "3. Add '# type: ignore' comments for unavoidable issues"
echo "4. Install missing type stubs with: pip install types-<package-name>"
