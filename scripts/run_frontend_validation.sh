#!/bin/bash
# Frontend validation suite for Phase 8
# Runs accessibility, visual, and performance checks
set -e

echo "=== Frontend Validation Suite ==="
echo "Starting: $(date)"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Results directory
RESULTS_DIR="docs/results"
mkdir -p "$RESULTS_DIR"

echo "Step 1: TypeScript type checking..."
cd frontend
if npx tsc --noEmit; then
    echo -e "${GREEN}✓ TypeScript check passed${NC}"
else
    echo -e "${RED}✗ TypeScript check failed${NC}"
    exit 1
fi

echo ""
echo "Step 2: Building production bundle..."
npm run build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build succeeded${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo "Step 3: Measuring bundle sizes..."
echo "Entry bundle (VITE_ENABLE_WORLD=false):"
ls -lh dist/assets/index-*.js | awk '{print $5, $9}'
ENTRY_SIZE=$(ls -l dist/assets/index-*.js | awk '{print $5}')

# Check for three.js chunk
echo "Lazy chunks:"
ls -lh dist/assets/*.js | grep -v index | awk '{print $5, $9}' || echo "No additional chunks"

# Build with world enabled
echo ""
echo "Building with VITE_ENABLE_WORLD=true..."
VITE_ENABLE_WORLD=true npm run build > /dev/null 2>&1
echo "Entry bundle (VITE_ENABLE_WORLD=true):"
ls -lh dist/assets/index-*.js | awk '{print $5, $9}'

echo ""
echo "Step 4: Starting preview server..."
npx vite preview --port 4173 &
PREVIEW_PID=$!
sleep 5

# Wait for server to be ready
MAX_RETRIES=10
RETRY=0
until curl -s http://localhost:4173 > /dev/null || [ $RETRY -eq $MAX_RETRIES ]; do
    echo "Waiting for preview server... ($RETRY/$MAX_RETRIES)"
    sleep 2
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Preview server failed to start${NC}"
    kill $PREVIEW_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Preview server running on http://localhost:4173${NC}"

echo ""
echo "Step 5: Running Playwright accessibility tests..."
# Note: Requires backend running on :8000 and seeded admin user
if npx playwright test e2e/a11y-visual.spec.ts; then
    echo -e "${GREEN}✓ Accessibility tests passed${NC}"
    A11Y_RESULT="PASS"
else
    echo -e "${RED}✗ Accessibility tests failed${NC}"
    A11Y_RESULT="FAIL"
fi

echo ""
echo "Step 6: Running Lighthouse..."
# Run Lighthouse on Ask page (requires authenticated session)
if npx lighthouse http://localhost:4173/ask \
    --only-categories=performance,accessibility \
    --output=json \
    --output-path="../$RESULTS_DIR/lighthouse-ask.json" \
    --chrome-flags="--headless"; then
    echo -e "${GREEN}✓ Lighthouse completed${NC}"
    
    # Extract scores
    PERF_SCORE=$(jq '.categories.performance.score * 100' "../$RESULTS_DIR/lighthouse-ask.json")
    A11Y_SCORE=$(jq '.categories.accessibility.score * 100' "../$RESULTS_DIR/lighthouse-ask.json")
    FCP=$(jq '.audits["first-contentful-paint"].numericValue / 1000' "../$RESULTS_DIR/lighthouse-ask.json")
    LCP=$(jq '.audits["largest-contentful-paint"].numericValue / 1000' "../$RESULTS_DIR/lighthouse-ask.json")
    CLS=$(jq '.audits["cumulative-layout-shift"].numericValue' "../$RESULTS_DIR/lighthouse-ask.json")
    
    echo "  Performance: $PERF_SCORE"
    echo "  Accessibility: $A11Y_SCORE"
    echo "  FCP: ${FCP}s"
    echo "  LCP: ${LCP}s"
    echo "  CLS: $CLS"
else
    echo -e "${RED}✗ Lighthouse failed${NC}"
    PERF_SCORE="N/A"
    A11Y_SCORE="N/A"
fi

# Stop preview server
kill $PREVIEW_PID 2>/dev/null || true

echo ""
echo "=== Validation Complete ==="
echo "Results:"
echo "  TypeScript: PASS"
echo "  Build: PASS"
echo "  A11y Tests: $A11Y_RESULT"
echo "  Lighthouse Performance: $PERF_SCORE"
echo "  Lighthouse Accessibility: $A11Y_SCORE"
echo ""
echo "Detailed results saved to $RESULTS_DIR/"
echo "Finished: $(date)"

# Generate markdown report
cat > "../$RESULTS_DIR/frontend-validation.md" <<EOF
# Frontend Validation Report

**Date**: $(date)
**Branch**: $(git branch --show-current)
**Commit**: $(git rev-parse --short HEAD)

## Summary

| Check | Result |
|-------|--------|
| TypeScript | ✅ PASS |
| Production Build | ✅ PASS |
| Playwright A11y | $A11Y_RESULT |
| Lighthouse Performance | $PERF_SCORE |
| Lighthouse Accessibility | $A11Y_SCORE |

## Bundle Sizes

| Build | Entry Bundle | Notes |
|-------|-------------|-------|
| VITE_ENABLE_WORLD=false | $ENTRY_SIZE | Default build |
| VITE_ENABLE_WORLD=true | (see dist/) | With 3D world |

## Lighthouse Metrics (Ask Page)

| Metric | Value | Target |
|--------|-------|--------|
| Performance Score | $PERF_SCORE | ≥90 |
| Accessibility Score | $A11Y_SCORE | 100 |
| First Contentful Paint | ${FCP}s | <1.8s |
| Largest Contentful Paint | ${LCP}s | <2.5s |
| Cumulative Layout Shift | $CLS | <0.1 |

## Files

- Lighthouse report: \`$RESULTS_DIR/lighthouse-ask.json\`
- Playwright results: \`frontend/e2e/results/\`

EOF

echo "Report written to $RESULTS_DIR/frontend-validation.md"
