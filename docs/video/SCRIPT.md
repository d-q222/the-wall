# Demo video: 90-second script (simple enough for a 5-year-old)

Length: **75–100 seconds.** 1920×1080, 30 fps, light theme, captions always on.
Rules: short words, one idea per scene, one picture per idea. No jargon on screen
(no "de-identification", "LoRA", "OAuth", "quasi-identifier"). Numbers only from
`results/results.json`, with n in the caption.

| Time | Scene | On screen | Voice-over (say exactly this) |
|---|---|---|---|
| 0:00–0:10 | 1. The secret box | Presenter slide 1, big title | "Lawyers keep every client's story in a secret box. They are not allowed to mix one client's secrets into another client's work." |
| 0:10–0:22 | 2. The problem | Title card: "So their AI has to forget everything." | "AI could learn from all those old cases and help next time. But it might spill one client's secrets. So today, lawyers use AI that forgets." |
| 0:22–0:40 | 3. The wall | Presenter slide 2: click "Run the attack live"; the requests arrive one by one and get stopped | "We put each client's box behind a wall. Watch: one helper asks for another client's box. The wall says no. Every time." |
| 0:40–1:02 | 4. Hiding the names | Presenter slide 3: yellow highlights and the orange underline appear, then click "De-identify" and the placeholders pop in | "To learn from old cases, we hide everything that says who someone is: their name, their company, their numbers. Even a sneaky clue like 'the only person who won this prize twice'. The lesson stays. The person disappears." |
| 1:02–1:20 | 5. Does it work? | Presenter slide 4: bars fill | "Simple rules miss most of the sneaky clues. Our own small AI, trained on River, caught 20 out of 20 on a test it had never seen. As good as the big AI models." |
| 1:20–1:32 | 6. Who helped | Presenter slide 5 (Built on) | "GBrain builds the walls. River trains our AI. Memorable remembers the lessons. QM gives every client their own room." |
| 1:32–1:38 | 7. The end | Presenter slide 6 | "Remember the lesson. Wall off the secret." |

Numbers used: blind set (40 cases written by a different AI that never saw our data): River-tuned 20/20 caught; Claude 19/20; patterns 12/20.
