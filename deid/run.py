"""Batch de-identification CLI: produces the "clean dataset for training" artifact.

Usage: uv run python -m deid.run in.jsonl out.jsonl [--practice immigration]

Reads {"text", "matter_id"?} rows, writes {"text", "removed", "residual_verdict"}
rows plus a one-line summary (docs, spans removed by kind, residual leaks flagged).
"""

import argparse
import json
from collections import Counter

from wall.contract import DeidentifyRequest
from wall.deid import deidentify


def run(infile: str, outfile: str, practice: str) -> str:
    docs = 0
    spans_by_kind: Counter[str] = Counter()
    residual_leaks = 0

    with open(infile) as fin, open(outfile, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            req = DeidentifyRequest(
                text=row["text"], practice=practice, matter_id=row.get("matter_id")
            )
            resp = deidentify(req)

            docs += 1
            for span in resp.spans:
                spans_by_kind[span.kind] += 1
            verdict = resp.residual.verdict if resp.residual else None
            if verdict == "leak":
                residual_leaks += 1

            fout.write(
                json.dumps(
                    {"text": resp.text, "removed": resp.removed, "residual_verdict": verdict}
                )
                + "\n"
            )

    kinds = ", ".join(f"{k}={v}" for k, v in sorted(spans_by_kind.items()))
    return f"docs={docs} spans_removed=({kinds}) residual_leaks={residual_leaks}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("--practice", default="immigration")
    args = parser.parse_args(argv)

    print(run(args.infile, args.outfile, args.practice))


if __name__ == "__main__":
    main()
