# VoltWise submission checklist

## Locally complete

- [x] Combined high-draw plus unavailable-telemetry safety invariant verified.
- [x] Direct high draw and transient 2,200 W peak trigger simulated cutoff.
- [x] High-draw paths perform zero retries, preserve trigger evidence, and end OFF.
- [x] No-draw failure and one-retry recovery verified independently.
- [x] Landing, failure, recovery, safety-stop, and energy scenes reproduced.
- [x] Official MCP client/server Streamable HTTP round trip verified.
- [x] Alexa+ simulation, telemetry simulation, and real MCP disclosed separately.
- [x] MIT license present.
- [x] `.gitignore`, `.env.example`, setup, tests, troubleshooting, and demo docs reviewed.
- [x] Video script, shot list, and recording guide prepared for a 2:40 take.
- [x] Devpost narrative prepared without claiming deployment or production Alexa+ access.

## Final local commands

```powershell
# Backend
.\.venv\Scripts\python.exe -m pytest -q

# Frontend and production bundle
cd frontend
npm.cmd test
npm.cmd run build
cd ..

# Three-process local demo
.\start-voltwise.bat
# Open http://127.0.0.1:5173
.\stop-voltwise.bat
```

Expected service URLs:

- UI: `http://127.0.0.1:5173`
- API/OpenAPI: `http://127.0.0.1:8000/docs`
- MCP Streamable HTTP: `http://127.0.0.1:8001/mcp`

## Human actions before submission

- [ ] Read the current official Amazon Developer Hackathon 2026 and Devpost
  rules. Verify eligibility, Alexa+ track selection, deadline/time zone, team
  membership, judging criteria, video constraints, and all mandatory fields.
- [ ] Create a public GitHub repository under the intended account. Extract the
  prepared release archive, review it, initialize Git, commit, and push. Do not
  add generated databases, browser profiles, `.env` files, tokens, build output,
  or the release archive itself.
- [ ] Replace **[ADD GITHUB URL]** in `DEVPOST_SUBMISSION.md`.
- [ ] Record the 2:40 browser demonstration using
  `SUBMISSION_VIDEO_RECORDING_GUIDE.md`; review disclosures and legibility.
- [ ] Upload the approved video to YouTube or Vimeo with the visibility required
  by the current rules, then replace **[ADD YOUTUBE OR VIMEO URL]**.
- [ ] Decide whether the optional deployment field should say **Local demo**.
  No AWS deployment exists and none should be claimed.
- [ ] Capture or select the required Devpost thumbnail/gallery media, ensuring
  no personal data or unsupported claims appear.
- [ ] Paste the final copy into Devpost, add team members and links, preview every
  section, and submit only after owner approval.

## Safe Git publication sequence

After installing Git and extracting the release archive into a new directory:

```powershell
git init
git add .
git status
git commit -m "Prepare VoltWise hackathon submission"
git branch -M main
git remote add origin <NEW_EMPTY_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Review `git status` and the GitHub file list before making the repository public.
Do not force-push or overwrite an existing remote.

## Final Devpost links

- GitHub: **[ADD GITHUB URL]**
- Video: **[ADD YOUTUBE OR VIMEO URL]**
- Live demo: **[ADD LIVE URL OR STATE "Local demo"]**

