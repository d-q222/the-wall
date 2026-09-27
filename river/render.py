"""Render judge_train_v2.jsonl (chat messages) into River training data.

Reads the data pack's JSONL (never copied into git) and writes one JSON-per-line
file of renderer-ready training examples to .runtime/river/. Run with:

    uv run python river/render.py
"""

import argparse
import json
from pathlib import Path

from river_client.renderers import TrainOnWhat, get_renderer

DEFAULT_SRC = Path("/Users/dqi26/the-wall/data/judge_train_v2.jsonl")
DEFAULT_OUT = Path(".runtime/river/train_rendered.jsonl")
BASE_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"


def render(src: Path, out: Path, base_model: str = BASE_MODEL) -> int:
    renderer = get_renderer(base_model)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with src.open() as fin, out.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            example = renderer.build_training_example(
                row["messages"], train_on=TrainOnWhat.LAST_ASSISTANT
            )
            datum = example.to_dict()
            fout.write(json.dumps(datum) + "\n")
            n += 1
    return n


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-model", default=BASE_MODEL)
    args = parser.parse_args()

    count = render(args.src, args.out, args.base_model)
    print(f"rendered {count} examples -> {args.out}")
