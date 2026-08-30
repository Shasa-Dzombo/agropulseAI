# Follow-up to setup_android_sdk.ps1: cmdline-tools are already downloaded and
# extracted at this point, but sdkmanager.bat's crude `java -version` parser
# chokes on the Oracle JDK stub at C:\Program Files\Common Files\Oracle\Java\javapath
# (JAVA_HOME was unset, so it fell back to that). Point JAVA_HOME at Android
# Studio's bundled JetBrains Runtime instead - it's a real, known-good JDK 17+
# that Android tooling is tested against - and retry license acceptance +
# package install.

# "Continue" (not "Stop") - sdkmanager.bat writes benign deprecation warnings
# to stderr, and PowerShell treats stderr from native commands as a
# script-terminating error under $ErrorActionPreference = "Stop", which
# silently killed this script after the first warning last run.
$ErrorActionPreference = "Continue"

$sdkRoot = "C:\Android\sdk"
$jbrHome = "C:\Program Files\Android\Android Studio\jbr"
$sdkmanager = Join-Path $sdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"

Write-Host "==> Setting JAVA_HOME (user env) to Android Studio's bundled JBR"
[Environment]::SetEnvironmentVariable("JAVA_HOME", $jbrHome, "User")
$env:JAVA_HOME = $jbrHome

Write-Host "==> Accepting SDK licenses"
# PowerShell's pipe-to-native-process doesn't feed multi-line stdin reliably
# to sdkmanager's interactive (y/N) prompts - route through cmd.exe with a
# real file redirected onto stdin instead, which sdkmanager reads correctly.
$yesFile = "$env:TEMP\android_sdk_yes.txt"
(1..20 | ForEach-Object { "y" }) -join "`r`n" | Set-Content -Path $yesFile -Encoding ASCII
cmd /c "type `"$yesFile`" | `"$sdkmanager`" --licenses --sdk_root=`"$sdkRoot`"" 2>&1 | Out-String | Write-Host

Write-Host "==> Installing platform-tools, platform, build-tools"
& $sdkmanager --sdk_root=$sdkRoot "platform-tools" "platforms;android-35" "build-tools;35.0.0" 2>&1 | Out-String | Write-Host

Write-Host "==> Verifying licenses fully accepted"
cmd /c "type `"$yesFile`" | `"$sdkmanager`" --licenses --sdk_root=`"$sdkRoot`"" 2>&1 | Out-String | Write-Host

Write-Host "==> DONE"
