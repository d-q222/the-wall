"""Build the HyperFrames demo composition: narration (macOS say), numbers from results.json, clips.

Usage: python3 tools/video/compose/build.py [--render]
Writes demo/index.html + demo/assets/{audio,clips}; --render also writes the MP4.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE / "demo"
ASSETS = PROJ / "assets"
WALL = Path("/Users/dqi26/the-wall")
RESULTS = WALL / "results" / "results.json"
CLIPS_DIR = WALL / ".runtime" / "video" / "clips"
OUT = WALL / ".runtime" / "video" / "wall-demo-3min.mp4"
VOICE, RATE = "Samantha", "172"
TARGET_TOTAL = 178.0


def scores():
    d = json.loads(RESULTS.read_text())

    def g(det, s):
        return d.get(det, {}).get(s)

    need = [("regex", "hard"), ("prompt_judge", "hard"), ("river_judge", "hard"), ("river_judge", "independent")]
    missing = [f"{a}/{b}" for a, b in need if not g(a, b)]
    if missing:
        sys.exit(f"results.json missing {missing}; refusing to invent numbers")
    return {k: g(*k) for k in need + [("regex", "independent"), ("prompt_judge", "independent")] if g(*k)}


def scenes(s):
    rh, ph, vh = s[("regex", "hard")], s[("prompt_judge", "hard")], s[("river_judge", "hard")]
    vi = s[("river_judge", "independent")]
    return [
        dict(id="hook", kind="title", min=14,
             title="A room full of future <mark>O-1s</mark>.",
             sub="Extraordinary ability. Built out of one person's identity.",
             say="A room full of future O-1s. Extraordinary ability: the visa a lot of founders end up filing for. "
                 "And every petition is built out of one person's identity. Their name, their employer, their salary, their awards."),
        dict(id="problem", kind="title", min=20,
             title="Firms stay safe by using AI that <mark>forgets</mark>.",
             sub="ABA Formal Opinion 512: a self-learning tool that can surface one client's facts in another client's file needs specific informed consent.",
             say="A small immigration firm that has won twenty of these has real know-how in that stack of petitions. "
                 "But A.B.A. Formal Opinion 512 says a self-learning tool that lets one client's facts surface in another client's file needs specific, informed consent. "
                 "So the standard advice is: don't train on client matters. Firms stay safe by using AI that forgets."),
        dict(id="wall", kind="clip", clip=1, shot="wall", min=24, label="The access wall",
             say="So we start with a wall. Every matter agent is scoped to one matter. "
                 "Here, an agent working one beneficiary's petition asks for another beneficiary's file, and then for every source at once. "
                 "It's refused, every time. That's the base layer everything else sits on."),
        dict(id="deid", kind="clip", clip=2, shot="review", min=34, label="De-identify an O-1 exhibit",
             say="Now an O-1 exhibit: a synthetic recommendation letter, never a real client. "
                 "One click, and names, employers, salaries, dates and receipt numbers become typed placeholders. "
                 "A lawyer can still follow the argument. "
                 "Then a judge trained on River reads what's left, and catches what rules miss: "
                 "a sentence with no name and no number that still describes exactly one person. "
                 "That span gets flagged, and redacted too."),
        dict(id="learn", kind="clip", clip=4, shot="training", min=24, label="River learns the firm's rules",
             say="Every firm draws that line a little differently, so River learns the firm's own rules. "
                 "When an attorney corrects a redaction, the correction becomes a training example. "
                 "Retrain, and the next draft comes back cleaner. "
                 "The model improves from the firm's judgment, not from its clients' facts."),
        dict(id="export", kind="clip", clip=3, shot="datasets", min=15, label="A clean training set",
             say="Run the whole binder of past petitions through, and export a clean training set: "
                 "the arguments, the criteria mapping, the shape of a winning case. Not whose case it was."),
        dict(id="score", kind="score", clip=7, shot="scoreboard", min=26, label="The honest scoreboard",
             rows=[("Regex", rh), ("Prompt-only judge", ph), ("River-tuned judge", vh)], indep=vi,
             say=f"Here's the honest scoreboard. On a hard held-out set of {rh['leaks']} paraphrased leaks, "
                 f"regex catches {rh['caught']}. The prompt-only judge catches {ph['caught']}. "
                 f"The River-tuned judge catches {vh['caught']}, with {vh['false_alarms']} false alarms on {vh['clean']} clean drafts. "
                 f"One caveat: that hard set shares a generator with the training data. "
                 f"On {vi['leaks']} independently written leaks, River catches {vi['caught']}, "
                 f"but raises {vi['false_alarms']} false alarms on {vi['clean']} clean drafts. Every number, with its n."),
        dict(id="close", kind="close", min=15,
             title="Compound the how.<br>Wall the <mark>what</mark>.",
             sub="github.com/d-q222/the-wall",
             say="We're not claiming compliance, and the consent duties under 512 remain. "
                 "What we claim is narrower, and checkable: identifiers removed, residual leakage measured, every number with its n. "
                 "Compound the how. Wall the what."),
    ]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def narrate(sc):
    (ASSETS / "audio").mkdir(parents=True, exist_ok=True)
    aiff = ASSETS / "audio" / f"{sc['id']}.aiff"
    wav = ASSETS / "audio" / f"{sc['id']}.wav"
    subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", str(aiff), sc["say"]], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(wav)], check=True)
    aiff.unlink()
    return probe(wav)


def clip_map():
    mf = CLIPS_DIR / "clips.json"
    if not mf.exists():
        return {}
    data = json.loads(mf.read_text())
    items = data if isinstance(data, list) else data.get("clips", [])
    out = {}
    for it in items:
        f = Path(it.get("file", ""))
        m = re.match(r"(\d+)", f.name)
        if not m:
            continue
        mp4 = (CLIPS_DIR / f.name).with_suffix(".mp4")
        if mp4.exists():
            out[int(m.group(1))] = mp4
    return out


def captions(text, start, dur):
    """Split narration into sentence chunks timed by character share."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    chunks = []
    for p in parts:  # break very long sentences at commas
        if len(p) > 110 and ", " in p:
            mid = p.find(", ", len(p) // 3) + 1
            chunks += [p[:mid].strip(), p[mid:].strip()]
        else:
            chunks.append(p)
    merged = []
    for c in chunks:  # fold tiny fragments into their neighbour so no caption flashes by
        if merged and (len(merged[-1]) < 45 or len(c) < 30) and len(merged[-1]) + len(c) < 120:
            merged[-1] += " " + c
        else:
            merged.append(c)
    chunks = merged
    total = sum(len(c) for c in chunks)
    t, out = start, []
    for c in chunks:
        d = dur * len(c) / total
        out.append((round(t, 2), round(d, 2), c.replace("A.B.A.", "ABA")))
        t += d
    return out


def media_html(sc, clips, start, dur):
    n = sc.get("clip")
    if n in clips:
        dst = ASSETS / "clips" / clips[n].name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clips[n], dst)
        wide = " narrow" if sc["kind"] == "score" else ""
        hold = dst.with_suffix(".last.png")  # clips are shorter than scenes: hold on the final frame
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.3", "-i", str(dst), "-frames:v", "1",
                        "-update", "1", str(hold)], check=True)
        vdur = round(min(dur, probe(dst)), 2)
        sc["hold"] = f"assets/clips/{hold.name}"
        return (f'<video id="m-{sc["id"]}" class="clip vframe{wide}" src="assets/clips/{dst.name}" muted playsinline '
                f'data-start="{start}" data-duration="{vdur}"></video>'), "video"
    return (f'<img id="m-{sc["id"]}" class="clip frame-media kb" src="assets/shots/{sc["shot"]}.png" '
            f'data-start="{start}" data-duration="{dur}" alt="">'), "shot"


