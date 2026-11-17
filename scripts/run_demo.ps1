# run_demo.ps1 - Launcher tiện ích cho Demo ETL Pipeline (Task 5.4)
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "  AIRBNB SINGAPORE DATA WAREHOUSE – CHẠY DEMO ETL PIPELINE (THÁI)" -ForegroundColor Yellow
Write-Host "=======================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir

Set-Location $projectRoot
$env:PYTHONPATH = "."

Write-Host "1. Chạy demo nhanh chế độ mẫu (Sample 500 dòng):" -ForegroundColor Green
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\demo_etl_pipeline.py" --sample 500

Write-Host "`n[GỢI Ý] Để chạy toàn bộ dữ liệu 1.17M dòng thật, gõ lệnh:" -ForegroundColor DarkGray
Write-Host "  .venv\Scripts\python scripts/demo_etl_pipeline.py --full`n" -ForegroundColor DarkGray

