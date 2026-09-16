# FloodLens Project Instructions

## Scope and source of truth

- The Git repository root is `/storage/projects/floodlens`.
- Read `.agent/index.md` and `.agent/STATE.md` before substantial work, then
  load only the routed knowledge relevant to the task.
- Treat current source, tests, configuration, and migrations as truth above
  generated knowledge or historical conversation notes.
- The repository root is the authoritative resident-facing rebuild. The
  previous root-level research prototype and its synthetic model artifacts
  have been removed and must not be recreated as resident-facing providers.
- Preserve the dirty worktree. Inspect `git status` before edits and do not
  reset, clean, stage, commit, or push unless the user explicitly requests it.

## Product and scientific boundaries

- Describe FloodLens Next as neighbourhood-scale flood awareness, not an
  official warning service, evacuation tool, exact depth prediction, or proof
  that a property will flood.
- Keep the selected 1, 2, or 5 km assessment circle distinct from a watershed.
- Never replace unavailable terrain, basin, river, weather, or labels with
  synthetic resident-facing output.
- An imported region is partial coverage. Return an explicit unavailable or
  outside-coverage state instead of implying worldwide data coverage.
- A nearby river and shared basin are context only; they do not prove
  property-level hydraulic connectivity.
- Do not use the legacy synthetic-trained model artifacts as evidence of
  real-world performance. Future ML requires real labels and event- or
  geography-held-out evaluation.

## Repository workflow

- For substantial tasks, update `.agent/TASK.md`, implement only the agreed
  scope, run relevant verification, inspect the diff, and update durable
  knowledge only after the result is supported.
- Record unrun or blocked checks explicitly. Do not infer runtime readiness
  from source presence.
- Do not download datasets, install packages, run migrations/importers,
  publish, deploy, or perform destructive operations without task-specific
  user authorization.
- Do not expose values from `.env` or other credential-bearing files.

## Knowledge maintenance

- Keep `.agent/STATE.md` limited to current progress, verification, blockers,
  and the next safe work.
- Put stable architecture and boundaries in `.agent/ARCHITECTURE.md`, concise
  operational facts in `.agent/knowledge.md`, API inventory in
  `.agent/endpoints.json`, and relationships in `.agent/graph.json`.
- Create `.agent/hardware.json` only after physical hardware integration exists
  in current source or verified hardware documentation.
- Treat `.agent/previous_conversations/` as historical context with lower
  reliability than current code and configuration.
