"""Retrain the River de-identifier with attorney corrections (the self-improving loop).

Retrain set = k3-river-deid's training rows + attorney feedback rows (upsampled so a
handful of corrections is not drowned out). LoRA SFT continues from k3's latest
checkpoint when one exists, else from the base model.

    uv run python -m river.retrain --run      # the training job itself (launch() nohups this)

State: /Users/dqi26/the-wall/.runtime/river-retrain/state.json
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from river.env import load_dotenv
from wall import feedback

BASE_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"
RUNTIME = feedback.RUNTIME
OUT = RUNTIME / "river-retrain"
STATE = OUT / "state.json"
TRAIN = OUT / "train.jsonl"
LOG = OUT / "train.log"
# k3-river-deid's outputs; override if k3 writes elsewhere.
K3_DATA = Path(os.environ.get("K3_DEID_DATA", RUNTIME / "river-deid" / "train.jsonl"))
K3_STATE = Path(os.environ.get("K3_DEID_STATE", RUNTIME / "river-deid" / "state.json"))
FEEDBACK_UPSAMPLE = 4
MAX_BASE_ROWS = 200
REPO = Path(__file__).resolve().parent.parent


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _base_rows() -> list[dict]:
    if not K3_DATA.exists():
        return []
    rows = [json.loads(line) for line in K3_DATA.read_text().splitlines() if line.strip()]
    random.Random(0).shuffle(rows)
    return rows[:MAX_BASE_ROWS]


def start_checkpoint() -> str | None:
    """Continue from our own last retrain if it finished, else from k3's checkpoint."""
    ours = _read_json(STATE)
    if ours.get("status") == "done" and ours.get("checkpoint"):
        return ours["checkpoint"]
    return _read_json(K3_STATE).get("checkpoint_path")


def plan() -> dict:
    n_feedback = len(feedback.load())
    n_base = len(_base_rows())
    return {
        "n_feedback": n_feedback,
        "n_base": n_base,
        "n_examples": n_base + n_feedback * FEEDBACK_UPSAMPLE,
        "from_checkpoint": start_checkpoint(),
        "base_model": BASE_MODEL,
    }


def state() -> dict:
    s = _read_json(STATE)
    pid = s.get("pid")
    if s.get("status") == "running" and pid:
        try:
            os.kill(pid, 0)
        except OSError:
            s["status"] = "failed"
            s.setdefault("error", "training process exited without finishing; see train.log")
    return s


def _write_state(**fields) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = _read_json(STATE)
    s.update(fields)
    STATE.write_text(json.dumps(s, indent=2))


def build_set() -> tuple[int, int]:
    fb = feedback.to_training_examples()
    rows = _base_rows() + fb * FEEDBACK_UPSAMPLE
    random.Random(1).shuffle(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    with TRAIN.open("w") as f:
        for r in rows:
            f.write(json.dumps({"messages": r["messages"]}) + "\n")
    return len(rows), len(fb)


def launch() -> dict:
    """Build the retrain set and start the River job in the background (nohup)."""
    current = state()
    if current.get("status") == "running":
        return {k: current.get(k) for k in ("job", "checkpoint", "n_examples", "n_feedback", "status")}
    n_examples, n_feedback = build_set()
    if n_feedback == 0:
        raise ValueError("no attorney corrections recorded yet")
    job = f"k2-deid-retrain-{int(time.time())}"
    from_ckpt = start_checkpoint()
    STATE.write_text("{}")
    _write_state(
        job=job, status="starting", n_examples=n_examples, n_feedback=n_feedback,
        from_checkpoint=from_ckpt, checkpoint=None, started_at=time.time(),
    )
    with LOG.open("w") as log:
        proc = subprocess.Popen(
            ["nohup", sys.executable, "-m", "river.retrain", "--run", "--job", job],
            cwd=REPO, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    _write_state(pid=proc.pid, status="running")
    return {"job": job, "checkpoint": from_ckpt, "n_examples": n_examples,
            "n_feedback": n_feedback, "status": "running"}


def run(job: str, batch_size: int = 8, lr: float = 1e-4, lora_rank: int = 16) -> None:
    import river_client as river
    from river_client.renderers import TrainOnWhat, get_renderer

    load_dotenv()
    renderer = get_renderer(BASE_MODEL)
    rows = [json.loads(line) for line in TRAIN.read_text().splitlines() if line.strip()]
    data = [
        renderer.build_training_example(r["messages"], train_on=TrainOnWhat.LAST_ASSISTANT).to_dict()
        for r in rows
    ]
    batches = [data[i : i + batch_size] for i in range(0, len(data), batch_size)]
    _write_state(n_steps_planned=len(batches))
    from_ckpt = _read_json(STATE).get("from_checkpoint")

    client = river.Client(api_key=os.environ["RIVER_API_KEY"])
    try:
        with client.session(job=job) as session:
            model = session.create_model(base_model=BASE_MODEL, lora=river.LoraConfig(rank=lora_rank))
            if from_ckpt:
                try:
                    model.load_weights(from_ckpt, load_optimizer=False)
                except river.RiverError as exc:
                    print(f"could not load {from_ckpt} ({exc}); training from base", flush=True)
                    _write_state(from_checkpoint=None, load_error=str(exc))
            for step, batch in enumerate(batches, start=1):
                fb, _ = model.train_step(batch, lr=lr, loss_fn="cross_entropy", grad_clip_norm=1.0)
                loss = fb.metrics.get("loss_mean")
                print(f"step {step}/{len(batches)} loss_mean={loss}", flush=True)
                _write_state(last_completed_step=step, loss_mean=loss)
            ckpt = model.save_weights("final", mode="inference")
            _write_state(status="done", checkpoint=ckpt.path, checkpoint_step=ckpt.step,
                         finished_at=time.time())
            print(f"retrain done: checkpoint={ckpt.path}", flush=True)
    except Exception as exc:
        _write_state(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--job", default=f"k2-deid-retrain-{int(time.time())}")
    args = parser.parse_args()
    if args.run:
        run(args.job)
    else:
        print(json.dumps(plan(), indent=2))
