# Count all lines of code in the project
$total = 0
$fileTypes = @("*.py", "*.cpp", "*.c", "*.h", "*.hpp", "*.ino")

Write-Host "Counting lines of code..." -ForegroundColor Cyan
Write-Host ""

foreach ($ext in $fileTypes) {
    $files = Get-ChildItem -Path . -Recurse -Include $ext -ErrorAction SilentlyContinue
    $extTotal = 0
    $fileCount = 0
    
    foreach ($file in $files) {
        try {
            $lines = (Get-Content $file.FullName -ErrorAction SilentlyContinue).Count
            if ($lines) {
                $extTotal += $lines
                $fileCount++
            }
        } catch {
            # Skip files that can't be read
        }
    }
    
    if ($fileCount -gt 0) {
        Write-Host "$ext : $extTotal lines across $fileCount files" -ForegroundColor Yellow
        $total += $extTotal
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "TOTAL LINES OF CODE: $total" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
