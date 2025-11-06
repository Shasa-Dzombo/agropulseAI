$files = Get-ChildItem "tests\*.py" -Recurse
$total = 0
foreach ($file in $files) {
    $lines = (Get-Content $file.FullName).Count
    Write-Host "$($file.Name): $lines lines"
    $total += $lines
}
Write-Host "`nTotal test lines: $total"