def score_panel(sc):
    rows = []
    for name, r in sc["rows"]:
        pct = 100 * r["caught"] / r["leaks"]
        rows.append(f'<div class="srow"><div class="sname">{name}</div>'
                    f'<div class="sbar"><div class="sfill" style="--w:{pct:.1f}%"></div></div>'
                    f'<div class="snum">{r["caught"]}<span>/{r["leaks"]}</span></div></div>')
    vh, vi = sc["rows"][-1][1], sc["indep"]
    return (f'<div class="spanel"><h3>Leaks caught, hard held-out set</h3>{"".join(rows)}'
            f'<p class="snote">River-tuned judge false alarms: {vh["false_alarms"]}/{vh["clean"]} clean drafts. '
            f'The hard set shares a generator with training.</p>'
            f'<h3 class="h3b">Independently written set</h3>'
            f'<div class="srow"><div class="sname">River-tuned judge</div>'
            f'<div class="sbar"><div class="sfill" style="--w:{100*vi["caught"]/vi["leaks"]:.1f}%"></div></div>'
            f'<div class="snum">{vi["caught"]}<span>/{vi["leaks"]}</span></div></div>'
            f'<p class="snote">False alarms: <b>{vi["false_alarms"]}/{vi["clean"]}</b> clean drafts. n = {vi["n"]}.</p></div>')


