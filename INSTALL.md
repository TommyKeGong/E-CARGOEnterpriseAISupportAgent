# Install in a Codex Project

Copy the **entire skill folder** into your project at:

```text
<repo>/
  AGENTS.md
  PROJECT_STATE.md
  DECISIONS.md
  .agents/
    skills/
      enterprise-ai-support-agent/
        SKILL.md
        references/
          architecture.md
          contracts.md
          roadmap.md
```

Recommended: copy `SKILL.md` and `references/` into `.agents/skills/enterprise-ai-support-agent/`, while copying `AGENTS.md`, `PROJECT_STATE.md`, `DECISIONS.md` to the repository root. `INSTALL.md` is informational.

## First Codex prompt
```text
Read AGENTS.md, .agents/skills/enterprise-ai-support-agent/SKILL.md,
all three reference documents, PROJECT_STATE.md, and DECISIONS.md.
Do not write application code yet. Inspect the actual repository and
report Phase 0 readiness, missing prerequisites, and an exact first
implementation step. Preserve all fixed architecture decisions.
```

## Handoff prompt before context exhaustion
```text
Update PROJECT_STATE.md with current phase, changed files, exact tests
and outputs, unresolved issues, and next three actions. Update
DECISIONS.md for any approved architecture deviations. Do not claim
unexecuted tests passed. Then give me a short restart prompt.
```

## New session restart prompt
```text
Resume this project. First read AGENTS.md, the project skill and its
references, PROJECT_STATE.md, and DECISIONS.md; inspect git status.
Summarize verified progress and resume the next unfinished milestone.
```

Note: Skill files provide durable **instructions and design context**, but cannot automatically save hidden model context. The agent must persist progress in PROJECT_STATE.md before compaction or session end.
