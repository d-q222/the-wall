"""Check data/blind.jsonl parses the way the eval runners read it. Prints counts only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_guard import parse_flat_row  # noqa: E402

path = Path(__file__).resolve().parent.parent / "data" / "blind.jsonl"
if not path.exists():
    sys.exit(f"missing {path}")
labels, bad = {"LEAK": 0, "CLEAN": 0}, []
for i, line in enumerate(path.read_text().splitlines(), 1):
    if not line.strip():
        continue
    row = parse_flat_row(json.loads(line))
    if row is None or not row.protected:
        bad.append(i)
    else:
        labels[row.label] += 1
print(f"LEAK {labels['LEAK']}, CLEAN {labels['CLEAN']}, n={sum(labels.values())}; unparseable lines: {bad or 'none'}")
sys.exit(1 if bad else 0)
