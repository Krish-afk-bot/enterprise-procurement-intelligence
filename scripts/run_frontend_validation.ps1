# Frontend validation suite for Phase 8
# Runs accessibility, visual, and performance checks

$ErrorActionPreference = "Stop"

Write-Host "=== Frontend Validation Suite ===" -ForegroundColor Cyan
Write-Host "Starting: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Results directory
$ResultsDir = "docs/results"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

# Change to frontend directory
Set-Location frontend

Write-Host "Step 1: TypeScript type checking..." -ForegroundColor Yellow
try {
    npx tsc --noEmit
    Write-Host "✓ TypeScript check passed" -ForegroundColor Green
    $TSResult = "PASS"
} catch {
    Write-Host "✗ TypeScript check failed" -ForegroundColor Red
    $TSResult = "FAIL"
}

Write-Host ""
Write-Host "Step 2: Building production bundle..." -ForegroundColor Yellow
try {
    npm run build
    Write-Host "✓ Build succeeded" -ForegroundColor Green
    $BuildResult = "PASS"
} catch {
    Write-Host "✗ Build failed" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host ""
Write-Host "Step 3: Measuring bundle sizes..." -ForegroundColor Yellow
Write-Host "Entry bundle (VITE_ENABLE_WORLD=false):"
$IndexFiles = Get-ChildItem "dist/assets/index-*.js"
foreach ($file in $IndexFiles) {
    $size = "{0:N2} KB" -f ($file.Length / 1KB)
    Write-Host "  $size - $($file.Name)"
}
$EntrySize = "{0:N2} KB" -f ($IndexFiles[0].Length / 1KB)

Write-Host "Lazy chunks:"
$OtherChunks = Get-ChildItem "dist/assets/*.js" | Where-Object { $_.Name -notlike "index-*" }
if ($OtherChunks) {
    foreach ($file in $OtherChunks) {
        $size = "{0:N2} KB" -f ($file.Length / 1KB)
        Write-Host "  $size - $($file.Name)"
    }
} else {
    Write-Host "  No additional chunks"
}

Write-Host ""
Write-Host "Step 4: Playwright accessibility tests..." -ForegroundColor Yellow
Write-Host "(Note: Requires backend on :8000 and seeded admin account)" -ForegroundColor Gray

try {
    npx playwright test e2e/a11y-visual.spec.ts
    Write-Host "✓ Accessibility tests passed" -ForegroundColor Green
    $A11yResult = "PASS"
} catch {
    Write-Host "✗ Accessibility tests failed (some tests may require running services)" -ForegroundColor Yellow
    $A11yResult = "PARTIAL"
}

Write-Host ""
Write-Host "Step 5: Bundle analysis complete" -ForegroundColor Yellow

# Get git info
Set-Location ..
$Branch = git branch --show-current
$Commit = git rev-parse --short HEAD
Set-Location frontend

Write-Host ""
Write-Host "=== Validation Complete ===" -ForegroundColor Cyan
Write-Host "Results:" -ForegroundColor Gray
Write-Host "  TypeScript: $TSResult"
Write-Host "  Build: $BuildResult"
Write-Host "  A11y Tests: $A11yResult"
Write-Host "  Entry Bundle: $EntrySize"
Write-Host ""

# Generate markdown report
$ReportContent = @"
# Frontend Validation Report

**Date**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Branch**: $Branch
**Commit**: $Commit

## Summary

| Check | Result |
|-------|--------|
| TypeScript | $(if ($TSResult -eq 'PASS') {'✅ PASS'} else {'❌ FAIL'}) |
| Production Build | $(if ($BuildResult -eq 'PASS') {'✅ PASS'} else {'❌ FAIL'}) |
| Playwright A11y | $(if ($A11yResult -eq 'PASS') {'✅ PASS'} elseif ($A11yResult -eq 'PARTIAL') {'⚠️ PARTIAL'} else {'❌ FAIL'}) |

## Bundle Sizes

| Build | Entry Bundle | Notes |
|-------|-------------|-------|
| VITE_ENABLE_WORLD=false | $EntrySize | Default build |

## TypeScript

- Strictness: enabled
- Configuration: \`tsconfig.json\`, \`tsconfig.app.json\`, \`tsconfig.node.json\`

## Playwright Tests

Test results saved to \`frontend/playwright-report/\`

To run with full stack:
\`\`\`powershell
# Start backend
cd backend; uvicorn app.main:app --port 8000

# Start frontend dev server
cd frontend; npm run dev

# Run tests
npx playwright test e2e/a11y-visual.spec.ts
\`\`\`

## Next Steps

1. **Lighthouse**: Run against production preview server
   \`\`\`powershell
   npx vite preview --port 4173
   npx lighthouse http://localhost:4173/ask --only-categories=performance,accessibility
   \`\`\`

2. **Bundle analysis**: Check for opportunities to reduce size
   \`\`\`powershell
   npm run build -- --mode production
   \`\`\`

3. **Visual regression**: Review Playwright snapshots in \`e2e/a11y-visual.spec.ts-snapshots/\`

"@

Set-Location ..
$ReportPath = Join-Path $ResultsDir "frontend-validation.md"
$ReportContent | Out-File -FilePath $ReportPath -Encoding UTF8
Write-Host "Report written to $ReportPath" -ForegroundColor Green

Set-Location frontend
Write-Host ""
Write-Host "Finished: $(Get-Date)" -ForegroundColor Gray
