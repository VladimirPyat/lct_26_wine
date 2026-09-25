---
description: Prune unused domain rule packs during project planning (Planner)
---

# prune-domain-rules

**Role:** @Planner (or user) on bootstrap / when project shape changes.

**Context:** Scan `.cursor/rules/` and `.cursor/agents/` on disk. Optional help: `MANIFEST.md`. Removals → `.trash/` only (`invariants.mdc`). Do **not** maintain a separate always-on pack list. **`.cursor/` is agent-read-only** — after ✅ the **human** moves files (or agent only proposes the list).

**Instruction:**
1. Detect present trees and stack: `src/`, `frontend/`, `tests/`, `alembic/`, `data/presentation/`, `agent_docs/`, manifests (`pyproject.toml`, `frontend/package.json`, …).
2. List `.cursor/rules/*.mdc`. Always keep: `invariants.mdc`, `paths-access.mdc`, `tooling.mdc`. Treat the rest as candidates.
3. Propose keep / disable (reason per file), e.g. no `frontend/` → disable `frontend-*`; no PPTX track → disable `pptx-presentation.mdc`. Optionally same for unused `agents/`.
4. **Warn** the user which files will leave active context; **STOP** for ✅ (or edited list). Do not move before confirmation.
5. After ✅: **human** runs `mkdir -p .trash && mv .cursor/rules/<file>.mdc .trash/` (and confirmed agents). Agent must **not** write/mv under `.cursor/` (hook-blocked). Optionally write the exact shell lines into chat / `agent_docs/drafts/cursor_rules/`.
6. Ensure `paths-access.mdc` / `tooling.mdc` still match the remaining stack — propose edits under `agent_docs/drafts/cursor_rules/`; human copies.
7. Russian summary: kept, to-move-to-trash, path/tooling edit proposals.

**Constraints:**
1. Never `rm`; never disable `invariants.mdc`, `paths-access.mdc`, or `tooling.mdc`.
2. Do not invent packs; only files present on disk (MANIFEST is a hint, not a second inventory).
3. Never modify `.cursor/` from the agent — staging + human copy/mv only.
