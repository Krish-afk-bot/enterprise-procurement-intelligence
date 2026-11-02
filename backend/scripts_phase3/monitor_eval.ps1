# Monitor long-running evaluation with periodic updates
param(
    [string]$LogFile = "eval_dev_baseline.log",
    [int]$RefreshSeconds = 30
)

$Host.UI.RawUI.WindowTitle = "Evaluation Monitor"
Clear-Host

while ($true) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Clear-Host
    
    Write-Host "=== Evaluation Monitor ===" -ForegroundColor Cyan
    Write-Host "Time: $timestamp" -ForegroundColor Gray
    Write-Host "Log: $LogFile" -ForegroundColor Gray
    Write-Host ""
    
    if (Test-Path $LogFile) {
        # Get current progress
        $progressLines = Get-Content $LogFile | Select-String "\[ *[0-9]+/90\]" | Select-Object -Last 5
        $modeLines = Get-Content $LogFile | Select-String "running mode" | Select-Object -Last 2
        
        Write-Host "Mode Progress:" -ForegroundColor Yellow
        foreach ($line in $modeLines) {
            Write-Host "  $line"
        }
        Write-Host ""
        
        Write-Host "Recent Questions (last 5):" -ForegroundColor Yellow
        foreach ($line in $progressLines) {
            $lineStr = $line.ToString()
            if ($lineStr -match "FAIL") {
                Write-Host "  $lineStr" -ForegroundColor Red
            } elseif ($lineStr -match "ok") {
                Write-Host "  $lineStr" -ForegroundColor Green
            } else {
                Write-Host "  $lineStr"
            }
        }
        Write-Host ""
        
        # Check for completion
        $completionMarkers = Get-Content $LogFile | Select-String "saved.*evaluation/v2"
        if ($completionMarkers.Count -ge 2) {
            Write-Host "✓ EVALUATION COMPLETE!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Both current and oracle modes finished." -ForegroundColor White
            Write-Host ""
            Write-Host "Next: Run Phase 3 analysis" -ForegroundColor Yellow
            Write-Host "  cd backend" -ForegroundColor Gray
            Write-Host "  .\scripts_phase3\run_phase3_analysis.ps1" -ForegroundColor Gray
            break
        }
        
        # Recent errors
        $errors = Get-Content $LogFile | Select-String "error" | Select-Object -Last 3
        if ($errors.Count -gt 0) {
            Write-Host "Recent Errors:" -ForegroundColor Red
            foreach ($err in $errors) {
                Write-Host "  $err" -ForegroundColor Red
            }
            Write-Host ""
        }
        
        Write-Host "Refreshing every $RefreshSeconds seconds... (Ctrl+C to stop)" -ForegroundColor Gray
    } else {
        Write-Host "Waiting for log file: $LogFile" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds $RefreshSeconds
}
