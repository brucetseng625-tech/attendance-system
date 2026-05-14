#!/usr/bin/env bash
# verify_setup.sh - Smoke test for the attendance system.
# Checks Python version, required packages, required files, and runs pytest.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "========================================"
echo "  Attendance System - Setup Verification"
echo "========================================"
echo ""

# -----------------------------------------------------------
# 1. Python version
# -----------------------------------------------------------
echo "--- Python Version ---"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        pass "Python ${PY_VERSION} (>= 3.10)"
    else
        fail "Python ${PY_VERSION} (< 3.10, need >= 3.10)"
    fi
else
    fail "python3 not found"
fi
echo ""

# -----------------------------------------------------------
# 2. Required packages
# -----------------------------------------------------------
echo "--- Required Packages ---"
PACKAGES=("supervision" "ultralytics" "insightface" "streamlit" "opencv-python" "numpy" "pyyaml" "loguru")
for pkg in "${PACKAGES[@]}"; do
    # Normalize: opencv-python imports as cv2
    import_name="$pkg"
    case "$pkg" in
        opencv-python) import_name="cv2" ;;
        pyyaml)        import_name="yaml" ;;
    esac
    if python3 -c "import ${import_name}" 2>/dev/null; then
        ver=$(python3 -c "import ${import_name}; print(getattr(${import_name}, '__version__', 'unknown'))" 2>/dev/null || echo "installed")
        pass "${pkg} (${ver})"
    else
        fail "${pkg} (not installed)"
    fi
done
echo ""

# -----------------------------------------------------------
# 3. Required project files
# -----------------------------------------------------------
echo "--- Required Files ---"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REQUIRED_FILES=(
    "src/__init__.py"
    "src/config.py"
    "src/face_db.py"
    "src/attendance_logger.py"
    "src/detector.py"
    "src/face_recognizer.py"
    "src/ui/__init__.py"
    "src/ui/streamlit_app.py"
    "main.py"
    "config.yaml"
    "requirements.txt"
    "README.md"
    "tests/__init__.py"
    "tests/test_integration.py"
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "${PROJECT_ROOT}/${f}" ]; then
        pass "${f}"
    else
        fail "${f}"
    fi
done

# Check directories
for d in tests data src src/ui; do
    if [ -d "${PROJECT_ROOT}/${d}" ]; then
        pass "${d}/ (directory)"
    else
        fail "${d}/ (directory missing)"
    fi
done
echo ""

# -----------------------------------------------------------
# 4. Run pytest
# -----------------------------------------------------------
echo "--- Running pytest ---"
cd "$PROJECT_ROOT"
if python3 -m pytest tests/test_integration.py -v --tb=short 2>&1; then
    pass "Integration tests passed"
else
    fail "Integration tests failed"
fi
echo ""

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
echo "========================================"
echo "  Summary: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
echo "========================================"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

exit 0
