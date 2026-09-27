"""Live wall attack: the chen matter agent tries to read the delmarva matter.

Run: uv run python walls/attack.py      (exits non-zero on any FAIL)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from walls.client import Client  # noqa: E402

GREEN, RED, BOLD, RESET = "\033[32m", "\033[31m", "\033[1m", "\033[0m"
results = []


def check(label, ok, detail):
    results.append(ok)
    tag = f"{GREEN}{BOLD}  PASS  {RESET}" if ok else f"{RED}{BOLD}  FAIL  {RESET}"
    print(f"{tag} {BOLD}{label}{RESET}\n         -> {detail}\n")


def sources(hits):
    return sorted({h["source_id"] for h in hits})


def main():
    print(f"\n{BOLD}=== ETHICAL WALL ATTACK: agent for matter 'chen' vs matter 'delmarva' ==={RESET}\n")
    chen = Client("chen")

    hits = chen.search("Harborview")
    check("1. chen searches its OWN fact 'Harborview'",
          len(hits) > 0 and sources(hits) == ["chen"],
          f"{len(hits)} hit(s), sources={sources(hits)}")

    control = Client("delmarva").search("Delmarva")
    check("   control: delmarva's own client CAN find 'Delmarva'",
          len(control) > 0, f"{len(control)} hit(s) -- the data exists behind the wall")

    hits = chen.search("Delmarva")
    check("2. chen searches for 'Delmarva'", len(hits) == 0,
          f"{len(hits)} hit(s), sources={sources(hits)}")

    try:
        hits = chen.search("Delmarva", source_id="__all__")
        check("3. chen asks for ALL sources (source_id='__all__')", len(hits) == 0,
              f"{len(hits)} hit(s) -- clamped to chen's grant")
    except PermissionError as e:
        check("3. chen asks for ALL sources (source_id='__all__')", True, f"refused: {e}")

    page = chen.get_page("session-demand-letter", source_id="delmarva")
    err = page.get("error")
    check("4. chen reads delmarva page 'session-demand-letter' directly",
          err == "permission_denied", f"{err or 'PAGE RETURNED -- WALL BREACHED'}")

    n_fail = results.count(False)
    if n_fail:
        print(f"{RED}{BOLD}##### WALL FAILED: {n_fail}/{len(results)} checks failed #####{RESET}\n")
    else:
        print(f"{GREEN}{BOLD}##### WALL HOLDS: {len(results)}/{len(results)} checks PASS #####{RESET}\n")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
