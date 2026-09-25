# Cursor rule / hook / agent proposals (staging)

Agents must **not** write directly to `.cursor/` (read-only for agents; hard gate in hooks).

When the user asks to change rules, hooks, or agent defs:

1. Mirror the target path here, e.g. proposed  
   `.cursor/rules/foo.mdc` → `agent_docs/drafts/cursor_rules/rules/foo.mdc`
2. Summarize the diff in chat and point to [`APPLY.md`](APPLY.md).
3. **Human** copies/merges into `.cursor/` manually.

Do not put secrets here.
