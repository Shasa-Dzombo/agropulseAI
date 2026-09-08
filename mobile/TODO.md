# AgroPulse — Ideas & Task Checklist

Running list of everything we've discussed, built, or floated — updated as we go. New ideas get added here when they come up; items get checked off (with a one-line note) when they land. Sent to you again at the end of each day's last commit.

## Done (2026-09-07)

- [x] Multi-provider AI service — `LLM_PROVIDER=openai|anthropic|ollama|openweight` switch, currently running Kimi (`kimi-k3`) via your self-hosted openweights gateway
- [x] Real drone flight boundary map — trace a polygon on the satellite view, live hectare readout
- [x] Farmer survey goals ("count" plants/trees and/or "health" analysis) + free-text notes, set once per flight
- [x] Farm's own recent input-log and yield-record history automatically fed into the AI analysis prompt
- [x] On-demand "Analyze with AI" per drone photo — capture → NDVI (instant, free) → AI diagnosis (on tap, ~15-20s)
- [x] Fixed "can't delete a flight/yield" — was a discoverability bug (swipe-only, no visible button), added visible delete icons
- [x] Pinch-to-zoom on captured photos
- [x] Analysis survives navigation — `DroneAnalysisTracker` means leaving the screen mid-analysis no longer loses the result
- [x] Diagnosis history screen (Home → "Diagnosis history") — greenhouse *and* drone diagnoses together, with the actual source photo
- [x] Tap-through detail view on any captured/analyzed drone photo (was dead space before)
- [x] Multi-select photo uploads — diagnosis screen bundles several photos into one diagnosis; drone screen adds several as separate photos
- [x] Investigated `app/ml`, `app/computer_vision`, `app/vision` — almost entirely fake/dead scaffolding (some code literally fabricates predictions with `np.random`); two things worth keeping (`rgb_indices.py` vegetation formulas, `yield_estimation/` PyTorch skeleton)
- [x] Investigated predictive-maintenance code (`app/iot/edge`) — real ML logic, but broken imports and never wired to anything live
- [x] Researched real public datasets for training — found real leads (Lacuna Fund Kenya smallholder set, Zindi, CCMT/TOM2024 disease datasets); confirmed nothing usable exists for farm-tool predictive maintenance specifically

## Done (2026-09-08)

- [x] **Scan mode build fixed** — the AndroidX conflict needed an explicit `implementation` dependency injected into every Android subproject via `plugins.withId` (a plain `resolutionStrategy.force()` and a naive `afterEvaluate` both failed first - see `android/build.gradle.kts`); verified for real this time by grepping the compiled `libapp.so` for the new screen's strings before installing, not just trusting the build's reported exit code

- [x] KML file import on mobile — "Import KML" button on both flight-create and flight-detail screens; opens the boundary map pre-loaded with the imported points for review/adjustment before saving. Needed a `file_picker` major-version bump (8.x → 10.3.3) partway through — the 8.x version's own Android build config was stale and blocked the release build; verified via the same compiled-binary check as scan mode before installing.

- [x] Saved/reusable boundary templates — full CRUD (`/drones/farms/{id}/boundaries`, `/drones/boundaries/{id}`), verified via curl; "save as template" bookmark icon on the boundary map, "Load saved template" picker (shared between flight-create and flight-detail screens) with per-item delete. This was the last piece of the original KML request.

## Still open (raised, not yet built)

- [ ] Fix `app/api/optimization.py`'s legacy auth — chatbot/scouting-plan endpoints still check the old pre-migration user system and 401 on real tokens; spawned as a background task yesterday, never landed (still broken as of this morning)
- [ ] Real video-stream pipeline (continuous local NDVI + periodic AI calls on sampled frames) — discussed as a bigger future lift, not started; scan mode is the fixed-interval-photo version of this, not true video
- [ ] Yield prediction from accumulated drone/diagnosis photos — needs real paired photo+harvest data first (not enough exists yet); revisit once a season or two of real data accumulates
- [ ] Predictive maintenance for farm tools — no usable public dataset exists; would need real usage/failure data collected from farmers directly

## Known pre-existing bugs (not ours, not fixed, just noted)

- [ ] `app/api/cctv.py` fails to load — missing `app.models.field` module (confirmed pre-existing via git history, unrelated to anything built this week)

## Dev environment / personal infra (not AgroPulse itself, tracked here anyway)

- [ ] Self-hosted VPN (or a config workaround) so ProtonVPN's kill-switch/LAN-blocking stops interrupting phone↔laptop dev testing, without paying for ProtonVPN Plus just for "Allow LAN". Two paths discussed: (1) check whether Proton's free tier still allows exporting a raw WireGuard/OpenVPN config for use with the plain WireGuard client instead of Proton's own app — the LAN-blocking is likely baked into Proton's app, not the protocol, so this might be a free fix; (2) if not, self-host WireGuard on a cheap VPS (~$3-6/mo) with a split-tunnel rule excluding the home LAN subnet. Held until after today's AgroPulse work; not started.
