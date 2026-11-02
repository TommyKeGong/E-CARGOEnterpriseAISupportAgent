# Codex Repository Instructions

This repository implements the **E-CARGO Knowledge Agent**: an agentic RAG research assistant for E-CARGO and Role-Based Collaboration (RBC). Before modifying code, read `.agents/skills/enterprise-ai-support-agent/SKILL.md` and applicable files in `references/`. The directory name is retained for continuity; its contents define the E-CARGO project.

## Every task

- Check `PROJECT_STATE.md`, `DECISIONS.md`, and `git status` before work.
- Preserve the single-agent, two-tool, evidence-grounded academic RAG MVP. Do not implement GMRA solving, experiment execution, optimisation, or arbitrary code execution in the MVP.
- Treat specifications as targets, not proof. Do not invent papers, authors, pages, formulas, experimental results, or E-CARGO conclusions.
- Use only user-provided, authorised, or publicly usable research material. Never add private lab files, unpublished work, or sensitive data to the repository.
- Add/update tests and run relevant checks. Never claim tests passed without execution.
- Update `PROJECT_STATE.md` after meaningful changes with files, commands/results, blockers, and next action.
- Ask before billable AWS operations, public deployment, data deletion, research downloads, or irreversible changes.

## Stable handoff

Before context exhaustion or session end, write the current milestone, changed files, verified commands/results, blockers, pending decisions, and next three steps to `PROJECT_STATE.md`. New sessions begin by reading that file and the project Skill.
