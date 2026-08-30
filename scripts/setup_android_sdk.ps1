# One-shot Android SDK provisioning for Flutter Android builds.
# Downloads the official cmdline-tools, lays them out the way sdkmanager
# expects (<sdk_root>\cmdline-tools\latest\...), then uses sdkmanager to pull
# platform-tools + a current platform + build-tools and accept licenses -
# all non-interactively, so it doesn't depend on Android Studio's GUI
# first-run Setup Wizard.

# "Continue" (not "Stop") - native tools like sdkmanager.bat write benign
# warnings to stderr, which PowerShell treats as script-terminating under
# $ErrorActionPreference = "Stop".
$ErrorActionPreference = "Continue"

$sdkRoot = "C:\Android\sdk"
$cmdlineToolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip"
$zipPath = "$env:TEMP\commandlinetools-win.zip"
$extractTmp = "$env:TEMP\cmdline-tools-extract"

Write-Host "==> Creating SDK root at $sdkRoot"
New-Item -ItemType Directory -Force -Path $sdkRoot | Out-Null

Write-Host "==> Downloading Android cmdline-tools ($cmdlineToolsUrl)"
Invoke-WebRequest -Uri $cmdlineToolsUrl -OutFile $zipPath

Write-Host "==> Extracting"
if (Test-Path $extractTmp) { Remove-Item -Recurse -Force $extractTmp }
Expand-Archive -Path $zipPath -DestinationPath $extractTmp -Force

$destination = Join-Path $sdkRoot "cmdline-tools\latest"
New-Item -ItemType Directory -Force -Path (Join-Path $sdkRoot "cmdline-tools") | Out-Null
if (Test-Path $destination) { Remove-Item -Recurse -Force $destination }
Move-Item -Path (Join-Path $extractTmp "cmdline-tools") -Destination $destination

Write-Host "==> Setting ANDROID_HOME / ANDROID_SDK_ROOT (user env)"
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $sdkRoot, "User")
[Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", $sdkRoot, "User")

$sdkmanager = Join-Path $destination "bin\sdkmanager.bat"
$platformToolsBin = Join-Path $sdkRoot "platform-tools"

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$toAdd = @((Join-Path $destination "bin"), $platformToolsBin)
foreach ($p in $toAdd) {
    if ($currentPath -notlike "*$p*") {
        $currentPath = "$currentPath;$p"
    }
}
[Environment]::SetEnvironmentVariable("Path", $currentPath, "User")
$env:Path = "$env:Path;$($toAdd -join ';')"
$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot

Write-Host "==> Accepting SDK licenses"
$yesBlock = (1..20 | ForEach-Object { "y" }) -join "`n"
$yesBlock | & $sdkmanager --licenses --sdk_root=$sdkRoot 2>&1 | Out-String | Write-Host

Write-Host "==> Installing platform-tools, platform, build-tools"
& $sdkmanager --sdk_root=$sdkRoot "platform-tools" "platforms;android-35" "build-tools;35.0.0" 2>&1 | Out-String | Write-Host

Write-Host "==> DONE"