def build():
    s = scores()
    scs = scenes(s)
    clips = clip_map()
    for sc in scs:
        sc["audio"] = narrate(sc)
        sc["dur"] = max(sc["min"], sc["audio"] + 1.6)
    extra = TARGET_TOTAL - sum(sc["dur"] for sc in scs)
    if extra > 0:  # give clip scenes the slack so footage breathes
        cl = [sc for sc in scs if sc["kind"] in ("clip", "score")]
        for sc in cl:
            sc["dur"] += extra / len(cl)
    body, js, t, report = [], [], 0.0, []
    for i, sc in enumerate(scs):
        st, d = round(t, 2), round(sc["dur"], 2)
        a0 = round(st + 0.6, 2)
        body.append(f'<audio id="a-{sc["id"]}" src="assets/audio/{sc["id"]}.wav" data-start="{a0}" '
                    f'data-duration="{sc["audio"]:.2f}"></audio>')
        sid = f's-{sc["id"]}'
        if sc["kind"] in ("title", "close"):
            body.append(f'<section id="{sid}" class="clip scene card {sc["kind"]}" data-start="{st}" data-duration="{d}">'
                        f'<div class="brand">The Wall</div>'
                        f'<h1 class="ttl">{sc["title"]}</h1><p class="sub">{html.escape(sc["sub"])}</p></section>')
            js.append(f'tl.from("#{sid} .ttl", {{opacity:0, y:30, duration:0.9, ease:"power3.out"}}, {st + 0.2});')
            js.append(f'tl.from("#{sid} .sub", {{opacity:0, y:16, duration:0.8, ease:"power2.out"}}, {st + 1.0});')
            js.append(f'tl.from("#{sid} mark", {{backgroundSize:"0% 100%", duration:0.8, ease:"power2.inOut"}}, {st + 1.4});')
            report.append((sc["id"], st, d, "title"))
        else:
            media, how = media_html(sc, clips, st, d)
            wide = "narrow" if sc["kind"] == "score" else ""
            panel = score_panel(sc) if sc["kind"] == "score" else ""
            body.append(f'<section id="{sid}" class="clip scene shotscene" data-start="{st}" data-duration="{d}">'
                        f'<div class="label"><span class="n">{i - 1}</span>{sc["label"]}</div>'
                        + (f'<div class="frame {wide}">{media}</div>' if how == "shot" else
                           f'<div class="frame {wide}"><img class="frame-media" src="{sc["hold"]}" alt=""></div>')
                        + f'{panel}</section>')
            if how == "video":  # HyperFrames: a timed <video> must not sit inside a timed wrapper
                body.append(media)
            js.append(f'tl.from("#{sid} .label", {{opacity:0, x:-24, duration:0.6, ease:"power2.out"}}, {st + 0.1});')
            fr = f"#{sid} .frame" if how == "shot" else f"#{sid} .frame, #m-{sc['id']}"
            js.append(f'tl.from("{fr}", {{opacity:0, y:24, duration:0.8, ease:"power3.out"}}, {st});')
            if how == "shot":
                js.append(f'tl.fromTo("#m-{sc["id"]}", {{scale:1.0}}, {{scale:1.07, duration:{d}, ease:"none"}}, {st});')
            if sc["kind"] == "score":
                js.append(f'tl.from("#{sid} .spanel", {{opacity:0, x:40, duration:0.7, ease:"power2.out"}}, {st + 0.4});')
                js.append(f'tl.from("#{sid} .sfill", {{width:0, duration:1.4, stagger:0.9, ease:"power2.out"}}, {st + 1.5});')
            report.append((sc["id"], st, d, how))
        for cst, cd, text in captions(sc["say"], a0, sc["audio"]):
            body.append(f'<div class="clip cap" data-start="{cst}" data-duration="{cd}"><span>{html.escape(text)}</span></div>')
        t += sc["dur"]
    total = round(t, 2)
    page = (HERE / "template.html").read_text()
    page = page.replace("{{TOTAL}}", str(total)).replace("{{BODY}}", "\n      ".join(body)).replace("{{JS}}", "\n      ".join(js))
    (PROJ / "index.html").write_text(page)
    for r in report:
        print(f"{r[0]:8s} start={r[1]:6.1f} dur={r[2]:5.1f} {r[3]}")
    print(f"total={total}s clips={sorted(clips)}")
    return total


def render():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "HYPERFRAMES_BROWSER_PATH": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
    subprocess.run(["npx", "hyperframes", "render", "-f", "30", "-q", "standard", "-w", "8", "-o", str(OUT)],
                   cwd=PROJ, check=True, env=env)
    print(f"rendered {OUT} {probe(OUT):.1f}s")


if __name__ == "__main__":
    build()
    if "--render" in sys.argv:
        render()
