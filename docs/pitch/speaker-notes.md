# Talk track: 6 slides, about 2 minutes, plain words

Open http://localhost:8788/demo/present.html. Arrow keys move. Press `f` for full screen in the browser.

1. **Lawyers can't let AI learn from old cases.**
   "Here's why. The American Bar Association's Formal Opinion 512 warns that an AI tool that learns from one client's files can reveal them in another client's work, even inside the same firm. Using one needs each client's informed consent, and fine print in the engagement letter isn't enough. So today, most firms use AI that forgets everything."

2. **Each client's files stay behind a wall.** Click **Try to break the wall**.
   "This AI helper works for one client. Watch it try to see another client's files." (Wait for the rows.) "Blocked. Nothing found. Every time. The wall held five out of five, live."

3. **Old cases can teach. Who they're about stays hidden.** Let the yellow and the underline appear, then click **Hide who it is**.
   "Yellow is what a simple search finds: names, companies, numbers. The underline is a clue: 'the only researcher to win this prize twice.' That still gives her away. Watch." (Click.) "Names, company, ID number, salary, and the clue, all hidden. Our AI checks again: nothing left gives her away. The lesson stays. The person disappears."

4. **A simple search misses the clues. AI catches them.**
   "A simple word search caught zero of 102 hidden clues. On a brand-new test, written by a different AI that never saw our data, Claude caught 19 of 20. Our own small AI, trained on River, caught 20 of 20. It sometimes flags things that are fine, and that's what we fix next."

5. **Who helped.**
   "GBrain keeps each client in a locked box. River is where we trained our own AI. Memorable remembers what worked, never who it was for. QM gives every case its own room. Superset let us build this with many AI helpers at once."

6. **Learn from every case. Keep every secret.**

## If something fails live
- Wall or hide button does nothing: press it once more. The page shows "shown from the last live run" if it falls back to a recorded result.
- Numbers slide empty: the server isn't running. Start it: `uv run uvicorn wall.server:app --port 8788`.

## Likely questions
- **Does this replace client consent?** No. It makes it easier to ask for: only lessons cross between clients, never who they're about.
- **Why not just search for names?** Slide 4: a word search caught 0 of 102 clues.
- **Where does your AI live?** We trained it on River, and it runs on River. It learned only from made-up examples.
- **Is this real client data?** No. Every person, company and case is made up.
