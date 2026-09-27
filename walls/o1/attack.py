"""Live wall attack between two O-1 beneficiaries: one beneficiary's agent tries to read another's.

Both matters share the firm's attorney (Naomi Castellanos-Reyes) and the same document types
(recommendation-letter, criteria-evidence, cover-letter-excerpt), so the wall has to hold on
source, not on content.

Run: uv run python walls/o1/attack.py [attacker] [target]   (default o1-umeh vs o1-achterberg;
     exits non-zero on any FAIL)
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from walls.client import Client  # noqa: E402

GREEN, RED, BOLD, RESET = "\033[32m", "\033[31m", "\033[1m", "\033[0m"
SHARED_ATTORNEY = "Naomi Castellanos-Reyes"
results = []


def check(label, ok, detail):
    results.append(ok)
    tag = f"{GREEN}{BOLD}  PASS  {RESET}" if ok else f"{RED}{BOLD}  FAIL  {RESET}"
    print(f"{tag} {BOLD}{label}{RESET}\n         -> {detail}\n")


def sources(hits):
    return sorted({h["source_id"] for h in hits})


def facts(matter):
    with open(os.path.join(REPO, "fixtures", "matters", matter, "matter.json")) as f:
        return json.load(f)["facts"]


def main(attacker="o1-umeh", target="o1-achterberg"):
    print(f"\n{BOLD}=== ETHICAL WALL ATTACK: O-1 beneficiary '{attacker}' vs '{target}' ==={RESET}\n")
    own_term = facts(attacker)["orgs"][0].split()[0]   # employer, e.g. "Terraform"
    secret = facts(target)["orgs"][0].split()[0]       # the target's employer, e.g. "Halcyon"
    a_number = next(d for d in facts(target)["distinctive"] if d.startswith("A") and "-" in d)
    agent = Client(attacker)

    hits = agent.search(own_term)
    check(f"1. {attacker} searches its OWN employer '{own_term}'",
          len(hits) > 0 and sources(hits) == [attacker],
          f"{len(hits)} hit(s), sources={sources(hits)}")

    control = Client(target).search(secret)
    check(f"   control: {target}'s own client CAN find its employer '{secret}'",
          len(control) > 0, f"{len(control)} hit(s) -- the data exists behind the wall")

    hits = agent.search(secret)
    check(f"2. {attacker} searches {target}'s employer '{secret}'", len(hits) == 0,
          f"{len(hits)} hit(s), sources={sources(hits)}")

    hits = agent.search(a_number)
    check(f"3. {attacker} searches {target}'s A-number", len(hits) == 0,
          f"{len(hits)} hit(s), sources={sources(hits)}")

    hits = agent.search(SHARED_ATTORNEY)
    check(f"4. {attacker} searches the attorney shared by every O-1 matter",
          sources(hits) == [attacker],
          f"{len(hits)} hit(s), sources={sources(hits)} -- only its own matter")

    try:
        hits = agent.search(secret, source_id="__all__")
        check(f"5. {attacker} asks for ALL sources (source_id='__all__')", len(hits) == 0,
              f"{len(hits)} hit(s) -- clamped to {attacker}'s grant")
    except PermissionError as e:
        check(f"5. {attacker} asks for ALL sources (source_id='__all__')", True, f"refused: {e}")

    page = agent.get_page("recommendation-letter", source_id=target)
    err = page.get("error")
    check(f"6. {attacker} reads {target} page 'recommendation-letter' directly",
          err == "permission_denied", f"{err or 'PAGE RETURNED -- WALL BREACHED'}")

    n_fail = results.count(False)
    if n_fail:
        print(f"{RED}{BOLD}##### WALL FAILED: {n_fail}/{len(results)} checks failed #####{RESET}\n")
    else:
        print(f"{GREEN}{BOLD}##### WALL HOLDS: {len(results)}/{len(results)} checks PASS #####{RESET}\n")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
