# Changelog

All notable changes to the `sleepstudy.app` dashboard project will be documented in this file.

---

## [1.1.9] - 2026-06-25

### Added
- **Sleep Aids Config Page**: Add tag creation/deletion configurations (e.g. `Nose Strips`, `Eye Mask`, `Earplugs`).
- **Interactive Sleep Journal**: Add click-to-toggle tag pills that light up on selection, and a dropdown selector for primary sleep positions (Back, Left Side, Right Side, Stomach, Mixed/Other).
- **Auto-Sync daemon**: Add an hourly background worker thread that automatically syncs Garmin data if missing.
- **Auto-Pruner**: Add a storage space utility to prune raw Garmin Connect JSON debug logs, keeping only the 7 most recent.
- **Cache Buster**: Add query string versioning to HTML resource links to prevent asset caching on client browsers.
- **"Preview" badges**: Mark the Snore & Cough Custom App and Sleep as Android Webhook cards in settings with warning labels.

---

## [1.1.0] - 2026-06-24

### Added
- **Custom Snore & Cough App API**: Add HTTP POST ingestion point to map noise levels to Garmin session schedules using deterministic merging.
- **Enrollment QR Code**: Add client auto-configuration QR codes mapped to dynamic server host IPs.
- **Webhook Web Loader**: Relocate manual JSON imports to the bottom sidebar navigation.

---

## [1.0.0] - 2026-06-23

### Added
- **Initial Release**: Basic sleep dashboard parsing Garmin Connect stage swimlanes, heart rates, respiration epoch vitals, database storage schema, and manual imports.
