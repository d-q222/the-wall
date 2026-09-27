# QM: room per matter, admin-gated skill promotion (FR-11 / FR-12)

QM (github.com/yc-software/qm) is cloned at `/Users/dqi26/the-wall/.runtime/qm`
(gitignored, not committed). Everything here talks to that clone's dev instance over
HTTP; nothing here is QM's own source.

## The auth problem, and how this gets past it

QM's dev sign-in is an email-link broker (Resend/SMTP) -- no good for a local-only box.
Its dev instance has a second, first-class local path we use instead:

- `PORTAL_LOCAL_AUTH_BYPASS` defaults to `"1"` for the dev instance (loopback-only), but
  we don't even need that -- we talk to **core** directly, not the portal.
- Core authenticates API calls with a signed "agent capability" token (the same kind its
  own harness mints for a live turn): a JWS compact HS256 token over
  `{actorId, scopeId, exp, ...}`, signed with `CAPABILITY_SECRET`. `up.sh` sets
  `CAPABILITY_SECRET` and `ADMIN_GRANTS=qm-admin:org_admin` to fixed dev-only values when
  booting, so `qm_client.py` can mint the exact same tokens locally (see its docstring
  for the byte-for-byte format) -- `qm-admin` is a real seeded org admin in *this*
  instance, not a claim to someone else's.

No browser, no email link, no separate human click: QM's admin gate for org-wide
promotion is a claim on the capability token (`liveActor: true`, checked against a real
seeded admin), not a UI confirmation. Setting `liveActor: true` here is honest -- these
scripts are a human running a one-off command, never an unattended cron, which is
exactly what that flag distinguishes.

## Demo steps

```sh
./qm/up.sh                                    # boots QM's dev instance (mock LLM, local Postgres)
uv run python qm/rooms.py                     # creates "delmarva" and "chen" projects (idempotent)
uv run python qm/promote.py <skill.md>        # authors a skill in delmarva, promotes it org-wide,
                                               # and proves it's now visible from chen
./qm/down.sh                                   # stops the dev instance (leaves qm-dev-postgres up)
```

`promote.py` prints each step and a final `FR-11 acceptance: PASS/FAIL` line. It:

1. Creates `<skill.md>`'s content as a skill homed in delmarva's room (QM
   auto-reviews + auto-publishes a freshly created skill -- no separate review step).
2. Confirms a fresh "chen-viewer" principal (no room membership at all) gets a 404 --
   room isolation is QM's default.
3. Promotes it org-wide via `POST /v1/share {type: "skill", toScope: "org"}` as the
   seeded admin.
4. Confirms "chen-viewer" now gets a 200 on the promoted (org-scoped) copy.

Re-running `promote.py` with the *same* skill file name is not idempotent (QM refuses to
recreate a non-archived skill of the same name in the same room) -- use a fresh file, or
archive the old skill first, if you want to demo it twice.

## FR-12 (P2): screening proxy

`qm/proxy.py` is a tiny adapter between QM's `securityScreen` proxy contract
(`{text, hook, metadata} -> {score, threshold}`) and wall's `/judge` contract
(`{current, protected, draft} -> {verdict}`, `wall/server.py`, not ours to edit).
Verified end-to-end against the real judge (`wall.judge`, a live claude-sonnet-5 call):
a delmarva-fact draft scored leak, an unrelated draft scored clean.

```sh
uv run python qm/proxy.py            # serves POST /screen on :8814 (a4-qm's dev port)
```

Point QM's per-project `securityScreen.endpoint` at `http://localhost:8814/screen`, with
`securityScreen.metadata: {current_matter, protected_matters}` set per room -- QM's
proxy payload has no room/matter concept of its own, so that mapping is supplied here,
not guessed.

## What's NOT done

- No Slack surface (`--no-slack`); no real LLM turns (`DEV_INSTANCE_ALLOW_MOCK=1`) --
  neither FR-11 nor FR-12 needs one. `rooms.py`/`promote.py` never touch an LLM.
- No sandbox execution (`qm-sandbox-local:latest` isn't built) -- irrelevant here, we
  never run an agent turn.
- FR-12's `securityScreen.metadata` per-room wiring is documented, not applied inside a
  live QM project (that's a QM deploy-config change, not a Python script) -- the
  adapter itself is verified end-to-end against the real judge.
