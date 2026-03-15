#!/bin/bash

# Spectra - Verification Script
# Verifies all fixes are correctly applied

echo "======================================"
echo "Spectra - Fix Verification"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Check 1: Model name in code
echo "1. Checking model name in code..."
MODEL_IN_CODE=$(grep "LIVE_MODEL = " backend/app/streaming/session.py | grep -o '"[^"]*"' | tr -d '"')
if [ "$MODEL_IN_CODE" = "gemini-2.0-flash-exp" ]; then
    echo -e "   ${GREEN}✓${NC} Model name correct: $MODEL_IN_CODE"
else
    echo -e "   ${RED}✗${NC} Model name incorrect: $MODEL_IN_CODE (expected: gemini-2.0-flash-exp)"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: No invalid model references in code
echo ""
echo "2. Checking for invalid model references in code..."
INVALID_REFS=$(grep -r "gemini-2.5-flash-native-audio-latest" --include="*.py" --include="*.js" --include="*.ts" --include="*.tsx" . 2>/dev/null | wc -l)
if [ "$INVALID_REFS" -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} No invalid model references in code"
else
    echo -e "   ${RED}✗${NC} Found $INVALID_REFS invalid model references in code"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: No invalid model references in config
echo ""
echo "3. Checking for invalid model references in config..."
INVALID_CONFIG=$(grep -r "gemini-2.5-flash-native-audio-latest" --include="*.tf" --include="*.mmd" --include=".env.example" . 2>/dev/null | wc -l)
if [ "$INVALID_CONFIG" -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} No invalid model references in config"
else
    echo -e "   ${RED}✗${NC} Found $INVALID_CONFIG invalid model references in config"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: README consistency
echo ""
echo "4. Checking README consistency..."
README_REFS=$(grep -c "gemini-2.0-flash-exp" README.md)
if [ "$README_REFS" -ge 3 ]; then
    echo -e "   ${GREEN}✓${NC} README has $README_REFS references to correct model"
else
    echo -e "   ${YELLOW}⚠${NC} README has only $README_REFS references (expected at least 3)"
fi

# Check 5: Typing delay
echo ""
echo "5. Checking typing delay..."
if grep -q "await sleep(15)" extension/content.js; then
    echo -e "   ${GREEN}✓${NC} Typing delay is 15ms"
else
    echo -e "   ${RED}✗${NC} Typing delay is not 15ms"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Architecture diagrams
echo ""
echo "6. Checking architecture diagrams..."
if grep -q "gemini-2.0-flash-exp" ARCHITECTURE.md && grep -q "gemini-2.0-flash-exp" architecture.mmd; then
    echo -e "   ${GREEN}✓${NC} Architecture diagrams use correct model"
else
    echo -e "   ${RED}✗${NC} Architecture diagrams have incorrect model"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: Duplicate content
echo ""
echo "7. Checking for duplicate content..."
DUPLICATE_COUNT=$(grep -c "## 📊 By the Numbers" README.md)
if [ "$DUPLICATE_COUNT" -eq 1 ]; then
    echo -e "   ${GREEN}✓${NC} No duplicate 'By the Numbers' section"
else
    echo -e "   ${RED}✗${NC} Found $DUPLICATE_COUNT 'By the Numbers' sections (expected 1)"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "======================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "======================================"
    echo ""
    echo "The project is ready for:"
    echo "  • Production deployment"
    echo "  • Competition submission"
    echo "  • User testing"
    exit 0
else
    echo -e "${RED}✗ $ERRORS check(s) failed${NC}"
    echo "======================================"
    echo ""
    echo "Please review the errors above and fix them."
    exit 1
fi
