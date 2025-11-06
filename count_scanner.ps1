# Count scanner/CCTV system lines
$scannerDirs = @(
    "nvr_system",
    "nvr_system_cnc",
    "pi_cctv",
    "esp32_snapshot_cam",
    "app\computer_vision"
)

$total = 0
$fileTypes = @("*.py", "*.cpp", "*.c", "*.h", "*.hpp", "*.ino")

Write-Host "Counting Scanner/CCTV System Lines..." -ForegroundColor Cyan
Write-Host ""

foreach ($dir in $scannerDirs) {
    $dirPath = Join-Path . $dir
    if (Test-Path $dirPath) {
        $dirTotal = 0
        $fileCount = 0
        
        foreach ($ext in $fileTypes) {
            $files = Get-ChildItem -Path $dirPath -Recurse -Include $ext -ErrorAction SilentlyContinue
            
            foreach ($file in $files) {
                try {
                    $lines = (Get-Content $file.FullName -ErrorAction SilentlyContinue).Count
                    if ($lines) {
                        $dirTotal += $lines
                        $fileCount++
                    }
                } catch {
                    # Skip files that can't be read
                }
            }
        }
        
        if ($fileCount -gt 0) {
            Write-Host "$dir : $dirTotal lines across $fileCount files" -ForegroundColor Yellow
            $total += $dirTotal
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SCANNER SYSTEM TOTAL: $total lines" -ForegroundColor Green
Write-Host "TARGET: 200,000 lines" -ForegroundColor Cyan
Write-Host "REMAINING: $([Math]::Max(0, 200000 - $total)) lines" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Green
