"""LoRA SFT for the judge model on River (PRD FR-9).

Two modes:

    uv run python -m river.train --smoke-test
        One tiny client.sample() call against the base model to confirm
        RIVER_API_KEY works before spending GPU time.

    uv run python -m river.train
        Training loop over the already-rendered .runtime/river/train_rendered.jsonl:
        LoRA SFT, checkpointing periodically and at the end. Writes
        job/checkpoint info to .runtime/river/state.json. Meant to be run
        under nohup so it survives the shell exiting:

            nohup uv run python -m river.train > .runtime/river/train.log 2>&1 &

Run as `-m river.train`, not `river/train.py` directly — the script imports
its own package (`river.env`), which only resolves when the repo root is on
sys.path.
"""

import argparse
import json
import os
import time
from pathlib import Path

import river_client as river

from river.env import load_dotenv

load_dotenv()

BASE_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"
DATA_PATH = Path(".runtime/river/train_rendered.jsonl")
STATE_PATH = Path(".runtime/river/state.json")


def _client() -> river.Client:
    return river.Client(api_key=os.environ["RIVER_API_KEY"])


def smoke_test(base_model: str = BASE_MODEL) -> None:
    client = _client()
    try:
        samples = client.sample(
            prompts="Reply with the single word: ok",
            base_model=base_model,
            max_tokens=5,
        )
        text = samples[0].text
        print(f"smoke test ok: base_model={base_model} sample_len={len(text)}")
    finally:
        client.close()


def _load_data(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _batches(data: list[dict], batch_size: int) -> list[list[dict]]:
    return [data[i : i + batch_size] for i in range(0, len(data), batch_size)]


def _write_state(**fields) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    existing.update(fields)
    STATE_PATH.write_text(json.dumps(existing, indent=2))


def train(
    base_model: str = BASE_MODEL,
    data_path: Path = DATA_PATH,
    batch_size: int = 8,
    max_steps: int = 80,
    lr: float = 1e-4,
    ckpt_every: int = 20,
    lora_rank: int = 16,
) -> None:
    data = _load_data(data_path)
    batches = _batches(data, batch_size)[:max_steps]
    n_examples = sum(len(b) for b in batches)
    print(f"training on {n_examples} examples in {len(batches)} steps (batch_size={batch_size})")

    client = _client()
    started = time.monotonic()
    _write_state(
        base_model=base_model,
        status="running",
        started_at=started,
        n_examples=n_examples,
        n_steps_planned=len(batches),
    )
    try:
        with client.session(job="b2-judge-sft") as session:
            model = session.create_model(
                base_model=base_model,
                lora=river.LoraConfig(rank=lora_rank),
            )
            ckpt = None
            for step, batch in enumerate(batches, start=1):
                fb, opt = model.train_step(
                    batch, lr=lr, loss_fn="cross_entropy", grad_clip_norm=1.0
                )
                elapsed = time.monotonic() - started
                print(
                    f"step {step}/{len(batches)}  model.step={model.step}  "
                    f"loss_mean={fb.metrics.get('loss_mean')}  "
                    f"grad_norm={opt.metrics.get('grad_norm')}  elapsed={elapsed:.0f}s",
                    flush=True,
                )
                if step % ckpt_every == 0:
                    ckpt = model.save_weights(f"step_{step:04d}", mode="inference")
                    _write_state(
                        checkpoint_path=ckpt.path,
                        checkpoint_step=ckpt.step,
                        checkpoint_type=ckpt.checkpoint_type,
                        last_completed_step=step,
                    )

            ckpt = model.save_weights("final", mode="inference")
            _write_state(
                checkpoint_path=ckpt.path,
                checkpoint_step=ckpt.step,
                checkpoint_type=ckpt.checkpoint_type,
                last_completed_step=len(batches),
                status="done",
                finished_at=time.monotonic(),
                elapsed_seconds=time.monotonic() - started,
            )
            print(f"training done: checkpoint={ckpt.path} step={ckpt.step}")
    except river.RiverError as exc:
        _write_state(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--ckpt-every", type=int, default=20)
    parser.add_argument("--lora-rank", type=int, default=16)
    args = parser.parse_args()

    if args.smoke_test:
        smoke_test(args.base_model)
    else:
        train(
            base_model=args.base_model,
            data_path=args.data,
            batch_size=args.batch_size,
            max_steps=args.max_steps,
            lr=args.lr,
            ckpt_every=args.ckpt_every,
            lora_rank=args.lora_rank,
        )
