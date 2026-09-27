# Demo video: 3-minute script

Working title: **Train on your firm's O-1 petitions without training on your clients.**
Length: 2:55–3:05. 1920×1080, 30 fps. Light theme (docs/DESIGN.md). Captions always on.
Every number on screen is read from `results/results.json` at render time and shown with n.
Claims follow `docs/pitch/claims.md` exactly.

| Time | Beat | On screen | Voice-over |
|---|---|---|---|
| 0:00–0:12 | Hook | Title card on paper white; a petition binder with exhibit tabs (generated B-roll if available, else Present cover) | "Every O-1 petition a firm has won is a playbook. Each one is also one person's file." |
| 0:12–0:32 | Problem | Present beat 1: ABA Formal Opinion 512 line | "ABA Formal Opinion 512 says a tool that learns from one client can't carry their facts into another client's work without informed consent. So today, small firms stay safe by using AI that forgets." |
| 0:32–0:40 | Promise | Title card: "Compound the how. Wall the what." | "We built AI that remembers the argument and walls off the person." |
| 0:40–1:05 | The wall (GBrain) | Access wall screen: Chen's agent asks for Delmarva's file; every request hits the wall; "Wall held 5/5" | "Each matter lives in its own GBrain source with its own read-only credentials. Here Chen's agent asks for everything, including another client's file. GBrain refuses. Permissions enforce the wall, not the prompt." |
| 1:05–1:40 | De-identify an O-1 exhibit | Review screen: o1-umeh recommendation letter; identifiers highlight, then collapse into typed placeholders; inspector groups them; judge verdict lands | "To learn from past petitions, we de-identify them. Names, employers, A-numbers, USCIS receipts, salaries become consistent placeholders, so the argument survives and the person doesn't. Then a model judge reads what's left for anything that still points to one person." |
| 1:40–2:05 | River learns the firm's rules | Model screen: de-identifier checkpoint, training examples by kind, an attorney correction, "Retrain with N corrections" | "The de-identifier is a model we trained on River, on this firm's own policy. When an attorney marks a miss, that correction becomes a training example, and River retrains. The firm's de-identifier gets better every week." |
| 2:05–2:20 | Clean dataset | Datasets screen: De-identify all, rows complete, Export training JSONL | "The output is a training set: every petition de-identified and checked, flagged ones held back." |
| 2:20–2:45 | Honest scoreboard | Evaluation screen | "Here's how the detectors compare. Pattern matching catches zero of 102 paraphrased leaks. On independent test sets, model judges catch 97 to 100 of 100. Our small River-tuned judge matches Claude on recall, but it flags more clean drafts, and calibrating that is next. The blind set was written by a different model family that never saw our data." |
| 2:45–2:55 | Built on | Built-on screen: GBrain, River, Memorable, QM | "GBrain holds the walls. River trains the models we own. Memorable keeps scrubbed procedures. QM gives every matter its own room and gates what crosses between them." |
| 2:55–3:02 | Close | "Compound the how. Wall the what." + github.com/d-q222/the-wall | "Compound the how. Wall the what." |

Numbers to verify before rendering (fill from results.json, never from memory): hard set regex 0/102; independent set per detector (n=100 leaks / 100 clean); blind set per detector (n=40) if scored.
