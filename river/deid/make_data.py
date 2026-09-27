"""Build River SFT data for the policy-driven de-identifier (wall/river_deid.py).

Sources: paragraphs of the o1-achterberg and o1-umeh fixtures (o1-duarte and
every other o1-* matter are held out for evals/deid) plus synthetic O-1
passages about invented people, written by Claude. Labels come from Claude
reading the firm policy; every label must be an exact substring of its passage
or it is dropped. Writes messages rows and rendered rows to
/Users/dqi26/the-wall/.runtime/river-deid/.

    uv run python -m river.deid.make_data --n-synthetic 420
"""

import argparse
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from river.env import load_dotenv
from wall.river_deid import BASE_MODEL, KINDS, system_prompt, valid_spans

load_dotenv()

OUT_DIR = Path("/Users/dqi26/the-wall/.runtime/river-deid")
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "matters"
TRAIN_MATTERS = ["o1-achterberg", "o1-umeh"]
MODEL = os.environ.get("WALL_LLM_MODEL", "claude-sonnet-5")

STYLES = [
    "a recommendation letter paragraph from a named expert",
    "a criteria-evidence paragraph citing an award and its year",
    "a cover-letter paragraph naming the petitioner employer and salary",
    "a paragraph about published articles and press coverage with outlet names",
    "a paragraph with a paraphrased quasi-identifier (a unique 'youngest/first/only' role, a named ranking list) and no proper names",
    "a paragraph of generic O-1 legal argument about the extraordinary-ability standard with NO identifiers",
    "an exhibit list paragraph mixing exhibit structure with receipt numbers, A-numbers or passport numbers",
    "a paragraph about judging the work of others on a named panel, with the panel's distinctive role",
]


def _client() -> anthropic.Anthropic:
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    return anthropic.Anthropic(
        default_headers={"anthropic-workspace-id": ws} if ws else None, max_retries=4
    )


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if b.type == "text")


def _json(text: str):
    start = min(i for i in (text.find("["), text.find("{")) if i >= 0)
    return json.loads(text[start : max(text.rfind("]"), text.rfind("}")) + 1])


def label(client, passage: str, hint: str = "") -> list[dict]:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt("immigration"),
        messages=[{"role": "user", "content": passage + (f"\n\n(Known matter facts: {hint})" if hint else "")}],
    )
    return valid_spans(passage, _json(_text(msg)).get("spans"))


def synth_batch(client, seed: int) -> list[str]:
    style = STYLES[seed % len(STYLES)]
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": (
            "Write 8 distinct passages (2-5 sentences each) from US O-1 visa petition "
            f"materials. Each should be {style}. Invent every person, company, award, "
            "number and outlet; use varied fields (science, arts, business, athletics, "
            "tech) and varied nationalities. Never use real people. "
            f"Variation seed {seed}. Reply with a JSON list of strings only."
        )}],
    )
    return [p for p in _json(_text(msg)) if isinstance(p, str)]


def _try(fn, *args, default=None):
    try:
        return fn(*args)
    except Exception as exc:  # drop batches/rows the model fails on
        print(f"{fn.__name__} failed: {type(exc).__name__}: {exc}"[:300], flush=True)
        return default


def fixture_passages() -> list[tuple[str, str]]:
    out = []
    for matter in TRAIN_MATTERS:
        facts = json.loads((FIXTURES / matter / "matter.json").read_text())["facts"]
        hint = "; ".join(v for vals in facts.values() for v in vals)
        for doc in sorted((FIXTURES / matter).glob("*.md")):
            for para in doc.read_text().split("\n\n"):
                if len(para.split()) >= 12:
                    out.append((para.strip(), hint))
    return out


def main(n_synthetic: int, workers: int) -> None:
    client = _client()
    with ThreadPoolExecutor(workers) as pool:
        batches = list(pool.map(lambda s: _try(synth_batch, client, s, default=[]), range((n_synthetic + 7) // 8)))
    passages = [(p, "") for b in batches for p in b][:n_synthetic] + fixture_passages()
    print(f"passages: {len(passages)}", flush=True)

    def safe_label(item):
        return item[0], _try(label, client, *item)

    with ThreadPoolExecutor(workers) as pool:
        labelled = [r for r in pool.map(safe_label, passages) if r[1] is not None]

    random.Random(0).shuffle(labelled)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from river_client.renderers import TrainOnWhat, get_renderer

    renderer = get_renderer(BASE_MODEL)
    n_spans = n_empty = 0
    with (OUT_DIR / "train.jsonl").open("w") as fm, (OUT_DIR / "train_rendered.jsonl").open("w") as fr:
        for passage, spans in labelled:
            n_spans += len(spans)
            n_empty += not spans
            messages = [
                {"role": "system", "content": system_prompt("immigration")},
                {"role": "user", "content": passage},
                {"role": "assistant", "content": json.dumps({"spans": spans})},
            ]
            fm.write(json.dumps({"messages": messages}) + "\n")
            ex = renderer.build_training_example(messages, train_on=TrainOnWhat.LAST_ASSISTANT)
            fr.write(json.dumps(ex.to_dict()) + "\n")
    kinds = {k: 0 for k in KINDS}
    for _, spans in labelled:
        for s in spans:
            kinds[s["kind"]] += 1
    print(json.dumps({"rows": len(labelled), "dropped": len(passages) - len(labelled),
                      "spans": n_spans, "empty_rows": n_empty, "kinds": kinds}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-synthetic", type=int, default=420)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    main(args.n_synthetic, args.workers)
