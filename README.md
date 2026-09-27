# The Wall — Ethical Wall Brain

Agent memory for small law firms: **compound the how, wall the what.**
Procedures learn across matters; client facts never cross them.

- PRD: `docs/PRD.md`
- Contract and branch ownership: `docs/CONTRACT.md`
- Data pack goes in `data/` (gitignored): `data/README.md`

```sh
uv sync
uv run pytest -q
uv run uvicorn wall.server:app --port 8787
```
