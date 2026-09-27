# Final 90-second video

Rebuilds `.runtime/video/wall-demo-90s.mp4` from the live presenter (http://localhost:8788/demo/present.html).
Run inside `.runtime/video/v90/` (narration `n1..n7.aiff` via `say -v Samantha -r 165`, captions `cap1..7.png`, title card `title.png`):

    node rec.mjs      # one 1920x1080 clip per scene, each as long as its narration
    python3 build2.py # overlays captions, adds narration, concatenates

Script and voice-over lines: `lines.txt` (matches docs/video/SCRIPT.md).
