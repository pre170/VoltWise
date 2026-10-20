# VoltWise submission video recording guide

## Prepare the machine

1. Use a local Windows account/profile that shows no personal bookmarks,
   messages, email, or cloud-drive notifications.
2. Set display scaling before recording. Prefer 1920x1080 or 1440x900 at 100%
   browser zoom. Disable notification banners and close unrelated applications.
3. From the repository root, run `start-voltwise.bat`. Wait for the readiness
   line listing UI, API, and MCP URLs.
4. Open `http://127.0.0.1:5173`, maximize the browser, and use **Reset demo**.
5. Perform one silent rehearsal using
   [the shot list](SUBMISSION_VIDEO_SHOTLIST.md). Confirm every expected value
   and that Technical evidence shows a successful MCP trace.

## Record

- Record only the browser window or a tightly cropped display. Capture at 30 fps
  or higher and 1080p when available.
- Use a quiet microphone and record narration live or add it afterward from
  [the timed script](SUBMISSION_VIDEO_SCRIPT.md).
- Pause briefly on expected/observed wattage, retry count, cutoff state, energy
  values, and MCP fields so they remain readable after compression.
- Reset between every scenario. Recovery must begin with **Diagnose heater**
  directly after selecting the Recovery preset.
- Keep the final edit below three minutes; the planned runtime is 2:40.

## Review before upload

- Audio matches the visible screen and contains no unsupported claims.
- The video says Alexa+ and telemetry are simulated and MCP is real.
- The cutoff is described as simulated and not certified protection.
- No passwords, tokens, local account names, notifications, or unrelated tabs
  are visible.
- The exported video is legible at normal playback size and has no long pauses.
- Add captions if the hosting platform supports them.

Upload and publication require the project owner's explicit approval. After
uploading to YouTube or Vimeo, copy the final public or unlisted URL into
`DEVPOST_SUBMISSION.md` and `SUBMISSION_CHECKLIST.md`.

