# Phase 3: Over-Refusal Analysis
# Run after Phase 2 (oracle evaluation) completes
# This script generates the diagnostic table for false refusals

param(
    [string]$Label = "dev-baseline",
    [string]$Model = "qwen2.5-coder-7b"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Phase 3: Over-Refusal Analysis ===" -ForegroundColor Cyan
Write-Host ""

# Check if current and oracle results exist
$CurrentFile = "data\evaluation\v2\${Label}_dev_current_${Model}.json"
$OracleFile = "data\evaluation\v2\${Label}_dev_oracle_${Model}.json"

if (-not (Test-Path $CurrentFile)) {
    Write-Host "Error: Current mode results not found at $CurrentFile" -ForegroundColor Red
    Write-Host "Run: python scripts_phase3/eval_v2.py --mode both --dataset dev --label $Label" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $OracleFile)) {
    Write-Host "Error: Oracle mode results not found at $OracleFile" -ForegroundColor Red
    Write-Host "Run: python scripts_phase3/eval_v2.py --mode oracle --dataset dev --label $Label" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found evaluation results" -ForegroundColor Green
Write-Host "  Current: $CurrentFile"
Write-Host "  Oracle:  $OracleFile"
Write-Host ""

# Step 1: Quick summaries
Write-Host "Step 1: Generating quick summaries..." -ForegroundColor Yellow
python scripts_phase3/quick_summary.py $CurrentFile
python scripts_phase3/quick_summary.py $OracleFile
Write-Host "✓ Summaries generated" -ForegroundColor Green
Write-Host ""

# Step 2: Oracle gap analysis
Write-Host "Step 2: Analyzing oracle vs current gap..." -ForegroundColor Yellow
python scripts_phase3/analyze_oracle_gap.py --dev --label $Label --model $Model
Write-Host "✓ Oracle gap analysis complete" -ForegroundColor Green
Write-Host ""

# Step 3: Over-refusal analysis (the key output)
Write-Host "Step 3: Analyzing false refusals..." -ForegroundColor Yellow
$OutputPath = "..\docs\results\over-refusal-dev.md"
python scripts_phase3/analyze_over_refusal.py --dev --output $OutputPath --label $Label --model $Model

if (Test-Path $OutputPath) {
    Write-Host "✓ Over-refusal analysis complete" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== RESULTS ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Reports generated:" -ForegroundColor White
    Write-Host "  1. Quick summaries: data\evaluation\v2\*_summary.md"
    Write-Host "  2. Oracle gap:      docs\results\oracle-gap-dev.md"
    Write-Host "  3. Over-refusal:    docs\results\over-refusal-dev.md"
    Write-Host ""
    Write-Host "⚠️  STOP AND REVIEW over-refusal-dev.md BEFORE IMPLEMENTING FIXES" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. Read docs\results\over-refusal-dev.md"
    Write-Host "  2. Identify the top refusal reason (e.g., coverage_check, claim_binding)"
    Write-Host "  3. Check evidence location (not_retrieved vs retrieved_not_in_context)"
    Write-Host "  4. Plan a targeted fix for the most common cause"
    Write-Host "  5. Implement, test, and validate with paired bootstrap"
} else {
    Write-Host "✗ Over-refusal analysis failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Phase 3 complete!" -ForegroundColor Green
