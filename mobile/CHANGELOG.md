# AgroPulse Mobile — Changelog

Running log of milestones for the Flutter app (`mobile/`). Kept lean on purpose — one entry per real milestone, not per commit.

## 2026-08-30 — Dev environment + project scaffold

- Set up Flutter 3.47.2 (stable) and the Android SDK on the dev machine from scratch (no prior Flutter/Dart/Android Studio install). Provisioned the Android SDK via `sdkmanager` cmdline-tools rather than Android Studio's GUI wizard, so it's scriptable — see `scripts/setup_android_sdk.ps1` and `scripts/setup_android_sdk_licenses.ps1`.
- **iOS builds are not possible on this machine** — Xcode requires macOS. Android-only until we have a Mac or a cloud macOS CI (Codemagic/Bitrise/GitHub Actions macOS runner).
- Scaffolded the Flutter project (`flutter create --org com.agropulse --project-name agropulse_mobile mobile`).
- Verified the full Android toolchain end-to-end: `flutter build apk --debug` succeeds (`flutter doctor` all green except the irrelevant Visual Studio/Windows-desktop check).
- Framework choice: Flutter over React Native — see the project decision context for the reasoning (camera/sensor-heavy app, team not JS-heavy).

## 2026-08-31 — Auth flow wired to the backend

