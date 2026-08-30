# AgroPulse Mobile — Changelog

Running log of milestones for the Flutter app (`mobile/`). Kept lean on purpose — one entry per real milestone, not per commit.

## 2026-08-30 — Dev environment + project scaffold

- Set up Flutter 3.47.2 (stable) and the Android SDK on the dev machine from scratch (no prior Flutter/Dart/Android Studio install). Provisioned the Android SDK via `sdkmanager` cmdline-tools rather than Android Studio's GUI wizard, so it's scriptable — see `scripts/setup_android_sdk.ps1` and `scripts/setup_android_sdk_licenses.ps1`.
- **iOS builds are not possible on this machine** — Xcode requires macOS. Android-only until we have a Mac or a cloud macOS CI (Codemagic/Bitrise/GitHub Actions macOS runner).
- Scaffolded the Flutter project (`flutter create --org com.agropulse --project-name agropulse_mobile mobile`).
- Verified the full Android toolchain end-to-end: `flutter build apk --debug` succeeds (`flutter doctor` all green except the irrelevant Visual Studio/Windows-desktop check).
- Framework choice: Flutter over React Native — see the project decision context for the reasoning (camera/sensor-heavy app, team not JS-heavy).

**Next up:** API client + login/register screens against the backend's `/api/v1/auth` endpoints.
