#!/bin/bash
# Code Quality and Development Scripts for RAG Chatbot
# This script provides convenient commands for code formatting, linting, and testing

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# Change to project root
cd "$PROJECT_ROOT"

# Function to show usage
show_usage() {
    cat << EOF
Usage: ./scripts/quality.sh <command>

Code Quality Commands:
  format           Format code with black (auto-fixes formatting issues)
  check-format     Check if code is properly formatted (no changes made)
  lint             Run ruff linter to check for code issues
  lint-fix         Run ruff with auto-fix for linting issues
  type-check       Run mypy static type checker
  test             Run all tests
  test-cov         Run tests with coverage report
  all              Run all quality checks (format, lint, type-check, test)

Examples:
  ./scripts/quality.sh format          # Format all code
  ./scripts/quality.sh all             # Run all checks
  ./scripts/quality.sh lint-fix        # Fix linting issues automatically

EOF
}

# Format code with black
format_code() {
    print_header "Formatting Code with Black"
    print_info "Running: black backend/"
    uv run black backend/
    print_success "Code formatted successfully"
}

# Check code formatting
check_format() {
    print_header "Checking Code Format"
    print_info "Running: black --check backend/"
    if uv run black --check backend/; then
        print_success "Code is properly formatted"
        return 0
    else
        print_error "Code formatting issues found"
        print_info "Run 'format' to fix automatically"
        return 1
    fi
}

# Run ruff linter
lint() {
    print_header "Running Ruff Linter"
    print_info "Running: ruff check backend/"
    if uv run ruff check backend/; then
        print_success "No linting issues found"
        return 0
    else
        print_error "Linting issues found"
        print_info "Run 'lint-fix' to attempt auto-fix"
        return 1
    fi
}

# Run ruff with auto-fix
lint_fix() {
    print_header "Running Ruff Linter with Auto-Fix"
    print_info "Running: ruff check --fix backend/"
    uv run ruff check --fix backend/ || true
    print_success "Linting fixes applied"
}

# Run mypy type checker
type_check() {
    print_header "Running MyPy Type Checker"
    print_info "Running: mypy backend/"
    if uv run mypy backend/; then
        print_success "No type checking issues found"
        return 0
    else
        print_warning "Type checking issues found (non-blocking)"
        return 0
    fi
}

# Run tests
run_tests() {
    print_header "Running Tests"
    print_info "Running: pytest backend/tests/"
    uv run pytest backend/tests/ -v
    print_success "Tests passed"
}

# Run tests with coverage
run_test_coverage() {
    print_header "Running Tests with Coverage"
    print_info "Running: pytest backend/tests/ --cov=backend --cov-report=term-missing"
    uv run pytest backend/tests/ --cov=backend --cov-report=term-missing
    print_success "Tests with coverage completed"
}

# Run all quality checks
run_all_checks() {
    print_header "Running All Quality Checks"

    local exit_code=0

    # Format check
    if ! check_format; then
        exit_code=1
    fi

    # Lint
    if ! lint; then
        exit_code=1
    fi

    # Type check (don't fail on type errors)
    type_check || true

    # Tests
    if ! run_tests; then
        exit_code=1
    fi

    if [ $exit_code -eq 0 ]; then
        print_header "All Quality Checks Passed! ✓"
    else
        print_header "Some Quality Checks Failed ✗"
    fi

    return $exit_code
}

# Main script logic
case "${1:-}" in
    format)
        format_code
        ;;
    check-format)
        check_format
        ;;
    lint)
        lint
        ;;
    lint-fix)
        lint_fix
        ;;
    type-check)
        type_check
        ;;
    test)
        run_tests
        ;;
    test-cov)
        run_test_coverage
        ;;
    all)
        run_all_checks
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