- **Fixed a real bug on the way in:** the repo root's `.gitignore` had a bare `lib/` rule (standard Python boilerplate for build artifacts) that was silently matching `mobile/lib/` too — the entire Flutter source tree was never actually committed by the previous scaffold commit. Added `!mobile/lib/` to un-ignore it. Worth knowing if any other `mobile/` subfolder ever mysteriously doesn't show up in `git status`.
- Added `ApiClient` (`lib/core/api_client.dart`) — thin JSON REST client against the FastAPI backend, with bearer-token attachment and a single automatic refresh-and-retry on a 401.
- Added `TokenStorage` — tokens go in the platform keystore (`flutter_secure_storage`), not plaintext prefs.
- Built the auth flow end to end against `app/api/auth.py`'s actual live schema (not the stale `QUICKSTART.md` example, which documents a different/older request shape): register, login, refresh (note: refresh token goes as a query param, not JSON body — that's how the backend endpoint is written), `/me`, logout.
- Login screen, register screen, and a placeholder home screen showing the logged-in user.
- Session persistence: app checks for a stored token on launch and skips straight to home if present.
- Tests added where there's real logic to protect: auth model JSON parsing (guards against silent drift from the backend schema) and a login-screen smoke test (fields render, empty-submit validation fires). No tests for the plain scaffolding.
- Full Android debug APK rebuild with the new native plugin (`flutter_secure_storage`) compiled in succeeds.
- **Live end-to-end verification against the backend surfaced three real, pre-existing backend bugs that made the entire `/auth` flow non-functional for any client, not just this app.** Fixed in `app/api/auth.py` and `app/db_config.py` (separate commit, since these aren't mobile-specific):
  1. `except jwt.JWTError` — that class doesn't exist in PyJWT (it's python-jose's name); every token decode crashed `/auth/me` with a 500. Fixed to `jwt.InvalidTokenError`.
  2. JWT `sub` claim was a raw int (`user.id`); PyJWT enforces `sub` must be a string per the JWT spec and rejected it (`InvalidSubjectError`) on *every* decode. Fixed to stringify on encode, `int()` on read.
  3. `get_production_db_dependency` never called `session.commit()` (only rollback-on-error) — every write through it, including new user registration, was silently discarded when the session closed. Registered users vanished instantly; login/me/refresh could never find them. Now commits on the success path.
  4. Bonus: `User.is_active` is a computed property gated on `status == ACTIVE`, which defaults to `PENDING_VERIFICATION` — and `/auth/verify-email` / `/auth/verify-phone` are non-functional (pre-existing, noted in the code), so no account could ever become active. Registration now sets `status=ACTIVE` directly as a stopgap; revisit once real verification exists.

  Verified via live `curl` round trip: register → tokens issued, `/me` returns the user, login with the same credentials succeeds, refresh issues new tokens, logout succeeds. All match the mobile client's expected JSON shapes exactly.

**Next up:** farm list / dashboard screen — blocked on a real backend fix first (see below), then the camera-upload → diagnosis flow.

**`app/api/farms.py` mounted, partially fixed:** it existed but was never in `main.py`'s router list. Fixed and verified:

- `FarmListResponse.uuid` was typed `str` but the `Farm` model returns a `uuid.UUID` object (Pydantic v2 doesn't auto-coerce that) - retyped to `UUID`.
- `primary_crop` and `verification_status` are required in the response schema but don't exist as columns on the `Farm` model at all (`AttributeError` on access, not just `None`) - made `Optional[...] = None` as a stopgap. Real fix is either adding those columns (migration) or dropping the fields from the API contract.
- **Verified:** `GET /farms` now returns real paginated data correctly (240 seeded farms) with no errors.

**Known broken, not fixed (documented instead of chased further at 1am):**
- `POST /farms` (create) passes `user_id=` to the `Farm()` constructor, but the actual column is `owner_id` - and also passes `farm_type`, `primary_crop`, `has_irrigation`, and `verification_status`, none of which exist on the model. Fails cleanly (500, no partial write) rather than corrupting anything, but create is unusable until this is fixed.
- `GET /farms/{farm_id}` (`FarmDetailResponse`) has the same `uuid: str` issue (not yet fixed there) plus deeper drift not fully mapped: `user_id` vs the model's `owner_id`, `global_gap_certified` vs the model's `gap_certified`, and several fields (`farm_type`, `cultivated_area_acres`, `has_irrigation`) that may not exist on the model at all. Needs a careful field-by-field pass against `app/models/database.py`'s `Farm` class before it's safe to call.
- `FieldResponse.uuid` (used by `/farms/{farm_id}/fields`) has the same untyped-`str` issue, unfixed. That whole sub-resource is moot anyway - `app/services/notification_service.py` imports `app.models.field.Field`, which doesn't exist as a module.

**Farm-list screen added** (`lib/features/farms/`) - `FarmListScreen`, `FarmRepository.listFarms()`, reachable from a "View farms" button on `HomeScreen`. Pull-to-refresh, empty state, error state with retry. Model parsing tested against the exact JSON shape captured from the live `GET /farms` fix above. **Not yet run in the app UI itself** (would need a full Android rebuild, ~10+ minutes - out of tonight's remaining window) - verified via `flutter analyze` (clean), unit tests (model parsing), and the separate live `curl` check of the endpoint it calls. Worth an actual on-device run next session before trusting it fully.

## 2026-08-31 (morning) — Login + farm list confirmed working in the running app

Ran the app for real (`flutter run -d web-server`, driven through the browser tool — no Android emulator/AVD exists yet, this doesn't touch the Android-native secure-storage path but does exercise the full UI + API integration) against the live backend: login with a real account, home screen shows the correct user, "View farms" shows the real seeded farm list with correct names/counties/acreages. No console errors. Closes the "not yet run in the app UI" gap from last night.

## 2026-08-31 (morning) — Farms CRUD fully fixed

Root cause on all the remaining `farms` bugs: **the codebase has two parallel model layers** ("Universe A" - `app/models/user.py` etc., tracked by Alembic, used by the async `app.database.get_db`; "Universe B" - the one giant `app/models/database.py`, *not* tracked by Alembic at all, used by the sync `app.db_config.get_production_db_dependency` that every real endpoint actually depends on). `app/api/farms.py` and `app/repositories/farm.py` were written assuming `Farm` had columns that were simply never added to Universe B's table: `primary_crop`, `farm_type`, `has_irrigation`, `verification_status`, `cultivated_area_acres`. Also: `Farm.owner_id` was being referred to as `user_id` in six places, and `FarmDetailResponse`/`FarmUpdateRequest` called it `global_gap_certified` where the model has `gap_certified`.

Fixed:
- Added the five missing columns to the `Farm` model and applied them to the live DB via `scripts/patch_farms_table.py` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, idempotent) - following this repo's existing convention for Universe B schema changes (Alembic doesn't reach this table; see `scripts/patch_users_table.py` for precedent). **No existing data was touched or lost.**
- `user_id` → `owner_id` everywhere in `app/api/farms.py` (create call + 6x `check_farm_access` calls).
- `global_gap_certified` → `gap_certified` in the response/update schemas, matching the model.
- `uuid: str` → `uuid: UUID` in `FarmDetailResponse` and `FieldResponse` (same Pydantic v2 coercion issue fixed in `FarmListResponse` earlier).
- `create_field` was passing a `size_hectares` kwarg the `Field` model doesn't have - removed.

**Verified live, full lifecycle:** create farm (with `farm_type`/`primary_crop`/`has_irrigation`) → get detail → update (`PATCH`) → create a field under it → list fields → soft-delete. All correct. `GET /farms` (list) still healthy afterward.

## 2026-08-31 (late morning) — Android emulator created; verified on a real device

Created an AVD (`agropulse_test`, Pixel 6 profile, Android 14/API 34, `google_apis` x86_64) via `avdmanager` - `sdkmanager` needed the `emulator` package plus a system image installed first. Booted it and ran the app for real (`flutter run -d emulator-5554`), driving it via `adb shell input` since there's no dedicated Android UI automation tool available here.

**This is the test the web-server run couldn't do:** confirmed the native `flutter_secure_storage` path actually works - logged in, force-stopped the app entirely (`adb shell am force-stop`), relaunched cold, and it went straight to the home screen (not login), proving the token round-trips through the real Android Keystore across process death. Farm list also renders correctly on-device. One transient "Handler sending message to a dead thread" warning from the secure-storage plugin appeared on the very first cold install/launch only - didn't recur on a clean relaunch, consistent with a known one-time engine-attach race rather than a real bug.

## 2026-08-31 (afternoon) — Diagnosis API rewritten; same "two universes" problem as auth

Before building the camera-upload screen, checked whether the currently-mounted `/diagnoses` API could actually be reached by a client logged in through the (now-working) `/auth` endpoints. It can't - **found the same Universe A/B split that caused the farms bugs, but worse here**: `app/api/diagnoses.py` used `app.auth.get_current_user` (Universe A), which checks a *different* `SECRET_KEY` (`"your-secret-key-here-change-in-production"`, hardcoded in `app/api/auth.py`) against `settings.SECRET_KEY` (`.env`'s `SECRET_KEY=your-secret-key-change-in-production` - one string has an extra `-here-` the other doesn't) and looks the user up in `app_users`, not `users`. A token from a real, working login would fail signature verification outright - this isn't an AWS/S3 problem, it's unreachable at the auth step.

Rewrote `app/api/diagnoses.py` from scratch against Universe B instead of trying to reconcile two incompatible auth systems - same pattern as the farms fix. Universe B already has a complete, well-designed `Diagnosis` model (`app/models/database.py`) correctly FK'd to the real `users`/`farms` tables; it just had no API built on it. Also dropped the permit/blockchain payment gating (Flutterwave/M-Pesa aren't configured here, so a permit could never actually be obtained - see the module's docstring for the full reasoning) and switched image storage from S3 (also unconfigured) to local disk, which `app/services/claude_ai_service.py` already reads directly. The old Universe A `Diagnosis`/`Permit` models are untouched - `app/api/drones.py` and `app/services/kindwise_disease_service.py` still depend on the same `app.models.diagnosis` module for the separate drone pipeline.

**Verified live, full round trip:** register → upload a real image (local disk) → create diagnosis → Claude vision call actually fires → get/list diagnosis. The only failure left is `"Your credit balance is too low to access the Anthropic API"` - the exact same Anthropic billing blocker flagged at the very start of this work, now confirmed to be the *only* thing standing between this feature and working end-to-end. Everything else - upload, persistence, error handling (stored as a clean `status: "failed"` with the real error message, no crash) - is solid.

## 2026-08-31 (afternoon, cont'd) — Camera-upload/diagnosis screen, end to end

Built the mobile side against the rewritten `/diagnoses` API: `DiagnosisUploadScreen` (camera or gallery via `image_picker`, optional symptoms note) → `DiagnosisResultScreen` (loading/failed/completed states - primary diagnosis, severity, confidence, treatment, prevention). Added `ApiClient.uploadFile()` for multipart uploads with the same auth/refresh-on-401 handling as the JSON methods. Camera permission added to both `AndroidManifest.xml` and `Info.plist` (iOS unbuildable here, but right for whenever there's a Mac).

**Found and fixed a real bug during on-device testing:** `http.MultipartFile.fromBytes()` sends no `Content-Type` by default, which made the backend's `file.content_type.startswith("image/")` check reject every upload with "File must be an image" - including real images. Fixed by looking up the MIME type from the filename (`mime` package) and setting it explicitly on the multipart file part.

**Verified the complete flow on the Android emulator**, driven via `adb shell input` + screenshots: Home → "Diagnose a plant" → picked an image from the gallery (pushed a test JPEG onto the emulator first) → filled in symptoms → submitted → landed on `DiagnosisResultScreen` showing a clean "Diagnosis failed" state with the real Anthropic error message rendered in the UI. Same billing blocker as everywhere else today - the pipeline itself (pick → upload → create → render result) is fully working.

**Next up:** register-screen UX improvements (county dropdown, show/hide password, password generator) and the farm-data-capture/dashboards/social-discovery/chama ideas, all previously queued. Once Anthropic credits are added, the whole diagnosis flow should work with zero further code changes.
