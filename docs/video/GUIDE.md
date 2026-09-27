# Making the demo video

Target: **90 seconds (1–2 minutes max)**, explained so a 5-year-old follows it. Footage = the 6-slide presenter (`/demo/present.html`) with its live buttons, recorded at 1920×1080.

## Pipeline
1. **Start the demo** from `main`: `uv run uvicorn wall.server:app --port 8788` (GBrain must be up on :3131; check with `uv run python walls/attack.py`).
2. **Capture real footage**: `tools/video/capture/` (Playwright, 1920×1080, one clip per beat, output `.runtime/video/clips/` + `clips.json`). Re-capture any screen that changed.
3. **Optional generated B-roll**: `tools/video/gen/` runs an open-weights model (LTX-Video, fallback Wan 2.x) locally via diffusers on Apple Silicon. Abstract shots only: binders, paper, placeholders. No people, faces, brands or rendered text. Hosted services (Higgsfield and its open-source studio front ends) need API keys and are not used.
4. **Compose** with HyperFrames (HeyGen's open-source HTML-to-video CLI, `npx hyperframes`): `tools/video/compose/`. Title cards and captions use `demo/assets/theme.css` tokens (Public Sans + Source Serif 4; ink `#14213D`, form blue `#1F4E9E`, found yellow `#FFE58A`).
5. **Narration**: macOS `say` per scene (pick a natural voice with `say -v '?'`), synced per beat; captions always on.
6. **Render** to `.runtime/video/wall-demo-3min.mp4`; extract a frame every 10 s with ffmpeg and look at every frame before sharing.

## Rules
- Real product footage for every product claim. Generated footage is atmosphere only.
- Every number comes from `results/results.json` or `evals/cost/results.json` at render time, with n. Never type a number by hand.
- Always pair the hard-set River score (102/102, same generator as training) with the independent-set result. Never show 102/102 alone.
- Say "removes identifiers, with residual leakage measured"; never "anonymized", "HIPAA-compliant", "GDPR-compliant", or "de-identified" as a legal status.
- Synthetic data only. Every person, company and award on screen is fictional.
- If a live call is replayed from cache, the on-screen "Replayed" tag stays visible.

## Backup
`tools/record/` records the Present flow end to end as a fallback screen recording (`.runtime/backup/`).
