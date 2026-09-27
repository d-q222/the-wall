"""LoRA SFT for the River de-identifier: river/train.py's loop, pointed at
/Users/dqi26/the-wall/.runtime/river-deid/ (rendered data in, state.json out).

    nohup uv run python -m river.deid.train > /Users/dqi26/the-wall/.runtime/river-deid/train.log 2>&1 &
"""

import argparse
from pathlib import Path

from river import train as judge_train

OUT_DIR = Path("/Users/dqi26/the-wall/.runtime/river-deid")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    judge_train.STATE_PATH = OUT_DIR / "state.json"
    judge_train.train(
        data_path=OUT_DIR / "train_rendered.jsonl",
        batch_size=args.batch_size,
        max_steps=args.max_steps,
        ckpt_every=20,
    )
