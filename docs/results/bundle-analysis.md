# Frontend Bundle Analysis

**Date**: November 3, 2026  
**Build**: Production (vite build)  
**VITE_ENABLE_WORLD**: false (default)

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Entry Bundle (raw) | 478.50 KB | <500 KB | ✅ PASS |
| Entry Bundle (gzip) | 149.22 KB | <200 KB | ✅ PASS |
| Three.js Chunk (gzip) | 233.14 KB | Lazy loaded | ✅ PASS |
| Total Bundle | 1.77 MB | <2 MB | ✅ PASS |

## Bundle Composition

### Entry Bundle (index-CJhRhKkd.js)
- **Size**: 478.50 KB (149.22 KB gzipped)
- **Contains**: React, React Router, TanStack Query, Zustand, UI components, base layout
- **Loaded**: On initial page load

### Lazy Chunks (Code-Split)

| Chunk | Raw Size | Gzip | Load Trigger |
|-------|----------|------|--------------|
| palette-DKor48s4.js | 858.36 KB | 233.14 KB | three.js/R3F (world enabled) |
| EvaluationPage-BlCEkw0I.js | 396.91 KB | 109.92 KB | Route: /evaluation |
| DocumentDetailPage-D81sh872.js | 32.92 KB | 9.29 KB | Route: /documents/:id |
| AdminPage-dXU5Aery.js | 23.18 KB | 5.62 KB | Route: /admin |
| DashboardPage-TjUj_cFr.js | 22.04 KB | 6.39 KB | Route: / (dashboard) |
| DocumentsPage-xwJx4DIg.js | 16.46 KB | 5.44 KB | Route: /documents |
| BandRegion-CpQlrAiU.js | 14.81 KB | 4.92 KB | World component |
| SearchPage-l9gRCAMu.js | 12.18 KB | 3.61 KB | Route: /search |
| GraphPage-DPmqZD3_.js | 10.65 KB | 3.57 KB | Route: /graph |
| ComparePage-u2DZ_ssx.js | 9.57 KB | 3.35 KB | Route: /compare |
| SupplierDetailPage-B2Tdura7.js | 9.25 KB | 2.58 KB | Route: /suppliers/:id |
| ContractDetailPage-DB7Luh90.js | 8.19 KB | 2.41 KB | Route: /contracts/:id |
| (11 smaller chunks) | <6 KB each | <3 KB each | Various components |

## Key Observations

### ✅ Strengths

1. **Entry bundle under 500KB**: At 478.50 KB raw (149 KB gzip), the initial load is reasonable
2. **Effective code splitting**: Major pages are separate chunks, loaded on-demand
3. **three.js isolation**: The 858 KB three.js bundle (palette chunk) is completely separate and only loads when world is enabled
4. **Gzip efficiency**: Good compression ratio (~31% of raw size on average)

### ⚠️ Considerations

1. **Large EvaluationPage**: 397 KB (110 KB gzip) - likely includes Recharts library for charts
2. **palette chunk**: 858 KB (233 KB gzip) - three.js + R3F + drei + world components
   - Only loaded when `VITE_ENABLE_WORLD=true` and user navigates to world view
   - Acceptable for optional feature

### 📊 Comparison with Targets

| Target | Requirement | Actual | Status |
|--------|-------------|--------|--------|
| Entry <500KB | Hard requirement | 478.50 KB | ✅ Pass |
| Entry gzip <200KB | Performance goal | 149.22 KB | ✅ Pass |
| Total <2MB | Soft limit | 1.77 MB | ✅ Pass |
| three.js lazy | Must be lazy | Yes, separate chunk | ✅ Pass |

## Recommendations

### High Priority
- None - bundle size is within acceptable limits

### Medium Priority
1. **Evaluate EvaluationPage dependencies**: If Recharts is causing the 397 KB chunk, consider lighter alternatives for simpler charts
2. **Tree-shaking verification**: Ensure unused Radix UI components are fully tree-shaken

### Low Priority
1. **Investigate palette chunk**: If world feature becomes default, consider splitting further (drei helpers vs core three.js)
2. **Monitor growth**: Track bundle sizes in CI to prevent regression

## Build Configuration

**Vite 6.4.4**
- Target: ES2020
- Minification: terser
- Code splitting: automatic (routes + dynamic imports)
- Chunking strategy: default Rollup heuristics

### Manual Chunks

No manual chunks currently defined. The default strategy successfully:
- Isolates three.js dependencies (palette chunk)
- Splits routes into separate chunks
- Keeps entry bundle minimal

## Historical Comparison

| Date | Entry (gzip) | three.js (gzip) | Notes |
|------|--------------|-----------------|-------|
| 2026-11-03 | 149.22 KB | 233.14 KB | Baseline measurement |

_Track future measurements here to detect growth over time._

## Verification Commands

```powershell
# Build and measure
cd frontend
npm run build

# Analyze bundle
$files = Get-ChildItem dist/assets/*.js
$files | ForEach-Object { 
    "{0:N2} KB - {1}" -f ($_.Length/1KB), $_.Name 
} | Sort-Object -Descending

# With world enabled
$env:VITE_ENABLE_WORLD='true'
npm run build
```

## Conclusion

The frontend bundle size is **well within acceptable limits**. The entry bundle is 149 KB gzipped (target <200 KB), and the optional three.js world feature is properly code-split into a separate 233 KB chunk. No immediate action required, but continued monitoring recommended.
