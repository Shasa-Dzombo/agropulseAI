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

**Next up:** create an Android AVD to verify the native path (secure storage) too; fix `POST /farms` (create) and `GET /farms/{id}` (detail) per the backend section above; then the camera-upload → diagnosis flow.
